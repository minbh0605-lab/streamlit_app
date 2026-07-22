import streamlit as st
import pandas as pd
import pydeck as pdk
import math

# ----------------------------
# 페이지 설정
# ----------------------------
st.set_page_config(
    page_title="서울시 공영주차장 안내",
    page_icon="🅿️",
    layout="wide"
)

st.title("🅿️ 서울시 공영주차장 안내 시스템")

st.write("""
CSV 파일을 업로드하면
- 자치구별 검색
- 무료/유료 검색
- 예상 주차요금 계산
- 가장 저렴한 주차장 추천
- 지도 표시
를 제공합니다.
""")

uploaded_file = st.file_uploader(
    "서울시 공영주차장 CSV 업로드",
    type="csv"
)

if uploaded_file is not None:

    # --------------------------------
    # cp949 인코딩
    # --------------------------------
    df = pd.read_csv(
        uploaded_file,
        encoding="cp949"
    )

    st.success("데이터 업로드 완료")

    # --------------------------------
    # 자치구 추출
    # --------------------------------
    df["자치구"] = (
        df["주소"]
        .astype(str)
        .str.split()
        .str[0]
    )

    # 숫자형 변환
    num_cols = [
        "기본 주차 요금",
        "기본 주차 시간(분 단위)",
        "추가 단위 요금",
        "추가 단위 시간(분 단위)",
        "위도",
        "경도"
    ]

    for col in num_cols:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    st.subheader("데이터 미리보기")
    st.dataframe(df.head())

    # ----------------------------
    # 사이드바
    # ----------------------------

    st.sidebar.title("검색 조건")

    gu_list = ["전체"] + sorted(
        df["자치구"].dropna().unique().tolist()
    )

    gu = st.sidebar.selectbox(
        "자치구",
        gu_list
    )

    parking_type = st.sidebar.selectbox(
        "주차장 종류",
        ["전체"] +
        sorted(
            df["주차장 종류명"]
            .dropna()
            .unique()
            .tolist()
        )
    )

    fee_type = st.sidebar.selectbox(
        "무료 / 유료",
        [
            "전체",
            "무료",
            "유료"
        ]
    )

    parking_time = st.sidebar.slider(
        "예상 주차시간(분)",
        30,
        720,
        60,
        step=10
    )

    # ----------------------------
    # 필터
    # ----------------------------

    result = df.copy()

    if gu != "전체":
        result = result[
            result["자치구"] == gu
        ]

    if parking_type != "전체":
        result = result[
            result["주차장 종류명"] == parking_type
        ]

    if fee_type != "전체":
        result = result[
            result["유무료구분명"] == fee_type
        ]
        # ----------------------------
    # 예상 요금 계산 함수
    # ----------------------------

    def calc_fee(row, minute):

        # 무료 주차장
        if row["유무료구분명"] == "무료":
            return 0

        basic_fee = row["기본 주차 요금"]
        basic_time = row["기본 주차 시간(분 단위)"]

        add_fee = row["추가 단위 요금"]
        add_time = row["추가 단위 시간(분 단위)"]

        # 결측치 처리
        if pd.isna(basic_fee):
            return 0

        if pd.isna(basic_time):
            basic_time = 0

        if pd.isna(add_fee):
            add_fee = 0

        if pd.isna(add_time):
            add_time = 0

        # 기본시간 이내
        if minute <= basic_time:
            return basic_fee

        # 추가요금 없는 경우
        if add_time == 0:
            return basic_fee

        extra_time = minute - basic_time

        extra_count = math.ceil(extra_time / add_time)

        total = basic_fee + extra_count * add_fee

        return total


    # ----------------------------
    # 예상요금 계산
    # ----------------------------

    result["예상요금"] = result.apply(
        lambda x: calc_fee(
            x,
            parking_time
        ),
        axis=1
    )

    # ----------------------------
    # 정렬
    # ----------------------------

    result = result.sort_values(
        "예상요금"
    )

    st.subheader("검색 결과")

    show_cols = [
        "주차장명",
        "자치구",
        "주차장 종류명",
        "유무료구분명",
        "기본 주차 요금",
        "예상요금"
    ]

    st.dataframe(
        result[show_cols],
        use_container_width=True
    )

    # ----------------------------
    # 가장 저렴한 주차장
    # ----------------------------

    if len(result) > 0:

        cheapest = result.iloc[0]

        st.success("💰 가장 저렴한 주차장")

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "주차장",
            cheapest["주차장명"]
        )

        c2.metric(
            "예상요금",
            f'{int(cheapest["예상요금"]):,}원'
        )

        c3.metric(
            "종류",
            cheapest["주차장 종류명"]
        )

        st.write("### 상세 정보")

        st.write("주소 :", cheapest["주소"])

        if "평일 운영 시작시각(HHMM)" in result.columns:
            st.write(
                "평일 운영시간 :",
                cheapest["평일 운영 시작시각(HHMM)"],
                "~",
                cheapest["평일 운영 종료시각(HHMM)"]
            )

        if "1일 최대요금" in result.columns:
            st.write(
                "1일 최대요금 :",
                cheapest["1일 최대요금"]
            )
    else:

        st.warning("검색 결과가 없습니다.")
        # ----------------------------
    # 지도 표시
    # ----------------------------

    st.subheader("🗺️ 주차장 위치")

    map_df = result.dropna(
        subset=["위도", "경도"]
    ).copy()

    if len(map_df) > 0:

        # 무료=초록 / 유료=빨강
        def color(row):
            if row["유무료구분명"] == "무료":
                return [0, 200, 0, 180]
            return [255, 0, 0, 180]

        map_df["color"] = map_df.apply(
            color,
            axis=1
        )

        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position='[경도, 위도]',
            get_fill_color="color",
            get_radius=80,
            pickable=True
        )

        view = pdk.ViewState(
            latitude=map_df["위도"].mean(),
            longitude=map_df["경도"].mean(),
            zoom=11
        )

        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={
                "html": """
                <b>{주차장명}</b><br/>
                주소 : {주소}<br/>
                종류 : {주차장 종류명}<br/>
                구분 : {유무료구분명}<br/>
                예상요금 : {예상요금}원
                """
            }
        )

        st.pydeck_chart(deck)

        else:

        st.warning("지도에 표시할 위치 정보가 없습니다.")

    # ----------------------------
    # 무료 주차장
    # ----------------------------

    st.subheader("🟢 무료 주차장")

    free_df = result[
        result["유무료구분명"] == "무료"
    ]

    if len(free_df) > 0:

        st.dataframe(
            free_df[
                [
                    "주차장명",
                    "주소",
                    "주차장 종류명"
                ]
            ],
            use_container_width=True
        )

        else:

        st.info("무료 주차장이 없습니다.")

    # ----------------------------
    # 유료 주차장
    # ----------------------------

    st.subheader("🔴 유료 주차장")

    pay_df = result[
        result["유무료구분명"] == "유료"
    ]

    if len(pay_df) > 0:

        st.dataframe(
            pay_df[
                [
                    "주차장명",
                    "주소",
                    "기본 주차 요금",
                    "예상요금"
                ]
            ],
            use_container_width=True
        )

        else:

        st.info("유료 주차장이 없습니다.")

    # ----------------------------
    # 통계
    # ----------------------------

    st.subheader("📊 검색 결과 통계")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "전체",
        len(result)
    )

    c2.metric(
        "무료",
        len(free_df)
    )

    c3.metric(
        "유료",
        len(pay_df)
    )

    if len(pay_df) > 0:

        avg_fee = pay_df["예상요금"].mean()

        st.metric(
            "평균 예상요금",
            f"{avg_fee:,.0f}원"
        )

    # ----------------------------
    # CSV 다운로드
    # ----------------------------

    csv = result.to_csv(
        index=False,
        encoding="cp949"
    )

    st.download_button(
        label="📥 검색 결과 다운로드",
        data=csv.encode("cp949"),
        file_name="parking_result.csv",
        mime="text/csv"
    )
# ----------------------------
# 운영시간 정보
# ----------------------------

st.subheader("🕒 운영시간")

if len(result) > 0:

    show = [
        "주차장명"
    ]

    if "평일 운영 시작시각(HHMM)" in result.columns:
        show.append("평일 운영 시작시각(HHMM)")

    if "평일 운영 종료시각(HHMM)" in result.columns:
        show.append("평일 운영 종료시각(HHMM)")

    if "토요일 운영 시작시각(HHMM)" in result.columns:
        show.append("토요일 운영 시작시각(HHMM)")

    if "토요일 운영 종료시각(HHMM)" in result.columns:
        show.append("토요일 운영 종료시각(HHMM)")

    if "공휴일 운영 시작시각(HHMM)" in result.columns:
        show.append("공휴일 운영 시작시각(HHMM)")

    if "공휴일 운영 종료시각(HHMM)" in result.columns:
        show.append("공휴일 운영 종료시각(HHMM)")

    st.dataframe(
        result[show],
        use_container_width=True
    )

# ----------------------------
# 일 최대요금
# ----------------------------

if "1일 최대요금" in result.columns:

    st.subheader("💰 1일 최대요금")

    st.dataframe(
        result[
            [
                "주차장명",
                "1일 최대요금"
            ]
        ],
        use_container_width=True
    )

# ----------------------------
# 월 정기권
# ----------------------------

if "월 정기권 금액" in result.columns:

    st.subheader("📅 월 정기권")

    st.dataframe(
        result[
            [
                "주차장명",
                "월 정기권 금액"
            ]
        ],
        use_container_width=True
    )

# ----------------------------
# 검색 결과 개수
# ----------------------------

st.markdown("---")

st.info(
    f"검색된 주차장 수 : {len(result)}개"
)

# ----------------------------
# 원본 데이터 보기
# ----------------------------

with st.expander("원본 데이터 보기"):

    st.dataframe(
        df,
        use_container_width=True
    )

# ----------------------------
# 앱 정보
# ----------------------------

st.markdown("---")

st.caption("서울시 공영주차장 정보 서비스")

st.caption("CSV : 서울 열린데이터광장")

st.caption("Developed with Streamlit")

# ----------------------------
# 예외 처리
# ----------------------------

    else:

    st.warning("CSV 파일을 업로드하세요.")

import streamlit as st
import pandas as pd
import pydeck as pdk
import math

st.set_page_config(
    page_title="서울 주차장 정보",
    page_icon="🅿️",
    layout="wide"
)

st.title("🅿️ 서울 주차장 정보 시스템")
st.write("CSV 파일을 업로드하여 주차장 정보를 확인하세요.")

uploaded_file = st.file_uploader(
    "주차장 CSV 업로드",
    type=["csv"]
)

if uploaded_file is not None:

    df = pd.read_csv(uploaded_file, encoding="cp949")

    st.success("데이터 업로드 완료!")

    st.subheader("데이터 미리보기")
    st.dataframe(df)

    st.sidebar.header("검색 조건")

    gu = st.sidebar.selectbox(
        "자치구 선택",
        ["전체"] + sorted(df["자치구"].unique().tolist())
    )

    parking_type = st.sidebar.selectbox(
        "주차장 종류",
        ["전체"] + sorted(df["주차장종류"].unique().tolist())
    )

    pay_type = st.sidebar.selectbox(
        "요금 구분",
        ["전체", "무료", "유료"]
    )

    parking_time = st.sidebar.number_input(
        "예상 주차 시간(분)",
        min_value=0,
        value=60
    )

    result = df.copy()

    if gu != "전체":
        result = result[result["자치구"] == gu]

    if parking_type != "전체":
        result = result[result["주차장종류"] == parking_type]

    if pay_type == "무료":
        result = result[result["무료여부"] == "무료"]

    elif pay_type == "유료":
        result = result[result["무료여부"] == "유료"]

    def calc_fee(row, minute):

        if row["무료여부"] == "무료":
            return 0

        basic_time = row["기본시간"]
        basic_fee = row["기본요금"]
        add_time = row["추가시간"]
        add_fee = row["추가요금"]

        if minute <= basic_time:
            return basic_fee

        extra = minute - basic_time

        count = math.ceil(extra / add_time)

        return basic_fee + count * add_fee


    result["예상요금"] = result.apply(
        lambda x: calc_fee(x, parking_time),
        axis=1
    )

    st.subheader("검색 결과")

    st.dataframe(result)

    if len(result) > 0:

        cheapest = result.sort_values("예상요금").iloc[0]

        st.success("가장 저렴한 주차장")

        col1, col2 = st.columns(2)

        col1.metric("주차장", cheapest["주차장명"])
        col2.metric("예상요금", f'{cheapest["예상요금"]:,}원')

    else:

        st.warning("검색 결과가 없습니다.")
        st.subheader("주차장 위치")

    layer = pdk.Layer(
        "ScatterplotLayer",
        data=result,
        get_position='[경도, 위도]',
        get_radius=80,
        get_fill_color='[255,0,0,180]',
        pickable=True
    )

    view = pdk.ViewState(
        latitude=result["위도"].mean(),
        longitude=result["경도"].mean(),
        zoom=11
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer],
            initial_view_state=view,
            tooltip={
                "text": """
주차장 : {주차장명}

자치구 : {자치구}

종류 : {주차장종류}

예상요금 : {예상요금}원
"""
            }
        )
    )

    st.subheader("무료 주차장")

    free_df = result[result["무료여부"] == "무료"]

    st.dataframe(free_df)

    st.subheader("유료 주차장")

    pay_df = result[result["무료여부"] == "유료"]

    st.dataframe(pay_df)

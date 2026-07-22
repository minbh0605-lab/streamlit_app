import os
import re
import subprocess
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import streamlit as st
from googleapiclient.discovery import build
from wordcloud import WordCloud

# ----------------------------------------------------
# 0. 한글 폰트 자동 설치 함수 (Streamlit Cloud 전용)
# ----------------------------------------------------
@st.cache_resource
def install_korean_font():
    """Streamlit Cloud(Linux) 환경에서 나눔 폰트를 자동으로 설치합니다."""
    try:
        # 리눅스 패키지 관리자로 fonts-nanum 설치
        subprocess.run(["apt-get", "update"], check=True)
        subprocess.run(["apt-get", "install", "-y", "fonts-nanum"], check=True)
        
        # matplotlib 폰트 캐시 삭제
        import matplotlib.font_manager as fm
        fm._rebuild() if hasattr(fm, '_rebuild') else None
    except Exception:
        # 로컬(Windows/Mac) 실행 시 패키지 설치 실패를 무시함
        pass

# 폰트 설치 실행
install_korean_font()

# 페이지 기본 설정
st.set_page_config(
    page_title="유튜브 댓글 분석기",
    page_icon="🎬",
    layout="wide"
)

# ----------------------------------------------------
# 1. API 키 불러오기 (Secrets 우선 -> 없으면 사이드바 입력)
# ----------------------------------------------------
API_KEY = None

# Secrets에 키가 있는지 확인
if "YOUTUBE_API_KEY" in st.secrets:
    API_KEY = st.secrets["YOUTUBE_API_KEY"]
else:
    # Secrets에 없을 경우 사이드바에서 사용자에게 직접 입력받음
    st.sidebar.title("🔑 설정")
    API_KEY = st.sidebar.text_input("YouTube API Key 입력", type="password")
    
    if not API_KEY:
        st.warning("👈 왼쪽 사이드바에 YouTube API Key를 입력하거나 Secrets를 설정해 주세요.")
        st.stop()

# ----------------------------------------------------
# 2. 헬퍼 함수 정의
# ----------------------------------------------------
def extract_video_id(url: str) -> str:
    """유튜브 URL에서 Video ID 추출"""
    regex = r"(?:v=|\/([0-9A-Za-z_-]{11}).*[\?&]v=|^you\.tu\/|embed\/|shorts\/|\/v\/|https?:\/\/(?:www\.)?youtube\.com\/watch\?v=)([^\"&?\/\s]{11})"
    match = re.search(regex, url)
    return match.group(1) if match else None


@st.cache_data(ttl=3600)
def fetch_youtube_comments(video_id: str, max_results: int = 200) -> pd.DataFrame:
    """유튜브 API를 사용해 댓글 수집"""
    try:
        youtube = build("youtube", "v3", developerKey=API_KEY)
        comments = []
        next_page_token = None

        while len(comments) < max_results:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_results - len(comments)),
                pageToken=next_page_token,
                order="relevance"
            )
            response = request.execute()

            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet["authorDisplayName"],
                    "comment": snippet["textOriginal"],
                    "like_count": snippet["likeCount"],
                    "published_at": snippet["publishedAt"]
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        df = pd.DataFrame(comments)
        if not df.empty:
            df["published_at"] = pd.to_datetime(df["published_at"])
            df["length"] = df["comment"].apply(len)
        return df

    except Exception as e:
        st.error(f"댓글 수집 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()


def generate_wordcloud(text: str):
    """시스템에 설치된 나눔고딕 폰트를 이용해 워드클라우드 생성"""
    clean_text = re.sub(r"[^가-힣\s]", "", text)

    # Linux 패키지로 설치되는 나눔고딕 기본 경로 지정
    font_path = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
    
    # 해당 경로에 폰트가 없을 경우 기본 시스템 폰트 탐색
    if not os.path.exists(font_path):
        font_path = None

    wc = WordCloud(
        font_path=font_path,
        background_color="white",
        width=800,
        height=400,
        max_words=100
    ).generate(clean_text)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")
    return fig


# ----------------------------------------------------
# 3. 메인 UI
# ----------------------------------------------------
st.title("🎬 유튜브 댓글 분석기")
st.caption("유튜브 영상의 댓글을 수집하고 다각도로 시각화해 드립니다.")

st.markdown("---")

col_input1, col_input2 = st.columns([3, 1])

with col_input1:
    url_input = st.text_input("유튜브 영상 URL을 입력하세요:", placeholder="https://www.youtube.com/watch?v=...")

with col_input2:
    max_comments = st.number_input("수집할 댓글 수", min_value=10, max_value=1000, value=200, step=50)

if st.button("댓글 분석 시작", type="primary"):
    if not url_input:
        st.warning("유튜브 URL을 입력해 주세요.")
    else:
        video_id = extract_video_id(url_input)
        if not video_id:
            st.error("유효하지 않은 유튜브 URL입니다.")
        else:
            with st.spinner("댓글을 가져오는 중입니다..."):
                df_comments = fetch_youtube_comments(video_id, max_results=max_comments)

            if df_comments.empty:
                st.warning("댓글을 찾을 수 없거나 댓글 창이 비활성화되어 있습니다.")
            else:
                st.success(f"총 {len(df_comments)}개의 댓글을 성공적으로 수집했습니다!")

                # 1. 지표
                col1, col2, col3 = st.columns(3)
                col1.metric("수집된 댓글 수", f"{len(df_comments)}개")
                col2.metric("총 좋아요 수", f"{df_comments['like_count'].sum():,}개")
                col3.metric("평균 댓글 길이", f"{int(df_comments['length'].mean())}자")

                st.markdown("---")

                # 2. 한글 워드 클라우드
                st.subheader("☁️ 워드 클라우드")
                all_text = " ".join(df_comments["comment"].tolist())
                if len(all_text.strip()) > 0:
                    fig_wc = generate_wordcloud(all_text)
                    st.pyplot(fig_wc)
                else:
                    st.info("시각화할 텍스트 데이터가 부족합니다.")

                st.markdown("---")

                # 3. 그래프 (Plotly)
                col_chart1, col_chart2 = st.columns(2)

                with col_chart1:
                    st.subheader("👍 좋아요 상위 댓글 Top 5")
                    top_liked = df_comments.nlargest(5, "like_count")[["author", "like_count", "comment"]]
                    fig_bar = px.bar(
                        top_liked,
                        x="like_count",
                        y="author",
                        orientation="h",
                        hover_data=["comment"],
                        labels={"like_count": "좋아요 수", "author": "작성자"},
                        color="like_count",
                        color_continuous_scale="Viridis"
                    )
                    fig_bar.update_layout(yaxis={"categoryorder": "total ascending"})
                    st.plotly_chart(fig_bar, use_container_width=True)

                with col_chart2:
                    st.subheader("📏 댓글 길이 분포")
                    fig_hist = px.histogram(
                        df_comments,
                        x="length",
                        nbins=20,
                        labels={"length": "글자 수", "count": "댓글 수"},
                        color_discrete_sequence=["#636EFA"]
                    )
                    st.plotly_chart(fig_hist, use_container_width=True)

                # 4. 데이터 표 및 CSV 다운로드
                st.markdown("---")
                st.subheader("📋 전체 댓글 목록")
                st.dataframe(df_comments[["author", "comment", "like_count", "published_at"]], use_container_width=True)

                csv_data = df_comments.to_csv(index=False, encoding="utf-8-sig")
                st.download_button(
                    label="📥 분석 데이터 CSV 다운로드",
                    data=csv_data,
                    file_name=f"youtube_comments_{video_id}.csv",
                    mime="text/csv"
                )

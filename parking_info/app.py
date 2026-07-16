from pathlib import Path

app_code = r'''# app.py
import streamlit as st
import pandas as pd
import pydeck as pdk
import math

st.set_page_config(page_title="서울 공영주차장 정보", layout="wide")
st.title("🅿️ 서울 공영주차장 정보")

uploaded = st.file_uploader("CSV 업로드", type="csv")
if uploaded:
    df = pd.read_csv(uploaded, encoding="cp949")
    df["자치구"] = df["주소"].astype(str).str.split().str[0]

    df["위도"] = pd.to_numeric(df["위도"], errors="coerce")
    df["경도"] = pd.to_numeric(df["경도"], errors="coerce")

    st.sidebar.header("검색")

    gu = st.sidebar.selectbox("자치구", ["전체"] + sorted(df["자치구"].dropna().unique()))
    typ = st.sidebar.selectbox("주차장 종류", ["전체"] + sorted(df["주차장 종류명"].dropna().unique()))
    fee = st.sidebar.selectbox("무료/유료", ["전체","무료","유료"])
    t = st.sidebar.number_input("예상 주차시간(분)", 0, 1440, 60)

    result = df.copy()
    if gu!="전체":
        result=result[result["자치구"]==gu]
    if typ!="전체":
        result=result[result["주차장 종류명"]==typ]
    if fee!="전체":
        result=result[result["유무료구분명"]==fee]

    def calc(row):
        if row["유무료구분명"]=="무료":
            return 0
        bt=row["기본 주차 시간(분 단위)"]
        bf=row["기본 주차 요금"]
        at=row["추가 단위 시간(분 단위)"]
        af=row["추가 단위 요금"]
        if pd.isna(bt) or pd.isna(bf):
            return 0
        if t<=bt:
            return bf
        if pd.isna(at) or at==0 or pd.isna(af):
            return bf
        return bf+math.ceil((t-bt)/at)*af

    result["예상요금"]=result.apply(calc,axis=1)

    st.dataframe(result)

    if not result.empty:
        cheap=result.sort_values("예상요금").iloc[0]
        st.success(f'가장 저렴한 주차장 : {cheap["주차장명"]} ({cheap["예상요금"]:,}원)')
        m=result.dropna(subset=["위도","경도"])
        if not m.empty:
            layer=pdk.Layer("ScatterplotLayer",data=m,get_position='[경도,위도]',
                            get_radius=70,
                            get_fill_color='[0,120,255,180]',
                            pickable=True)
            view=pdk.ViewState(latitude=m["위도"].mean(),
                               longitude=m["경도"].mean(),
                               zoom=11)
            st.pydeck_chart(pdk.Deck(
                layers=[layer],
                initial_view_state=view,
                tooltip={"text":"{주차장명}\n{주소}\n예상요금:{예상요금}원"}
            ))
'''

req = "streamlit\npandas\npydeck\n"

Path("/mnt/data/app.py").write_text(app_code, encoding="utf-8")
Path("/mnt/data/requirements.txt").write_text(req, encoding="utf-8")

print("done")

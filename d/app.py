import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(
    page_title="스마트 주식 분석 & 예측 대시보드",
    page_icon="📈",
    layout="wide"
)

# --- 사이드바 설정 ---
st.sidebar.header("📌 기본 설정")

# 티커 입력 (기본값: Apple)
ticker_symbol = st.sidebar.text_input("기준 종목 티커 입력 (예: AAPL, NVDA, 005930.KS)", value="AAPL")

# 기간 선택
period_options = {"1개월": "1mo", "3개월": "3mo", "6개월": "6mo", "1년": "1y", "5년": "5y"}
selected_period_label = st.sidebar.selectbox("조회 기간", list(period_options.keys()), index=3)
period = period_options[selected_period_label]

# 보조지표 선택
st.sidebar.subheader("📊 기술적 지표")
show_ma = st.sidebar.checkbox("이동평균선 (20일, 60일)", value=True)
show_rsi = st.sidebar.checkbox("RSI 지표 표시", value=True)


# --- 데이터 로드 함수 ---
@st.cache_data(ttl=3600)
def load_stock_data(ticker, period_str):
    stock = yf.Ticker(ticker)
    df = stock.history(period=period_str)
    info = stock.info
    return df, info

try:
    df, info = load_stock_data(ticker_symbol, period)

    if df.empty:
        st.error("데이터를 불러올 수 없습니다. 티커명을 확인해 주세요.")
        st.stop()

    # 종목 이름 및 상단 메트릭
    company_name = info.get("longName", ticker_symbol)
    st.title(f"📈 {company_name} ({ticker_symbol.upper()})")

    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    price_change = current_price - prev_price
    price_change_pct = (price_change / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    price_unit = "$" if not ticker_symbol.endswith((".KS", ".KQ")) else "원"
    
    if price_unit == "$":
        col1.metric("현재가", f"${current_price:.2f}", f"{price_change_pct:+.2f}%")
    else:
        col1.metric("현재가", f"{int(current_price):,}원", f"{price_change_pct:+.2f}%")
        
    col2.metric("52주 최고가", f"{info.get('fiftyTwoWeekHigh', 'N/A')}")
    col3.metric("52주 최저가", f"{info.get('fiftyTwoWeekLow', 'N/A')}")
    col4.metric("PER (주가수익비율)", f"{info.get('trailingPE', 'N/A')}")

    st.markdown("---")

    # --- 탭 구성 ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 차트 분석", 
        "🔮 미래 가격 예측", 
        "⚖️ 종목 비교", 
        "📋 기업 정보"
    ])

    # ==========================================
    # TAB 1: 차트 분석
    # ==========================================
    with tab1:
        rows = 2 if show_rsi else 1
        row_heights = [0.7, 0.3] if show_rsi else [1.0]

        fig = make_subplots(
            rows=rows, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05,
            row_heights=row_heights
        )

        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="주가"
        ), row=1, col=1)

        if show_ma:
            df['MA20'] = df['Close'].rolling(window=20).mean()
            df['MA60'] = df['Close'].rolling(window=60).mean()
            fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], mode='lines', name='MA 20', line=dict(color='orange', width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], mode='lines', name='MA 60', line=dict(color='green', width=1.5)), row=1, col=1)

        if show_rsi:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], mode='lines', name='RSI (14)', line=dict(color='purple', width=1.5)), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)

        fig.update_layout(height=600, xaxis_rangeslider_visible=False, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # TAB 2: 미래 가격 예측 (몬테카를로 시뮬레이션)
    # ==========================================
    with tab2:
        st.subheader("🎲 몬테카를로 시뮬레이션 기반 미래 주가 시나리오")
        st.write("과거 일일 수익률의 평균과 변동성을 이용해 미래 주가의 확률적 궤적을 가상 시뮬레이션합니다.")

        col_p1, col_p2 = st.columns(2)
        sim_days = col_p1.slider("예측할 미래 일수 (Trading Days)", min_value=10, max_value=252, value=60, step=10)
        num_simulations = col_p2.slider("시뮬레이션 횟수", min_value=100, max_value=2000, value=500, step=100)

        log_returns = np.log(1 + df['Close'].pct_change().dropna())
        u = log_returns.mean()
        var = log_returns.var()
        drift = u - (0.5 * var)
        stdev = log_returns.std()

        daily_returns = np.exp(drift + stdev * np.random.normal(size=(sim_days, num_simulations)))
        price_list = np.zeros_like(daily_returns)
        price_list[0] = current_price

        for t in range(1, sim_days):
            price_list[t] = price_list[t - 1] * daily_returns[t]

        fig_sim = go.Figure()
        for i in range(min(num_simulations, 100)):
            fig_sim.add_trace(go.Scatter(y=price_list[:, i], mode='lines', line=dict(width=0.5), opacity=0.3, showlegend=False))

        mean_path = np.mean(price_list, axis=1)
        p10_path = np.percentile(price_list, 10, axis=1)
        p90_path = np.percentile(price_list, 90, axis=1)

        fig_sim.add_trace(go.Scatter(y=mean_path, mode='lines', name='평균 예상 경로', line=dict(color='black', width=3)))
        fig_sim.add_trace(go.Scatter(y=p90_path, mode='lines', name='상위 10% 비관/낙관 경계', line=dict(color='green', width=2, dash='dash')))
        fig_sim.add_trace(go.Scatter(y=p10_path, mode='lines', name='하위 10% 경계', line=dict(color='red', width=2, dash='dash')))

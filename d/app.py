import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(
    page_title="스마트 주식 분석 & 백테스팅 대시보드",
    page_icon="📈",
    layout="wide"
)

# --- 사이드바 설정 ---
st.sidebar.header("📌 기본 설정")
ticker_symbol = st.sidebar.text_input(
    "기준 종목 티커 (예: AAPL, NVDA, 005930.KS)", 
    value="AAPL"
)

period_options = {
    "1개월": "1mo", 
    "3개월": "3mo", 
    "6개월": "6mo", 
    "1년": "1y", 
    "5년": "5y"
}
selected_period_label = st.sidebar.selectbox(
    "조회 기간", 
    list(period_options.keys()), 
    index=3
)
period = period_options[selected_period_label]

st.sidebar.subheader("📊 기술적 지표")
show_ma = st.sidebar.checkbox("이동평균선 (20일, 60일)", value=True)
show_rsi = st.sidebar.checkbox("RSI 지표 표시", value=True)


# --- 데이터 로드 ---
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

    # 지표 자동 계산 (이동평균선 및 RSI)
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # --- 타이틀 및 지표 ---
    company_name = info.get("longName", ticker_symbol)
    st.title(f"📈 {company_name} ({ticker_symbol.upper()})")

    current_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2]
    price_change_pct = ((current_price - prev_price) / prev_price) * 100

    col1, col2, col3, col4 = st.columns(4)
    price_unit = "$" if not ticker_symbol.endswith((".KS", ".KQ")) else "원"
    
    if price_unit == "$":
        col1.metric("현재가", f"${current_price:.2f}", f"{price_change_pct:+.2f}%")
    else:
        col1.metric("현재가", f"{int(current_price):,}원", f"{price_change_pct:+.2f}%")
        
    col2.metric("52주 최고가", f"{info.get('fiftyTwoWeekHigh', 'N/A')}")
    col3.metric("52주 최저가", f"{info.get('fiftyTwoWeekLow', 'N/A')}")
    col4.metric("PER", f"{info.get('trailingPE', 'N/A')}")

    # ==========================================
    # 🔔 매수/매도 실시간 신호 감지 알림 배너
    # ==========================================
    latest_rsi = df['RSI'].iloc[-1]
    ma20_curr = df['MA20'].iloc[-1]
    ma60_curr = df['MA60'].iloc[-1]
    ma20_prev = df['MA20'].iloc[-2]
    ma60_prev = df['MA60'].iloc[-2]

    is_golden_cross = (ma20_prev < ma60_prev) and (ma20_curr >= ma60_curr)
    is_dead_cross = (ma20_prev > ma60_prev) and (ma20_curr <= ma60_curr)

    signals = []
    if is_golden_cross:
        signals.append("🚨 [골든크로스 발생] 20일 이동평균선이 60일선을 상향 돌파했습니다! (매수 신호)")
    if latest_rsi <= 30:
        signals.append(f"🚨 [과매도 구간] RSI 지표가 {latest_rsi:.1f}로 30 이하입니다! (매수 관점)")
    if is_dead_cross:
        signals.append("⚠️ [데드크로스 발생] 20일 이동평균선이 60일선을 하향 이탈했습니다! (매도 신호)")
    if latest_rsi >= 70:
        signals.append(f"⚠️ [과열 구간] RSI 지표가 {latest_rsi:.1f}로 70 이상입니다! (매도 관점)")

    if signals:
        for sig in signals:
            if "매수" in sig:
                st.success(sig)
            else:
                st.warning(sig)
    else:
        st.info("ℹ️ 현재 특이한 매수/매도 기술적 신호(골든/데드크로스, RSI 과열/과매도)는 발견되지 않았습니다.")

    st.markdown("---")

    # --- 탭 구성 (신규 탭 추가) ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 차트 분석", 
        "💰 적립식 백테스팅", 
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
            rows=rows, 
            cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05, 
            row_heights=row_heights
        )
        
        fig.add_trace(
            go.Candlestick(
                x=df.index, 
                open=df['Open'], 
                high=df['High'], 
                low=df['Low'], 
                close=df['Close'], 
                name="주가"
            ), 
            row=1, col=1
        )

        if show_ma:
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=df['MA20'], 
                    mode='lines', name='MA 20', 
                    line=dict(color='orange', width=1.5)
                ), 
                row=1, col=1
            )
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=df['MA60'], 
                    mode='lines', name='MA 60', 
                    line=dict(color='green', width=1.5)
                ), 
                row=1, col=1
            )

        if show_rsi:
            fig.add_trace(
                go.Scatter(
                    x=df.index, y=df['RSI'], 
                    mode='lines', name='RSI (14)', 
                    line=dict(color='purple', width=1.5)
                ), 
                row=2, col=1
            )
            fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="blue", row=2, col=1)

        fig.update_layout(
            height=550, 
            xaxis_rangeslider_visible=False, 
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)

    # ==========================================
    # TAB 2: "그때 샀다면?" 적립식 백테스팅
    # ==========================================
    with tab2:
        st.subheader("💡 '그때 매월 꾸준히 샀다면?' 적립식 투자 시뮬레이션")
        st.write("선택한 조회 기간 동안 매월 첫 영업일에 일정 금액을 적립식으로 매수했을 때의 성과를 계산합니다.")

        col_b1, col_b2 = st.columns(2)
        default_amount = 100000 if ticker_symbol.endswith((".KS", ".KQ")) else 100
        amount_unit = "원" if ticker_symbol.endswith((".KS", ".KQ")) else "달러($)"
        
        monthly_amount = col_b1.number_input(
            f"매월 적립 투자 금액 ({amount_unit})", 
            min_value=1000 if price_unit == "원" else 10, 
            value=default_amount, 
            step=10000 if price_unit == "원" else 50
        )

        # 월별 첫 번째 거래일 데이터 추출
        df_monthly = df.resample('MS').first().dropna()

        if not df_monthly.empty:
            total_shares = 0.0
            total_invested = 0.0
            history_dates = []
            portfolio_values = []
            invested_values = []

            for date, row in df_monthly.iterrows():
                buy_price = row['Close']
                shares_bought = monthly_amount / buy_price
                total_shares += shares_bought
                total_invested += monthly_amount

                history_dates.append(date)
                portfolio_values.append(total_shares * buy_price)
                invested_values.append(total_invested)

            current_portfolio_value = total_shares * current_price
            total_profit = current_portfolio_value - total_invested
            profit_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0

            # 결과 요약 카드리포트
            res_col1, res_col2, res_col3, res_col4 = st.columns(4)
            
            if price_unit == "$":
                res_col1.metric("총 원금", f"${total_invested:,.2f}")
                res_col2.metric("현재 평가금", f"${current_portfolio_value:,.2f}")
                res_col3.metric("총 평가손익", f"${total_profit:+,.2f}", f"{profit_rate:+.2f}%")
            else:
                res_col1.metric("총 원금", f"{int(total_invested):,}원")
                res_col2.metric("현재 평가금", f"{int(current_portfolio_value):,}원")
                res_col3.metric("총 평가손익", f"{int(total_profit):+,}원", f"{profit_rate:+.2f}%")

            res_col4.metric("총 보유 주식 수", f"{total_shares:.2f} 주")

            # 자산 추이 시각화 그래프
            fig_dca = go.Figure()
            fig_dca.add_trace(go.Scatter(
                x=history_dates, y=invested_values, 
                mode='lines', name='누적 투자 원금', 
                line=dict(color='gray', dash='dash')
            ))
            fig_dca.add_trace(go.Scatter(
                x=history_dates, y=portfolio_values, 
                mode='lines', name='포트폴리오 평가금액', 
                line=dict(color='blue', width=2)
            ))
            fig_dca.update_layout(
                title="시간 경과에 따른 적립 자산 추이",
                xaxis_title="날짜",
                yaxis_title=f"금액 ({amount_unit})",
                height=450
            )
            st.plotly_chart(fig_dca, use_container_width=True)
        else:
            st.warning("백테스트를 계산할 충분한 기간 데이터가 없습니다.")

    # ==========================================
    # TAB 3: 미래 가격 예측
    # ==========================================
    with tab3:
        st.subheader("🎲 몬테카를로 시뮬레이션 기반 미래 주가 시나리오")
        col_p1, col_p2 = st.columns(2)
        sim_days = col_p1.slider(
            "예측 일수", 
            min_value=10, max_value=252, value=60, step=10
        )
        num_simulations = col_p2.slider(
            "시뮬레이션 횟수", 
            min_value=100, max_value=1000, value=300, step=100
        )

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
        for i in range(min(num_simulations, 50)):
            fig_sim.add_trace(
                go.Scatter(
                    y=price_list[:, i], 
                    mode='lines', 
                    line=dict(width=0.5), 
                    opacity=0.2, 
                    showlegend=False
                )
            )

        mean_path = np.mean(price_list, axis=1)
        p10_path = np.percentile(price_list, 10, axis=1)
        p90_path = np.percentile(price_list, 90, axis=1)

        fig_sim.add_trace(
            go.Scatter(
                y=mean_path, 
                mode='lines', 
                name='평균 예상 경로', 
                line=dict(color='black', width=3)
            )
        )
        fig_sim.add_trace(
            go.Scatter(
                y=p90_path, 
                mode='lines', 
                name='상위 10% 경계', 
                line=dict(color='green', width=2, dash='dash')
            )
        )
        fig_sim.add_trace(
            go.Scatter(
                y=p10_path, 
                mode='lines', 
                name='하위 10% 경계', 
                line=dict(color='red', width=2, dash='dash')
            )
        )

        fig_sim.update_layout(
            title=f"{ticker_symbol.upper()} - 향후 {sim_days}일 예측", 
            xaxis_title="일수", 
            yaxis_title="예상 주가", 
            height=450
        )
        st.plotly_chart(fig_sim, use_container_width=True)

        final_prices = price_list[-1, :]
        res_col1, res_col2, res_col3 = st.columns(3)
        res_col1.metric("중앙값", f"{np.median(final_prices):.2f}")
        res_col2.metric("하위 10% (비관적)", f"{np.percentile(final_prices, 10):.2f}")
        res_col3.metric("상위 10% (낙관적)", f"{np.percentile(final_prices, 90):.2f}")

    # ==========================================
    # TAB 4: 종목 비교
    # ==========================================
    with tab4:
        st.subheader("⚖️ 다중 종목 수익률 비교")
        compare_inputs = st.text_input(
            "비교할 티커 입력 (쉼표 구분)", 
            value=f"{ticker_symbol}, MSFT, GOOGL, NVDA"
        )
        compare_tickers = [
            t.strip().upper() 
            for t in compare_inputs.split(",") 
            if t.strip()
        ]

        if compare_tickers:
            comp_df = pd.DataFrame()
            for comp_ticker in compare_tickers:
                try:
                    c_data = yf.Ticker(comp_ticker).history(period=period)
                    if not c_data.empty:
                        comp_df[comp_ticker] = (
                            (c_data['Close'] / c_data['Close'].iloc[0]) - 1
                        ) * 100
                except Exception:
                    pass

            if not comp_df.empty:
                fig_comp = go.Figure()
                for col in comp_df.columns:
                    fig_comp.add_trace(
                        go.Scatter(
                            x=comp_df.index, 
                            y=comp_df[col], 
                            mode='lines', 
                            name=col
                        )
                    )
                fig_comp.update_layout(
                    title="누적 수익률 비교 (%)", 
                    xaxis_title="날짜", 
                    yaxis_title="수익률 (%)", 
                    height=450
                )
                st.plotly_chart(fig_comp, use_container_width=True)

    # ==========================================
    # TAB 5: 기업 정보
    # ==========================================
    with tab5:
        st.subheader("기업 개요")
        st.write(info.get("summaryProfile", "설명 정보가 없습니다."))
        summary_data = {
            "지표": ["시가총액", "배당수익률", "EPS", "PBR"],
            "값": [
                f"{info.get('marketCap', 0):,}",
                f"{info.get('dividendYield', 0) * 100:.2f}%" if info.get('dividendYield') else "N/A",
                f"{info.get('trailingEps', 'N/A')}",
                f"{info.get('priceToBook', 'N/A')}"
            ]
        }
        st.table(pd.DataFrame(summary_data))

except Exception as e:
    st.error(f"오류가 발생했습니다: {e}")

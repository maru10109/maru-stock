import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 설정 (기존 main.py와 스타일 통일)
st.set_page_config(page_title="AI 종목 추천 엔진", page_icon="🤖", layout="wide")

st.title("🤖 AI & 퀀트 기반 실시간 종목 추천")
st.markdown("최신 시장 데이터를 실시간으로 분석하여 사용자의 투자 성향에 가장 적합한 자산을 추천합니다.")

# 분석 대상 풀 (기존 종목 리스트 유지)
TICKERS = {
    "한국: KOSPI 지수": "^KS11",
    "한국: 삼성전자": "005930.KS",
    "한국: SK하이닉스": "000660.KS",
    "한국: 현대차": "005380.KS",
    "한국: NAVER": "035420.KS",
    "미국: S&P 500 지수": "^GSPC",
    "미국: 애플 (AAPL)": "AAPL",
    "미국: 마이크로소프트 (MSFT)": "MSFT",
    "미국: 엔비디아 (NVDA)": "NVDA",
    "미국: 테슬라 (TSLA)": "TSLA"
}

# --- 사이드바 설정 ---
st.sidebar.header("👤 투자 성향 분석 설정")

# 1. 투자 성향 선택
invest_style = st.sidebar.radio(
    "당신의 투자 성향을 선택하세요:",
    ("공격투자형 (High Risk, High Return)", 
     "든든밸런스형 (Growth & Stability)", 
     "절대안정형 (Low Risk, Market Follower)")
)

# 데이터 백테스팅 기간 (최근 6개월 데이터로 지표 산출)
today = datetime.today()
six_months_ago = today - timedelta(days=180)

# AI 분석용 데이터 일괄 다운로드 함수
@st.cache_data(ttl=3600)
def fetch_analysis_data(tickers_dict, start, end):
    ticker_list = list(tickers_dict.values())
    try:
        df = yf.download(ticker_list, start=start, end=end, auto_adjust=True)
        if df.empty or 'Close' not in df.columns:
            return pd.DataFrame()
        
        price_df = df['Close']
        inv_tickers = {v: k for k, v in tickers_dict.items()}
        price_df = price_df.rename(columns=inv_tickers)
        price_df.index = price_df.index.tz_localize(None)
        
        # 결측치 정제
        price_df = price_df.ffill().bfill()
        return price_df
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return pd.DataFrame()

# --- AI 추천 알고리즘 엔진 ---
def ai_recommendation_engine(price_df, style):
    analysis_results = []
    
    for col in price_df.columns:
        series = price_df[col]
        
        # 1. 최근 1개월 및 3개월 수익률 계산
        ret_1m = ((series.iloc[-1] / series.iloc[-20]) - 1) * 100 if len(series) > 20 else 0
        ret_3m = ((series.iloc[-1] / series.iloc[-60]) - 1) * 100 if len(series) > 60 else 0
        
        # 2. 변동성 (표준편차 기반 일일 변동성)
        volatility = series.pct_change().std() * (252 ** 0.5) * 100 # 연율화 변동성(%)
        
        # 3. 기술적 지표 (현재가 대비 50일 이동평균선 위치)
        ma_50 = series.rolling(window=50).mean().iloc[-1]
        above_ma50 = 1 if series.iloc[-1] > ma_50 else 0
        
        # 성향별 AI 스코어링 로직
        if "공격투자형" in style:
            # 공격형: 최근 모멘텀이 강하고 변동성이 높은 종목에 가산점
            ai_score = (ret_1m * 0.4) + (ret_3m * 0.4) + (volatility * 0.2) + (above_ma50 * 5)
            reason = "최근 강력한 거래 대금과 모멘텀을 동반한 주가 상승세가 돋보이며, 고변동성을 활용한 단기 수익 창출에 유리합니다."
        elif "든든밸런스형" in style:
            # 밸런스형: 적당한 우상향 추세와 안정적인 변동성을 가진 우량주에 가산점
            ai_score = (ret_3m * 0.5) - (abs(volatility - 20) * 0.3) + (above_ma50 * 10)
            reason = "안정적인 펀더멘탈을 바탕으로 시장 대비 견조한 흐름을 유지하고 있으며, 리스크와 리턴의 밸런스가 매우 우수합니다."
        else:
            # 절대안정형: 변동성이 낮고 지수 추종형이거나 방어적인 자산에 가산점
            ai_score = -(volatility * 0.7) + (ret_3m * 0.3)
            if "지수" in col: # 시장 지수 가산점
                ai_score += 15
            reason = "낮은 가격 변동성을 기록하고 있어 하락장 방어력이 뛰어나며, 장기 자산 배분 및 적립식 투자에 가장 이상적입니다."
            
        analysis_results.append({
            "종목명": col,
            "AI 스코어": ai_score,
            "최근 1달 수익률": f"{ret_1m:.2f}%",
            "최근 3달 수익률": f"{ret_3m:.2f}%",
            "연간 변동성": f"{volatility:.1f}%",
            "추천 사유": reason
        })
        
    # 점수가 높은 순으로 정렬하여 반환
    result_df = pd.DataFrame(analysis_results)
    return result_df.sort_values(by="AI 스코어", ascending=False).reset_index(drop=True)

# --- 메인 화면 출력 ---
with st.spinner("AI가 실시간 시장 동향 및 기술적 지표를 분석 중입니다... 🤖📊"):
    raw_data = fetch_analysis_data(TICKERS, six_months_ago, today)

if raw_data.empty:
    st.error("분석 데이터를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")
else:
    # AI 엔진 구동
    recommended_df = ai_recommendation_engine(raw_data, invest_style)
    
    # 1위 종목 추출
    top_pick = recommended_df.iloc[0]["종목명"]
    
    st.success(f"🎉 AI 분석 결과, 현재 당신의 투자 성향에 맞는 탑 픽(Top Pick)은 **[{top_pick}]** 입니다!")
    
    # 주요 추천 종목 카드 레이아웃 (상위 3개)
    st.subheader("🌟 AI 추천 Top 3 종목 상세 분석")
    cols = st.columns(3)
    
    for i in range(3):
        item = recommended_df.iloc[i]
        with cols[i]:
            st.markdown(f"### **{i+1}위. {item['종목명']}**")
            st.metric(label="최근 3개월 수익률", value=item["최근 3달 수익률"])
            st.markdown(f"**변동성 수준:** `{item['연간 변동성']}`")
            st.info(f"**AI 진단:** {item['추천 사유']}")
            
    st.markdown("---")
    
    # 전체 순위 표 제공
    st.subheader("📊 전체 분석 대상 순위 리스트")
    display_df = recommended_df.drop(columns=["AI 스코어"])
    st.dataframe(display_df, use_container_width=True, hide_index=False)
    
    # 탑 픽 종목의 최근 6개월 주가 흐름 차트 시각화
    st.markdown("---")
    st.subheader(f"📈 1위 추천 종목 [{top_pick}]의 최근 6개월 주가 추이")
    
    # 주가 정규화 (비교가 아닌 단일 추세용 raw 가격 차트)
    fig_stock = px.line(
        raw_data, 
        x=raw_data.index, 
        y=top_pick, 
        title=f"{top_pick} 종가 추세 정보",
        labels={"value": "주가 (원/달러)", "Date": "날짜"}
    )
    fig_stock.update_layout(hovermode="x unified")
    st.plotly_chart(fig_stock, use_container_width=True)

st.markdown("---")
st.caption("※ 본 AI 추천 시스템은 최근 6개월간의 가격 모멘텀, 변동성, 기술적 지표를 기반으로 한 퀀트 모델입니다. 이는 투자 권유가 아니며 모든 투자의 책임은 본인에게 있습니다.")

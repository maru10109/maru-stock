import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="한/미 주요 주식 수익률 비교", page_icon="📈", layout="wide")

st.title("📈 한/미 주요 주식 & 지수 수익률 비교 분석기")
st.markdown("한국과 미국의 대표 종목 및 시장 지수의 **누적 수익률(%)**을 한눈에 비교해 보세요.")

# 분석 대상 주식 딕셔너리
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
st.sidebar.header("설정 (Settings)")

# 날짜 선택
today = datetime.today()
one_year_ago = today - timedelta(days=365)

start_date = st.sidebar.date_input("시작일", one_year_ago)
end_date = st.sidebar.date_input("종료일", today)

# 종목 다중 선택
selected_names = st.sidebar.multiselect(
    "비교할 종목을 선택하세요 (다중 선택 가능):",
    options=list(TICKERS.keys()),
    default=["한국: 삼성전자", "미국: 애플 (AAPL)", "한국: KOSPI 지수", "미국: S&P 500 지수"]
)

# 데이터 다운로드 및 정제 함수 (통합 다운로드 방식으로 완벽 해결)
@st.cache_data(ttl=3600)
def load_data(tickers_dict, start, end):
    if not tickers_dict:
        return pd.DataFrame()
        
    ticker_list = list(tickers_dict.values())
    
    try:
        # 모든 종목을 '한 번에' 다운로드하여 내부적으로 날짜 축을 자동 결합합니다.
        # auto_adjust=True를 통해 최신 yfinance 버전의 Close(수정종가)를 가져옵니다.
        df = yf.download(ticker_list, start=start, end=end, auto_adjust=True)
        
        if df.empty:
            return pd.DataFrame()
            
        # 단일 종목 선택 시와 다중 종목 선택 시의 데이터프레임 구조 대응
        if 'Close' in df.columns:
            if isinstance(df.columns, pd.MultiIndex):
                price_data = df['Close']  # 다중 종목일 때
            else:
                price_data = pd.DataFrame({ticker_list[0]: df['Close']})  # 단일 종목일 때
        else:
            return pd.DataFrame()
            
        # 티커 기호(예: AAPL)를 사용자가 읽기 좋은 이름(예: 미국: 애플 (AAPL))으로 일괄 변경
        inv_tickers = {v: k for k, v in tickers_dict.items()}
        price_data = price_data.rename(columns=inv_tickers)
        
        # 시간대(Timezone) 정보를 완전히 지우고 순수한 '연-월-일' 날짜로 통일
        price_data.index = price_data.index.tz_localize(None)
        price_data.index = pd.to_datetime(price_data.index.date)
        
        # 중복 날짜가 생길 경우 최신 데이터만 남김
        price_data = price_data.groupby(price_data.index).last()
        
        # 한/미 휴장일 차이로 생기는 빈칸(NaN)을 직전 거래일 주가로 채워넣음
        price_data = price_data.ffill().bfill()
        
        # 사용자가 선택한 종목 순서대로 열 정렬
        final_cols = [name for name in tickers_dict.keys() if name in price_data.columns]
        price_data = price_data[final_cols]
        
        return price_data
        
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return pd.DataFrame()

# --- 메인 화면 로직 ---
if not selected_names:
    st.warning("사이드바에서 하나 이상의 종목을 선택해 주세요.")
else:
    selected_tickers = {name: TICKERS[name] for name in selected_names}
    
    with st.spinner("주식 데이터를 불러오는 중입니다... ⏳"):
        price_data = load_data(selected_tickers, start_date, end_date)
        
    if price_data.empty:
        st.error("선택한 기간의 데이터가 없습니다. 날짜를 다시 설정해 주세요.")
    else:
        # 누적 수익률(%) 계산 (첫날 가격 기준으로 변동률 계산)
        returns_data = (price_data / price_data.iloc[0] - 1) * 100
        
        # Plotly 반응형 선형 차트 생성
        fig = px.line(
            returns_data, 
            x=returns_data.index, 
            y=returns_data.columns,
            title=f"누적 수익률 비교 ({start_date} ~ {end_date})",
            labels={"value": "누적 수익률 (%)", "Date": "날짜", "variable": "종목"}
        )
        fig.update_layout(hovermode="x unified", legend_title_text="종목명")
        fig.update_yaxes(ticksuffix="%")
        
        # 차트 출력
        st.plotly_chart(fig, use_container_width=True)
        
        # 요약 테이블 데이터 생성
        st.subheader("📊 기간 내 요약 지표")
        
        summary_data = []
        for col in price_data.columns:
            start_price = price_data[col].iloc[0]
            end_price = price_data[col].iloc[-1]
            total_return = returns_data[col].iloc[-1]
            
            summary_data.append({
                "종목명": col,
                "시작 가격": f"{start_price:,.2f}",
                "최종 가격": f"{end_price:,.2f}",
                "누적 수익률 (%)": f"{total_return:,.2f}%"
            })
            
        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.caption("※ 본 데이터는 Yahoo Finance를 통해 제공되며, 실제 거래 데이터와 약간의 지연이나 차이가 있을 수 있습니다. 투자 참고용으로만 사용해 주세요.")

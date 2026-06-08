import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 페이지 설정
st.set_page_config(page_title="한/미 주요 주식 수익률 비교", page_icon="📈", layout="wide")

st.title("📈 한/미 주요 주식 & 지수 수익률 비교 분석기")
st.markdown("한국과 미국의 대표 종목 및 시장 지수의 **누적 수익률(%)**을 한눈에 비교해 보세요.")

# 분석 대상 주식 딕셔너리 (표시명: 티커)
# 한국 주식은 티커 뒤에 '.KS'(코스피) 또는 '.KQ'(코스닥)를 붙여야 합니다.
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

# 데이터 다운로드 캐싱 함수 (속도 최적화 및 최신 yfinance 버전 대응)
@st.cache_data(ttl=3600) # 1시간마다 데이터 갱신
def load_data(tickers_dict, start, end):
    data = pd.DataFrame()
    for name, ticker in tickers_dict.items():
        try:
            # 최신 yfinance는 history()를 사용해 'Close'를 가져오는 것이 가장 안정적입니다.
            # 기본적으로 액면분할 및 배당이 자동으로 반영된 종가 데이터를 반환합니다.
            df = yf.Ticker(ticker).history(start=start, end=end)
            
            if not df.empty and 'Close' in df.columns:
                data[name] = df['Close']
            else:
                st.warning(f"{name}({ticker})의 해당 기간 데이터가 존재하지 않습니다.")
        except Exception as e:
            st.error(f"{name}({ticker}) 데이터를 불러오는 데 실패했습니다: {e}")
            
    # 한국/미국 주식의 타임존 정보가 섞여서 생기는 시각화 에러 방지
    if not data.empty:
        data.index = data.index.tz_localize(None)
        
    return data

# --- 메인 화면 로직 ---
if not selected_names:
    st.warning("사이드바에서 하나 이상의 종목을 선택해 주세요.")
else:
    # 선택된 종목의 티커만 필터링
    selected_tickers = {name: TICKERS[name] for name in selected_names}
    
    with st.spinner("주식 데이터를 불러오는 중입니다... ⏳"):
        # 데이터 로드
        price_data = load_data(selected_tickers, start_date, end_date)
        
    if price_data.empty:
        st.error("선택한 기간의 데이터가 없습니다. 날짜를 다시 설정해 주세요.")
    else:
        # 1. 누적 수익률(%) 계산 로직
        # 기준일(첫 거래일)의 가격을 0%로 맞추고 이후의 변화량을 퍼센트로 계산
        returns_data = (price_data / price_data.iloc[0] - 1) * 100
        
        # Plotly를 이용한 반응형 선형 차트 생성
        fig = px.line(
            returns_data, 
            x=returns_data.index, 
            y=returns_data.columns,
            title=f"누적 수익률 비교 ({start_date} ~ {end_date})",
            labels={"value": "누적 수익률 (%)", "Date": "날짜", "variable": "종목"}
        )
        
        # 차트 레이아웃 조정 (에러 났던 괄호 부분을 확실하게 닫았습니다!)
        fig.update_layout(hovermode="x unified", legend_title_text="종목명")
        fig.update_yaxes(ticksuffix="%")
        
        # 차트 출력
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. 요약 테이블 데이터 생성
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

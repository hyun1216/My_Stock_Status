# My Stock Status

import streamlit as st
import yfinance as yf
import pandas as pd

# 페이지 설정 (와이드 모드)
st.set_page_config(page_title="My Stock Status", layout="wide")

st.title("📊 My Stock Status")

# 1. 사이드바 설정 (종목 관리)
st.sidebar.header("설정")
tickers_input = st.sidebar.text_input("종목 코드 (쉼표 구분)", "TSLA, NVDA, 005930.KS, QLD")
tickers = [t.strip() for t in tickers_input.split(",")]

# 2. 환율 정보 가져오기 (USD/KRW)
def get_exchange_rate():
    ex_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
    return round(ex_rate, 2)

exchange_rate = get_exchange_rate()
st.sidebar.metric("현재 환율 (USD/KRW)", f"{exchange_rate}원")

# 3. 데이터 가져오기 함수
def fetch_stock_data(tickers):
    data_list = []
    for ticker in tickers:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        
        current_price = info['last_price']
        prev_close = info['previous_close']
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        # 기본 정보 (달러/원화 계산)
        is_us = not ticker.endswith((".KS", ".KQ"))
        price_krw = current_price * exchange_rate if is_us else current_price
        price_usd = current_price if is_us else current_price / exchange_rate
        
        data_list.append({
            "종목코드": ticker,
            "현재가(USD)": round(price_usd, 2),
            "현재가(KRW)": int(price_krw),
            "등락률(%)": round(change_pct, 2),
            "구분": "미국" if is_us else "국내"
        })
    return pd.DataFrame(data_list)

# 4. 데이터 표시 및 스타일링
df = fetch_stock_data(tickers)

# 음전(마이너스)일 때 빨간색으로 표시하는 함수
def color_negative_red(val):
    color = 'red' if val < 0 else 'black'
    return f'color: {color}'

# 엑셀 스타일 시트 적용
styled_df = df.style.map(color_negative_red, subset=['등락률(%)']) \
                   .format({
                       "현재가(USD)": "${:,.2f}",
                       "현재가(KRW)": "{:,.0f}원",
                       "등락률(%)": "{:+.2f}%" # 서식 오류도 살짝 수정했어!
                   })

st.subheader("📈 실시간 보유 종목 현황")
# 사무실용 엑셀 디자인을 위해 use_container_width 사용
st.dataframe(styled_df, use_container_width=True)

# 5. 자동 새로고침 버튼
if st.button('데이터 새로고침'):
    st.rerun()

import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# 페이지 설정 (사무실 엑셀 느낌을 위해 와이드 모드)
st.set_page_config(page_title="My Stock Status", layout="wide")

# 세션 상태 초기화 (선택된 종목들을 저장할 공간)
if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = []

# 환율 정보 가져오기 함수 (1시간 캐싱 처리로 로딩 속도 최적화)
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return round(ex_rate, 2)
    except:
        return 1350.00 # API 오류 시 임시 기본값

exchange_rate = get_exchange_rate()

# 야후 파이낸셜 검색 API 함수 (한국어/영어 대응)
def search_stock(query):
    if not query:
        return []
    
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR"
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    try:
        response = requests.get(url, headers=headers)
        results = response.json().get('quotes', [])
        return [{"symbol": r['symbol'], "shortname": r.get('shortname', r['symbol'])} for r in results[:5]]
    except:
        return []

# 데이터 가져오기 함수
def fetch_stock_data(stock_list):
    if not stock_list:
        return pd.DataFrame()
        
    data_list = []
    for stock in stock_list:
        ticker = stock['symbol']
        name = stock['shortname']
        
        try:
            yf_stock = yf.Ticker(ticker)
            info = yf_stock.fast_info
            
            current_price = info.get('last_price', 0)
            prev_close = info.get('previous_close', 0)
            change_pct = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0
            
            is_us = not ticker.endswith((".KS", ".KQ"))
            price_krw = current_price * exchange_rate if is_us else current_price
            price_usd = current_price if is_us else current_price / exchange_rate
            
            data_list.append({
                "종목명": name,
                "종목코드": ticker,
                "현재가(USD)": round(price_usd, 2),
                "현재가(KRW)": int(price_krw),
                "등락률(%)": round(change_pct, 2),
                "구분": "미국" if is_us else "국내"
            })
        except Exception:
            pass # 데이터 로드 실패 시 무시하고 다음 종목으로 넘어감
            
    return pd.DataFrame(data_list)


# ==========================================
# 🖥️ 화면 UI 구성 시작
# ==========================================

st.title("📊 My Stock Status")
st.sidebar.metric("현재 환율 (USD/KRW)", f"{exchange_rate:,.2f}원")

# 1. 검색 및 선택 영역
st.subheader("🔍 종목 설정")
search_query = st.text_input("종목명 또는 티커 검색 (예: 테슬라, 005930, QLD)", placeholder="검색어를 입력하세요...")

if search_query:
    search_results = search_stock(search_query)
    if search_results:
        st.write("검색 결과 (클릭해서 추가):")
        cols = st.columns(len(search_results))
        for idx, item in enumerate(search_results):
            btn_label = f"{item['shortname']}\n({item['symbol']})"
            if cols[idx].button(btn_label, key=f"search_{item['symbol']}"):
                # 중복 추가 방지
                if not any(s['symbol'] == item['symbol'] for s in st.session_state.selected_stocks):
                    st.session_state.selected_stocks.append(item)
                    st.rerun()
    else:
        st.caption("검색 결과가 없어. 티커를 다시 확인해봐!")

st.divider()

# 2. 선택된 종목 리스트 (태그 스타일)
st.write(f"**선택한 종목 {len(st.session_state.selected_stocks)}개**")

if st.session_state.selected_stocks:
    chip_cols = st.columns(max(len(st.session_state.selected_stocks), 1))
    for i, stock in enumerate(st.session_state.selected_stocks):
        with chip_cols[i]:
            if st.button(f"{stock['shortname']} ✖", key=f"del_{stock['symbol']}"):
                st.session_state.selected_stocks.pop(i)
                st.rerun()

st.divider()

# 3. 실시간 대시보드 표출 영역
st.subheader("실시간 현황")

if st.session_state.selected_stocks:
    df = fetch_stock_data(st.session_state.selected_stocks)
    
    if not df.empty:
        # 음전일 때 빨간색 표시
        def color_negative_red(val):
            color = 'red' if val < 0 else 'black'
            return f'color: {color}'
        
        # applymap 대신 map 사용 (에러 해결) 및 엑셀 포맷팅
        styled_df = df.style.map(color_negative_red, subset=['등락률(%)']) \
                        .format({
                            "현재가(USD)": "${:,.2f}",
                            "현재가(KRW)": "{:,.0f}원",
                            "등락률(%)": "{:+.2f}%"
                        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        # 새로고침 버튼
        if st.button('데이터 새로고침'):
            st.rerun()
    else:
        st.error("데이터를 불러오는 데 실패했습니다.")
else:
    st.info("👆 위에서 종목을 검색해서 추가해주세요")

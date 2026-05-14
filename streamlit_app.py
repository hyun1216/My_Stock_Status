import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib.parse

# ==========================================
# ⚙️ 초기 설정 및 데이터 수집 함수
# ==========================================

# 1. 페이지 설정 (사무실 엑셀 느낌을 위해 와이드 모드)
st.set_page_config(page_title="My Stock Status", layout="wide")

# 2. 세션 상태 초기화 (선택된 종목들을 저장할 공간)
if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = []

# 3. 환율 정보 가져오기 함수 (1시간 캐싱 처리로 로딩 속도 최적화)
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return round(ex_rate, 2)
    except:
        return 1400.00 # API 오류 시 임시 기본값

exchange_rate = get_exchange_rate()

# 4. 야후 파이낸셜 검색 API (자체 한글 사전 + 야후 API 하이브리드)
def search_stock(query):
    if not query:
        return []
    
    # 자주 찾는 종목 자체 한글 매핑 사전
    COMMON_STOCKS = {
        "테슬라": "TSLA", "애플": "AAPL", "엔비디아": "NVDA", "마이크로소프트": "MSFT", 
        "아마존": "AMZN", "구글": "GOOGL", "메타": "META", "넷플릭스": "NFLX",
        "삼성전자": "005930.KS", "삼성전자우": "005935.KS", "SK하이닉스": "000660.KS", 
        "카카오": "035720.KS", "네이버": "035420.KS", "현대차": "005380.KS",
        "기아": "000270.KS", "에코프로": "086520.KQ", "에코프로비엠": "247540.KQ",
        "QLD": "QLD", "TQQQ": "TQQQ", "SOXL": "SOXL", "SPY": "SPY", "QQQ": "QQQ"
    }
    
    query_clean = query.replace(" ", "").upper()
    local_results = []
    
    # 사전에서 먼저 검색
    for name, ticker in COMMON_STOCKS.items():
        if query_clean in name.replace(" ", "").upper() or query_clean in ticker:
            local_results.append({"symbol": ticker, "shortname": name})
            
    if local_results:
        return local_results[:5]
        
    # 사전에 없으면 야후 API 호출
    encoded_query = urllib.parse.quote(query)
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={encoded_query}&lang=ko-KR&region=KR"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            results = response.json().get('quotes', [])
            valid_results = [r for r in results if r.get('quoteType') in ['EQUITY', 'ETF']]
            
            search_list = []
            for r in valid_results[:5]:
                name = r.get('shortname') or r.get('longname') or r.get('symbol')
                search_list.append({"symbol": r['symbol'], "shortname": name})
            return search_list
        return []
    except Exception:
        return []

# 5. 실시간(최근) 데이터 가져오기 함수
def fetch_stock_data(stock_list):
    if not stock_list:
        return pd.DataFrame()
        
    data_list = []
    for stock in stock_list:
        ticker = stock['symbol']
        name = stock['shortname']
        
        try:
            yf_stock = yf.Ticker(ticker)
            hist = yf_stock.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
            elif not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_close = current_price
            else:
                continue
                
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
            pass
            
    return pd.DataFrame(data_list)


# ==========================================
# 🖥️ 화면 UI 구성
# ==========================================

st.title("📊 My Stock Status")
st.sidebar.metric("현재 환율 (USD/KRW)", f"{exchange_rate:,.2f}원")

# --- 종목 검색 영역 ---
st.subheader("🔍 종목 설정")
search_query = st.text_input("종목명 또는 티커 검색 (예: 테슬라, 삼성전자, AAPL)", placeholder="엔터를 치면 검색됩니다...")

if search_query:
    search_results = search_stock(search_query)
    if search_results:
        st.write("검색 결과 (클릭해서 추가):")
        cols = st.columns(len(search_results))
        for idx, item in enumerate(search_results):
            btn_label = f"{item['shortname']}\n({item['symbol']})"
            if cols[idx].button(btn_label, key=f"search_{item['symbol']}"):
                if not any(s['symbol'] == item['symbol'] for s in st.session_state.selected_stocks):
                    st.session_state.selected_stocks.append(item)
                    st.rerun()
    else:
        st.caption("검색 결과가 없네! 영문 티커나 종목 코드(예: 005930.KS)로 직접 검색해 봐.")

st.divider()

# --- 선택된 종목 태그 영역 ---
st.write(f"**선택한 종목 {len(st.session_state.selected_stocks)}개**")

if st.session_state.selected_stocks:
    chip_cols = st.columns(max(len(st.session_state.selected_stocks), 1))
    for i, stock in enumerate(st.session_state.selected_stocks):
        with chip_cols[i]:
            if st.button(f"{stock['shortname']} ✖", key=f"del_{stock['symbol']}"):
                st.session_state.selected_stocks.pop(i)
                st.rerun()

st.divider()

# --- 실시간 대시보드 (엑셀 스타일 표) 영역 ---
st.subheader("📈 실시간 보유 종목 현황")

if st.session_state.selected_stocks:
    with st.spinner("데이터를 불러오는 중이야..."):
        df = fetch_stock_data(st.session_state.selected_stocks)
    
    if not df.empty:
        # 음전 시 빨간색 표시 로직
        def color_negative_red(val):
            color = 'red' if val < 0 else 'black'
            return f'color: {color}'
        
        styled_df = df.style.map(color_negative_red, subset=['등락률(%)']) \
                        .format({
                            "현재가(USD)": "${:,.2f}",
                            "현재가(KRW)": "{:,.0f}원",
                            "등락률(%)": "{:+.2f}%"
                        })
        
        # hide_index=True로 엑셀 느낌 극대화
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        if st.button('데이터 새로고침 🔄'):
            st.rerun()
    else:
        st.error("데이터를 가져오는 데 실패했어. 야후 파이낸스 접속 문제일 수 있어.")
else:
    st.info("👆 위에서 종목을 검색해서 추가해 줘!")

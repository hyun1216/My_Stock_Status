import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# 페이지 설정
st.set_page_config(page_title="My Stock Status", layout="wide")

# 세션 상태 초기화
if 'selected_stocks' not in st.session_state:
    st.session_state.selected_stocks = []

# 환율 정보 가져오기 함수
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return round(ex_rate, 2)
    except:
        return 1400.00 # API 오류 시 임시 환율

exchange_rate = get_exchange_rate()

# 야후 파이낸셜 검색 API (보안 우회 및 한글 지원 강화)
def search_stock(query):
    if not query:
        return []
    
    # 한국 지역 설정 추가
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}&lang=ko-KR&region=KR"
    # 실제 브라우저처럼 보이게 길고 복잡한 User-Agent 사용! (야후 차단 방지)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            results = response.json().get('quotes', [])
            # 주식(EQUITY)과 ETF만 깔끔하게 필터링
            valid_results = [r for r in results if r.get('quoteType') in ['EQUITY', 'ETF']]
            
            search_list = []
            for r in valid_results[:5]:
                # 이름이 없으면 티커를 이름으로 사용
                name = r.get('shortname') or r.get('longname') or r.get('symbol')
                search_list.append({"symbol": r['symbol'], "shortname": name})
            return search_list
        return []
    except Exception as e:
        return []

# 데이터 가져오기 함수 (안정적인 history 방식 적용)
def fetch_stock_data(stock_list):
    if not stock_list:
        return pd.DataFrame()
        
    data_list = []
    for stock in stock_list:
        ticker = stock['symbol']
        name = stock['shortname']
        
        try:
            yf_stock = yf.Ticker(ticker)
            
            # fast_info 대신 가장 확실한 최근 5일 데이터 조회
            hist = yf_stock.history(period="5d")
            
            if not hist.empty and len(hist) >= 2:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2] # 어제 종가
            elif not hist.empty:
                current_price = hist['Close'].iloc[-1]
                prev_close = current_price
            else:
                continue # 데이터가 아예 없으면 건너뜀
                
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
# 🖥️ 화면 UI 구성 시작
# ==========================================

st.title("📊 My Stock Status")
st.sidebar.metric("현재 환율 (USD/KRW)", f"{exchange_rate:,.2f}원")

st.subheader("🔍 종목 설정")
search_query = st.text_input("종목명 또는 티커 검색 (예: 테슬라, 삼성전자, QLD)", placeholder="엔터를 치면 검색됩니다...")

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
        st.caption("검색 결과가 없네! 영문 티커(예: TSLA, 005930.KS)로 직접 검색해 봐.")

st.divider()

st.write(f"**선택한 종목 {len(st.session_state.selected_stocks)}개**")

if st.session_state.selected_stocks:
    chip_cols = st.columns(max(len(st.session_state.selected_stocks), 1))
    for i, stock in enumerate(st.session_state.selected_stocks):
        with chip_cols[i]:
            if st.button(f"{stock['shortname']} ✖", key=f"del_{stock['symbol']}"):
                st.session_state.selected_stocks.pop(i)
                st.rerun()

st.divider()

st.subheader("📈 실시간 보유 종목 현황")

if st.session_state.selected_stocks:
    with st.spinner("데이터를 불러오는 중이야..."):
        df = fetch_stock_data(st.session_state.selected_stocks)
    
    if not df.empty:
        def color_negative_red(val):
            color = 'red' if val < 0 else 'black'
            return f'color: {color}'
        
        styled_df = df.style.map(color_negative_red, subset=['등락률(%)']) \
                        .format({
                            "현재가(USD)": "${:,.2f}",
                            "현재가(KRW)": "{:,.0f}원",
                            "등락률(%)": "{:+.2f}%"
                        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        
        if st.button('데이터 새로고침 🔄'):
            st.rerun()
    else:
        st.error("데이터를 가져오는 데 실패했어. 야후 파이낸스 접속 문제이거나 상장 폐지된 종목일 수 있어.")
else:
    st.info("👆 위에서 종목을 검색해서 추가해 줘!")

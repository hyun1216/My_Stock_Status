import urllib.parse

# 야후 파이낸셜 검색 API (자체 한글 사전 + 야후 API 하이브리드)
def search_stock(query):
    if not query:
        return []
    
    # 1. 자주 찾는 종목 자체 한글 매핑 사전 (여기에 원하는 걸 계속 추가해도 돼!)
    COMMON_STOCKS = {
        "테슬라": "TSLA", "애플": "AAPL", "엔비디아": "NVDA", "마이크로소프트": "MSFT", 
        "아마존": "AMZN", "구글": "GOOGL", "메타": "META", "넷플릭스": "NFLX",
        "삼성전자": "005930.KS", "삼성전자우": "005935.KS", "SK하이닉스": "000660.KS", 
        "카카오": "035720.KS", "네이버": "035420.KS", "현대차": "005380.KS",
        "기아": "000270.KS", "에코프로": "086520.KQ", "에코프로비엠": "247540.KQ",
        "QLD": "QLD", "TQQQ": "TQQQ", "SOXL": "SOXL" # 자주 보는 ETF도 추가!
    }
    
    # 검색어 띄어쓰기 제거 후 부분 일치 검색
    query_clean = query.replace(" ", "").upper()
    local_results = []
    
    for name, ticker in COMMON_STOCKS.items():
        if query_clean in name.replace(" ", "").upper() or query_clean in ticker:
            local_results.append({"symbol": ticker, "shortname": name})
            
    # 사전에 매핑된 결과가 있으면 바로 반환!
    if local_results:
        return local_results[:5]
        
    # 2. 사전에 없으면 야후 파이낸스 API로 영문/티커 검색 진행
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

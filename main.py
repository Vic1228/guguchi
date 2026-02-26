import yfinance as yf
import os
import sys
import wcwidth
import twstock

def ljust_width(string, width):
    """根據字元實際視覺寬度進行靠左對齊補空白"""
    # 計算字串目前的視覺寬度
    current_width = sum(wcwidth.wcwidth(c) if wcwidth.wcwidth(c) > 0 else 0 for c in string)
    # 計算需要補足幾格空白
    padding = max(0, width - current_width)
    return string + " " * padding

def get_stock_name(stock_code):
    """利用 twstock 取得中文股票名稱"""
    stock_info = twstock.codes.get(stock_code)
    if stock_info:
        return stock_info.name
    return "未知"

def calculate_shares(stock_code, allocated_capital):
    """
    抓取最新股價並計算可以買進的零股數
    """
    stock_name = get_stock_name(stock_code)
    try:
        # 將 stderr 導向 devnull 以隱藏 yfinance 找不到股票時的紅字警告
        stderr_backup = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        
        try:
            ticker = f"{stock_code}.TW"
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")
            
            # 如果是上櫃股票，.TW 會抓不到，改嘗試 .TWO
            if hist.empty:
                ticker = f"{stock_code}.TWO"
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
        finally:
            # 確保結束後將 stderr 恢復
            sys.stderr.close()
            sys.stderr = stderr_backup

        if hist.empty:
            print(f"警告：無法取得 {stock_code} 的股價資料。請確認代碼是否正確。")
            return stock_name, 0, 0.0, 0.0

        current_price = hist['Close'].iloc[-1]
        
        # 計算可買零股數量 (無條件捨去)
        shares = int(allocated_capital // current_price)
        cost = shares * current_price
        
        return stock_name, shares, current_price, cost
    except Exception as e:
        print(f"處理 {stock_code} 時發生錯誤: {e}")
        return stock_name, 0, 0.0, 0.0

def main():
    print("=== 每週台股零股試算工具 ===")
    
    # 取得本金輸入
    try:
        total_capital = float(input("請輸入本週欲投資的總本金 (元)："))
    except ValueError:
        print("輸入錯誤，請輸入數字。")
        return

    # 取得股票清單輸入
    print("\n請輸入 5 檔股票代碼（例如：2330 2317 2454 2308 2881）")
    stock_input = input("股票代碼 (以空白分隔)：")
    
    stocks = stock_input.split()
    if len(stocks) != 5:
        print(f"提醒：您輸入了 {len(stocks)} 檔股票，建議輸入 5 檔。我們將繼續為您試算。")
    
    # 資金平均分配
    num_stocks = len(stocks)
    if num_stocks == 0:
        print("未輸入股票代碼，程式結束。")
        return
        
    allocated_capital = total_capital / num_stocks
    print(f"\n總本金 {total_capital:,.0f} 元，平均分配給 {num_stocks} 檔股票，每檔分配 {allocated_capital:,.0f} 元。\n")
    
    # 增加表格寬度以容納長股票名稱 (有些傳回英文名稱滿長的，設定寬度為 30)
    print("-" * 90)
    print(f"{'股票代碼':<10} | {ljust_width('股票名稱', 30)} | {'最新股價':<10} | {'可買股數':<10} | {'預估花費':<10}")
    print("-" * 90)
    
    total_cost = 0
    results = []

    for stock_code in stocks:
        stock_name, shares, price, cost = calculate_shares(stock_code, allocated_capital)
        total_cost += cost
        results.append((stock_code, stock_name, price, shares, cost))
        
        # 使用自訂的 ljust_width 來對齊中英文字串
        padded_name = ljust_width(stock_name, 30)
        print(f"{stock_code:<14} | {padded_name} | {price:<14.2f} | {shares:<14} | {cost:,.2f}")
        
    print("-" * 90)
    
    remaining_capital = total_capital - total_cost
    print(f"\n【試算總結】")
    print(f"預估總花費： {total_cost:,.2f} 元")
    print(f"剩餘現金：   {remaining_capital:,.2f} 元")

if __name__ == "__main__":
    main()

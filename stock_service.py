"""
股價服務 - 抓取台股即時股價與中文名稱
"""
import os
import sys
import yfinance as yf
import twstock


def get_stock_name(stock_code):
    """利用 twstock 取得中文股票名稱"""
    stock_info = twstock.codes.get(str(stock_code))
    if stock_info:
        return stock_info.name
    return "未知"


def get_stock_price(stock_code):
    """
    抓取台股最新收盤價
    先嘗試上市 (.TW)，再嘗試上櫃 (.TWO)
    回傳: (price, success)
    """
    stderr_backup = sys.stderr
    sys.stderr = open(os.devnull, 'w')

    try:
        # 先嘗試上市
        ticker = f"{stock_code}.TW"
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")

        # 上櫃
        if hist.empty:
            ticker = f"{stock_code}.TWO"
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1d")

        if hist.empty:
            return 0.0, False

        return float(hist['Close'].iloc[-1]), True
    except Exception:
        return 0.0, False
    finally:
        sys.stderr.close()
        sys.stderr = stderr_backup


def get_stock_info(stock_code):
    """
    同時取得名稱與最新股價
    回傳: {"code", "name", "price", "success"}
    """
    name = get_stock_name(stock_code)
    price, success = get_stock_price(stock_code)
    return {
        "code": stock_code,
        "name": name,
        "price": price,
        "success": success
    }

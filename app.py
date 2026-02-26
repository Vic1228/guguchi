"""
股票追蹤 Web 應用 - Flask 主程式
"""
from flask import Flask, render_template, request, jsonify
from models import (
    init_db, get_config, update_config,
    create_batch, get_all_batches, get_batch, update_batch, delete_batch,
    add_stock_record, get_stocks_by_batch, update_stock_record,
    update_stock_current_price, delete_stock_record, get_all_stock_records,
    sell_stock, unsell_stock
)
from stock_service import get_stock_name, get_stock_price, get_stock_info
from datetime import datetime

app = Flask(__name__)

# 啟動時初始化資料庫
init_db()

# 台股手續費標準費率
STANDARD_FEE_RATE = 0.001425  # 0.1425%
# 證交稅稅率
SECURITIES_TAX_RATE = 0.003    # 0.3%
# 手續費折讓 (固定 2.8 折)
FEE_DISCOUNT = 0.28


def calc_fees(buy_price, shares, price_for_sell, fee_discount):
    """
    計算單檔股票的交易成本
    price_for_sell: 已賣出時傳入 sell_price，未賣出傳入 current_price
    """
    buy_amount = buy_price * shares
    sell_amount = (price_for_sell or 0) * shares

    buy_fee = int(buy_amount * STANDARD_FEE_RATE * fee_discount)  # 無條件捨去
    sell_fee = int(sell_amount * STANDARD_FEE_RATE * fee_discount)
    sell_tax = int(sell_amount * SECURITIES_TAX_RATE)

    total_cost = buy_amount + buy_fee
    net_value = sell_amount - sell_fee - sell_tax
    net_pnl = net_value - total_cost
    net_pnl_pct = ((net_value / total_cost - 1) * 100) if total_cost > 0 else 0

    return {
        "buy_amount": buy_amount,
        "buy_fee": buy_fee,
        "sell_amount": sell_amount,
        "sell_fee": sell_fee,
        "sell_tax": sell_tax,
        "total_fees": buy_fee + sell_fee + sell_tax,
        "total_cost": total_cost,
        "net_value": net_value,
        "net_pnl": net_pnl,
        "net_pnl_pct": net_pnl_pct
    }


def get_effective_sell_price(stock):
    """取得用於計算的賣出價：已賣出用 sell_price，否則用 current_price"""
    if stock.get("is_sold"):
        return stock.get("sell_price", 0)
    return stock.get("current_price", 0)


# ============ 頁面路由 ============

@app.route("/")
def index():
    """首頁"""
    return render_template("index.html")


# ============ Config API ============

@app.route("/api/config", methods=["GET"])
def api_get_config():
    config = get_config()
    return jsonify(config)


@app.route("/api/config", methods=["POST"])
def api_update_config():
    data = request.get_json()
    initial_capital = float(data.get("initial_capital", 0))
    fee_discount = float(data.get("fee_discount", 0.28))
    update_config(initial_capital, fee_discount)
    return jsonify({"success": True, "initial_capital": initial_capital, "fee_discount": fee_discount})


# ============ Batch API ============

@app.route("/api/batches", methods=["GET"])
def api_get_batches():
    batches = get_all_batches()
    # 為每個批次附帶股票紀錄摘要
    for batch in batches:
        stocks = get_stocks_by_batch(batch["id"])
        batch_total_cost = 0
        batch_net_value = 0
        batch_total_fees = 0
        for s in stocks:
            price = get_effective_sell_price(s)
            fees = calc_fees(s["buy_price"], s["shares"], price, FEE_DISCOUNT)
            batch_total_cost += fees["total_cost"]
            batch_net_value += fees["net_value"]
            batch_total_fees += fees["total_fees"]
        batch["stock_count"] = len(stocks)
        batch["total_cost"] = batch_total_cost
        batch["total_market_value"] = batch_net_value
        batch["total_fees"] = batch_total_fees
        batch["total_pnl"] = batch_net_value - batch_total_cost
        batch["total_pnl_pct"] = ((batch_net_value / batch_total_cost - 1) * 100) if batch_total_cost > 0 else 0
    return jsonify(batches)


@app.route("/api/batches", methods=["POST"])
def api_create_batch():
    data = request.get_json()
    name = data.get("name", "")
    start_date = data.get("start_date", datetime.now().strftime("%Y-%m-%d"))
    allocated_capital = float(data.get("allocated_capital", 0))
    batch_id = create_batch(name, start_date, allocated_capital)
    return jsonify({"success": True, "batch_id": batch_id})


@app.route("/api/batches/<int:batch_id>", methods=["GET"])
def api_get_batch(batch_id):
    batch = get_batch(batch_id)
    if not batch:
        return jsonify({"error": "批次不存在"}), 404
    stocks = get_stocks_by_batch(batch_id)
    # 為每檔股票附加費用計算
    for s in stocks:
        price = get_effective_sell_price(s)
        fees = calc_fees(s["buy_price"], s["shares"], price, FEE_DISCOUNT)
        s.update(fees)
    batch["stocks"] = stocks
    return jsonify(batch)


@app.route("/api/batches/<int:batch_id>", methods=["PUT"])
def api_update_batch(batch_id):
    data = request.get_json()
    name = data.get("name", "")
    start_date = data.get("start_date", "")
    allocated_capital = float(data.get("allocated_capital", 0))
    update_batch(batch_id, name, start_date, allocated_capital)
    return jsonify({"success": True})


@app.route("/api/batches/<int:batch_id>", methods=["DELETE"])
def api_delete_batch(batch_id):
    delete_batch(batch_id)
    return jsonify({"success": True})


# ============ Stock Record API ============

@app.route("/api/batches/<int:batch_id>/stocks", methods=["POST"])
def api_add_stock(batch_id):
    data = request.get_json()
    stock_code = str(data.get("stock_code", "")).strip()
    stock_name = data.get("stock_name", "")
    buy_price = float(data.get("buy_price", 0))
    shares = int(data.get("shares", 0))

    # 如果沒提供名稱，自動查詢
    if not stock_name:
        stock_name = get_stock_name(stock_code)

    record_id = add_stock_record(batch_id, stock_code, stock_name, buy_price, shares)
    return jsonify({"success": True, "record_id": record_id, "stock_name": stock_name})


@app.route("/api/stocks/<int:record_id>", methods=["PUT"])
def api_update_stock(record_id):
    data = request.get_json()
    buy_price = float(data.get("buy_price", 0))
    shares = int(data.get("shares", 0))
    update_stock_record(record_id, buy_price, shares)
    return jsonify({"success": True})


@app.route("/api/stocks/<int:record_id>", methods=["DELETE"])
def api_delete_stock(record_id):
    delete_stock_record(record_id)
    return jsonify({"success": True})


@app.route("/api/stocks/<int:record_id>/sell", methods=["POST"])
def api_sell_stock(record_id):
    """標記股票為已賣出"""
    data = request.get_json()
    sell_price = float(data.get("sell_price", 0))
    sell_date = data.get("sell_date", datetime.now().strftime("%Y-%m-%d"))
    sell_stock(record_id, sell_price, sell_date)
    return jsonify({"success": True})


@app.route("/api/stocks/<int:record_id>/unsell", methods=["POST"])
def api_unsell_stock(record_id):
    """取消賣出狀態"""
    unsell_stock(record_id)
    return jsonify({"success": True})


# ============ 即時股價 API ============

@app.route("/api/stock-info/<stock_code>", methods=["GET"])
def api_stock_info(stock_code):
    """查詢單一股票的名稱與最新股價"""
    info = get_stock_info(stock_code)
    return jsonify(info)


@app.route("/api/refresh-prices/<int:batch_id>", methods=["POST"])
def api_refresh_prices(batch_id):
    """更新某批次所有未賣出股票的最新股價"""
    stocks = get_stocks_by_batch(batch_id)
    updated = []
    for stock in stocks:
        if stock.get("is_sold"):
            continue
        price, success = get_stock_price(stock["stock_code"])
        if success:
            update_stock_current_price(stock["id"], price)
            updated.append({
                "id": stock["id"],
                "stock_code": stock["stock_code"],
                "current_price": price
            })
    return jsonify({"success": True, "updated": updated})


@app.route("/api/refresh-all-prices", methods=["POST"])
def api_refresh_all_prices():
    """更新所有批次中未賣出股票的最新股價"""
    batches = get_all_batches()
    total_updated = 0
    for batch in batches:
        stocks = get_stocks_by_batch(batch["id"])
        for stock in stocks:
            if stock.get("is_sold"):
                continue
            price, success = get_stock_price(stock["stock_code"])
            if success:
                update_stock_current_price(stock["id"], price)
                total_updated += 1
    return jsonify({"success": True, "total_updated": total_updated})


# ============ 試算 API ============

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    """每週零股試算：給定預算和股票清單，平均分配試算"""
    data = request.get_json()
    budget = float(data.get("budget", 0))
    stock_codes = data.get("stocks", [])

    if budget <= 0 or not stock_codes:
        return jsonify({"error": "請輸入預算和至少一檔股票"}), 400

    num_stocks = len(stock_codes)
    allocated = budget / num_stocks
    results = []
    total_cost = 0

    for code in stock_codes:
        code = str(code).strip()
        if not code:
            continue
        name = get_stock_name(code)
        price, success = get_stock_price(code)
        if success and price > 0:
            shares = int(allocated // price)
            cost = shares * price
            buy_fee = int(cost * STANDARD_FEE_RATE * FEE_DISCOUNT)
            total_with_fee = cost + buy_fee
        else:
            shares = 0
            cost = 0
            buy_fee = 0
            total_with_fee = 0

        total_cost += total_with_fee
        results.append({
            "stock_code": code,
            "stock_name": name,
            "price": price if success else 0,
            "shares": shares,
            "cost": cost,
            "buy_fee": buy_fee,
            "total_with_fee": total_with_fee
        })

    return jsonify({
        "budget": budget,
        "allocated_per_stock": allocated,
        "num_stocks": num_stocks,
        "results": results,
        "total_cost": total_cost,
        "remaining": budget - total_cost
    })


# ============ 統計 API ============

@app.route("/api/summary", methods=["GET"])
def api_summary():
    """取得整體統計摘要"""
    batches = get_all_batches()

    total_cost = 0
    total_net_value = 0
    total_fees = 0
    total_realized_pnl = 0
    total_unrealized_pnl = 0

    batch_summaries = []
    for batch in batches:
        stocks = get_stocks_by_batch(batch["id"])
        batch_cost = 0
        batch_net = 0
        batch_fees = 0
        batch_realized = 0
        batch_unrealized = 0
        for s in stocks:
            price = get_effective_sell_price(s)
            fees = calc_fees(s["buy_price"], s["shares"], price, FEE_DISCOUNT)
            batch_cost += fees["total_cost"]
            batch_net += fees["net_value"]
            batch_fees += fees["total_fees"]
            if s.get("is_sold"):
                batch_realized += fees["net_pnl"]
            else:
                batch_unrealized += fees["net_pnl"]

        batch_pnl = batch_net - batch_cost
        batch_pnl_pct = ((batch_net / batch_cost - 1) * 100) if batch_cost > 0 else 0

        total_cost += batch_cost
        total_net_value += batch_net
        total_fees += batch_fees
        total_realized_pnl += batch_realized
        total_unrealized_pnl += batch_unrealized

        batch_summaries.append({
            "id": batch["id"],
            "name": batch["name"],
            "start_date": batch["start_date"],
            "total_cost": batch_cost,
            "total_market_value": batch_net,
            "total_fees": batch_fees,
            "pnl": batch_pnl,
            "pnl_pct": batch_pnl_pct,
            "realized_pnl": batch_realized,
            "unrealized_pnl": batch_unrealized,
            "stock_count": len(stocks)
        })

    total_pnl = total_net_value - total_cost
    total_pnl_pct = ((total_net_value / total_cost - 1) * 100) if total_cost > 0 else 0

    return jsonify({
        "total_invested": total_cost,
        "total_market_value": total_net_value,
        "total_fees": total_fees,
        "total_pnl": total_pnl,
        "total_pnl_pct": total_pnl_pct,
        "realized_pnl": total_realized_pnl,
        "unrealized_pnl": total_unrealized_pnl,
        "batch_count": len(batches),
        "batches": batch_summaries
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

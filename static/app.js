/**
 * 股票追蹤 — 前端邏輯
 */

// ============ Helpers ============

function fmt(n) {
    return Number(n).toLocaleString("zh-TW", { maximumFractionDigits: 0 });
}

function fmtDecimal(n, d = 2) {
    return Number(n).toLocaleString("zh-TW", { minimumFractionDigits: d, maximumFractionDigits: d });
}

function pnlClass(val) {
    return val > 0 ? "positive" : val < 0 ? "negative" : "";
}

function pnlSign(val) {
    return val > 0 ? "+" : "";
}

async function api(url, opts = {}) {
    const res = await fetch(url, {
        headers: { "Content-Type": "application/json" },
        ...opts
    });
    return res.json();
}

function showToast(msg, type = "success") {
    const container = document.getElementById("toastContainer");
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function escHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

// ============ Init ============

document.addEventListener("DOMContentLoaded", () => {
    loadSummary();
});

// ============ Summary / Stats ============

async function loadSummary() {
    const data = await api("/api/summary");

    document.getElementById("statTotalInvested").textContent = `$${fmt(data.total_invested)}`;
    document.getElementById("statMarketValue").textContent = `$${fmt(data.total_market_value)}`;

    const feesEl = document.getElementById("statTotalFees");
    feesEl.textContent = `$${fmt(data.total_fees || 0)}`;

    const pnlEl = document.getElementById("statTotalPnl");
    pnlEl.textContent = `${pnlSign(data.total_pnl)}$${fmt(Math.abs(data.total_pnl))}`;
    pnlEl.className = `stat-value ${pnlClass(data.total_pnl)}`;

    const pctEl = document.getElementById("statPnlPct");
    pctEl.textContent = `${pnlSign(data.total_pnl_pct)}${fmtDecimal(data.total_pnl_pct)}%`;
    pctEl.className = `stat-value ${pnlClass(data.total_pnl_pct)}`;

    renderBatchList(data.batches);
}

// ============ Batch List ============

function renderBatchList(batches) {
    const container = document.getElementById("batchList");

    if (!batches || batches.length === 0) {
        container.innerHTML = "";
        container.appendChild(createEmptyState());
        return;
    }

    container.innerHTML = batches.map(b => {
        const pnlCls = pnlClass(b.pnl);
        const pnlText = `${pnlSign(b.pnl)}$${fmt(Math.abs(b.pnl))} (${pnlSign(b.pnl_pct)}${fmtDecimal(b.pnl_pct)}%)`;
        return `
        <div class="batch-card" id="batch-${b.id}">
            <div class="batch-card-header" onclick="toggleBatch(${b.id})">
                <div class="batch-info">
                    <span class="batch-name">${escHtml(b.name)}</span>
                    <span class="batch-date">${b.start_date} · ${b.stock_count} 檔 · 投入 $${fmt(b.total_cost)}</span>
                </div>
                <span class="batch-pnl ${pnlCls}">${pnlText}</span>
            </div>
            <div class="batch-card-body" id="batch-body-${b.id}">
                <div style="text-align:center; padding:20px; color:var(--text-muted);">載入中...</div>
            </div>
        </div>`;
    }).join("");
}

function createEmptyState() {
    const div = document.createElement("div");
    div.className = "empty-state";
    div.id = "emptyState";
    div.innerHTML = `
        <div class="empty-icon">📊</div>
        <p>尚未建立任何投資批次</p>
        <button class="btn btn-primary" onclick="openNewBatchModal()">建立第一個批次</button>
    `;
    return div;
}

// ============ Toggle Batch Detail ============

async function toggleBatch(batchId) {
    const card = document.getElementById(`batch-${batchId}`);
    if (card.classList.contains("expanded")) {
        card.classList.remove("expanded");
        return;
    }

    card.classList.add("expanded");
    await loadBatchDetail(batchId);
}

async function loadBatchDetail(batchId) {
    const body = document.getElementById(`batch-body-${batchId}`);
    body.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);"><span class="spinner"></span> 載入中...</div>`;

    const batch = await api(`/api/batches/${batchId}`);
    const stocks = batch.stocks || [];

    if (stocks.length === 0) {
        body.innerHTML = `<p class="text-muted text-sm" style="padding:16px 0;">尚無股票紀錄</p>`;
    } else {
        let totalCost = 0, totalNetValue = 0, totalFees = 0;

        const rows = stocks.map(s => {
            const cost = s.total_cost || (s.buy_price * s.shares);
            const netVal = s.net_value || 0;
            const pnl = s.net_pnl || (netVal - cost);
            const pnlPct = s.net_pnl_pct || 0;
            const fees = s.total_fees || 0;
            const isSold = s.is_sold;
            totalCost += cost;
            totalNetValue += netVal;
            totalFees += fees;

            const cls = pnlClass(pnl);
            const soldBadge = isSold
                ? `<span style="background:var(--success-bg); color:var(--success); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:600;">已賣出</span>`
                : `<span style="background:var(--warning-bg); color:var(--warning); padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:600;">持有中</span>`;
            
            const priceDisplay = isSold
                ? `$${fmtDecimal(s.sell_price)} <span class="text-muted text-sm">(賣)</span>`
                : `${s.current_price ? "$" + fmtDecimal(s.current_price) : "—"}`;

            const actionBtn = isSold
                ? `<button class="btn btn-secondary btn-sm" onclick="unsellStock(${s.id}, ${batchId})" title="取消賣出" style="padding:4px 8px; font-size:0.75rem;">↩ 取消</button>`
                : `<button class="btn btn-primary btn-sm" onclick="promptSellStock(${s.id}, '${escHtml(s.stock_code)}', '${escHtml(s.stock_name)}', ${batchId})" style="padding:4px 8px; font-size:0.75rem;">💰 賣出</button>`;

            const rowStyle = isSold ? 'opacity:0.7;' : '';

            return `<tr style="${rowStyle}">
                <td><strong>${escHtml(s.stock_code)}</strong></td>
                <td>${escHtml(s.stock_name)}</td>
                <td>$${fmtDecimal(s.buy_price)}</td>
                <td>${fmt(s.shares)}</td>
                <td>${priceDisplay}</td>
                <td>$${fmt(cost)}</td>
                <td style="color:var(--warning);">$${fmt(fees)}</td>
                <td class="pnl-${cls || 'zero'}">${pnlSign(pnl)}$${fmt(Math.abs(pnl))} (${pnlSign(pnlPct)}${fmtDecimal(pnlPct)}%)</td>
                <td>${soldBadge}</td>
                <td>${actionBtn}</td>
            </tr>`;
        }).join("");

        const totalPnl = totalNetValue - totalCost;
        const totalPnlPct = totalCost > 0 ? ((totalNetValue / totalCost - 1) * 100) : 0;
        const totalCls = pnlClass(totalPnl);

        body.innerHTML = `
            <table class="stock-table">
                <thead>
                    <tr>
                        <th>代碼</th>
                        <th>名稱</th>
                        <th>買入價</th>
                        <th>股數</th>
                        <th>現價/賣價</th>
                        <th>總成本</th>
                        <th>費用</th>
                        <th>淨損益</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                    <tr style="border-top:2px solid var(--border-color); font-weight:700;">
                        <td colspan="5" style="text-align:right;">合計</td>
                        <td>$${fmt(totalCost)}</td>
                        <td style="color:var(--warning);">$${fmt(totalFees)}</td>
                        <td class="pnl-${totalCls || 'zero'}">${pnlSign(totalPnl)}$${fmt(Math.abs(totalPnl))} (${pnlSign(totalPnlPct)}${fmtDecimal(totalPnlPct)}%)</td>
                        <td colspan="2"></td>
                    </tr>
                </tbody>
            </table>
            <div class="batch-actions">
                <button class="btn btn-secondary btn-sm" onclick="refreshBatchPrices(${batchId})">🔄 更新股價</button>
                <button class="btn btn-secondary btn-sm" onclick="openEditBatchModal(${batchId})">✏️ 編輯</button>
                <button class="btn btn-danger btn-sm" onclick="deleteBatch(${batchId})">🗑️ 刪除批次</button>
            </div>
            <div class="text-muted text-sm mt-2">
                手續費 2.8 折 · 
                ${stocks[0]?.price_updated_at ? "股價更新時間：" + stocks[0].price_updated_at : "尚未更新股價"}
            </div>
        `;
    }
}

// ============ Sell Stock (Modal) ============

function promptSellStock(recordId, stockCode, stockName, batchId) {
    document.getElementById("sellModalTitle").textContent = `賣出 ${stockCode} ${stockName}`;
    document.getElementById("sellRecordId").value = recordId;
    document.getElementById("sellBatchId").value = batchId;
    document.getElementById("sellPrice").value = "";
    document.getElementById("sellDate").value = new Date().toISOString().split("T")[0];
    document.getElementById("sellModal").classList.add("active");
}

function closeSellModal() {
    document.getElementById("sellModal").classList.remove("active");
}

async function confirmSellStock() {
    const recordId = document.getElementById("sellRecordId").value;
    const batchId = document.getElementById("sellBatchId").value;
    const sellPrice = parseFloat(document.getElementById("sellPrice").value);
    const sellDate = document.getElementById("sellDate").value;

    if (isNaN(sellPrice) || sellPrice <= 0) {
        showToast("請輸入有效的賣出價格", "error");
        return;
    }

    await api(`/api/stocks/${recordId}/sell`, {
        method: "POST",
        body: JSON.stringify({ sell_price: sellPrice, sell_date: sellDate })
    });
    closeSellModal();
    showToast("已記錄賣出！");
    await loadBatchDetail(parseInt(batchId));
    loadSummary();
}

async function unsellStock(recordId, batchId) {
    showConfirm("確定要取消此筆賣出紀錄？", async () => {
        await api(`/api/stocks/${recordId}/unsell`, { method: "POST" });
        showToast("已取消賣出");
        await loadBatchDetail(batchId);
        loadSummary();
    });
}

// ============ Confirm Dialog (Modal) ============

let _confirmCallback = null;

function showConfirm(message, callback) {
    document.getElementById("confirmMessage").textContent = message;
    _confirmCallback = callback;
    document.getElementById("confirmModal").classList.add("active");
}

function closeConfirmModal() {
    document.getElementById("confirmModal").classList.remove("active");
    _confirmCallback = null;
}

async function executeConfirmAction() {
    const cb = _confirmCallback;
    closeConfirmModal();
    if (cb) await cb();
}

// ============ Refresh Prices ============

async function refreshBatchPrices(batchId) {
    showToast("正在更新股價...");
    await api(`/api/refresh-prices/${batchId}`, { method: "POST" });
    showToast("股價已更新！");
    await loadBatchDetail(batchId);
    loadSummary();
}

async function refreshAllPrices() {
    showToast("正在更新所有股價，這可能需要一些時間...");
    const result = await api("/api/refresh-all-prices", { method: "POST" });
    showToast(`已更新 ${result.total_updated} 檔股票的股價`);
    loadSummary();
}

// ============ Batch Modal ============

let stockRowCount = 0;

function openNewBatchModal() {
    document.getElementById("batchModalTitle").textContent = "新增投資批次";
    document.getElementById("editBatchId").value = "";
    document.getElementById("batchName").value = "";
    document.getElementById("batchDate").value = new Date().toISOString().split("T")[0];

    const container = document.getElementById("stockInputs");
    container.innerHTML = "";
    stockRowCount = 0;

    for (let i = 0; i < 5; i++) addStockRow();

    document.getElementById("batchModal").classList.add("active");
}

async function openEditBatchModal(batchId) {
    const batch = await api(`/api/batches/${batchId}`);

    document.getElementById("batchModalTitle").textContent = "編輯投資批次";
    document.getElementById("editBatchId").value = batchId;
    document.getElementById("batchName").value = batch.name;
    document.getElementById("batchDate").value = batch.start_date;

    const container = document.getElementById("stockInputs");
    container.innerHTML = "";
    stockRowCount = 0;

    const stocks = batch.stocks || [];
    if (stocks.length === 0) {
        for (let i = 0; i < 5; i++) addStockRow();
    } else {
        for (const s of stocks) {
            addStockRow(s.stock_code, s.stock_name, s.buy_price, s.shares, s.id);
        }
    }

    document.getElementById("batchModal").classList.add("active");
}

function closeBatchModal() {
    document.getElementById("batchModal").classList.remove("active");
}

function addStockRow(code = "", name = "", price = "", shares = "", recordId = "") {
    stockRowCount++;
    const container = document.getElementById("stockInputs");

    const row = document.createElement("div");
    row.className = "stock-input-row";
    row.dataset.recordId = recordId;
    row.innerHTML = `
        <input type="text" class="stock-code-input" placeholder="代碼" value="${escHtml(String(code))}" onblur="lookupStockName(this)">
        <span class="stock-name-label">${name || "—"}</span>
        <input type="number" class="stock-price-input" placeholder="買入價" value="${price}" step="0.01">
        <input type="number" class="stock-shares-input" placeholder="股數" value="${shares}">
        <button class="remove-stock-btn" onclick="this.parentElement.remove()" title="移除">✕</button>
    `;
    container.appendChild(row);
}

async function lookupStockName(input) {
    const code = input.value.trim();
    if (!code) return;

    const nameLabel = input.parentElement.querySelector(".stock-name-label");
    nameLabel.textContent = "查詢中...";

    try {
        const info = await api(`/api/stock-info/${code}`);
        nameLabel.textContent = info.name || "未知";
    } catch {
        nameLabel.textContent = "查詢失敗";
    }
}

async function saveBatch() {
    const editId = document.getElementById("editBatchId").value;
    const name = document.getElementById("batchName").value.trim();
    const date = document.getElementById("batchDate").value;

    if (!name) { showToast("請輸入批次名稱", "error"); return; }
    if (!date) { showToast("請選擇日期", "error"); return; }

    const rows = document.querySelectorAll("#stockInputs .stock-input-row");
    const stocks = [];
    for (const row of rows) {
        const code = row.querySelector(".stock-code-input").value.trim();
        const stockName = row.querySelector(".stock-name-label").textContent;
        const buyPrice = parseFloat(row.querySelector(".stock-price-input").value) || 0;
        const sharesVal = parseInt(row.querySelector(".stock-shares-input").value) || 0;
        const recordId = row.dataset.recordId;

        if (code) {
            stocks.push({ code, name: stockName, buy_price: buyPrice, shares: sharesVal, record_id: recordId });
        }
    }

    try {
        let batchId;

        if (editId) {
            await api(`/api/batches/${editId}`, {
                method: "PUT",
                body: JSON.stringify({ name, start_date: date, allocated_capital: 0 })
            });
            batchId = editId;

            for (const s of stocks) {
                if (s.record_id) {
                    await api(`/api/stocks/${s.record_id}`, {
                        method: "PUT",
                        body: JSON.stringify({ buy_price: s.buy_price, shares: s.shares })
                    });
                } else {
                    await api(`/api/batches/${batchId}/stocks`, {
                        method: "POST",
                        body: JSON.stringify({ stock_code: s.code, stock_name: s.name, buy_price: s.buy_price, shares: s.shares })
                    });
                }
            }
        } else {
            const result = await api("/api/batches", {
                method: "POST",
                body: JSON.stringify({ name, start_date: date, allocated_capital: 0 })
            });
            batchId = result.batch_id;

            for (const s of stocks) {
                await api(`/api/batches/${batchId}/stocks`, {
                    method: "POST",
                    body: JSON.stringify({ stock_code: s.code, stock_name: s.name, buy_price: s.buy_price, shares: s.shares })
                });
            }
        }

        showToast("批次已儲存，正在抓取最新股價...");
        await api(`/api/refresh-prices/${batchId}`, { method: "POST" });

        closeBatchModal();
        showToast("儲存完成！股價已更新。");
        loadSummary();
    } catch (err) {
        showToast("儲存失敗：" + err.message, "error");
    }
}

// ============ Delete Batch ============

async function deleteBatch(batchId) {
    showConfirm("確定要刪除此批次？此操作無法復原。", async () => {
        await api(`/api/batches/${batchId}`, { method: "DELETE" });
        showToast("批次已刪除");
        loadSummary();
    });
}

// ============ Calculator (試算) ============

let _lastCalcResult = null;

function openCalcModal() {
    document.getElementById("calcBudget").value = "";
    document.getElementById("calcStocks").value = "";
    document.getElementById("calcResult").innerHTML = "";
    document.getElementById("calcToRecordBtn").style.display = "none";
    document.getElementById("calcBtn").disabled = false;
    _lastCalcResult = null;
    document.getElementById("calcModal").classList.add("active");
}

function closeCalcModal() {
    document.getElementById("calcModal").classList.remove("active");
}

async function runCalculation() {
    const budget = parseFloat(document.getElementById("calcBudget").value);
    const stocksInput = document.getElementById("calcStocks").value.trim();

    if (!budget || budget <= 0) {
        showToast("請輸入有效的投資預算", "error");
        return;
    }
    if (!stocksInput) {
        showToast("請輸入至少一檔股票代碼", "error");
        return;
    }

    // 支持空白、逗號分隔
    const stocks = stocksInput.split(/[\s,，]+/).filter(s => s);

    const resultDiv = document.getElementById("calcResult");
    resultDiv.innerHTML = `<div style="text-align:center; padding:16px; color:var(--text-muted);"><span class="spinner"></span> 正在查詢股價並試算...</div>`;
    document.getElementById("calcBtn").disabled = true;

    try {
        const data = await api("/api/calculate", {
            method: "POST",
            body: JSON.stringify({ budget, stocks })
        });

        if (data.error) {
            resultDiv.innerHTML = `<p style="color:var(--danger);">${data.error}</p>`;
            document.getElementById("calcBtn").disabled = false;
            return;
        }

        _lastCalcResult = data;

        const rows = data.results.map(r => {
            return `<tr>
                <td><strong>${escHtml(r.stock_code)}</strong></td>
                <td>${escHtml(r.stock_name)}</td>
                <td>${r.price > 0 ? "$" + fmtDecimal(r.price) : "—"}</td>
                <td>${fmt(r.shares)}</td>
                <td>$${fmt(r.cost)}</td>
                <td style="color:var(--warning);">$${fmt(r.buy_fee)}</td>
                <td>$${fmt(r.total_with_fee)}</td>
            </tr>`;
        }).join("");

        resultDiv.innerHTML = `
            <div class="text-muted text-sm mb-2" style="margin-bottom:8px;">
                預算 $${fmt(data.budget)} ÷ ${data.num_stocks} 檔 = 每檔分配 $${fmt(data.allocated_per_stock)}
            </div>
            <table class="stock-table" style="min-width:auto;">
                <thead>
                    <tr>
                        <th>代碼</th>
                        <th>名稱</th>
                        <th>最新股價</th>
                        <th>可買股數</th>
                        <th>小計</th>
                        <th>手續費</th>
                        <th>含費總計</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows}
                    <tr style="border-top:2px solid var(--border-color); font-weight:700;">
                        <td colspan="4" style="text-align:right;">合計</td>
                        <td colspan="3">$${fmt(data.total_cost)}</td>
                    </tr>
                </tbody>
            </table>
            <div style="margin-top:12px; padding:12px; background:var(--bg-input); border-radius:8px;">
                <span style="color:var(--success); font-weight:700;">💰 剩餘現金：$${fmt(data.remaining)}</span>
            </div>
        `;

        document.getElementById("calcToRecordBtn").style.display = "inline-flex";
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">試算失敗：${err.message}</p>`;
    }

    document.getElementById("calcBtn").disabled = false;
}

async function calcToRecord() {
    if (!_lastCalcResult) return;

    closeCalcModal();

    // 打開新增批次 Modal 並預填試算結果
    document.getElementById("batchModalTitle").textContent = "新增投資批次（試算結果）";
    document.getElementById("editBatchId").value = "";
    document.getElementById("batchName").value = `第__週`;
    document.getElementById("batchDate").value = new Date().toISOString().split("T")[0];

    const container = document.getElementById("stockInputs");
    container.innerHTML = "";
    stockRowCount = 0;

    for (const r of _lastCalcResult.results) {
        if (r.shares > 0) {
            addStockRow(r.stock_code, r.stock_name, r.price, r.shares);
        }
    }

    document.getElementById("batchModal").classList.add("active");
}

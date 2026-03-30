/* SC Accountant — Dashboard Application */

const API = "";
const REFRESH_INTERVAL = 1800000; // 30 minutes
const LOCATION_POLL_INTERVAL = 30000; // 30 seconds

let currentTab = "balancesheet";
let currentPage = 0;
let currentPeriod = "month";
let refreshTimer = null;
let locationPollTimer = null;

// Opportunities filter state (cached on load)
let cachedLocations = null;
let cachedPlayerLocation = null;
let cachedShips = null;
let selectedSystem = "";
let selectedLocation = "";
let selectedCargoScu = 0;
let selectedShipName = ""; // tracks which ship is selected (by display label)

// Category cache for forms
let cachedCategories = null;

// Tab help text shown in the footer
const TAB_DESCRIPTIONS = {
  balancesheet: "Financial snapshot showing total assets, liabilities, and net worth.",
  operations: "Income statement showing revenue, costs, and profit margins for the selected period.",
  ledger: "Complete record of all transactions — income and expenses, sorted by date.",
  fleet: "Registry of owned ships, vehicles, and equipment with purchase prices and market values.",
  orders: "Purchase and sales orders with automatic fulfillment tracking as trades are recorded.",
  banking: "Loan management — track money lent out and borrowed, with interest calculations.",
  portfolio: "Open commodity positions with cost basis, market value, and unrealized profit/loss.",
  opportunities: "Trade route suggestions ranked by profit margin, based on live market data.",
  group: "Multi-player session tracking with revenue splitting and payout calculations.",
  statistics: "Visual analytics and charts of your financial activity over time.",
  about: "About SC Accountant — project info and remote access.",
};

// --- Initialization ---

document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupPeriodSelect();
  setupModal();
  loadBalance();
  loadTab(currentTab);
  loadOpportunityData();
  loadCategories();
  startAutoRefresh();
  startLocationPolling();
});

async function loadOpportunityData() {
  const [locations, playerLoc, ships] = await Promise.all([
    fetchJSON("/api/locations"),
    fetchJSON("/api/player-location"),
    fetchJSON("/api/ships"),
  ]);
  cachedLocations = locations;
  cachedPlayerLocation = playerLoc;
  cachedShips = ships;
}

function startLocationPolling() {
  if (locationPollTimer) clearInterval(locationPollTimer);
  locationPollTimer = setInterval(pollPlayerLocation, LOCATION_POLL_INTERVAL);
}

async function pollPlayerLocation() {
  const newLoc = await fetchJSON("/api/player-location");
  if (!newLoc) return;

  const oldName = cachedPlayerLocation && cachedPlayerLocation.available
    ? (cachedPlayerLocation.location_name || "")
    : "";
  const newName = newLoc.available ? (newLoc.location_name || "") : "";

  cachedPlayerLocation = newLoc;

  // If location changed and we're on the opportunities tab, refresh it
  if (oldName !== newName && currentTab === "opportunities") {
    renderOpportunities();
  }
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentTab = btn.dataset.tab;
      currentPage = 0;
      loadTab(currentTab);
    });
  });
}

function setupPeriodSelect() {
  const sel = document.getElementById("period-select");
  sel.addEventListener("change", () => {
    currentPeriod = sel.value;
    currentPage = 0;
    loadTab(currentTab);
  });
}

let lastDataVersion = 0;

function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  // Poll the data version counter every 2s — refreshes only when data changes
  refreshTimer = setInterval(async () => {
    try {
      const res = await fetch(API + "/api/version?_=" + Date.now(), { cache: "no-store" });
      if (!res.ok) return;
      const data = await res.json();
      if (data.version !== lastDataVersion) {
        lastDataVersion = data.version;
        loadBalance();
        loadTab(currentTab);
      }
    } catch (e) {
      // Server unreachable — skip this cycle
    }
  }, 2000);
}

// --- API Helpers ---

async function fetchJSON(url) {
  try {
    const res = await fetch(API + url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    updateStatus("Connected");
    return await res.json();
  } catch (err) {
    updateStatus("Disconnected");
    return null;
  }
}

function updateStatus() {
  // Status display removed — help text now lives in footer
}

function fmt(amount) {
  if (amount == null) return "0 aUEC";
  return amount.toLocaleString("en-US", { maximumFractionDigits: 0 }) + " aUEC";
}

function fmtPct(value) {
  if (value == null) return "0%";
  return value.toFixed(1) + "%";
}

function signClass(amount) {
  if (amount > 0) return "positive";
  if (amount < 0) return "negative";
  return "";
}

// --- Balance ---

async function loadBalance() {
  const data = await fetchJSON("/api/balance");
  if (!data) return;
  const el = document.getElementById("balance");
  el.textContent = data.formatted;
}

// --- Network Info ---

async function renderAbout() {
  const content = document.getElementById("content");

  let html = '<div class="about-page">';
  html += '<div class="about-section">';
  html += "<h2>SC Accountant</h2>";
  html += "<p>A full-featured accounting companion for Star Citizen, built as a Wingman AI skill.</p>";
  html += "<p>Track transactions, manage assets, plan orders, analyze trade opportunities, "
    + "run group sessions with split calculations, and monitor your financial performance "
    + "across all gameplay activities.</p>";
  html += "</div>";

  html += '<div class="about-section">';
  html += "<h3>Features</h3>";
  html += "<ul>";
  html += "<li><strong>Balance Sheet</strong> — Assets, liabilities, and net worth overview</li>";
  html += "<li><strong>Operations</strong> — Income statement with revenue, costs, and margins</li>";
  html += "<li><strong>Ledger</strong> — Complete transaction history</li>";
  html += "<li><strong>My Assets</strong> — Ship, vehicle, and equipment registry</li>";
  html += "<li><strong>Orders</strong> — Purchase and sales order tracking with auto-fulfillment</li>";
  html += "<li><strong>Banking</strong> — Loan management with interest calculations</li>";
  html += "<li><strong>Portfolio</strong> — Commodity positions with unrealized P&L</li>";
  html += "<li><strong>Opportunities</strong> — Trade routes ranked by profit margin</li>";
  html += "<li><strong>Group Events</strong> — Multi-player sessions with revenue splitting</li>";
  html += "<li><strong>Statistics</strong> — Visual charts and financial analytics</li>";
  html += "</ul>";
  html += "</div>";

  html += '<div class="about-section">';
  html += "<h3>Voice Commands</h3>";
  html += "<p>All features are accessible via voice through your Wingman AI assistant. "
    + "Ask your wingman to record transactions, check your balance, open the dashboard, "
    + "create orders, and more.</p>";
  html += "</div>";

  // Remote access section
  const netData = await fetchJSON("/api/network");
  if (netData && netData.lan_ip && netData.lan_ip !== "127.0.0.1") {
    html += '<div class="about-section">';
    html += "<h3>Remote Access</h3>";
    html += "<p>Access this dashboard from a tablet or phone on the same network:</p>";
    html += '<div class="about-remote">';
    html += `<a href="${escHtml(netData.lan_url)}" target="_blank" class="lan-link about-lan-url">${escHtml(netData.lan_url)}</a>`;
    if (netData.qr_svg) {
      html += '<div class="about-qr">' + netData.qr_svg + "</div>";
    }
    html += "</div>";
    html += "</div>";
  }

  html += '<div class="about-section">';
  html += "<h3>Support</h3>";
  html += '<p>For documentation, updates, and support visit the official forum post on the Wingman AI Discord:</p>';
  html += '<p><a href="https://discord.com/channels/1173573578604687360/1477699669336260682" target="_blank" class="lan-link">Wingman AI Discord — SC Accountant</a></p>';
  html += "</div>";

  html += '<div class="about-section about-credits">';
  html += "<p>Author: Mallachi</p>";
  html += "</div>";

  html += "</div>";

  content.innerHTML = html;
}

// --- Tab Router ---

function loadTab(tab) {
  const content = document.getElementById("content");
  content.innerHTML = '<div class="loading">Loading...</div>';
  const helpEl = document.getElementById("tab-help-text");
  if (helpEl) helpEl.textContent = TAB_DESCRIPTIONS[tab] || "";

  switch (tab) {
    case "ledger": return renderLedger();
    case "fleet": return renderFleet();
    case "orders": return renderOrders();
    case "operations": return renderOperations();
    case "balancesheet": return renderBalanceSheet();
    case "banking": return renderBanking();
    case "portfolio": return renderPortfolio();
    case "opportunities": return renderOpportunities();
    case "group": return renderGroupSession();
    case "statistics": return renderStatistics();
    case "about": return renderAbout();
  }
}

// --- Ledger Tab ---

async function renderLedger() {
  const data = await fetchJSON(
    `/api/transactions?page=${currentPage}&period=${currentPeriod}&page_size=25`
  );
  if (!data) return showEmpty("No data available");

  const content = document.getElementById("content");
  if (data.transactions.length === 0) {
    return showEmpty("No transactions recorded");
  }

  const cols = ["date", "type", "category", "amount", "description", "notes", "location"];
  let html = `<table id="ledger-table">
    <thead>
      <tr>
        <th>Date</th><th>Type</th><th>Category</th>
        <th>Amount</th><th>Description</th><th>Notes</th><th>Location</th>
      </tr>
      ${buildFilterRow(cols)}
    </thead><tbody>`;

  for (let i = 0; i < data.transactions.length; i++) {
    const t = data.transactions[i];
    const cls = t.type === "income" ? "income" : "expense";
    const sign = t.type === "income" ? "+" : "-";
    html += `<tr class="clickable-row" data-idx="${i}"
      data-date="${escHtml(formatTimestamp(t.timestamp))}"
      data-type="${escHtml(t.type)}"
      data-category="${escHtml(t.category)}"
      data-amount="${t.amount}"
      data-description="${escHtml(t.description)}"
      data-notes="${escHtml(t.notes || "")}"
      data-location="${escHtml(t.location)}">
      <td>${formatTimestamp(t.timestamp)}</td>
      <td class="${cls}">${sign}</td>
      <td>${t.category}</td>
      <td class="num ${cls}">${fmt(t.amount)}</td>
      <td title="${escHtml(t.description)}">${escHtml(t.description)}</td>
      <td>${escHtml(t.notes || "")}</td>
      <td>${escHtml(t.location)}</td>
    </tr>`;
  }

  html += "</tbody></table>";
  html += renderPagination(data.page, data.total_pages);

  content.innerHTML = html;
  setupPagination();

  wireTableFilters("ledger-table", content);

  // Wire row clicks for editing
  content.querySelectorAll(".clickable-row").forEach((row) => {
    row.addEventListener("click", () => {
      const txn = data.transactions[parseInt(row.dataset.idx)];
      openEditTransactionForm(txn);
    });
  });
}

// --- Fleet Tab ---

async function renderFleet() {
  const [fleetData, summaryData] = await Promise.all([
    fetchJSON(`/api/fleet?status=active`),
    fetchJSON("/api/fleet/summary"),
  ]);

  const content = document.getElementById("content");
  if (!fleetData || fleetData.total === 0) {
    content.innerHTML = actionBar("+ Add Asset");
    wireActionButton(openAssetForm);
    return;
  }

  let html = actionBar("+ Add Asset");
  html += '<div class="summary-row">';
  html += summaryCard("Total Assets", summaryData.total_count || 0);
  html += summaryCard("Total Value", fmt(summaryData.total_value || 0));

  if (summaryData.by_type) {
    for (const [type, info] of Object.entries(summaryData.by_type)) {
      html += summaryCard(
        type.charAt(0).toUpperCase() + type.slice(1) + "s",
        info.count,
        fmt(info.value)
      );
    }
  }
  html += "</div>";

  const fleetCols = ["name", "type", "purchase", "market", "location", "notes"];
  html += `<table id="fleet-table">
    <thead><tr>
      <th>Name</th><th>Type</th><th>Purchase Price</th>
      <th>Market Value</th><th>Location</th><th>Notes</th>
    </tr>
    ${buildFilterRow(fleetCols)}
    </thead><tbody>`;

  for (let i = 0; i < fleetData.assets.length; i++) {
    const a = fleetData.assets[i];
    html += `<tr class="clickable-row" data-idx="${i}"
      data-name="${escHtml(a.name)}"
      data-type="${escHtml(a.asset_type)}"
      data-purchase="${a.purchase_price}"
      data-market="${a.market_value}"
      data-location="${escHtml(a.location)}"
      data-notes="${escHtml(a.notes)}">
      <td><strong>${escHtml(a.name)}</strong></td>
      <td>${a.asset_type}</td>
      <td class="num">${a.formatted_purchase_price}</td>
      <td class="num">${a.formatted_market_value}</td>
      <td>${escHtml(a.location)}</td>
      <td>${escHtml(a.notes)}</td>
    </tr>`;
  }

  html += "</tbody></table>";
  content.innerHTML = html;
  wireActionButton(openAssetForm);
  wireTableFilters("fleet-table", content);

  // Wire row clicks for editing
  content.querySelectorAll(".clickable-row").forEach((row) => {
    row.addEventListener("click", () => {
      const asset = fleetData.assets[parseInt(row.dataset.idx)];
      openEditAssetForm(asset);
    });
  });
}

// --- Orders (Planned Purchase/Sales Orders) ---

async function renderOrders() {
  const data = await fetchJSON("/api/planned-orders");
  const content = document.getElementById("content");

  if (!data) return showEmpty("No data available");

  let html = actionBar("+ Purchase Order", "+ Sales Order");

  // Summary cards
  const allOrders = data.orders || [];
  const openPO = allOrders.filter(o => o.order_type === "purchase" && (o.status === "open" || o.status === "partial"));
  const openSO = allOrders.filter(o => o.order_type === "sale" && (o.status === "open" || o.status === "partial"));
  const fulfilled = allOrders.filter(o => o.status === "fulfilled");
  const totalPlanned = openPO.reduce((s, o) => s + o.estimated_total, 0)
    + openSO.reduce((s, o) => s + o.estimated_total, 0);

  html += '<div class="summary-row">';
  html += summaryCard("Purchase Orders", openPO.length, "open/partial");
  html += summaryCard("Sales Orders", openSO.length, "open/partial");
  html += summaryCard("Fulfilled", fulfilled.length);
  if (totalPlanned > 0) html += summaryCard("Planned Value", fmt(totalPlanned));
  html += "</div>";

  if (allOrders.length === 0) {
    html += '<div class="empty-state"><div class="icon">--</div><div>No planned orders yet</div></div>';

    content.innerHTML = html;
    wireActionButton(() => openPlannedOrderForm("purchase"), 0);
    wireActionButton(() => openPlannedOrderForm("sale"), 1);
    return;
  }

  // Orders table
  const cols = ["type", "item", "progress", "price", "location", "status", "notes"];
  html += `<table id="orders-table">
    <thead><tr>
      <th>Type</th><th>Item</th><th>Progress</th>
      <th>Unit Price</th><th>Location</th><th>Status</th><th>Notes</th>
    </tr>
    ${buildFilterRow(cols)}
    </thead><tbody>`;

  for (let i = 0; i < allOrders.length; i++) {
    const o = allOrders[i];
    const statusCls = o.status === "fulfilled" ? "positive"
      : o.status === "cancelled" ? "negative"
      : o.status === "partial" ? "warning" : "";
    const typeBadge = o.order_type === "purchase"
      ? '<span class="badge badge-buy">BUY</span>'
      : '<span class="badge badge-sell">SELL</span>';

    const progressBar = `<div class="progress-bar-container">
      <div class="progress-bar-fill" style="width:${o.progress_pct}%"></div>
      <span class="progress-bar-text">${o.fulfilled_quantity}/${o.ordered_quantity} ${o.quantity_unit}</span>
    </div>`;

    html += `<tr class="clickable-row" data-idx="${i}"
      data-type="${o.order_type}"
      data-item="${escHtml(o.item_name)}"
      data-progress="${o.fulfilled_quantity}/${o.ordered_quantity}"
      data-price="${o.formatted_unit_price}"
      data-location="${escHtml(o.target_location)}"
      data-status="${o.status}"
      data-notes="${escHtml(o.notes)}">
      <td>${typeBadge}</td>
      <td><strong>${escHtml(o.item_name)}</strong></td>
      <td>${progressBar}</td>
      <td class="num">${o.formatted_unit_price || "-"}</td>
      <td>${escHtml(o.target_location)}</td>
      <td><span class="${statusCls}">${o.status}</span></td>
      <td>${escHtml(o.notes)}</td>
    </tr>`;
  }

  html += "</tbody></table>";
  content.innerHTML = html;

  wireActionButton(() => openPlannedOrderForm("purchase"), 0);
  wireActionButton(() => openPlannedOrderForm("sale"), 1);
  wireTableFilters("orders-table", content);

  // Wire row clicks for editing
  content.querySelectorAll(".clickable-row").forEach((row) => {
    row.addEventListener("click", () => {
      const order = allOrders[parseInt(row.dataset.idx)];
      openEditPlannedOrderForm(order);
    });
  });
}

function openPlannedOrderForm(orderType) {
  const title = orderType === "purchase" ? "New Purchase Order" : "New Sales Order";
  const body = `
    <div class="form-group">
      <label>Item Name</label>
      <input id="f-po-item" type="text" required placeholder="e.g. Prospector, Laranite">
    </div>
    <div class="form-group">
      <label>Quantity</label>
      <input id="f-po-qty" type="number" min="0.01" step="0.01" required value="1">
    </div>
    <div class="form-group">
      <label>Unit</label>
      <select id="f-po-unit">
        <option value="units">Units</option>
        <option value="scu">SCU</option>
        <option value="cscu">cSCU</option>
      </select>
    </div>
    <div class="form-group">
      <label>Target Price per Unit (aUEC)</label>
      <input id="f-po-price" type="number" min="0" step="1" value="0">
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-po-location" type="text" placeholder="Optional">
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-po-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  openModal(title, body, async () => {
    try {
      await postJSON("/api/planned-orders", {
        order_type: orderType,
        item_name: document.getElementById("f-po-item").value,
        ordered_quantity: parseFloat(document.getElementById("f-po-qty").value) || 1,
        quantity_unit: document.getElementById("f-po-unit").value,
        target_price_per_unit: parseFloat(document.getElementById("f-po-price").value) || 0,
        target_location: document.getElementById("f-po-location").value,
        notes: document.getElementById("f-po-notes").value,
      });
      showModalSuccess("Order created");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openEditPlannedOrderForm(order) {
  const typeBadge = order.order_type === "purchase" ? "Purchase Order" : "Sales Order";

  // Build fulfillment history
  let fulfillmentHtml = "";
  if (order.fulfillments && order.fulfillments.length > 0) {
    fulfillmentHtml = '<div class="form-group"><label>Fulfillment History</label><div class="fulfillment-list">';
    for (const f of order.fulfillments) {
      fulfillmentHtml += `<div class="fulfillment-entry">
        <span>${formatTimestamp(f.date)}</span>
        <span>${f.quantity} ${order.quantity_unit}</span>
        <span>${fmt(f.amount)}</span>
      </div>`;
    }
    fulfillmentHtml += "</div></div><hr>";
  }

  const body = `
    ${fulfillmentHtml}
    <div class="form-group">
      <label>Item Name</label>
      <input id="f-po-item" type="text" required>
    </div>
    <div class="form-group">
      <label>Ordered Quantity</label>
      <input id="f-po-qty" type="number" min="0.01" step="0.01" required>
    </div>
    <div class="form-group">
      <label>Unit</label>
      <select id="f-po-unit">
        <option value="units">Units</option>
        <option value="scu">SCU</option>
        <option value="cscu">cSCU</option>
      </select>
    </div>
    <div class="form-group">
      <label>Target Price per Unit (aUEC)</label>
      <input id="f-po-price" type="number" min="0" step="1">
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-po-location" type="text">
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-po-notes" rows="2"></textarea>
    </div>
    <hr>
    <div class="form-group form-actions-row">
      ${order.status !== "cancelled" ? '<button type="button" id="f-po-cancel" class="btn-warning">Cancel Order</button>' : ""}
      <button type="button" id="f-po-delete" class="btn-danger">Delete Order</button>
    </div>`;

  openModal("Edit " + typeBadge, body, async () => {
    try {
      await putJSON(`/api/planned-orders/${order.id}`, {
        item_name: document.getElementById("f-po-item").value,
        ordered_quantity: parseFloat(document.getElementById("f-po-qty").value),
        quantity_unit: document.getElementById("f-po-unit").value,
        target_price_per_unit: parseFloat(document.getElementById("f-po-price").value) || 0,
        target_location: document.getElementById("f-po-location").value,
        notes: document.getElementById("f-po-notes").value,
      });
      showModalSuccess("Order updated");
    } catch (err) {
      showModalError(err.message);
    }
  });

  // Pre-fill fields
  document.getElementById("f-po-item").value = order.item_name;
  document.getElementById("f-po-qty").value = order.ordered_quantity;
  document.getElementById("f-po-unit").value = order.quantity_unit;
  document.getElementById("f-po-price").value = order.target_price_per_unit || 0;
  document.getElementById("f-po-location").value = order.target_location || "";
  document.getElementById("f-po-notes").value = order.notes || "";

  // Wire cancel button
  const cancelBtn = document.getElementById("f-po-cancel");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", async () => {
      if (!confirm(`Cancel this ${order.order_type} order for ${order.item_name}?`)) return;
      try {
        await putJSON(`/api/planned-orders/${order.id}`, { status: "cancelled" });
        showModalSuccess("Order cancelled");
      } catch (err) {
        showModalError(err.message);
      }
    });
  }

  // Wire delete button
  document.getElementById("f-po-delete").addEventListener("click", async () => {
    if (!confirm(`Permanently delete this order for ${order.item_name}?`)) return;
    try {
      const res = await fetch(`/api/planned-orders/${order.id}`, { method: "DELETE" });
      if (!res.ok) {
        const err = await res.json();
        showModalError(err.error || "Delete failed");
        return;
      }
      showModalSuccess("Order deleted");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

// --- Operations (Income Statement) ---

async function renderOperations() {
  const data = await fetchJSON(`/api/income-statement?period=${currentPeriod}`);
  if (!data) return showEmpty("No data available");

  const content = document.getElementById("content");
  let html = '<div class="summary-row">';
  html += summaryCard("Revenue", fmt(data.revenue), null, "positive");
  html += summaryCard("COGS", fmt(data.cogs), null, "negative");
  html += summaryCard(
    "Gross Margin",
    fmt(data.gross_margin),
    fmtPct(data.gross_margin_pct)
  );
  html += summaryCard(
    "Net Profit",
    fmt(data.net_operating_profit),
    fmtPct(data.net_margin_pct),
    data.net_operating_profit >= 0 ? "positive" : "negative"
  );
  html += "</div>";

  // Revenue breakdown
  html += '<div class="statement-section"><h3>Revenue</h3>';
  if (data.revenue_by_category) {
    for (const [cat, amount] of Object.entries(data.revenue_by_category)) {
      const pct =
        data.revenue > 0 ? ((amount / data.revenue) * 100).toFixed(1) : "0";
      html += statementRow(cat, fmt(amount), pct + "%", true);
    }
  }
  html += statementRow("Total Revenue", fmt(data.revenue), "", false, true);
  html += "</div>";

  // COGS
  if (data.cogs > 0) {
    html += '<div class="statement-section"><h3>Cost of Goods Sold</h3>';
    if (data.cogs_by_category) {
      for (const [cat, amount] of Object.entries(data.cogs_by_category)) {
        html += statementRow(cat, "-" + fmt(amount), "", true);
      }
    }
    html += statementRow("Total COGS", "-" + fmt(data.cogs), "", false, true);
    html += "</div>";
  }

  // OpEx
  if (data.opex > 0) {
    html += '<div class="statement-section"><h3>Operating Expenses</h3>';
    if (data.opex_by_category) {
      for (const [cat, amount] of Object.entries(data.opex_by_category)) {
        html += statementRow(cat, "-" + fmt(amount), "", true);
      }
    }
    html += statementRow("Total OpEx", "-" + fmt(data.opex), "", false, true);
    html += "</div>";
  }

  // Activity margins
  if (data.activity_margins && data.activity_margins.length > 0) {
    html += '<div class="statement-section"><h3>By Activity</h3>';
    for (const am of data.activity_margins) {
      if (am.revenue > 0 || am.costs > 0) {
        const name = am.activity.replace(/_/g, " ");
        const cap = name.charAt(0).toUpperCase() + name.slice(1);
        html += statementRow(cap, fmt(am.margin), fmtPct(am.margin_pct), true);
      }
    }
    html += "</div>";
  }

  // CAPEX (investing expenses)
  if (data.capex > 0) {
    html += '<div class="statement-section"><h3>Capital Expenditures</h3>';
    if (data.capex_by_category) {
      for (const [cat, amount] of Object.entries(data.capex_by_category)) {
        html += statementRow(cat, "-" + fmt(amount), "", true);
      }
    }
    html += statementRow("Total CAPEX", "-" + fmt(data.capex), "", false, true);
    html += "</div>";
  }

  // Cash Flow Summary (derived from income statement data)
  const opInflows = data.revenue;
  const opOutflows = data.cogs + data.opex;
  const opNet = opInflows - opOutflows;
  const invNet = -data.capex;
  const netCash = opNet + invNet;

  html += '<div class="statement-section"><h3>Cash Flow</h3>';
  html += statementRow("Operating Inflows", "+" + fmt(opInflows), "", true);
  html += statementRow("Operating Outflows", "-" + fmt(opOutflows), "", true);
  html += statementRow("Operating Net", fmt(opNet), "", false, true);
  if (data.capex > 0) {
    html += statementRow("Investing Outflows", "-" + fmt(data.capex), "", true);
    html += statementRow("Investing Net", fmt(invNet), "", false, true);
  }
  html += statementRow("Net Cash Change", fmt(netCash), "", false, true);
  html += "</div>";

  content.innerHTML = html;
}

// --- Balance Sheet ---

async function renderBalanceSheet() {
  const data = await fetchJSON("/api/balance-sheet");
  if (!data) return showEmpty("No data available");

  const content = document.getElementById("content");
  const ast = data.assets;
  const liab = data.liabilities;
  const eq = data.equity;

  let html = actionBar("+ Set Balance");
  html += '<div class="summary-row">';
  html += summaryCard("Total Assets", fmt(ast.total), null, "positive");
  html += summaryCard("Total Liabilities", fmt(liab.total), null, "negative");
  html += summaryCard(
    "Net Worth",
    fmt(eq.net_worth),
    null,
    eq.net_worth >= 0 ? "positive" : "negative"
  );
  html += "</div>";

  html += '<div class="statement-section"><h3>Assets</h3>';
  html += statementRow("Cash", fmt(ast.cash));
  if (ast.ships > 0) html += statementRow(`Ships (${ast.ships_count})`, fmt(ast.ships));
  if (ast.components > 0) html += statementRow("Components", fmt(ast.components));
  if (ast.vehicles > 0) html += statementRow("Vehicles", fmt(ast.vehicles));
  if (ast.cargo > 0) html += statementRow("Cargo (Positions)", fmt(ast.cargo));
  if (ast.inventory > 0) html += statementRow("Inventory", fmt(ast.inventory));
  if (ast.receivables > 0) html += statementRow("Receivables", fmt(ast.receivables));
  html += statementRow("Total Assets", fmt(ast.total), "", false, true);
  html += "</div>";

  html += '<div class="statement-section"><h3>Liabilities</h3>';
  if (liab.payables > 0) {
    html += statementRow("Payables", fmt(liab.payables));
  } else {
    html += statementRow("(none)", "0 aUEC");
  }
  html += statementRow("Total Liabilities", fmt(liab.total), "", false, true);
  html += "</div>";

  html += '<div class="statement-section"><h3>Equity</h3>';
  html += statementRow("Net Worth", fmt(eq.net_worth), "", false, true);
  html += "</div>";

  content.innerHTML = html;
  wireActionButton(openBalanceForm);
}

// --- Portfolio ---

async function renderPortfolio() {
  const data = await fetchJSON("/api/positions");
  if (!data || data.total === 0) {
    const content = document.getElementById("content");
    content.innerHTML = actionBar("+ Record Purchase", "+ Record Sale");
    wireActionButton(openPurchaseForm, 0);
    wireActionButton(openSaleForm, 1);
    return;
  }

  const content = document.getElementById("content");
  const totalInvested = data.positions.reduce((s, p) => s + p.buy_total, 0);
  const totalPnl = data.positions.reduce((s, p) => s + p.unrealized_pnl, 0);

  let html = actionBar("+ Record Purchase", "+ Record Sale");
  html += '<div class="summary-row">';
  html += summaryCard("Positions", data.total);
  html += summaryCard("Invested", fmt(totalInvested));
  html += summaryCard(
    "Unrealized P&L",
    fmt(totalPnl),
    null,
    totalPnl >= 0 ? "positive" : "negative"
  );
  html += "</div>";

  const portCols = ["commodity", "qty", "invested", "market", "pnl"];
  html += `<table id="portfolio-table">
    <thead><tr>
      <th>Commodity</th><th>Qty</th><th>Invested</th>
      <th>Market Value</th><th>P&L</th>
    </tr>
    ${buildFilterRow(portCols)}
    </thead><tbody>`;

  for (const p of data.positions) {
    const cls = signClass(p.unrealized_pnl);
    const sign = p.unrealized_pnl >= 0 ? "+" : "";
    html += `<tr
      data-commodity="${escHtml(p.commodity_name)}"
      data-qty="${p.quantity}"
      data-invested="${p.buy_total}"
      data-market="${p.market_value || ""}"
      data-pnl="${p.unrealized_pnl}">
      <td>${escHtml(p.commodity_name)}</td>
      <td class="num">${p.quantity}</td>
      <td class="num">${p.formatted_invested}</td>
      <td class="num">${p.formatted_market}</td>
      <td class="num ${cls}">${sign}${p.formatted_pnl}</td>
    </tr>`;
  }

  html += "</tbody></table>";
  content.innerHTML = html;
  wireActionButton(openPurchaseForm, 0);
  wireActionButton(openSaleForm, 1);
  wireTableFilters("portfolio-table", content);
}

// --- Opportunities ---

async function renderOpportunities() {
  let url = "/api/opportunities";
  const params = [];
  if (selectedSystem) params.push(`system=${encodeURIComponent(selectedSystem)}`);
  if (selectedLocation) params.push(`location=${encodeURIComponent(selectedLocation)}`);
  if (selectedCargoScu > 0) params.push(`cargo_scu=${selectedCargoScu}`);
  if (params.length > 0) url += "?" + params.join("&");

  // Fetch opportunities + fresh player location in parallel
  const [data, freshPlayerLoc] = await Promise.all([
    fetchJSON(url),
    fetchJSON("/api/player-location"),
  ]);
  if (freshPlayerLoc) cachedPlayerLocation = freshPlayerLoc;

  const content = document.getElementById("content");

  // Build filter bar
  let html = '<div class="filter-bar">';
  html += buildSystemDropdown();
  html += buildLocationDropdown();
  html += buildShipDropdown();
  html += '<button id="opp-refresh-btn" class="refresh-btn" title="Refresh">Refresh</button>';
  html += "</div>";

  if (!data || data.total === 0) {
    html += '<div class="empty-state"><div class="icon">--</div><div>No trade opportunities available</div></div>';

    content.innerHTML = html;
    setupOpportunityFilters();
    return;
  }

  const oppCols = ["commodity", "buyloc", "buyterminal", "sellloc", "sellterminal", "available", "effective", "margin", "profit"];
  html += `<table id="opp-table">
    <thead><tr>
      <th>Commodity</th><th>Buy Location</th><th>Buy Terminal</th>
      <th>Sell Location</th><th>Sell Terminal</th>
      <th>Available</th><th>Effective</th>
      <th>Margin/SCU</th><th>Est. Profit</th>
    </tr>
    ${buildFilterRow(oppCols)}
    </thead><tbody>`;

  for (const o of data.opportunities) {
    html += `<tr
      data-commodity="${escHtml(o.commodity_name)}"
      data-buyloc="${escHtml(o.buy_location)}"
      data-buyterminal="${escHtml(o.buy_terminal)}"
      data-sellloc="${escHtml(o.sell_location)}"
      data-sellterminal="${escHtml(o.sell_terminal)}"
      data-available="${escHtml(o.formatted_available)}"
      data-effective="${escHtml(o.formatted_effective)}"
      data-margin="${escHtml(o.formatted_margin)}"
      data-profit="${escHtml(o.formatted_profit)}">
      <td>${escHtml(o.commodity_name)}</td>
      <td>${escHtml(o.buy_location)}</td>
      <td>${escHtml(o.buy_terminal)}</td>
      <td>${escHtml(o.sell_location)}</td>
      <td>${escHtml(o.sell_terminal)}</td>
      <td class="num">${o.formatted_available}</td>
      <td class="num">${o.formatted_effective}</td>
      <td class="num positive">${o.formatted_margin}/SCU</td>
      <td class="num positive">${o.formatted_profit}</td>
    </tr>`;
  }

  html += "</tbody></table>";
  content.innerHTML = html;
  setupOpportunityFilters();
  wireTableFilters("opp-table", content);
}

function buildSystemDropdown() {
  let html = '<select id="system-select" class="filter-select">';
  html += '<option value="">All Systems</option>';
  html += '<option value="Stanton">Stanton</option>';
  html += '<option value="Nyx">Nyx</option>';
  html += '<option value="Pyro">Pyro</option>';

  html += "</select>";
  return html;
}

function buildLocationDropdown() {
  let html = '<select id="location-select" class="filter-select">';
  html += '<option value="">All Locations</option>';

  // "My Location" from SC_LogReader (only shown if available)
  if (cachedPlayerLocation && cachedPlayerLocation.available && cachedPlayerLocation.location_name) {
    const locName = cachedPlayerLocation.location_name;
    html += `<option value="${escHtml(locName)}">My Location — ${escHtml(locName)}</option>`;
  }

  // All trade terminals from market database, filtered by selected system
  if (cachedLocations && cachedLocations.terminals) {
    let terminals = cachedLocations.terminals;
    if (selectedSystem) {
      terminals = terminals.filter(
        (t) => t.star_system.toLowerCase() === selectedSystem.toLowerCase()
      );
    }
    for (const t of terminals) {
      html += `<option value="${escHtml(t.name)}">${escHtml(t.name)}</option>`;
    }
  }

  html += "</select>";
  return html;
}

function buildShipDropdown() {
  let html = '<select id="ship-select" class="filter-select">';
  html += '<option value="0|">All Ships (no cargo limit)</option>';

  if (cachedShips && cachedShips.length > 0) {
    const sorted = [...cachedShips].sort((a, b) => {
      const nameA = `${a.manufacturer} ${a.name}`.toLowerCase();
      const nameB = `${b.manufacturer} ${b.name}`.toLowerCase();
      return nameA.localeCompare(nameB);
    });
    for (const ship of sorted) {
      const label = `${ship.manufacturer} ${ship.name}`;
      const val = `${ship.cargo_scu}|${label}`;
      html += `<option value="${escHtml(val)}">${escHtml(label)} (${ship.cargo_scu} SCU)</option>`;
    }
  }

  html += "</select>";
  return html;
}

function setupOpportunityFilters() {
  const sysSel = document.getElementById("system-select");
  const locSel = document.getElementById("location-select");
  const shipSel = document.getElementById("ship-select");
  const refreshBtn = document.getElementById("opp-refresh-btn");

  if (sysSel) {
    sysSel.value = selectedSystem;
    sysSel.addEventListener("change", () => {
      selectedSystem = sysSel.value;
      selectedLocation = ""; // Reset location when system changes
      renderOpportunities();
    });
  }

  if (locSel) {
    locSel.value = selectedLocation;
    locSel.addEventListener("change", () => {
      selectedLocation = locSel.value;
      renderOpportunities();
    });
  }

  if (shipSel) {
    // Restore selection by matching the stored label
    const storedVal = `${selectedCargoScu}|${selectedShipName}`;
    shipSel.value = storedVal;
    shipSel.addEventListener("change", () => {
      const parts = shipSel.value.split("|");
      selectedCargoScu = parseFloat(parts[0]) || 0;
      selectedShipName = parts.slice(1).join("|");
      renderOpportunities();
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", async () => {
      refreshBtn.disabled = true;
      refreshBtn.textContent = "Refreshing...";
      // Determine location for generation based on current filter
      let genLocation = "";
      if (selectedLocation && cachedPlayerLocation && cachedPlayerLocation.available) {
        // If "My Location" is selected, pass the player location name
        if (selectedLocation === cachedPlayerLocation.location_name) {
          genLocation = cachedPlayerLocation.location_name;
        } else {
          genLocation = selectedLocation;
        }
      } else if (selectedLocation) {
        genLocation = selectedLocation;
      }
      try {
        await fetch("/api/opportunities/refresh", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({location: genLocation, system: selectedSystem}),
        });
      } catch (e) { /* ignore */ }
      refreshBtn.textContent = "Refresh";
      refreshBtn.disabled = false;
      renderOpportunities();
    });
  }
}

// --- Banking Tab ---

async function renderBanking() {
  const data = await fetchJSON("/api/loans");
  const content = document.getElementById("content");

  let html = actionBar("+ New Loan Out", "+ New Loan In");

  if (data && data.summary) {
    const s = data.summary;
    html += '<div class="summary-row">';
    html += summaryCard("Total Lent Out", s.formatted_lent, null, "positive");
    html += summaryCard("Total Borrowed", s.formatted_borrowed, null, "negative");
    html += summaryCard("Interest Earning", s.formatted_interest_earning, null, "positive");
    html += summaryCard("Interest Owing", s.formatted_interest_owing, null, "negative");
    html += "</div>";
  }

  if (!data || data.total === 0) {
    html += '<div class="empty-state"><div class="icon">--</div><div>No loans recorded</div></div>';

    content.innerHTML = html;
    wireActionButton(() => openLoanForm("lent"), 0);
    wireActionButton(() => openLoanForm("borrowed"), 1);
    return;
  }

  const bankCols = ["counterparty", "type", "principal", "remaining", "rate", "interest", "totalowed", "startdate", "status"];
  html += `<table id="banking-table">
    <thead><tr>
      <th>Counterparty</th><th>Type</th><th>Principal</th>
      <th>Remaining</th><th>Rate</th><th>Interest Owed</th>
      <th>Total Owed</th><th>Start Date</th><th>Status</th><th></th>
    </tr>
    ${buildFilterRow(bankCols, 1)}
    </thead><tbody>`;

  for (let i = 0; i < data.loans.length; i++) {
    const ln = data.loans[i];
    const typeLabel = ln.loan_type === "lent" ? "Lent" : "Borrowed";
    const typeCls = ln.loan_type === "lent" ? "positive" : "negative";
    const statusCls = ln.status === "settled" ? "positive" : (ln.status === "defaulted" ? "negative" : "");
    html += `<tr class="clickable-row" data-idx="${i}"
      data-counterparty="${escHtml(ln.counterparty)}"
      data-type="${escHtml(typeLabel)}"
      data-principal="${ln.principal}"
      data-remaining="${ln.remaining_principal}"
      data-rate="${ln.interest_rate}% / ${ln.interest_period}"
      data-interest="${ln.accrued_interest}"
      data-totalowed="${ln.total_owed}"
      data-startdate="${(ln.start_date || "").substring(0, 10)}"
      data-status="${ln.status}">
      <td><strong>${escHtml(ln.counterparty)}</strong></td>
      <td class="${typeCls}">${typeLabel}</td>
      <td class="num">${ln.formatted_principal}</td>
      <td class="num">${ln.formatted_remaining}</td>
      <td class="num">${ln.interest_rate}% / ${ln.interest_period}</td>
      <td class="num">${ln.formatted_interest}</td>
      <td class="num">${ln.formatted_total_owed}</td>
      <td>${(ln.start_date || "").substring(0, 10)}</td>
      <td class="${statusCls}">${ln.status}</td>
      <td>${ln.status === "active" ? `<button class="btn-small pay-btn" data-idx="${i}">Pay</button> <button class="btn-small forgive-btn" data-idx="${i}">Forgive</button>` : ""}</td>
    </tr>`;
  }

  html += "</tbody></table>";
  content.innerHTML = html;
  wireActionButton(() => openLoanForm("lent"), 0);
  wireActionButton(() => openLoanForm("borrowed"), 1);
  wireTableFilters("banking-table", content);

  // Wire row clicks for editing
  content.querySelectorAll(".clickable-row").forEach((row) => {
    row.addEventListener("click", (e) => {
      // Don't open edit if an action button was clicked
      if (e.target.classList.contains("pay-btn") || e.target.classList.contains("forgive-btn")) return;
      const loan = data.loans[parseInt(row.dataset.idx)];
      openEditLoanForm(loan);
    });
  });

  // Wire pay buttons
  content.querySelectorAll(".pay-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const loan = data.loans[parseInt(btn.dataset.idx)];
      openPaymentForm(loan);
    });
  });

  // Wire forgive buttons
  content.querySelectorAll(".forgive-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const loan = data.loans[parseInt(btn.dataset.idx)];
      openForgiveForm(loan);
    });
  });
}

function openLoanForm(loanType) {
  const typeLabel = loanType === "lent" ? "Loan Out (I lend)" : "Loan In (I borrow)";
  const now = new Date().toISOString().substring(0, 16);

  const body = `
    <div class="form-group">
      <label>Counterparty (Player Name)</label>
      <input id="f-counterparty" type="text" required placeholder="e.g. PlayerName">
    </div>
    <div class="form-group">
      <label>Principal Amount (aUEC)</label>
      <input id="f-principal" type="number" min="1" step="1" required>
    </div>
    <div class="form-group">
      <label>Interest Rate (%)</label>
      <input id="f-interest-rate" type="number" min="0" step="0.1" value="0" required>
    </div>
    <div class="form-group">
      <label>Interest Period</label>
      <select id="f-interest-period" required>
        <option value="hour">Hourly</option>
        <option value="day">Daily</option>
        <option value="week" selected>Weekly</option>
        <option value="month">Monthly</option>
        <option value="year">Yearly</option>
      </select>
    </div>
    <div class="form-group">
      <label>Start Date</label>
      <input id="f-start-date" type="datetime-local" value="${now}">
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-loan-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  openModal(typeLabel, body, async () => {
    try {
      const startDate = document.getElementById("f-start-date").value;
      await postJSON("/api/loans", {
        loan_type: loanType,
        counterparty: document.getElementById("f-counterparty").value,
        principal: parseFloat(document.getElementById("f-principal").value),
        interest_rate: parseFloat(document.getElementById("f-interest-rate").value),
        interest_period: document.getElementById("f-interest-period").value,
        start_date: startDate ? new Date(startDate).toISOString() : "",
        notes: document.getElementById("f-loan-notes").value,
      });
      showModalSuccess("Loan created");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openEditLoanForm(loan) {
  const body = `
    <div class="form-group">
      <label>Counterparty</label>
      <input id="f-counterparty" type="text" required>
    </div>
    <div class="form-group">
      <label>Interest Rate (%)</label>
      <input id="f-interest-rate" type="number" min="0" step="0.1" required>
    </div>
    <div class="form-group">
      <label>Interest Period</label>
      <select id="f-interest-period" required>
        <option value="hour">Hourly</option>
        <option value="day">Daily</option>
        <option value="week">Weekly</option>
        <option value="month">Monthly</option>
        <option value="year">Yearly</option>
      </select>
    </div>
    <div class="form-group">
      <label>Start Date</label>
      <input id="f-start-date" type="datetime-local">
    </div>
    <div class="form-group">
      <label>Status</label>
      <select id="f-loan-status">
        <option value="active">Active</option>
        <option value="settled">Settled</option>
        <option value="defaulted">Defaulted</option>
      </select>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-loan-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  openModal("Edit Loan", body, async () => {
    try {
      const startDate = document.getElementById("f-start-date").value;
      await putJSON(`/api/loans/${loan.id}`, {
        counterparty: document.getElementById("f-counterparty").value,
        interest_rate: parseFloat(document.getElementById("f-interest-rate").value),
        interest_period: document.getElementById("f-interest-period").value,
        start_date: startDate ? new Date(startDate).toISOString() : loan.start_date,
        status: document.getElementById("f-loan-status").value,
        notes: document.getElementById("f-loan-notes").value,
      });
      showModalSuccess("Loan updated");
    } catch (err) {
      showModalError(err.message);
    }
  });

  // Pre-fill after modal is open
  document.getElementById("f-counterparty").value = loan.counterparty;
  document.getElementById("f-interest-rate").value = loan.interest_rate;
  document.getElementById("f-interest-period").value = loan.interest_period;
  // Convert ISO to datetime-local format
  if (loan.start_date) {
    document.getElementById("f-start-date").value = loan.start_date.substring(0, 16);
  }
  document.getElementById("f-loan-status").value = loan.status;
  document.getElementById("f-loan-notes").value = loan.notes || "";
}

function openPaymentForm(loan) {
  const body = `
    <div class="form-group">
      <label>Remaining Principal</label>
      <div class="form-value">${loan.formatted_remaining}</div>
    </div>
    <div class="form-group">
      <label>Accrued Interest</label>
      <div class="form-value">${loan.formatted_interest}</div>
    </div>
    <div class="form-group">
      <label>Total Owed</label>
      <div class="form-value"><strong>${loan.formatted_total_owed}</strong></div>
    </div>
    <hr>
    <div class="form-group">
      <label>Payment Amount (aUEC)</label>
      <input id="f-payment-amount" type="number" min="1" step="1" required>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-payment-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  const title = loan.loan_type === "lent"
    ? `Payment from ${loan.counterparty}`
    : `Payment to ${loan.counterparty}`;

  openModal(title, body, async () => {
    try {
      await postJSON(`/api/loans/${loan.id}/payment`, {
        amount: parseFloat(document.getElementById("f-payment-amount").value),
        notes: document.getElementById("f-payment-notes").value,
      });
      showModalSuccess("Payment recorded");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openForgiveForm(loan) {
  const body = `
    <div class="form-group">
      <label>Remaining Principal</label>
      <div class="form-value">${loan.formatted_remaining}</div>
    </div>
    <div class="form-group">
      <label>Accrued Interest</label>
      <div class="form-value">${loan.formatted_interest}</div>
    </div>
    <div class="form-group">
      <label>Total Owed</label>
      <div class="form-value"><strong>${loan.formatted_total_owed}</strong></div>
    </div>
    <hr>
    <div class="form-group">
      <label>Amount to Forgive (aUEC)</label>
      <input id="f-forgive-amount" type="number" min="1" step="1" required>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-forgive-notes" rows="2" placeholder="Reason for forgiveness"></textarea>
    </div>`;

  const title = loan.loan_type === "lent"
    ? `Forgive Loan to ${loan.counterparty}`
    : `Forgiveness from ${loan.counterparty}`;

  openModal(title, body, async () => {
    try {
      await postJSON(`/api/loans/${loan.id}/forgive`, {
        amount: parseFloat(document.getElementById("f-forgive-amount").value),
        notes: document.getElementById("f-forgive-notes").value,
      });
      showModalSuccess("Forgiveness recorded");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

// --- Statistics Tab ---

let statsCharts = []; // track chart instances for cleanup

function destroyStatsCharts() {
  for (const c of statsCharts) {
    try { c.destroy(); } catch (_) { /* ignore */ }
  }
  statsCharts = [];
}

// Shared dark theme defaults for Chart.js
const CHART_COLORS = {
  income: "#3fb950",
  expense: "#f85149",
  net: "#58a6ff",
  balance: "#d2a8ff",
  grid: "rgba(48, 54, 61, 0.6)",
  text: "#8b949e",
  palette: [
    "#58a6ff", "#3fb950", "#f85149", "#d29922", "#db6d28",
    "#d2a8ff", "#a5d6ff", "#7ee787", "#ffa657", "#ff7b72",
    "#79c0ff", "#56d364", "#e3b341", "#f0883e", "#bc8cff",
  ],
};

function chartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: CHART_COLORS.text, font: { size: 11 } } },
      tooltip: { backgroundColor: "#161b22", titleColor: "#e6edf3", bodyColor: "#e6edf3", borderColor: "#30363d", borderWidth: 1 },
    },
    scales: {
      x: { ticks: { color: CHART_COLORS.text, font: { size: 10 } }, grid: { color: CHART_COLORS.grid } },
      y: { ticks: { color: CHART_COLORS.text, font: { size: 10 } }, grid: { color: CHART_COLORS.grid } },
    },
  };
}

async function renderStatistics() {
  destroyStatsCharts();
  const content = document.getElementById("content");

  // Default date range: last 30 days
  const now = new Date();
  const thirtyAgo = new Date(now);
  thirtyAgo.setDate(thirtyAgo.getDate() - 30);
  const defaultFrom = thirtyAgo.toISOString().substring(0, 10);
  const defaultTo = now.toISOString().substring(0, 10);

  let html = '<div class="stats-controls">';
  html += '<label>From <input type="date" id="stats-from" value="' + defaultFrom + '"></label>';
  html += '<label>To <input type="date" id="stats-to" value="' + defaultTo + '"></label>';
  html += '<select id="stats-granularity">';
  html += '<option value="daily" selected>Daily</option>';
  html += '<option value="weekly">Weekly</option>';
  html += '<option value="monthly">Monthly</option>';
  html += '</select>';
  html += '<button id="stats-apply" class="btn-primary" style="padding:4px 14px;font-size:12px;">Apply</button>';
  html += '</div>';

  // Summary cards
  html += '<div class="summary-row" id="stats-summary"></div>';

  // Chart grid
  html += '<div class="stats-grid">';
  html += '<div class="chart-panel chart-wide"><h3>Revenue vs Expenses</h3><div class="chart-container"><canvas id="chart-rev-exp"></canvas></div></div>';
  html += '<div class="chart-panel chart-wide"><h3>Net Profit</h3><div class="chart-container"><canvas id="chart-net"></canvas></div></div>';
  html += '<div class="chart-panel chart-wide"><h3>Running Balance</h3><div class="chart-container"><canvas id="chart-balance"></canvas></div></div>';
  html += '<div class="chart-panel"><h3>Income by Category</h3><div class="chart-container chart-square"><canvas id="chart-income-cat"></canvas></div></div>';
  html += '<div class="chart-panel"><h3>Expenses by Category</h3><div class="chart-container chart-square"><canvas id="chart-expense-cat"></canvas></div></div>';
  html += '<div class="chart-panel"><h3>Activity Breakdown</h3><div class="chart-container chart-square"><canvas id="chart-activity"></canvas></div></div>';
  html += '<div class="chart-panel chart-wide"><h3>Top Commodities (Net Profit)</h3><div class="chart-container"><canvas id="chart-commodities"></canvas></div></div>';
  html += '</div>';

  content.innerHTML = html;

  // Wire apply button and initial load
  const applyBtn = document.getElementById("stats-apply");
  applyBtn.addEventListener("click", () => loadStatsData());
  document.getElementById("stats-from").addEventListener("change", () => loadStatsData());
  document.getElementById("stats-to").addEventListener("change", () => loadStatsData());
  document.getElementById("stats-granularity").addEventListener("change", () => loadStatsData());

  loadStatsData();
}

async function loadStatsData() {
  const dateFrom = document.getElementById("stats-from").value;
  const dateTo = document.getElementById("stats-to").value;
  const granularity = document.getElementById("stats-granularity").value;

  const params = [];
  if (dateFrom) params.push("date_from=" + dateFrom);
  if (dateTo) params.push("date_to=" + dateTo);
  params.push("granularity=" + granularity);

  const data = await fetchJSON("/api/statistics?" + params.join("&"));
  if (!data) return;

  destroyStatsCharts();

  // Summary cards
  const sumEl = document.getElementById("stats-summary");
  if (sumEl && data.totals) {
    const t = data.totals;
    sumEl.innerHTML =
      summaryCard("Transactions", t.transaction_count) +
      summaryCard("Total Income", fmt(t.income), null, "positive") +
      summaryCard("Total Expenses", fmt(t.expenses), null, "negative") +
      summaryCard("Net Profit", fmt(t.net), null, t.net >= 0 ? "positive" : "negative");
  }

  const tl = data.timeline || [];
  const labels = tl.map(d => d.date);

  // 1) Revenue vs Expenses — bar chart
  statsCharts.push(new Chart(document.getElementById("chart-rev-exp"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: "Income", data: tl.map(d => d.income), backgroundColor: CHART_COLORS.income + "cc", borderColor: CHART_COLORS.income, borderWidth: 1 },
        { label: "Expenses", data: tl.map(d => d.expenses), backgroundColor: CHART_COLORS.expense + "cc", borderColor: CHART_COLORS.expense, borderWidth: 1 },
      ],
    },
    options: { ...chartDefaults(), plugins: { ...chartDefaults().plugins, legend: { display: true, labels: { color: CHART_COLORS.text } } } },
  }));

  // 2) Net Profit — line with gradient fill
  const netCtx = document.getElementById("chart-net").getContext("2d");
  const netGradient = netCtx.createLinearGradient(0, 0, 0, 250);
  netGradient.addColorStop(0, "rgba(88, 166, 255, 0.3)");
  netGradient.addColorStop(1, "rgba(88, 166, 255, 0.0)");
  statsCharts.push(new Chart(netCtx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Net Profit",
        data: tl.map(d => d.net),
        borderColor: CHART_COLORS.net,
        backgroundColor: netGradient,
        fill: true,
        tension: 0.3,
        pointRadius: tl.length > 60 ? 0 : 3,
        pointHoverRadius: 5,
      }],
    },
    options: { ...chartDefaults(), plugins: { ...chartDefaults().plugins, legend: { display: false } } },
  }));

  // 3) Running Balance — area chart
  const balCtx = document.getElementById("chart-balance").getContext("2d");
  const balGradient = balCtx.createLinearGradient(0, 0, 0, 250);
  balGradient.addColorStop(0, "rgba(210, 168, 255, 0.3)");
  balGradient.addColorStop(1, "rgba(210, 168, 255, 0.0)");
  statsCharts.push(new Chart(balCtx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "Balance",
        data: tl.map(d => d.balance),
        borderColor: CHART_COLORS.balance,
        backgroundColor: balGradient,
        fill: true,
        tension: 0.3,
        pointRadius: tl.length > 60 ? 0 : 3,
        pointHoverRadius: 5,
      }],
    },
    options: { ...chartDefaults(), plugins: { ...chartDefaults().plugins, legend: { display: false } } },
  }));

  // 4) Income by Category — doughnut
  const incCats = data.income_by_category || {};
  statsCharts.push(new Chart(document.getElementById("chart-income-cat"), {
    type: "doughnut",
    data: {
      labels: Object.keys(incCats),
      datasets: [{
        data: Object.values(incCats),
        backgroundColor: CHART_COLORS.palette,
        borderColor: "#0d1117",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: CHART_COLORS.text, font: { size: 10 }, padding: 8 } },
        tooltip: chartDefaults().plugins.tooltip,
      },
    },
  }));

  // 5) Expenses by Category — doughnut
  const expCats = data.expense_by_category || {};
  statsCharts.push(new Chart(document.getElementById("chart-expense-cat"), {
    type: "doughnut",
    data: {
      labels: Object.keys(expCats),
      datasets: [{
        data: Object.values(expCats),
        backgroundColor: CHART_COLORS.palette.slice().reverse(),
        borderColor: "#0d1117",
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: CHART_COLORS.text, font: { size: 10 }, padding: 8 } },
        tooltip: chartDefaults().plugins.tooltip,
      },
    },
  }));

  // 6) Activity Breakdown — horizontal bar
  const actData = data.activity_breakdown || {};
  const actLabels = Object.keys(actData);
  statsCharts.push(new Chart(document.getElementById("chart-activity"), {
    type: "bar",
    data: {
      labels: actLabels.map(a => a.charAt(0).toUpperCase() + a.slice(1).replace(/_/g, " ")),
      datasets: [
        { label: "Income", data: actLabels.map(a => actData[a].income), backgroundColor: CHART_COLORS.income + "cc" },
        { label: "Expenses", data: actLabels.map(a => actData[a].expenses), backgroundColor: CHART_COLORS.expense + "cc" },
      ],
    },
    options: {
      ...chartDefaults(),
      indexAxis: "y",
      plugins: { ...chartDefaults().plugins, legend: { display: true, labels: { color: CHART_COLORS.text } } },
    },
  }));

  // 7) Top Commodities — horizontal bar
  const comms = data.top_commodities || [];
  statsCharts.push(new Chart(document.getElementById("chart-commodities"), {
    type: "bar",
    data: {
      labels: comms.map(c => c.name),
      datasets: [{
        label: "Net Profit",
        data: comms.map(c => c.profit),
        backgroundColor: comms.map(c => c.profit >= 0 ? CHART_COLORS.income + "cc" : CHART_COLORS.expense + "cc"),
        borderColor: comms.map(c => c.profit >= 0 ? CHART_COLORS.income : CHART_COLORS.expense),
        borderWidth: 1,
      }],
    },
    options: {
      ...chartDefaults(),
      indexAxis: "y",
      plugins: { ...chartDefaults().plugins, legend: { display: false } },
    },
  }));
}

// --- Table Filters ---

function buildFilterRow(cols, extraCols) {
  let cells = cols.map(c => `<th><input type="text" class="col-filter" data-col="${c}" placeholder="Filter..."></th>`).join("");
  for (let i = 0; i < (extraCols || 0); i++) cells += "<th></th>";
  return `<tr class="filter-row">${cells}</tr>`;
}

function wireTableFilters(tableId, container) {
  const el = container || document;
  el.querySelectorAll(`#${tableId} .col-filter`).forEach((input) => {
    input.addEventListener("input", () => {
      const filters = {};
      el.querySelectorAll(`#${tableId} .col-filter`).forEach((f) => {
        const val = f.value.trim().toLowerCase();
        if (val) filters[f.dataset.col] = val;
      });
      el.querySelectorAll(`#${tableId} tbody tr`).forEach((row) => {
        let visible = true;
        for (const [col, term] of Object.entries(filters)) {
          const cellVal = (row.dataset[col] || "").toLowerCase();
          if (!cellVal.includes(term)) { visible = false; break; }
        }
        row.style.display = visible ? "" : "none";
      });
    });
  });
}

// --- UI Helpers ---

function showEmpty(message) {
  document.getElementById("content").innerHTML =
    `<div class="empty-state"><div class="icon">--</div><div>${message}</div></div>`;
}

function summaryCard(label, value, sub, colorClass) {
  const cls = colorClass ? ` ${colorClass}` : "";
  return `<div class="summary-card">
    <div class="label">${label}</div>
    <div class="value${cls}">${value}</div>
    ${sub ? `<div class="sub">${sub}</div>` : ""}
  </div>`;
}

function statementRow(label, value, extra, indent, isTotal) {
  const cls = [];
  if (indent) cls.push("indent");
  if (isTotal) cls.push("total");
  return `<div class="statement-row ${cls.join(" ")}">
    <span class="label">${label}</span>
    <span class="value">${value}${extra ? ` <small style="color:var(--text-muted)">${extra}</small>` : ""}</span>
  </div>`;
}

function renderPagination(page, totalPages) {
  return `<div class="pagination">
    <button class="prev-btn" ${page <= 0 ? "disabled" : ""}>Prev</button>
    <span class="page-info">Page ${page + 1} of ${totalPages}</span>
    <button class="next-btn" ${page + 1 >= totalPages ? "disabled" : ""}>Next</button>
  </div>`;
}

function setupPagination() {
  const prev = document.querySelector(".prev-btn");
  const next = document.querySelector(".next-btn");
  if (prev) {
    prev.addEventListener("click", () => {
      if (currentPage > 0) { currentPage--; loadTab(currentTab); }
    });
  }
  if (next) {
    next.addEventListener("click", () => {
      currentPage++;
      loadTab(currentTab);
    });
  }
}

// --- Modal System ---

let _modalSubmitHandler = null;

function setupModal() {
  const overlay = document.getElementById("modal-overlay");
  const closeBtn = document.getElementById("modal-close");
  const cancelBtn = document.getElementById("modal-cancel");
  const form = document.getElementById("modal-form");

  closeBtn.addEventListener("click", closeModal);
  cancelBtn.addEventListener("click", closeModal);

  // Close on overlay click (but not modal body)
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });

  // Close on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && overlay.style.display !== "none") {
      closeModal();
    }
  });

  // Form submit
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (_modalSubmitHandler) _modalSubmitHandler();
  });
}

function openModal(title, bodyHtml, onSubmit) {
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHtml;
  document.getElementById("modal-status").textContent = "";
  document.getElementById("modal-status").className = "modal-status";
  document.getElementById("modal-overlay").style.display = "flex";
  _modalSubmitHandler = onSubmit;

  // Focus first input
  const firstInput = document.querySelector("#modal-body input, #modal-body select");
  if (firstInput) setTimeout(() => firstInput.focus(), 50);
}

function closeModal() {
  document.getElementById("modal-overlay").style.display = "none";
  _modalSubmitHandler = null;
}

function showModalSuccess(msg) {
  const status = document.getElementById("modal-status");
  status.textContent = msg;
  status.className = "modal-status success";
  setTimeout(() => {
    closeModal();
    loadBalance();
    loadTab(currentTab);
  }, 800);
}

function showModalError(msg) {
  const status = document.getElementById("modal-status");
  status.textContent = msg;
  status.className = "modal-status error";
}

async function postJSON(url, data) {
  const res = await fetch(API + url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

async function putJSON(url, data) {
  const res = await fetch(API + url, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || `HTTP ${res.status}`);
  return json;
}

// --- Category Cache ---

async function loadCategories() {
  cachedCategories = await fetchJSON("/api/categories");
}

function buildCategoryOptions() {
  if (!cachedCategories) return '<option value="">Loading...</option>';
  let html = '<option value="">-- Select --</option>';
  const income = cachedCategories.filter((c) => c.type === "income");
  const expense = cachedCategories.filter((c) => c.type === "expense");

  html += '<optgroup label="Income">';
  for (const c of income) html += `<option value="${c.value}">${escHtml(c.label)}</option>`;
  html += "</optgroup>";

  html += '<optgroup label="Expense">';
  for (const c of expense) html += `<option value="${c.value}">${escHtml(c.label)}</option>`;
  html += "</optgroup>";

  return html;
}

// --- Form Functions ---

function openTransactionForm() {
  const body = `
    <div class="form-group">
      <label>Category</label>
      <select id="f-category" required>${buildCategoryOptions()}</select>
    </div>
    <div class="form-group">
      <label>Amount (aUEC)</label>
      <input id="f-amount" type="number" min="1" step="1" required>
    </div>
    <div class="form-group">
      <label>Description</label>
      <input id="f-description" type="text" required>
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-location" type="text" placeholder="Optional">
    </div>
    <div class="form-group">
      <label>Tags</label>
      <input id="f-tags" type="text" placeholder="Comma-separated, optional">
    </div>`;

  openModal("Add Transaction", body, async () => {
    try {
      await postJSON("/api/transactions", {
        category: document.getElementById("f-category").value,
        amount: parseFloat(document.getElementById("f-amount").value),
        description: document.getElementById("f-description").value,
        location: document.getElementById("f-location").value,
        tags: document.getElementById("f-tags").value,
      });
      showModalSuccess("Transaction recorded");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openAssetForm() {
  const body = `
    <div class="form-group">
      <label>Asset Type</label>
      <select id="f-asset-type" required>
        <option value="">-- Select --</option>
        <option value="ship">Ship</option>
        <option value="vehicle">Vehicle</option>
        <option value="component">Component</option>
        <option value="equipment">Equipment</option>
      </select>
    </div>
    <div class="form-group">
      <label>Name</label>
      <input id="f-name" type="text" required placeholder="e.g. My Cutlass Black">
    </div>
    <div class="form-group">
      <label>Purchase Price (aUEC)</label>
      <input id="f-purchase-price" type="number" min="0" step="1" value="0">
    </div>
    <div class="form-group">
      <label>Ship Model</label>
      <input id="f-ship-model" type="text" placeholder="Optional, e.g. Cutlass Black">
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-asset-location" type="text" placeholder="Optional">
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  openModal("Add Asset", body, async () => {
    try {
      await postJSON("/api/fleet", {
        asset_type: document.getElementById("f-asset-type").value,
        name: document.getElementById("f-name").value,
        purchase_price: parseFloat(document.getElementById("f-purchase-price").value) || 0,
        ship_model: document.getElementById("f-ship-model").value,
        location: document.getElementById("f-asset-location").value,
        notes: document.getElementById("f-notes").value,
      });
      showModalSuccess("Asset registered");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openBalanceForm() {
  const body = `
    <div class="form-group">
      <label>Current Balance (aUEC)</label>
      <input id="f-balance" type="number" step="1" required>
      <div class="hint">This will overwrite the current balance. Use this to correct or initialize your aUEC amount.</div>
    </div>`;

  openModal("Set Balance", body, async () => {
    try {
      await postJSON("/api/balance", {
        amount: parseFloat(document.getElementById("f-balance").value),
      });
      showModalSuccess("Balance updated");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openPurchaseForm() {
  const body = `
    <div class="form-group">
      <label>Commodity Name</label>
      <input id="f-commodity" type="text" required placeholder="e.g. Laranite">
    </div>
    <div class="form-group">
      <label>Quantity (SCU)</label>
      <input id="f-quantity" type="number" min="0.01" step="0.01" required>
    </div>
    <div class="form-group">
      <label>Price per SCU (aUEC)</label>
      <input id="f-price" type="number" min="0.01" step="0.01" required>
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-pos-location" type="text" placeholder="Optional">
    </div>`;

  openModal("Record Purchase", body, async () => {
    try {
      await postJSON("/api/positions", {
        commodity_name: document.getElementById("f-commodity").value,
        quantity_scu: parseFloat(document.getElementById("f-quantity").value),
        price_per_scu: parseFloat(document.getElementById("f-price").value),
        location: document.getElementById("f-pos-location").value,
      });
      showModalSuccess("Purchase recorded");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openEditTransactionForm(txn) {
  const body = `
    <div class="form-group">
      <label>Category</label>
      <select id="f-category" required>${buildCategoryOptions()}</select>
    </div>
    <div class="form-group">
      <label>Amount (aUEC)</label>
      <input id="f-amount" type="number" min="1" step="1" required>
    </div>
    <div class="form-group">
      <label>Description</label>
      <input id="f-description" type="text" required>
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-location" type="text" placeholder="Optional">
    </div>
    <div class="form-group">
      <label>Tags</label>
      <input id="f-tags" type="text" placeholder="Comma-separated, optional">
    </div>
    <hr>
    <div class="form-group">
      <button type="button" id="f-delete-txn" class="btn-danger">Delete Transaction</button>
    </div>`;

  openModal("Edit Transaction", body, async () => {
    try {
      await putJSON(`/api/transactions/${txn.id}`, {
        category: document.getElementById("f-category").value,
        amount: parseFloat(document.getElementById("f-amount").value),
        description: document.getElementById("f-description").value,
        location: document.getElementById("f-location").value,
        tags: document.getElementById("f-tags").value,
      });
      showModalSuccess("Transaction updated");
    } catch (err) {
      showModalError(err.message);
    }
  });

  // Pre-fill after modal is open
  document.getElementById("f-category").value = txn.category;
  document.getElementById("f-amount").value = txn.amount;
  document.getElementById("f-description").value = txn.description;
  document.getElementById("f-location").value = txn.location || "";
  document.getElementById("f-tags").value = (txn.tags || []).join(", ");

  // Wire delete button
  document.getElementById("f-delete-txn").addEventListener("click", async () => {
    if (!confirm(`Delete this transaction?\n\n${txn.description}\n${txn.amount} aUEC`)) return;
    try {
      const res = await fetch(`/api/transactions/${txn.id}`, {method: "DELETE"});
      if (!res.ok) {
        const err = await res.json();
        showModalError(err.error || "Delete failed");
        return;
      }
      showModalSuccess("Transaction deleted");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openEditAssetForm(asset) {
  const body = `
    <div class="form-group">
      <label>Asset Type</label>
      <select id="f-asset-type" required>
        <option value="ship">Ship</option>
        <option value="vehicle">Vehicle</option>
        <option value="component">Component</option>
        <option value="equipment">Equipment</option>
      </select>
    </div>
    <div class="form-group">
      <label>Name</label>
      <input id="f-name" type="text" required>
    </div>
    <div class="form-group">
      <label>Purchase Price (aUEC)</label>
      <input id="f-purchase-price" type="number" min="0" step="1">
    </div>
    <div class="form-group">
      <label>Ship Model</label>
      <input id="f-ship-model" type="text" placeholder="Optional">
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-asset-location" type="text" placeholder="Optional">
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  openModal("Edit Asset", body, async () => {
    try {
      await putJSON(`/api/fleet/${asset.id}`, {
        asset_type: document.getElementById("f-asset-type").value,
        name: document.getElementById("f-name").value,
        purchase_price: parseFloat(document.getElementById("f-purchase-price").value) || 0,
        ship_model: document.getElementById("f-ship-model").value,
        location: document.getElementById("f-asset-location").value,
        notes: document.getElementById("f-notes").value,
      });
      showModalSuccess("Asset updated");
    } catch (err) {
      showModalError(err.message);
    }
  });

  // Pre-fill after modal is open
  document.getElementById("f-asset-type").value = asset.asset_type;
  document.getElementById("f-name").value = asset.name;
  document.getElementById("f-purchase-price").value = asset.purchase_price || 0;
  document.getElementById("f-ship-model").value = asset.ship_model || "";
  document.getElementById("f-asset-location").value = asset.location || "";
  document.getElementById("f-notes").value = asset.notes || "";

  // Add delete button to modal footer
  const modalActions = document.querySelector(".modal-actions");
  if (modalActions) {
    const deleteBtn = document.createElement("button");
    deleteBtn.type = "button";
    deleteBtn.className = "btn-danger";
    deleteBtn.textContent = "Delete Asset";
    deleteBtn.addEventListener("click", async () => {
      if (!confirm(`Delete "${asset.name}"? This cannot be undone.`)) return;
      try {
        const resp = await fetch(`/api/fleet/${asset.id}`, {method: "DELETE"});
        if (!resp.ok) {
          const err = await resp.json();
          showModalError(err.error || "Delete failed");
          return;
        }
        closeModal();
        renderFleet();
      } catch (err) {
        showModalError(err.message);
      }
    });
    modalActions.insertBefore(deleteBtn, modalActions.firstChild);
  }
}

function openSaleForm() {
  const body = `
    <div class="form-group">
      <label>Commodity Name</label>
      <input id="f-sale-commodity" type="text" required placeholder="e.g. Laranite">
    </div>
    <div class="form-group">
      <label>Quantity (SCU)</label>
      <input id="f-sale-quantity" type="number" min="0.01" step="0.01" required>
    </div>
    <div class="form-group">
      <label>Sale Price per SCU (aUEC)</label>
      <input id="f-sale-price" type="number" min="0.01" step="0.01" required>
    </div>
    <div class="form-group">
      <label>Location</label>
      <input id="f-sale-location" type="text" placeholder="Optional">
    </div>`;

  openModal("Record Sale", body, async () => {
    try {
      await postJSON("/api/sales", {
        commodity_name: document.getElementById("f-sale-commodity").value,
        quantity_scu: parseFloat(document.getElementById("f-sale-quantity").value),
        price_per_scu: parseFloat(document.getElementById("f-sale-price").value),
        location: document.getElementById("f-sale-location").value,
      });
      showModalSuccess("Sale recorded");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

// --- Action Bar Helper ---

// --- Group Session Tab ---

async function renderGroupSession() {
  const data = await fetchJSON("/api/group-session");
  const content = document.getElementById("content");

  if (!data) {
    content.innerHTML = '<div class="empty-state"><div class="icon">--</div><div>Could not load group session data</div></div>';
    return;
  }

  const isActive = data.active;

  let html = "";

  // Action bar — same pattern as Portfolio and Banking tabs
  if (isActive) {
    html += actionBar("+ Group Buy", "+ Group Sell");
  }

  // Status bar
  html += '<div class="group-status-bar">';
  html += `<span class="status-dot ${isActive ? "active" : "inactive"}"></span>`;
  html += `<span class="status-text">${isActive ? "Group session active since " + formatTimestamp(data.started_at) : "No active group session"}</span>`;
  html += '<div class="group-status-actions">';
  if (isActive) {
    html += '<button class="btn-stop-session" id="group-stop-btn">Stop Session</button>';
  } else {
    html += '<button class="btn-start-session" id="group-start-btn">Start Group Session</button>';
  }
  html += "</div>";
  html += "</div>";

  if (!isActive) {
    // Fetch and display past sessions
    const history = await fetchJSON("/api/group-session/history") || [];
    if (history.length > 0) {
      const histCols = ["started", "ended", "transactions", "income", "expenses", "net"];
      html += `<table id="group-history-table">
      <thead>
        <tr>
          <th>Started</th><th>Ended</th><th>Transactions</th>
          <th>Income</th><th>Expenses</th><th>Net</th>
        </tr>
        ${buildFilterRow(histCols)}
      </thead><tbody>`;
      for (let i = 0; i < history.length; i++) {
        const s = history[i];
        const netCls = s.net >= 0 ? "positive" : "negative";
        html += `<tr class="clickable-row" data-idx="${i}"
          data-started="${escHtml(formatTimestamp(s.started_at))}"
          data-ended="${escHtml(formatTimestamp(s.ended_at))}"
          data-transactions="${s.transaction_count}"
          data-income="${s.total_income}"
          data-expenses="${s.total_expenses}"
          data-net="${s.net}">
          <td>${formatTimestamp(s.started_at)}</td>
          <td>${formatTimestamp(s.ended_at)}</td>
          <td class="num">${s.transaction_count}</td>
          <td class="num positive">${fmt(s.total_income)}</td>
          <td class="num negative">${fmt(s.total_expenses)}</td>
          <td class="num ${netCls}">${fmt(s.net)}</td>
        </tr>`;
      }
      html += "</tbody></table>";
    } else {
      html += '<div class="empty-state"><div class="icon">--</div><div>No past group sessions</div></div>';
    }

    content.innerHTML = html;
    wireTableFilters("group-history-table", content);

    // Wire history row clicks to open session detail
    content.querySelectorAll("#group-history-table .clickable-row").forEach((row) => {
      row.addEventListener("click", () => {
        const s = history[parseInt(row.dataset.idx)];
        renderGroupSessionDetail(s.id);
      });
    });

    const startBtn = document.getElementById("group-start-btn");
    if (startBtn) {
      startBtn.addEventListener("click", async () => {
        await fetch("/api/group-session/start", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({players: [
            {name: "Your Cut", percentage: 50},
            {name: "Player 2", percentage: 50},
          ]}),
        });
        renderGroupSession();
      });
    }
    return;
  }

  // Active session layout: ledger on left, calculator on right
  html += '<div class="group-layout">';

  // Left: group ledger
  html += '<div class="group-ledger">';
  html += '<div class="summary-row">';
  html += summaryCard("Income", data.formatted_income, `${data.transaction_count} transactions`, "positive");
  html += summaryCard("Expenses", data.formatted_expenses, null, "negative");
  html += summaryCard("Net", data.formatted_net, null, data.net >= 0 ? "positive" : "negative");
  html += "</div>";

  if (data.transactions && data.transactions.length > 0) {
    const groupCols = ["date", "type", "category", "amount", "description", "notes", "location"];
    html += `<table id="group-txn-table">
    <thead>
      <tr>
        <th>Date</th><th>Type</th><th>Category</th>
        <th>Amount</th><th>Description</th><th>Notes</th><th>Location</th>
      </tr>
      ${buildFilterRow(groupCols)}
    </thead><tbody>`;
    for (let i = 0; i < data.transactions.length; i++) {
      const t = data.transactions[i];
      const cls = t.type === "income" ? "income" : "expense";
      const sign = t.type === "income" ? "+" : "-";
      html += `<tr class="clickable-row" data-idx="${i}"
        data-date="${escHtml(formatTimestamp(t.timestamp))}"
        data-type="${escHtml(t.type)}"
        data-category="${escHtml(t.category)}"
        data-amount="${t.amount}"
        data-description="${escHtml(t.description)}"
        data-notes="${escHtml(t.notes || "")}"
        data-location="${escHtml(t.location || "")}">
        <td>${formatTimestamp(t.timestamp)}</td>
        <td class="${cls}">${sign}</td>
        <td>${escHtml(t.category)}</td>
        <td class="num ${cls}">${fmt(t.amount)}</td>
        <td title="${escHtml(t.description)}">${escHtml(t.description)}</td>
        <td>${escHtml(t.notes || "")}</td>
        <td>${escHtml(t.location || "")}</td>
      </tr>`;
    }
    html += "</tbody></table>";
  } else {
    html += '<div class="empty-state"><div class="icon">--</div><div>No transactions in this group session yet</div></div>';
  }
  html += "</div>";

  // Right: split calculator
  html += '<div class="group-calculator">';
  html += "<h3>Split Calculator</h3>";

  const splitMode = data.split_mode || "percentage";
  html += '<div class="split-mode-toggle">';
  html += `<button class="split-mode-btn ${splitMode === "percentage" ? "active" : ""}" data-mode="percentage">Percentage</button>`;
  html += `<button class="split-mode-btn ${splitMode === "flat" ? "active" : ""}" data-mode="flat">Flat Rate</button>`;
  html += "</div>";

  const players = data.players || [];
  html += '<div id="player-list">';
  for (let i = 0; i < players.length; i++) {
    html += playerRowHtml(i, players[i].name, players[i].percentage, players[i].flat_amount, splitMode);
  }
  if (players.length === 0) {
    html += playerRowHtml(0, "Your Cut", 50, 0, splitMode);
    html += playerRowHtml(1, "Player 2", 50, 0, splitMode);
  }
  html += "</div>";

  html += '<div class="player-controls">';
  html += '<button id="add-player-btn">+ Player</button>';
  html += '<button id="remove-player-btn">- Player</button>';
  html += '<button id="split-equal-btn">Equal Split</button>';
  html += '<button id="save-players-btn" class="btn-primary" style="padding:3px 10px;font-size:11px;">Save</button>';
  html += "</div>";

  // Split validation warning
  html += '<div id="pct-warning"></div>';

  // Summary with payment tracking
  const net = data.net || 0;
  html += '<div class="group-summary-section">';
  html += "<h4>Total Split</h4>";

  const displayPlayers = players.length > 0 ? players : [
    {name: "Your Cut", percentage: 50},
    {name: "Player 2", percentage: 50},
  ];

  html += `<div class="split-row"><span class="player-name">Net Total</span><span class="player-amount ${net >= 0 ? "positive" : "negative"}">${data.formatted_net}</span></div>`;
  html += '<div style="border-top:1px solid var(--border);margin:6px 0;"></div>';

  for (let i = 0; i < displayPlayers.length; i++) {
    const p = displayPlayers[i];
    const isOwner = i === 0;
    const customAmt = p.custom_amount !== undefined && p.custom_amount !== null;
    let share;
    let splitLabel;
    if (customAmt) {
      share = p.custom_amount;
      splitLabel = "custom";
    } else if (splitMode === "flat") {
      share = p.flat_amount || 0;
      splitLabel = `${formatAuec(share)} flat`;
    } else {
      share = net * (p.percentage / 100);
      splitLabel = `${p.percentage}%`;
    }
    const formatted = formatAuec(share);
    const isPaid = p.paid || false;

    html += `<div class="split-row">
      <span class="player-name">${escHtml(p.name)} (${splitLabel})</span>
      <span class="player-amount ${share >= 0 ? "positive" : "negative"}">${formatted}</span>
      <button class="btn-small group-edit-cut-btn" data-idx="${i}" title="Edit cut">Edit</button>`;

    if (!isOwner) {
      if (isPaid) {
        html += `<span class="paid-badge">Paid</span>`;
      } else {
        html += `<button class="btn-small group-paid-btn" data-idx="${i}">Payment Posted</button>`;
      }
    }
    html += "</div>";
  }
  html += "</div>";

  html += "</div>"; // calculator
  html += "</div>"; // layout

  content.innerHTML = html;

  wireTableFilters("group-txn-table", content);

  // Wire row clicks for editing group transactions
  content.querySelectorAll("#group-txn-table .clickable-row").forEach((row) => {
    row.addEventListener("click", () => {
      const txn = data.transactions[parseInt(row.dataset.idx)];
      openEditTransactionForm(txn);
    });
  });

  // Wire up buttons
  const stopBtn = document.getElementById("group-stop-btn");
  if (stopBtn) {
    stopBtn.addEventListener("click", async () => {
      if (confirm("Stop the group session? All transactions are preserved.")) {
        await fetch("/api/group-session/stop", {method: "POST"});
        renderGroupSession();
      }
    });
  }

  // Wire group buy/sell action bar buttons (same pattern as Portfolio tab)
  wireActionButton(() => openGroupTransactionForm("buy"), 0);
  wireActionButton(() => openGroupTransactionForm("sell"), 1);

  // Wire payment posted buttons
  content.querySelectorAll(".group-paid-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const idx = parseInt(btn.dataset.idx);
      await fetch(`/api/group-session/players/${idx}/paid`, {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({paid: true}),
      });
      renderGroupSession();
    });
  });

  // Wire edit cut buttons
  content.querySelectorAll(".group-edit-cut-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = parseInt(btn.dataset.idx);
      const p = displayPlayers[idx];
      let defaultShare;
      if (splitMode === "flat") {
        defaultShare = p.flat_amount || 0;
      } else {
        defaultShare = net * (p.percentage / 100);
      }
      const currentAmt = (p.custom_amount !== undefined && p.custom_amount !== null) ? p.custom_amount : defaultShare;
      openEditCutForm(idx, p.name, currentAmt);
    });
  });

  setupGroupPlayerControls(displayPlayers, splitMode, net);
}

async function renderGroupSessionDetail(sessionId) {
  const data = await fetchJSON(`/api/group-session/${sessionId}`);
  const content = document.getElementById("content");
  if (!data) return showEmpty("Session not found");

  let html = '<div class="tab-action-bar">';
  html += '<button class="btn-add" id="back-to-group-btn">Back to Group Events</button>';
  html += "</div>";

  html += '<div class="group-status-bar">';
  html += '<span class="status-dot inactive"></span>';
  html += `<span class="status-text">Session: ${formatTimestamp(data.started_at)} — ${formatTimestamp(data.ended_at)}</span>`;
  html += "</div>";

  html += '<div class="group-layout">';

  // Left: transaction ledger
  html += '<div class="group-ledger">';
  html += '<div class="summary-row">';
  html += summaryCard("Income", data.formatted_income, `${data.transaction_count} transactions`, "positive");
  html += summaryCard("Expenses", data.formatted_expenses, null, "negative");
  html += summaryCard("Net", data.formatted_net, null, data.net >= 0 ? "positive" : "negative");
  html += "</div>";

  if (data.transactions && data.transactions.length > 0) {
    const detailCols = ["date", "type", "category", "amount", "description", "notes", "location"];
    html += `<table id="group-detail-table">
    <thead>
      <tr>
        <th>Date</th><th>Type</th><th>Category</th>
        <th>Amount</th><th>Description</th><th>Notes</th><th>Location</th>
      </tr>
      ${buildFilterRow(detailCols)}
    </thead><tbody>`;
    for (let i = 0; i < data.transactions.length; i++) {
      const t = data.transactions[i];
      const cls = t.type === "income" ? "income" : "expense";
      const sign = t.type === "income" ? "+" : "-";
      html += `<tr class="clickable-row" data-idx="${i}"
        data-date="${escHtml(formatTimestamp(t.timestamp))}"
        data-type="${escHtml(t.type)}"
        data-category="${escHtml(t.category)}"
        data-amount="${t.amount}"
        data-description="${escHtml(t.description)}"
        data-notes="${escHtml(t.notes || "")}"
        data-location="${escHtml(t.location || "")}">
        <td>${formatTimestamp(t.timestamp)}</td>
        <td class="${cls}">${sign}</td>
        <td>${escHtml(t.category)}</td>
        <td class="num ${cls}">${fmt(t.amount)}</td>
        <td title="${escHtml(t.description)}">${escHtml(t.description)}</td>
        <td>${escHtml(t.notes || "")}</td>
        <td>${escHtml(t.location || "")}</td>
      </tr>`;
    }
    html += "</tbody></table>";
  } else {
    html += '<div class="empty-state"><div class="icon">--</div><div>No transactions in this session</div></div>';
  }
  html += "</div>";

  // Right: split summary (read-only for ended sessions)
  const net = data.net || 0;
  const players = data.players || [];
  const splitMode = data.split_mode || "percentage";

  if (players.length > 0) {
    html += '<div class="group-calculator">';
    html += "<h3>Split Summary</h3>";
    html += `<div class="split-row"><span class="player-name">Net Total</span><span class="player-amount ${net >= 0 ? "positive" : "negative"}">${data.formatted_net}</span></div>`;
    html += '<div style="border-top:1px solid var(--border);margin:6px 0;"></div>';
    for (const p of players) {
      let share;
      let splitLabel;
      if (p.custom_amount !== undefined && p.custom_amount !== null) {
        share = p.custom_amount;
        splitLabel = "custom";
      } else if (splitMode === "flat") {
        share = p.flat_amount || 0;
        splitLabel = `${formatAuec(share)} flat`;
      } else {
        share = net * (p.percentage / 100);
        splitLabel = `${p.percentage}%`;
      }
      html += `<div class="split-row">
        <span class="player-name">${escHtml(p.name)} (${splitLabel})</span>
        <span class="player-amount ${share >= 0 ? "positive" : "negative"}">${formatAuec(share)}</span>
        ${p.paid ? '<span class="paid-badge">Paid</span>' : ""}
      </div>`;
    }
    html += "</div>";
  }

  html += "</div>"; // layout

  content.innerHTML = html;

  wireTableFilters("group-detail-table", content);

  // Wire row clicks for editing
  content.querySelectorAll("#group-detail-table .clickable-row").forEach((row) => {
    row.addEventListener("click", () => {
      const txn = data.transactions[parseInt(row.dataset.idx)];
      openEditTransactionForm(txn);
    });
  });

  // Wire back button
  document.getElementById("back-to-group-btn").addEventListener("click", () => {
    renderGroupSession();
  });
}

function openGroupTransactionForm(txnType) {
  const label = txnType === "sell" ? "Group Sell" : "Group Buy";
  const body = `
    <div class="form-group">
      <label>Commodity</label>
      <input id="f-group-commodity" type="text" required placeholder="e.g. Bexalite">
    </div>
    <div class="form-group">
      <label>Amount (aUEC)</label>
      <input id="f-group-amount" type="number" min="1" step="1" required>
    </div>
    <div class="form-group">
      <label>Notes</label>
      <textarea id="f-group-notes" rows="2" placeholder="Optional"></textarea>
    </div>`;

  openModal(label, body, async () => {
    try {
      await postJSON("/api/group-session/transaction", {
        type: txnType,
        commodity: document.getElementById("f-group-commodity").value,
        amount: parseFloat(document.getElementById("f-group-amount").value),
        notes: document.getElementById("f-group-notes").value,
      });
      showModalSuccess(`${label} recorded`);
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function openEditCutForm(playerIdx, playerName, currentAmount) {
  const body = `
    <div class="form-group">
      <label>Player</label>
      <div class="form-value">${escHtml(playerName)}</div>
    </div>
    <div class="form-group">
      <label>Cut Amount (aUEC)</label>
      <input id="f-cut-amount" type="number" step="1" value="${Math.round(currentAmount)}" required>
    </div>`;

  openModal(`Edit Cut — ${escHtml(playerName)}`, body, async () => {
    try {
      await putJSON(`/api/group-session/players/${playerIdx}/cut`, {
        amount: parseFloat(document.getElementById("f-cut-amount").value),
      });
      showModalSuccess("Cut updated");
    } catch (err) {
      showModalError(err.message);
    }
  });
}

function playerRowHtml(index, name, percentage, flatAmount, mode) {
  if (mode === "flat") {
    const amt = flatAmount !== undefined && flatAmount !== null ? Math.round(flatAmount) : 0;
    return `<div class="player-row" data-idx="${index}">
      <input type="text" class="player-name-input" value="${escHtml(name)}" placeholder="Player name">
      <input type="number" class="player-flat-input" value="${amt}" step="1">
      <span class="pct-label">aUEC</span>
    </div>`;
  }
  return `<div class="player-row" data-idx="${index}">
    <input type="text" class="player-name-input" value="${escHtml(name)}" placeholder="Player name">
    <input type="number" class="player-pct-input" value="${percentage}" min="0" max="100" step="0.1">
    <span class="pct-label">%</span>
  </div>`;
}

function setupGroupPlayerControls(initialPlayers, splitMode, net) {
  const addBtn = document.getElementById("add-player-btn");
  const removeBtn = document.getElementById("remove-player-btn");
  const equalBtn = document.getElementById("split-equal-btn");
  const saveBtn = document.getElementById("save-players-btn");

  // Wire split mode toggle
  document.querySelectorAll(".split-mode-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const newMode = btn.dataset.mode;
      if (newMode === splitMode) return;
      const players = getPlayerListFromDOM(splitMode);
      await fetch("/api/group-session/players", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({players, split_mode: newMode}),
      });
      renderGroupSession();
    });
  });

  if (addBtn) {
    addBtn.addEventListener("click", () => {
      const list = document.getElementById("player-list");
      const count = list.querySelectorAll(".player-row").length;
      const div = document.createElement("div");
      div.innerHTML = playerRowHtml(count, `Player ${count + 1}`, 0, 0, splitMode);
      list.appendChild(div.firstElementChild);
      updateSplitWarning(splitMode, net);
    });
  }

  if (removeBtn) {
    removeBtn.addEventListener("click", () => {
      const list = document.getElementById("player-list");
      const rows = list.querySelectorAll(".player-row");
      if (rows.length > 2) {
        rows[rows.length - 1].remove();
        updateSplitWarning(splitMode, net);
      }
    });
  }

  if (equalBtn) {
    equalBtn.addEventListener("click", () => {
      const rows = document.querySelectorAll("#player-list .player-row");
      if (splitMode === "flat") {
        const equalAmt = Math.round(net / rows.length);
        rows.forEach(r => {
          r.querySelector(".player-flat-input").value = equalAmt;
        });
      } else {
        const equal = Math.round((100 / rows.length) * 10) / 10;
        rows.forEach(r => {
          r.querySelector(".player-pct-input").value = equal;
        });
      }
      updateSplitWarning(splitMode, net);
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const players = getPlayerListFromDOM(splitMode);
      await fetch("/api/group-session/players", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({players, split_mode: splitMode}),
      });
      renderGroupSession();
    });
  }

  // Live validation
  document.getElementById("player-list").addEventListener("input", () => updateSplitWarning(splitMode, net));
  updateSplitWarning(splitMode, net);
}

function getPlayerListFromDOM(mode) {
  const rows = document.querySelectorAll("#player-list .player-row");
  const players = [];
  rows.forEach(r => {
    const name = r.querySelector(".player-name-input").value || "Unnamed";
    if (mode === "flat") {
      const flatInput = r.querySelector(".player-flat-input");
      players.push({
        name,
        percentage: 0,
        flat_amount: parseFloat(flatInput?.value) || 0,
      });
    } else {
      const pctInput = r.querySelector(".player-pct-input");
      players.push({
        name,
        percentage: parseFloat(pctInput?.value) || 0,
        flat_amount: 0,
      });
    }
  });
  return players;
}

function updateSplitWarning(mode, net) {
  const rows = document.querySelectorAll("#player-list .player-row");
  const warn = document.getElementById("pct-warning");
  if (!warn) return;

  if (mode === "flat") {
    let total = 0;
    rows.forEach(r => {
      total += parseFloat(r.querySelector(".player-flat-input")?.value) || 0;
    });
    const diff = Math.abs(total - net);
    if (diff > 1) {
      warn.innerHTML = `<span class="pct-warning">Total: ${formatAuec(total)} / Net: ${formatAuec(net)} (${formatAuec(net - total)} unallocated)</span>`;
    } else {
      warn.innerHTML = `<span style="color:var(--accent-green);font-size:11px;">Total: ${formatAuec(total)} — fully allocated</span>`;
    }
  } else {
    let total = 0;
    rows.forEach(r => {
      total += parseFloat(r.querySelector(".player-pct-input")?.value) || 0;
    });
    if (Math.abs(total - 100) > 0.1) {
      warn.innerHTML = `<span class="pct-warning">Total: ${total.toFixed(1)}% (should be 100%)</span>`;
    } else {
      warn.innerHTML = `<span style="color:var(--accent-green);font-size:11px;">Total: ${total.toFixed(1)}%</span>`;
    }
  }
}

function formatAuec(value) {
  const abs = Math.abs(value);
  let formatted;
  if (abs >= 1000000) {
    formatted = (abs / 1000000).toFixed(2) + "M";
  } else if (abs >= 1000) {
    formatted = (abs / 1000).toFixed(1) + "K";
  } else {
    formatted = abs.toFixed(0);
  }
  return (value < 0 ? "-" : "") + formatted + " aUEC";
}

function formatTimestamp(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, "0");
  const da = String(d.getDate()).padStart(2, "0");
  const h = String(d.getHours()).padStart(2, "0");
  const mi = String(d.getMinutes()).padStart(2, "0");
  return `${y}:${mo}:${da} - ${h}:${mi}`;
}

// --- Utility Functions ---

function actionBar(...labels) {
  let html = '<div class="tab-action-bar">';
  for (let i = 0; i < labels.length; i++) {
    html += `<button class="btn-add" id="tab-add-btn-${i}">${escHtml(labels[i])}</button>`;
  }
  html += "</div>";
  return html;
}

function wireActionButton(onClick, index) {
  const idx = index != null ? index : 0;
  const btn = document.getElementById(`tab-add-btn-${idx}`);
  if (btn) btn.addEventListener("click", onClick);
}

function escHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

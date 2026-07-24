// app.js — Module 6 (API layer) + Module 7 (chart wiring)

async function apiGet(path, params = {}) {
  const url = new URL(API_BASE + path);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null) url.searchParams.set(k, v);
  });

  const res = await fetch(url, {
    headers: { "ngrok-skip-browser-warning": "true" },
  });

  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`);
  }
  return res.json();
}

// GET /api/customers — user_id, name, limit, order, agg, sale_profit
function getCustomers({ user_id, name = true, limit = 10, order = "DESC", agg = "COUNT", sale_profit = "off" }) {
  return apiGet("/api/customers", { user_id, name, limit, order, agg, sale_profit });
}

// GET /api/products — same shape as customers
function getProducts({ user_id, name = true, limit = 10, order = "DESC", agg = "COUNT", sale_profit = "off" }) {
  return apiGet("/api/products", { user_id, name, limit, order, agg, sale_profit });
}

// GET /api/locations — user_id, limit, order, agg, level (no name/sale_profit toggle)
function getLocations({ user_id, limit = 10, order = "DESC", agg = "COUNT", level = "city" }) {
  return apiGet("/api/locations", { user_id, limit, order, agg, level });
}

// GET /api/employees — NOTE: param is `sales_profit`, not `sale_profit`
// (matches the naming already used in query_functions.py / app.py)
function getEmployees({ user_id, name = true, limit = 10, order = "DESC", agg = "COUNT", sales_profit = "off" }) {
  return apiGet("/api/employees", { user_id, name, limit, order, agg, sales_profit });
}

// GET /api/forecast — user_id, name_chosen, product_name
function getForecast({ user_id, name_chosen, product_name = true }) {
  return apiGet("/api/forecast", { user_id, name_chosen, product_name });
}

// ---------------------------------------------------------------------------
// Module 7 — control wiring + Chart.js rendering
// ---------------------------------------------------------------------------

const root = getComputedStyle(document.documentElement);
const COLOR_PHOSPHOR = root.getPropertyValue("--phosphor").trim();
const COLOR_AMBER = root.getPropertyValue("--amber").trim();
const COLOR_LINE = root.getPropertyValue("--line").trim();
const COLOR_TEXT_DIM = root.getPropertyValue("--text-dim").trim();

Chart.defaults.font.family = "'IBM Plex Mono', monospace";
Chart.defaults.color = COLOR_TEXT_DIM;

let currentDim = "customers";
let resultsChart = null;
let forecastChart = null;

const dimButtons = document.querySelectorAll(".dim-btn");
const spGroup = document.getElementById("sp-group");
const levelGroup = document.getElementById("level-group");
const statusLine = document.getElementById("status-line");

function setStatus(msg) {
  statusLine.textContent = msg;
}

function updateControlVisibility() {
  // Locations has a `level` selector and no sale_profit toggle;
  // customers/products/employees are the reverse (per Module 5).
  if (currentDim === "locations") {
    levelGroup.classList.remove("is-hidden");
    spGroup.classList.add("is-hidden");
  } else {
    levelGroup.classList.add("is-hidden");
    spGroup.classList.remove("is-hidden");
  }
}

dimButtons.forEach((btn) => {
  btn.addEventListener("click", () => {
    dimButtons.forEach((b) => b.classList.remove("is-active"));
    btn.classList.add("is-active");
    currentDim = btn.dataset.dim;
    updateControlVisibility();
  });
});

function baseChartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: COLOR_LINE }, ticks: { color: COLOR_TEXT_DIM } },
      y: { grid: { color: COLOR_LINE }, ticks: { color: COLOR_TEXT_DIM }, beginAtZero: true },
    },
    ...extra,
  };
}

function renderResultsChart(data) {
  const labels = data.map((d) => d.label);
  const values = data.map((d) => d.value);

  if (resultsChart) resultsChart.destroy();

  resultsChart = new Chart(document.getElementById("results-chart"), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: currentDim,
          data: values,
          backgroundColor: "rgba(111, 255, 166, 0.55)",
          borderColor: COLOR_PHOSPHOR,
          borderWidth: 1,
        },
      ],
    },
    options: baseChartOptions(),
  });
}

function renderForecastChart(data) {
  const labels = data.map((d) => d.month);
  const values = data.map((d) => d.quantity);

  if (forecastChart) forecastChart.destroy();

  forecastChart = new Chart(document.getElementById("forecast-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "quantity",
          data: values,
          borderColor: COLOR_AMBER,
          backgroundColor: "rgba(255, 180, 84, 0.15)",
          tension: 0.25,
          fill: true,
          pointRadius: 3,
        },
      ],
    },
    options: baseChartOptions(),
  });
}

async function runQuery() {
  const user_id = document.getElementById("user-id").value;
  const limit = document.getElementById("limit").value;
  const order = document.getElementById("order").value;
  const agg = document.getElementById("agg").value;
  const sale_profit = document.getElementById("sale-profit").value;
  const level = document.getElementById("level").value;

  setStatus("querying...");
  try {
    let data;
    switch (currentDim) {
      case "customers":
        data = await getCustomers({ user_id, limit, order, agg, sale_profit });
        break;
      case "products":
        data = await getProducts({ user_id, limit, order, agg, sale_profit });
        break;
      case "locations":
        data = await getLocations({ user_id, limit, order, agg, level });
        break;
      case "employees":
        data = await getEmployees({ user_id, limit, order, agg, sales_profit: sale_profit });
        break;
    }
    renderResultsChart(data);
    setStatus(`ok — ${data.length} rows (${currentDim})`);
  } catch (err) {
    console.error(err);
    setStatus(`error — ${err.message}`);
  }
}

async function runForecast() {
  const user_id = document.getElementById("user-id").value;
  const name_chosen = document.getElementById("forecast-name").value.trim();

  if (!name_chosen) {
    setStatus("error — enter a product name first");
    return;
  }

  setStatus("forecasting...");
  try {
    const data = await getForecast({ user_id, name_chosen });
    renderForecastChart(data);
    setStatus(`ok — ${data.length} months for "${name_chosen}"`);
  } catch (err) {
    console.error(err);
    setStatus(`error — ${err.message}`);
  }
}

async function uploadNewUser() {
  const username = document.getElementById("new-username").value.trim();
  const file = document.getElementById("csv-file").files[0];

  if (!username) {
    setStatus("error — enter a username first");
    return;
  }
  if (!file) {
    setStatus("error — choose a CSV file first");
    return;
  }

  const formData = new FormData();
  formData.append("username", username);
  formData.append("file", file);

  setStatus("uploading & creating account...");
  try {
    const res = await fetch(API_BASE + "/api/upload", {
      method: "POST",
      headers: { "ngrok-skip-browser-warning": "true" }, // no Content-Type: browser sets the multipart boundary
      body: formData,
    });
    const result = await res.json();
    if (!res.ok) {
      throw new Error(result.error || `upload failed: ${res.status}`);
    }
    document.getElementById("user-id").value = result.user_id;
    setStatus(`ok — account "${result.username}" created as user_id ${result.user_id}`);
  } catch (err) {
    console.error(err);
    setStatus(`error — ${err.message}`);
  }
}

document.getElementById("run-btn").addEventListener("click", runQuery);
document.getElementById("forecast-run-btn").addEventListener("click", runForecast);
document.getElementById("upload-btn").addEventListener("click", uploadNewUser);

updateControlVisibility();


function getOrder(row_id) {
  return apiGet(`/api/order/${row_id}`);
}

async function lookupOrder() {
  const row_id = document.getElementById("edit-row-id").value;
  if (!row_id) {
    setStatus("error — enter a row_id first");
    return;
  }
  setStatus("looking up order...");
  try {
    const data = await getOrder(row_id);
    document.getElementById("edit-quantity").value = data.quantity;
    document.getElementById("edit-sales").value = data.sales;
    document.getElementById("edit-discount").value = data.discount;
    document.getElementById("edit-profit").value = data.profit ?? "";
    document.getElementById("edit-returned").value = String(data.returned ?? 0);
    setStatus(`ok — loaded row_id ${data.row_id}`);
  } catch (err) {
    console.error(err);
    setStatus(`error — ${err.message}`);
  }
}

async function saveOrder() {
  const row_id = document.getElementById("edit-row-id").value;
  const quantity = document.getElementById("edit-quantity").value;
  const sales = document.getElementById("edit-sales").value;
  const discount = document.getElementById("edit-discount").value;
  const profit = document.getElementById("edit-profit").value;
  const returned = document.getElementById("edit-returned").value;

  if (!row_id || !quantity || !sales || !discount || !profit) {
    setStatus("error — fill in row_id, quantity, sales, discount, and profit");
    return;
  }

  setStatus("saving update...");
  try {
    const res = await fetch(`${API_BASE}/api/order/${row_id}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "ngrok-skip-browser-warning": "true",
      },
      body: JSON.stringify({
        quantity: Number(quantity),
        sales: Number(sales),
        discount: Number(discount),
        profit: Number(profit),
        returned: Number(returned),
      }),
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.error || `update failed: ${res.status}`);
    setStatus(`ok — row_id ${result.row_id} updated`);
  } catch (err) {
    console.error(err);
    setStatus(`error — ${err.message}`);
  }
}

async function deleteAccount() {
  const user_id = document.getElementById("delete-user-id").value;
  if (!user_id) {
    setStatus("error — enter a user_id first");
    return;
  }
  setStatus("deleting account...");
  try {
    const res = await fetch(`${API_BASE}/api/users/${user_id}`, {
      method: "DELETE",
      headers: { "ngrok-skip-browser-warning": "true" },
    });
    const result = await res.json();
    if (!res.ok) throw new Error(result.error || `delete failed: ${res.status}`);
    setStatus(`ok — user_id ${result.user_id} deleted`);
  } catch (err) {
    console.error(err);
    setStatus(`error — ${err.message}`);
  }
}

document.getElementById("lookup-btn").addEventListener("click", lookupOrder);
document.getElementById("save-order-btn").addEventListener("click", saveOrder);
document.getElementById("delete-user-btn").addEventListener("click", deleteAccount);
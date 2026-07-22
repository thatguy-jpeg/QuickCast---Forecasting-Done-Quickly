# QuickCast Build Spec — Modularized

Reorganizes `quickcast_frontend_spec.md` into self-contained modules. Nothing
is summarized away — schema, function code, and deployment details are
reproduced in full inside their module so each one can be worked (or handed
to Claude) on its own, in order, without re-reading the whole original spec.

**Usage:** ask for one module at a time — "do Module 2" — rather than the
whole build in one shot. Later modules assume earlier ones are done.

## Module index

| # | Module | Depends on | Produces |
|---|--------|-----------|----------|
| 0 | Project context & deployment constraints | — | shared assumptions, no code |
| 1 | Database schema & data notes | — | shared assumptions, no code |
| 2 | Existing query functions | 1 | Python functions to wrap |
| 3 | Backend — connection/session strategy | 1, 2 | decision + `get_conn()`/`setup()` pattern |
| 4 | Backend — routes & response shape | 2, 3 | `app.py` |
| 5 | Frontend — page structure & controls | 4 | `index.html`, `style.css` |
| 6 | Frontend — API layer & config | 4 | `config.js`, fetch helper in `app.js` |
| 7 | Frontend — charts | 5, 6 | chart rendering in `app.js` |
| 8 | Explicitly out of scope | — | guardrails, no code |
| 9 | Demo-day runbook | 4–7 | operational checklist |

---

## Module 0 — Project context & deployment constraints

**Goal:** a local Flask backend + static frontend demo for a short video, not
a production app. Data is a Superstore-style retail sales dataset in SQLite;
schema and query logic already exist and are treated as correct.

**Deployment topology:**
- Frontend: static HTML/CSS/JS on **GitHub Pages** (public `https://username.github.io/...`).
- Backend: Flask runs **locally**, exposed via an **ngrok tunnel** (`ngrok http 5000`), giving a public `https://xxxx.ngrok-free.app` URL that forwards to `localhost`.
- Frontend and backend are on different origins → **flask-cors is required**, not optional. Enable CORS for all routes, or scope to the GitHub Pages origin.
- **ngrok free-tier interstitial:** a first-visit browser warning page also intercepts `fetch()` calls unless every request sends the header `ngrok-skip-browser-warning: true`. Without it, JSON responses come back as the warning HTML instead of data.
- **ngrok URL is not stable** on the free tier — it changes every tunnel restart. Keep the backend base URL in one place (`config.js`, a single `const API_BASE = "..."`) so it can be swapped in seconds before recording.
- ngrok needs a free account + local authtoken (`ngrok config add-authtoken ...`) — one-time setup, do before recording day.
- **Demo sequence:** start Flask locally → start `ngrok http <port>` → copy the `https://...ngrok-free.app` URL into `config.js` → open the GitHub Pages site → record. Flask and the ngrok tunnel must both stay running the entire time.

---

## Module 1 — Database schema & data notes

**Goal:** shared ground truth for every later module. No code produced here.

```sql
CREATE TABLE users(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
) STRICT;

CREATE TABLE customers(
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL
) STRICT;

CREATE TABLE employees(
    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    retail_sales_people TEXT NOT NULL
) STRICT;

CREATE TABLE locations(
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL,
    state TEXT,
    city TEXT NOT NULL,
    postal_code TEXT
) STRICT;

CREATE TABLE products(
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category TEXT,
    subcategory TEXT
) STRICT;

CREATE TABLE records(
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL UNIQUE,
    user_id INTEGER NOT NULL,
    customer_id INTEGER NOT NULL,
    location_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,

    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE RESTRICT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT,
    FOREIGN KEY (location_id) REFERENCES locations(location_id) ON DELETE RESTRICT,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE RESTRICT
) STRICT;

CREATE TABLE orders(
    order_id TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    row_id INTEGER PRIMARY KEY,
    quantity INTEGER NOT NULL DEFAULT 1,
    sales INTEGER NOT NULL,
    discount INTEGER NOT NULL DEFAULT 0,
    profit INTEGER,
    returned INTEGER CHECK (returned IN (0, 1)),

    FOREIGN KEY (order_id) REFERENCES records(order_id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
) STRICT;
```

**Key data notes:**
- `records` = one row per order (header/fact table). `orders` = one row per line item (`row_id` is the true unique key — the same product can appear twice in one order).
- `sales`, `discount`, `profit` are stored as **integer cents**. Divide by 100 when displaying in the frontend — this belongs in the backend response layer (Module 4), not the frontend.
- `order_id` is TEXT (e.g. `"CA-2020-152156"`), not integer.
- `order_date` is expected as ISO `YYYY-MM-DD`. **Open item to verify:** source CSV used `M/D/YYYY`. Fix recommended at load time (`pd.to_datetime(..., format="%m/%d/%Y").dt.strftime("%Y-%m-%d")`) so `forecast()`'s `strftime('%Y-%m', order_date)` grouping works. If unverified and still `M/D/YYYY` in the live db, the forecast endpoint will silently return null months. This is a data-layer check, out of scope for the Flask/frontend modules but worth confirming before Module 9.
- `PRAGMA foreign_keys = ON;` must be set per-connection (not persisted in the db file) — every connection the backend opens needs this.
- A `TEMP TABLE user_records`, created via `setup(cur, user_id)`, is required **once per connection** before any query function works — they all query `user_records`, not `records` directly. This drives the whole Module 3 decision.

---

## Module 2 — Existing query functions (wrap, don't rewrite)

**Goal:** treat these as correct and tested. Backend routes call these
as-is; don't modify the SQL inside them.

```python
def setup(cur, user_id):
    subquery = f'''
    SELECT * 
    FROM records
    WHERE user_id = {user_id};
    '''

    query = f'''
    CREATE TEMP TABLE user_records AS
    {subquery}
    '''

    cur.execute(query)

def customer_query(cur, name=True, limit=10, order="DESC", agg="COUNT", sale_profit=False):
    if name:
        col = "customer_name"
    else:
        col = "customer_id"

    if sale_profit != False:
        query = f'''
        SELECT {col}, {agg}({sale_profit})
        FROM user_records
        LEFT JOIN customers
        USING (customer_id)
        LEFT JOIN orders
        USING (order_id)
        GROUP BY customer_id
        ORDER BY {agg}({sale_profit}) {order}
        LIMIT {limit};
        '''
    else:
        query = f'''
        SELECT {col}, {agg}(record_id)
        FROM user_records
        LEFT JOIN customers
        USING (customer_id)
        GROUP BY customer_id
        ORDER BY {agg}(record_id) {order}
        LIMIT {limit};
        '''

    cur.execute(query)
    return cur.fetchall()

def product_query(cur, name=True, limit=10, order="DESC", agg="COUNT", sale_profit=False):
    if name:
        col = "product_name"
    else:
        col = "product_id"

    if sale_profit != False:
        query = f'''
        SELECT {col}, {agg}({sale_profit})
        FROM user_records
        LEFT JOIN orders
        USING (order_id)
        LEFT JOIN products
        USING (product_id)
        GROUP BY product_id
        ORDER BY {agg}({sale_profit}) {order}
        LIMIT {limit};
        '''
    else:
        query = f'''
        SELECT {col}, {agg}(record_id)
        FROM user_records
        LEFT JOIN orders
        USING (order_id)
        LEFT JOIN products
        USING (product_id)
        GROUP BY product_id
        ORDER BY {agg}(record_id) {order}
        LIMIT {limit};
        '''

    cur.execute(query)
    return cur.fetchall()

def location_query(cur, limit=10, order="DESC", agg="COUNT", level="city"):
    query = f'''
    SELECT {level}, {agg}(DISTINCT order_id)
    FROM user_records
    LEFT JOIN locations
    USING (location_id)
    GROUP BY {level}
    ORDER BY {agg}(DISTINCT order_id) {order}
    LIMIT {limit};
    '''

    cur.execute(query)
    return cur.fetchall()

def employee_query(cur, name=True, limit=10, order="DESC", agg="COUNT", sales_profit=False):
    if name:
        col = "retail_sales_people"
    else: 
        col = "employee_id"
    
    if sales_profit != False:
        query = f'''
        SELECT {col}, {agg}({sales_profit})
        FROM user_records
        LEFT JOIN employees
        USING (employee_id)
        LEFT JOIN orders
        USING (order_id)
        GROUP BY employee_id
        ORDER BY {agg}({sales_profit}) {order}
        LIMIT {limit};
        '''
    else:
        query = f'''
        SELECT {col}, {agg}(record_id)
        FROM user_records
        LEFT JOIN employees
        USING (employee_id)
        GROUP BY employee_id
        ORDER BY {agg}(record_id) {order}
        LIMIT {limit};
        '''
    
    cur.execute(query)
    return cur.fetchall()

def forecast(cur, name_chosen, product_name=True):
    if product_name:
        col = "product_name"
    else:
        col = "product_id"

    query = f'''
    SELECT strftime('%Y-%m', order_date) AS month, SUM(quantity)
    FROM user_records
    LEFT JOIN orders
    USING (order_id)
    LEFT JOIN products
    USING (product_id)
    WHERE {col} = ?
    GROUP BY month
    ORDER BY month;
    '''

    cur.execute(query, (name_chosen,))
    return cur.fetchall()
```

**Notes:**
- `agg`/`order`/`level`/`name`/`sale_profit`-selection params are meant to come from a **fixed set of UI buttons/dropdowns**, not free text — no SQL-injection sanitization was added on those by design (accepted scope decision). `name_chosen` in `forecast()` **is** parameterized with `?` since it's real typed/selected user input.
- `location_query` has no `sale_profit`/name toggle — always returns `{level}, {agg}(DISTINCT order_id)`.
- The `else` branches (no sales/profit) always aggregate `record_id` — effectively a count unless a different `agg` is passed.

---

## Module 3 — Backend: connection/session strategy

**Goal:** resolve the TEMP TABLE scoping problem before writing any routes.

**The problem:** `setup()` creates a `TEMP TABLE`, scoped to the single
connection that created it — it vanishes when that connection closes. A
standalone `POST /api/setup` endpoint that opens a connection, runs
`setup()`, and closes it **will not work**: the temp table is gone before
the next request opens its own new connection.

**Two options:**
- **Recommended (simplest for a demo):** no separate `/api/setup` endpoint.
  Every query endpoint takes `user_id` as a request param and, within one
  request: open connection → `setup(cur, user_id)` → run the query function
  → return JSON → close connection. Slightly redundant (`user_records`
  rebuilt every call) but avoids all cross-request state — right tradeoff
  at demo scale.
- **More "correct," more complexity:** one persistent connection per browser
  session, stored server-side keyed by session/user ID, so `setup()` runs
  once. Not recommended here — adds thread-safety/lifecycle/cleanup
  complexity for no benefit at this scale.

**Decision for this build:** the recommended option. Every endpoint in
Module 4 takes `user_id` and does open → setup → query → close internally.

---

## Module 4 — Backend: routes & response shape

**Goal:** `app.py`, wrapping Module 2's functions per Module 3's strategy.

**Routes:**
- `GET /api/customers` — `user_id`, `name`, `limit`, `order`, `agg`, `sale_profit`
- `GET /api/products` — same shape, plus `user_id`
- `GET /api/locations` — `user_id`, `limit`, `order`, `agg`, `level`
- `GET /api/employees` — `user_id`, `name`, `limit`, `order`, `agg`, `sales_profit`
- `GET /api/forecast` — `user_id`, `name_chosen`, `product_name`

**Requirements:**
- Divide `sales`/`discount`/`profit` by 100 before returning JSON, so the frontend doesn't have to — but only when the aggregate is actually a currency figure (`SUM`/`AVG`/`MAX`/`MIN` of `sales`/`profit`). `COUNT(sales)` is a row count, not money — don't divide it.
- Set `PRAGMA foreign_keys = ON;` on every new connection.
- Include `flask-cors`, enabled for the app (frontend origin `https://username.github.io`, backend origin the ngrok URL).
- Nothing in `app.py` needs to know about ngrok — it's purely a tunnel in front of the existing local server.
- DB file is `quickcast.db`.
- `cur.fetchall()` returns tuples — convert to a list of dicts before `jsonify()` (e.g. `{"label": ..., "value": ...}`), not bare positional pairs the frontend has to interpret.
- Flask's debugger (`debug=True`) should stay **off** for this build — the server gets tunneled to the public internet via ngrok, and the debugger allows arbitrary code execution from any error page.

---

## Module 5 — Frontend: page structure & controls

**Goal:** `index.html` + `style.css`. Single static page, demo-quality, not
production polish.

**Needed elements:**
- A way to enter/select a `user_id` (default to the seeded Guest user if simplest). Since Module 3's chosen strategy has no separate setup call, this is just a value held in the page and sent as a param on every fetch.
- Dimension selector: Customers / Products / Locations / Employees.
- `agg` selector: COUNT / SUM / AVG / MAX / MIN.
- `order` selector: ASC / DESC.
- `limit` input.
- Locations-only: a `level` selector (city / state / country).
- Customers/Products/Employees-only: a `sale_profit` toggle (off / sales / profit).
- A results area for a **bar chart** (top-N).
- A separate **Forecast** section: product name input, renders monthly quantity as a **line chart**.
- No auth, no responsive design, no error-state polish required.

---

## Module 6 — Frontend: API layer & config

**Goal:** `config.js` + the fetch helper in `app.js`.

- Keep the backend base URL in one config value (`config.js`, a single `const API_BASE = "..."`) — not hardcoded per call. It needs to be editable in seconds when the ngrok tunnel restarts.
- Every `fetch()` call to the backend must include the header `ngrok-skip-browser-warning: true`, or responses come back as ngrok's HTML warning page instead of JSON.
- Endpoint params map 1:1 to Module 4's query params (`user_id`, `name`, `limit`, `order`, `agg`, `sale_profit`/`sales_profit`, `level`, `name_chosen`, `product_name`).

---

## Module 7 — Frontend: charts

**Goal:** wire Module 5's controls and Module 6's API layer into Chart.js.

- Dimension explorer results (customers/products/locations/employees) → **bar chart**, re-rendered on each "Run."
- Forecast results (month, quantity) → **line chart**, one product at a time.
- Chart.js only — no other charting library.

---

## Module 8 — Explicitly out of scope

- Input sanitization/validation on `agg`, `order`, `level`, `name` toggles (fixed UI values only — already discussed and accepted).
- Multi-user auth flows beyond picking a `user_id`.
- Mobile/responsive layout.
- Production error handling/loading states beyond basic demo-safe behavior.
- Any hosting solution other than ngrok (no need to evaluate Render/Railway/etc.).

---

## Module 9 — Demo-day runbook

Depends on Modules 4–7 being complete.

1. Confirm `order_date` is stored as `YYYY-MM-DD` in the live `quickcast.db` (Module 1's open item) — otherwise `/api/forecast` silently returns null months.
2. Start Flask locally.
3. Start `ngrok http <port>` (authtoken already configured).
4. Copy the `https://...ngrok-free.app` forwarding URL into `config.js`'s `API_BASE`.
5. Open the GitHub Pages site.
6. Record. Keep the Flask process and the ngrok tunnel running for the full session.

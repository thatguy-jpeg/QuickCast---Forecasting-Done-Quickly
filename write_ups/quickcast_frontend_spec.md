# QuickCast — Flask + JS Frontend Build Request

## Project summary
QuickCast is a school project (course DSCI-D 532) built on a Superstore-style retail
sales dataset, normalized into a SQLite database. The database schema and all
data-loading/query logic are already built and working. What's needed now is a
**simple local demo frontend**: a Flask backend exposing the existing query functions
as JSON endpoints, and a static HTML/CSS/JS page (charts via Chart.js) that calls
those endpoints and renders the results. This is for a short demo video — not a
production app.

**Everything below is context from a prior conversation where the schema and backend
logic were built and debugged. Please treat the SQL/Python here as already correct
and tested — the task is to build the Flask + frontend layer on top of it.**

---

## Deployment context (important)
- **Frontend**: static HTML/CSS/JS deployed to **GitHub Pages** (public URL,
  `https://username.github.io/...`).
- **Backend**: Flask runs **locally** on the dev machine, exposed to the public
  internet via an **ngrok tunnel** (`ngrok http 5000`, or whatever port Flask uses).
  This gives a public `https://xxxx.ngrok-free.app` URL that forwards to
  `localhost`. GitHub Pages' JS calls that ngrok URL, not `localhost` directly.
- Because frontend (GitHub Pages, https) and backend (ngrok tunnel, https) are on
  **different origins**, `flask-cors` is required — not optional. Enable CORS on
  the Flask app for all routes, or scope it to the GitHub Pages origin.
- **ngrok's free tier interstitial**: visiting a free ngrok URL in a browser shows
  a "you are about to visit..." warning page before forwarding the request. This
  also affects `fetch()` calls from JS unless the request includes the header
  `ngrok-skip-browser-warning: true` — add this header to every frontend `fetch()`
  call, or the JSON responses will come back as this warning HTML instead of data.
- **The ngrok URL is not stable** on the free tier — it changes every time the
  tunnel restarts (unless a paid reserved domain is used). Put the backend base URL
  in one obvious place in the frontend JS (e.g. a single `const API_BASE = "..."`
  at the top of a `config.js`) so it can be updated in seconds right before
  recording, rather than hardcoded in multiple places.
- ngrok requires a free account + authtoken configured locally (`ngrok config
  add-authtoken ...`) before `ngrok http` will work — a one-time setup step, not
  a code change, but worth doing before the day of recording rather than during it.
- **Sequence for the actual demo**: start Flask locally → start `ngrok http <port>`
  → copy the resulting `https://...ngrok-free.app` URL into `config.js` → open the
  GitHub Pages site → record. The Flask process and the ngrok tunnel both need to
  stay running the entire time the demo page is being used.

---

## Database schema (SQLite, STRICT tables)

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
- `records` = one row per order (header/fact table). `orders` = one row per line
  item within an order (`row_id` is the true unique key, since the same product can
  appear twice in one order).
- `sales`, `discount`, `profit` are stored as **integer cents** (multiplied by 100
  at load time to avoid SQLite's lack of a native DECIMAL type). **Divide by 100
  when displaying these in the frontend.**
- `order_id` is TEXT (Superstore-style IDs like `"CA-2020-152156"`), not integer.
- `order_date` is expected to be stored as ISO `YYYY-MM-DD`. **Open item to verify:**
  the raw source CSV stores dates as `M/D/YYYY` (e.g. `12/28/2014`). A fix was
  recommended (convert with `pd.to_datetime(..., format="%m/%d/%Y").dt.strftime("%Y-%m-%d")`
  at load time) so `forecast()`'s `strftime('%Y-%m', order_date)` grouping works.
  **Confirm this was applied** — if `order_date` is still `M/D/YYYY` in the live db,
  the forecast endpoint will silently return null months.
- `PRAGMA foreign_keys = ON;` must be set per-connection (not persisted in the db
  file) — make sure the Flask app sets this on every connection it opens.
- A `TEMP TABLE user_records` must be created via `setup(cur, user_id)` **once per
  session/connection** before any of the query functions below will work — they all
  query `user_records`, not `records` directly.

---

## Existing backend functions (already written and tested — wrap these, don't rewrite them)

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

Notes on these functions:
- `agg`/`order`/`level`/`col`-selection params (`name`, `sale_profit`) are intended
  to come from a **fixed set of UI buttons/dropdowns**, not raw free-text user input
  — no SQL-injection sanitization was added on those params by design (acceptable
  scope decision for this project). `name_chosen` in `forecast()` **is** parameterized
  properly with `?` since it's real user-facing input (typed/selected product name).
- `location_query` has no `sale_profit`/name toggle — it always returns
  `{level}, {agg}(DISTINCT order_id)`.
- The `else` branches (no sales/profit) always aggregate `record_id` — effectively a
  count of records unless a different `agg` is passed.

---

## What to build

### 1. Flask backend (`app.py`)
- One endpoint per function above, returning JSON.

- **⚠️ Critical connection-handling gap to resolve while building:** `setup()`
  creates a `TEMP TABLE`, which SQLite scopes to the **single connection** that
  created it — it vanishes the moment that connection closes. A naive design with
  a standalone `POST /api/setup` endpoint that opens a connection, runs `setup()`,
  and closes it (per the earlier draft of this doc) **will not work** — the temp
  table would be gone before the next request (`/api/customers`, etc.) opens its
  own new connection. Two real options:
  - **(Recommended for a demo, simplest)**: drop the separate `/api/setup` endpoint
    entirely. Instead, every query endpoint takes `user_id` as a request param,
    and internally does: open connection → `setup(cur, user_id)` → run the actual
    query function → return JSON → close connection, all within that one request.
    Slightly redundant (re-creates `user_records` on every call), but avoids all
    cross-request state management, which is the right tradeoff for a short demo.
  - **(More "correct," more complexity)**: keep one persistent connection per
    browser session (e.g. stored server-side keyed by a session/user ID) so
    `setup()` only runs once. Not recommended here — adds real complexity
    (thread-safety, connection lifecycle, cleanup) for no benefit at demo scale.
  - **Whichever is chosen, every endpoint below needs `user_id` in its params**,
    not just a separate setup call.

- Revised suggested routes (per the recommended approach above — `user_id` on
  every call, no separate setup endpoint):
  - `GET /api/customers` — query params: `user_id`, `name`, `limit`, `order`, `agg`, `sale_profit`
  - `GET /api/products` — same param shape, plus `user_id`
  - `GET /api/locations` — query params: `user_id`, `limit`, `order`, `agg`, `level`
  - `GET /api/employees` — query params: `user_id`, `name`, `limit`, `order`, `agg`, `sales_profit`
  - `GET /api/forecast` — query params: `user_id`, `name_chosen`, `product_name`
- Remember to divide `sales`/`discount`/`profit` values by 100 before returning them
  in JSON, so the frontend doesn't have to.
- Set `PRAGMA foreign_keys = ON;` on every new connection.
- Include `flask-cors` and enable it on the app (frontend origin will be
  `https://username.github.io`, backend origin will be the ngrok URL — these must
  be allowed to talk to each other).
- No need for the app to know about ngrok itself — ngrok just forwards traffic to
  whatever port Flask is already running on. Nothing in `app.py` changes because of
  ngrok; it's purely a tunnel in front of the existing local server.
- The SQLite database file is `quickcast.db`. The six functions above live in
  whichever local `.py` file they were written to (name not specified in this
  handoff — confirm the actual filename/import path before writing `app.py`,
  or just paste the functions directly into `app.py` if simplest for a one-file demo).
- `cur.fetchall()` returns a list of tuples — convert to a list of dicts (or at
  least pair values with labels) before `jsonify()`, so the frontend JS gets
  something like `[{"customer_name": "...", "count": 12}, ...]` rather than bare
  `["...", 12]` pairs it has to interpret positionally.

### 2. Frontend (static HTML/CSS/JS, Chart.js for charts)
- Single page, simple/clean — demo quality, not production polish.
- A way to enter/select a `user_id` and trigger `/api/setup` (default to the seeded
  Guest user if that's simplest).
- Controls (dropdowns/buttons, matching the backend's fixed-value assumption):
  - Dimension selector: Customers / Products / Locations / Employees
  - `agg` selector: COUNT / SUM / AVG / MAX / MIN
  - `order` selector: ASC / DESC
  - `limit` input
  - For Locations: a `level` selector (city / state / country)
  - A `sale_profit` toggle (off / sales / profit) for customers/products/employees
- Top-N results render as a **bar chart**.
- A separate **Forecast** section: pick/type a product name, render **monthly
  quantity as a line chart**.
- No auth, no responsive design, no error-state polish needed — out of scope for
  this demo per prior discussion.
- Every `fetch()` call to the backend must include the header
  `ngrok-skip-browser-warning: true`, or responses will come back as ngrok's HTML
  warning page instead of JSON (see Deployment context above).
- Keep the backend base URL in one config value (`config.js` or similar) at the top
  of the JS, not hardcoded per-call — it will need to be updated whenever the ngrok
  tunnel restarts.

---

## Explicitly out of scope
- Input sanitization/validation on `agg`, `order`, `level`, `name` toggles (fixed
  UI values only, not raw text — already discussed and accepted as-is)
- Multi-user auth flows beyond picking a `user_id`
- Mobile/responsive layout
- Production error handling/loading states beyond basic demo-safe behavior
- Any hosting solution other than ngrok (no need to evaluate Render/Railway/etc. —
  decision is made)

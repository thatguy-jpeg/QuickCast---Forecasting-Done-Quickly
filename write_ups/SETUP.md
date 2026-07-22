# QuickCast — Setup & Demo-Day Runbook

Everything below assumes the codebase as reviewed: `database_init.py`,
`insertion.py` (fixed version — postal code + rounding bugs patched),
`guest_insertion.py`, `query_functions.py`, `app.py`, `index.html`,
`style.css`, `config.js`, `app.js`.

---

## 0. One-time prerequisites

- Python 3.10+
- The raw dataset CSV, named exactly:
  `Retail-Supply-Chain-Sales-Dataset(Retails Order Full Dataset).csv`
  placed in the same directory as `guest_insertion.py`.
- A free [ngrok](https://ngrok.com) account.
- A GitHub repo with Pages enabled, for the static frontend.

Install Python deps:

```bash
pip install pandas numpy flask flask-cors --break-system-packages
```

(Drop `--break-system-packages` if you're in a virtualenv.)

Install ngrok and authenticate once:

```bash
ngrok config add-authtoken <your-token-from-ngrok-dashboard>
```

---

## 1. Build the database

All backend `.py` files (`database_init.py`, `insertion.py`, `guest_insertion.py`,
`query_functions.py`, `app.py`) go in one folder, alongside the raw CSV.

**Use the fixed `insertion.py`** — the original had two bugs:
- money fields (`sales`/`discount`/`profit` × 100) used `int()`, which
  truncates instead of rounds and can silently drop a cent
- `postal_code` was cast with bare `str()`, which turns missing codes into
  the literal string `"nan"` and turns real ones into `"10024.0"` once any
  postal code in the file is missing (which upcasts the whole column to float)

If `quickcast.db` already exists from a previous run, delete it first —
otherwise you'll get duplicate/stale data:

```bash
rm -f quickcast.db guest_data.csv demo_data.csv
python3 guest_insertion.py
```

This reads the raw CSV, splits off an 80/20 `guest_data.csv` / `demo_data.csv`,
and loads `guest_data.csv` into `quickcast.db` under a single `"Guest"` user
(`user_id = 1`).

**Sanity check the load:**

```bash
python3 -c "
import sqlite3
con = sqlite3.connect('quickcast.db')
c = con.cursor()
for t in ('users','customers','locations','employees','products','records','orders'):
    print(t, c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0])
print(c.execute('SELECT order_date FROM records LIMIT 3').fetchall())
"
```

- Row counts should be nonzero for every table.
- `order_date` values must look like `2020-01-05` (`YYYY-MM-DD`). If you see
  `1/5/2020` instead, the date-format fix in `insertion.py` didn't run —
  re-check you're using the fixed file, not an older copy.

---

## 2. Run the Flask backend

From the same folder:

```bash
python3 app.py
```

Runs on `http://localhost:5000`. Leave this terminal open — it needs to
stay running for the whole demo.

Quick check it's alive and returning real (not cents) values:

```bash
curl "http://localhost:5000/api/customers?user_id=1&agg=SUM&sale_profit=sales"
```

Values should look like dollars (e.g. `27.99`), not cents (`2799`).

---

## 3. Start the ngrok tunnel

In a **second terminal**, same machine:

```bash
ngrok http 5000
```

Copy the `https://xxxx.ngrok-free.app` forwarding URL it prints — this
changes every time you restart the tunnel (free tier has no fixed domain).

Leave this terminal open too. Both Flask and ngrok must run simultaneously
for the whole demo.

---

## 4. Point the frontend at the tunnel

Open `config.js` and replace the placeholder:

```js
const API_BASE = "https://xxxx.ngrok-free.app";   // <-- your real URL from step 3
```

This is the **only** file that needs editing between sessions — everything
else is static.

---

## 5. Deploy the frontend to GitHub Pages

One-time:

1. Put `index.html`, `style.css`, `config.js`, `app.js` in a GitHub repo.
2. Repo Settings → Pages → deploy from the branch containing these files.
3. Note the resulting URL: `https://<username>.github.io/<repo>/`.

Every time you update `config.js` with a new ngrok URL, commit and push —
GitHub Pages redeploys automatically (usually under a minute).

If you'd rather not push to GitHub before every recording, you can instead
just open `index.html` locally in a browser after editing `config.js` — it
still works, since the frontend only talks to the ngrok URL, not to
GitHub Pages itself. Use GitHub Pages only when you actually need the
public link.

---

## 5b. New feature: upload demo data as a new user (live, in-app)

The page now has an **UPLOAD CSV** panel above USER_ID. It calls `POST /api/upload`
(`username` + `file` as multipart form data), which:

1. Rejects if `username` already exists in `users` (409).
2. Runs the CSV through the same `insert_records_orders()` used for the Guest
   load, under the new username.
3. Returns the new `user_id`, which the page auto-fills into the USER_ID field.

**File requirement:** the CSV must have the same 19 columns as `demo_data.csv`
(the split-off 20% from `guest_insertion.py`). For the demo, just upload
`demo_data.csv` directly through the panel — that's exactly what it's for.

**Known limitation, accepted for demo scope:** `insert_customers` /
`insert_locations` / `insert_employees` each commit immediately and
independently (pre-existing behavior, not changed here). `app.py` pre-checks
the username before calling any of them, which covers the most likely
on-camera failure (re-using a username). But if the upload fails for some
other reason (e.g. malformed row) partway through, rows already committed to
`customers`/`locations`/`employees`/`products` for that attempt are not rolled
back. Not a concern for a single clean demo run; worth knowing if you're
retrying failed uploads repeatedly.

Quick check it works before recording:

```bash
curl -X POST http://localhost:5000/api/upload \
  -F "username=demo_run1" \
  -F "file=@demo_data.csv"
```

Should return `{"user_id": 2, "username": "demo_run1"}` (or similar).

---

## 6. Full demo-day sequence

Do these in order, right before recording:

1. Confirm `quickcast.db` is built and `order_date` is `YYYY-MM-DD` (§1).
2. Terminal 1: `python3 app.py`
3. Terminal 2: `ngrok http 5000`
4. Copy the new `https://xxxx.ngrok-free.app` URL into `config.js`.
5. Commit/push `config.js` if using GitHub Pages, or just refresh the local
   `index.html` if running it locally.
6. Open the site, set **USER_ID** to `1` (the seeded Guest), pick a
   dimension, hit **RUN QUERY**.
7. Test the **Forecast** panel with a product name that actually exists in
   your data (spot-check one via `query_functions.product_query` or a quick
   `SELECT product_name FROM products LIMIT 5` if unsure).
8. Record. Keep both terminals running until you're done.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Frontend gets HTML instead of JSON | ngrok interstitial page | Confirm `app.js`'s `fetch()` calls include the `ngrok-skip-browser-warning: true` header (already in the codebase — check you didn't strip it) |
| CORS error in browser console | Origins don't match | `flask-cors`'s `CORS(app)` is already wide-open in `app.py` — if you scoped it down, make sure the GitHub Pages origin is included |
| Forecast returns empty months | `order_date` not `YYYY-MM-DD` | Re-run §1 with the fixed `insertion.py`; check the sanity query |
| Money values look 100x too large | Frontend re-dividing already-converted values, or hitting a raw/older backend | `app.py` already divides SUM/AVG/MAX/MIN of sales/profit by 100 server-side — don't divide again in JS |
| Postal codes show `"nan"` or end in `.0` | Old `insertion.py` (pre-fix) | Rebuild `quickcast.db` with the corrected file from this conversation |
| `ngrok-free.app` URL stopped working mid-demo | Tunnel restarted, URL rotated | Re-copy the new URL into `config.js`, redeploy/refresh |
| `/api/*` calls 404 or hang | Flask not running, or wrong port in `ngrok http <port>` | Confirm Flask's terminal shows it's serving on 5000 and ngrok was started with the same port |

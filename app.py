"""
QuickCast backend — Module 4.

Strategy (per Module 3, already decided): no separate /api/setup endpoint.
Every query endpoint takes user_id and, within a single request, does:
open connection -> PRAGMA foreign_keys=ON -> setup(cur, user_id) -> run the
query function -> convert rows to dicts -> close connection -> jsonify.
"""

import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS

from query_functions import (
    setup,
    customer_query,
    product_query,
    location_query,
    employee_query,
    forecast,
)

app = Flask(__name__)
# Frontend origin is GitHub Pages, backend origin is the ngrok tunnel.
# Wide open here since this is a local demo build; scope to the GitHub
# Pages origin if you want it tighter.
CORS(app)

DB_PATH = "quickcast.db"


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ---------------------------------------------------------------------------
# Helpers for shaping responses (Module 4 requirements)
# ---------------------------------------------------------------------------

def rows_to_dicts(rows, key_a, key_b):
    return [{key_a: r[0], key_b: r[1]} for r in rows]


def divide_cents(dicts, value_key):
    for d in dicts:
        if d[value_key] is not None:
            d[value_key] = d[value_key] / 100
    return dicts


def is_currency_agg(agg, sale_profit_param):
    """True only when the aggregate is actually a money figure: SUM/AVG/MAX/MIN
    of sales or profit. COUNT(sales) is a row count, not money — never divide."""
    return sale_profit_param in ("sales", "profit") and agg.upper() != "COUNT"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/api/customers")
def api_customers():
    user_id = request.args.get("user_id", type=int)
    name = request.args.get("name", "true").lower() == "true"
    limit = request.args.get("limit", 10, type=int)
    order = request.args.get("order", "DESC")
    agg = request.args.get("agg", "COUNT")
    sale_profit_param = request.args.get("sale_profit", "off")
    sale_profit_col = sale_profit_param if sale_profit_param in ("sales", "profit") else False

    conn = get_conn()
    cur = conn.cursor()
    setup(cur, user_id)
    rows = customer_query(cur, name=name, limit=limit, order=order, agg=agg, sale_profit=sale_profit_col)
    conn.close()

    data = rows_to_dicts(rows, "label", "value")
    if is_currency_agg(agg, sale_profit_param):
        data = divide_cents(data, "value")
    return jsonify(data)


@app.route("/api/products")
def api_products():
    user_id = request.args.get("user_id", type=int)
    name = request.args.get("name", "true").lower() == "true"
    limit = request.args.get("limit", 10, type=int)
    order = request.args.get("order", "DESC")
    agg = request.args.get("agg", "COUNT")
    sale_profit_param = request.args.get("sale_profit", "off")
    sale_profit_col = sale_profit_param if sale_profit_param in ("sales", "profit") else False

    conn = get_conn()
    cur = conn.cursor()
    setup(cur, user_id)
    rows = product_query(cur, name=name, limit=limit, order=order, agg=agg, sale_profit=sale_profit_col)
    conn.close()

    data = rows_to_dicts(rows, "label", "value")
    if is_currency_agg(agg, sale_profit_param):
        data = divide_cents(data, "value")
    return jsonify(data)


@app.route("/api/locations")
def api_locations():
    user_id = request.args.get("user_id", type=int)
    limit = request.args.get("limit", 10, type=int)
    order = request.args.get("order", "DESC")
    agg = request.args.get("agg", "COUNT")
    level = request.args.get("level", "city")

    conn = get_conn()
    cur = conn.cursor()
    setup(cur, user_id)
    rows = location_query(cur, limit=limit, order=order, agg=agg, level=level)
    conn.close()

    # location_query always aggregates order_id, never sales/profit — no cents division.
    data = rows_to_dicts(rows, "label", "value")
    return jsonify(data)


@app.route("/api/employees")
def api_employees():
    user_id = request.args.get("user_id", type=int)
    name = request.args.get("name", "true").lower() == "true"
    limit = request.args.get("limit", 10, type=int)
    order = request.args.get("order", "DESC")
    agg = request.args.get("agg", "COUNT")
    sales_profit_param = request.args.get("sales_profit", "off")
    sales_profit_col = sales_profit_param if sales_profit_param in ("sales", "profit") else False

    conn = get_conn()
    cur = conn.cursor()
    setup(cur, user_id)
    rows = employee_query(cur, name=name, limit=limit, order=order, agg=agg, sales_profit=sales_profit_col)
    conn.close()

    data = rows_to_dicts(rows, "label", "value")
    if is_currency_agg(agg, sales_profit_param):
        data = divide_cents(data, "value")
    return jsonify(data)


@app.route("/api/forecast")
def api_forecast():
    user_id = request.args.get("user_id", type=int)
    name_chosen = request.args.get("name_chosen")
    product_name = request.args.get("product_name", "true").lower() == "true"

    conn = get_conn()
    cur = conn.cursor()
    setup(cur, user_id)
    rows = forecast(cur, name_chosen, product_name=product_name)
    conn.close()

    # month, quantity — quantity is a unit count, not currency, no division.
    data = rows_to_dicts(rows, "month", "quantity")
    return jsonify(data)


if __name__ == "__main__":
    # debug stays OFF: this server gets tunneled to the public internet via
    # ngrok, and the Flask debugger allows arbitrary code execution from any
    # error page.
    app.run(port=5000, debug=False)

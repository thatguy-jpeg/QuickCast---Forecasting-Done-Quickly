import pandas as pd
import numpy as np
import sqlite3 as sql
from database_init import init

def clean_postal_code(value):
    if pd.isna(value):
        return None
    if isinstance(value, float):
        return str(int(value))
    return str(value)

def insert_locations(cur, df):
    df = df[["Country", "State", "City", "Postal Code"]].drop_duplicates()
    ids = []

    for row in df.itertuples(index=False):
        query = '''
        INSERT INTO locations (country, state, city, postal_code)
        VALUES (?, ?, ?, ?)
        RETURNING location_id;
        '''
        cur.execute(query, (row[0], row[1], row[2], clean_postal_code(row[3])))
        ids.append(cur.fetchone()[0])

    df["location_id"] = ids
    cur.connection.commit()

    return df

def insert_customers(cur, df):
    df = df[["Customer ID", "Customer Name"]].drop_duplicates(subset=["Customer ID"])
    ids = []

    for name in df["Customer Name"]:
        query = '''
        INSERT INTO customers (customer_name) VALUES (?) RETURNING customer_id;
        '''
        cur.execute(query, (name,))
        ids.append(cur.fetchone()[0])

    df["customer_id"] = ids
    cur.connection.commit()

    return df

def insert_products(cur, df):
    df = df[["Product ID", "Product Name", "Category", "Sub-Category"]].drop_duplicates(subset = ["Product ID"])
    ids = []

    for row in df.itertuples(index=False):
        query = '''
        INSERT INTO products (product_name, category, subcategory)
        VALUES (?, ?, ?)
        RETURNING product_id;
        '''
        cur.execute(query, (row[1], row[2], row[3]))
        ids.append(cur.fetchone()[0])

    df["product_id"] = ids
    cur.connection.commit()

    return df

def insert_employees(cur, df):
    df = df[["Retail Sales People"]].drop_duplicates()
    ids = []

    for row in df.itertuples(index=False):
        query = '''
        INSERT INTO employees (retail_sales_people)
        VALUES (?)
        RETURNING employee_id;
        '''

        cur.execute(query, (row[0],))
        ids.append(cur.fetchone()[0])

    df["employee_id"] = ids
    cur.connection.commit()

    return df

def insert_user(cur, username="Guest", password=""):
    id = []

    query = '''
    INSERT INTO users (username, password)
    VALUES (?, ?)
    RETURNING user_id;
    '''

    cur.execute(query, (username, password))
    id.append(cur.fetchone()[0])

    cur.connection.commit()

    return id

def insert_records_orders(cur, df, username="Guest", password=""):
    customers = insert_customers(cur=cur, df=df)
    locations = insert_locations(cur=cur, df=df)
    employees = insert_employees(cur=cur, df=df)
    users = insert_user(cur=cur, username=username, password=password)
    products = insert_products(cur=cur, df=df)

    df = df.merge(customers[["Customer ID", "customer_id"]], on="Customer ID")
    df = df.merge(locations[["Country", "State", "City", "Postal Code", "location_id"]], on=["Country", "State", "City", "Postal Code"])
    df = df.merge(employees[["Retail Sales People", "employee_id"]], on="Retail Sales People")
    df = df.merge(products[["Product ID", "product_id"]], on="Product ID")
    df["user_id"] = users[0]

    df["Order Date"] = pd.to_datetime(df["Order Date"], format="%m/%d/%Y").dt.strftime("%Y-%m-%d")

    recs = df[["Order ID", "customer_id", "location_id", "employee_id", "user_id", "Order Date"]].drop_duplicates(subset = ["Order ID"])

    df[["Sales"]] = df[["Sales"]] * 100
    df[["Profit"]] = df[["Profit"]] * 100
    df[["Discount"]] = df[["Discount"]] * 100

    for row in recs.itertuples(index=False):
        query = '''
        INSERT INTO records (order_id, customer_id, location_id, employee_id, user_id, order_date)
        VALUES (?, ?, ?, ?, ?, ?)
        '''

        cur.execute(query, (row[0], row[1], row[2], row[3], row[4], row[5]))

    ords = df[["Row ID", "Order ID", "product_id", "Quantity", "Sales", "Discount", "Profit", "Returned"]]

    for row in ords.itertuples(index=False):
        query = '''
    INSERT INTO orders (row_id, order_id, product_id, quantity, sales, discount, profit, returned)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
        
        cur.execute(query, (row[0], row[1], row[2], row[3], round(row[4]), round(row[5]), round(row[6]), row[7]))
    
    cur.connection.commit()

    return users[0]
import pandas as pd
import numpy as np
import sqlite3 as sql
from database_init import init
from pathlib import Path
from insertion import insert_records_orders

if not Path("../data/guest_data.csv").exists():
    
    df = pd.read_csv("../data/Retail-Supply-Chain-Sales-Dataset(Retails Order Full Dataset).csv", encoding="latin1")

    df = df[["Row ID", "Order ID", "Order Date", "Customer ID", "Customer Name", "Country", "City", "State", "Postal Code", "Retail Sales People", "Product ID", "Category", "Sub-Category", "Product Name", "Returned", "Sales", "Quantity", "Discount", "Profit"]]

    df["Returned"] = df["Returned"].replace({"Not": 0, "Yes": 1})

    demo = df.sample(frac=0.2, random_state=42)
    main = df.drop(demo.index)

    main.to_csv('guest_data.csv', index=False)
    demo.to_csv('demo_data.csv', index=False)


df = pd.read_csv("../data/guest_data.csv", encoding="latin1")

init()

con = sql.connect("../quickcast.db")
c = con.cursor()

c.execute("PRAGMA foreign_keys = ON;")

insert_records_orders(df=df, cur=c)

con.commit()
con.close()
import sqlite3 as sql
import pandas as pd

con = sql.connect("quickcast.db")
c = con.cursor()

g = set(pd.read_csv("data/guest_data.csv")["Order ID"])
d = set(pd.read_csv("data/demo_data.csv")["Order ID"])
print(len(g & d))
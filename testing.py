import sqlite3 as sql
import pandas as pd

con = sql.connect("quickcast.db")
c = con.cursor()

query = '''
SELECT *
FROM locations
WHERE state = 'Texas'
LIMIT 50;
'''

for i in c.execute(query):
    print(i)

query = '''
SELECT *
FROM products
LIMIT 100;
'''

for i in c.execute(query):
    print(i)

query = '''
SELECT *
FROM records
ORDER BY record_id DESC
LIMIT 30;
'''

for i in c.execute(query):
    print(i)

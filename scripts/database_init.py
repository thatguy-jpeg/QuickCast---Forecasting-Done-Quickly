def init():
    
    import sqlite3 as sql

    con = sql.connect('../quickcast.db')

    c = con.cursor()

    query = '''
    PRAGMA foreign_keys = OFF;
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS records(
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
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL DEFAULT ""
    ) STRICT;
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS customers(
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL
    ) STRICT;
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS employees(
    employee_id INTEGER PRIMARY KEY AUTOINCREMENT,
    retail_sales_people TEXT NOT NULL
    ) STRICT;
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS locations(
    location_id INTEGER PRIMARY KEY AUTOINCREMENT,
    country TEXT NOT NULL,
    state TEXT,
    city TEXT NOT NULL,
    postal_code TEXT
    ) STRICT;
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS products(
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category TEXT,
    subcategory TEXT
    ) STRICT;
    '''

    c.execute(query)

    query = '''
    CREATE TABLE IF NOT EXISTS orders(
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
    '''

    c.execute(query)

    query = '''
    PRAGMA foreign_keys = ON;
    '''

    c.execute(query)

    con.commit()
    con.close()
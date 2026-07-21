def setup(cur, user_id):
    
    query = '''
    DROP TABLE IF EXISTS user_records;
    '''

    cur.execute(query)
    
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
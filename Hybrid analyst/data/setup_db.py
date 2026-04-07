"""
Sets up a realistic business SQLite database for the Hybrid AI Analyst demo.
Tables: customers, products, orders, order_items, sales_reps, regions
"""

import sqlite3
import random
from datetime import datetime, timedelta

DB_PATH = "data/business.db"

def setup():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ── REGIONS ──────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS regions (
        region_id   INTEGER PRIMARY KEY,
        region_name TEXT NOT NULL,
        country     TEXT NOT NULL
    )""")
    cur.executemany("INSERT OR IGNORE INTO regions VALUES (?,?,?)", [
        (1, "North America", "USA"),
        (2, "Europe",        "UK"),
        (3, "Asia Pacific",  "Australia"),
        (4, "South Asia",    "India"),
    ])

    # ── SALES REPS ────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sales_reps (
        rep_id    INTEGER PRIMARY KEY,
        name      TEXT NOT NULL,
        region_id INTEGER,
        quota     REAL,
        FOREIGN KEY (region_id) REFERENCES regions(region_id)
    )""")
    cur.executemany("INSERT OR IGNORE INTO sales_reps VALUES (?,?,?,?)", [
        (1, "Alice Johnson",  1, 500000),
        (2, "Bob Smith",      1, 450000),
        (3, "Clara Diaz",     2, 400000),
        (4, "David Lee",      3, 380000),
        (5, "Eva Patel",      4, 350000),
        (6, "Frank Nguyen",   2, 420000),
    ])

    # ── CUSTOMERS ─────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id   INTEGER PRIMARY KEY,
        company_name  TEXT NOT NULL,
        industry      TEXT,
        region_id     INTEGER,
        plan          TEXT,
        mrr           REAL,
        joined_date   TEXT,
        FOREIGN KEY (region_id) REFERENCES regions(region_id)
    )""")
    customers = [
        (1,  "TechCorp Inc",       "SaaS",       1, "Enterprise", 12000, "2022-01-15"),
        (2,  "FinBank Ltd",        "Finance",     2, "Pro",         4500, "2022-03-20"),
        (3,  "RetailGiant",        "Retail",      3, "Enterprise",  9800, "2021-11-05"),
        (4,  "HealthPlus",         "Healthcare",  4, "Starter",     1200, "2023-02-10"),
        (5,  "EduLearn",           "Education",   1, "Pro",         3200, "2022-07-18"),
        (6,  "LogiTrack",          "Logistics",   2, "Enterprise",  8700, "2021-09-30"),
        (7,  "CloudNine",          "SaaS",        1, "Enterprise", 15000, "2020-05-22"),
        (8,  "GreenEnergy Co",     "Energy",      3, "Pro",         5600, "2023-01-08"),
        (9,  "MediaHouse",         "Media",       4, "Starter",      900, "2023-04-14"),
        (10, "AutoDrive",          "Automotive",  1, "Pro",         4100, "2022-10-01"),
        (11, "PharmaLink",         "Healthcare",  2, "Enterprise", 11000, "2021-06-17"),
        (12, "FoodTech",           "Food",        4, "Starter",     1500, "2023-05-25"),
        (13, "SecureIT",           "Cybersecurity",1,"Enterprise", 13500, "2020-12-03"),
        (14, "TravelEase",         "Travel",      3, "Pro",         3800, "2022-08-11"),
        (15, "BuildSmart",         "Construction",2, "Pro",         4200, "2023-03-19"),
    ]
    cur.executemany("INSERT OR IGNORE INTO customers VALUES (?,?,?,?,?,?,?)", customers)

    # ── PRODUCTS ──────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id   INTEGER PRIMARY KEY,
        product_name TEXT NOT NULL,
        category     TEXT,
        unit_price   REAL,
        cost_price   REAL
    )""")
    cur.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?,?,?)", [
        (1, "Data Enrichment API",     "API",      299.00, 45.00),
        (2, "CRM Integration Pack",    "Add-on",   149.00, 20.00),
        (3, "Analytics Dashboard",     "Platform", 499.00, 80.00),
        (4, "Export Credits (1000)",   "Credits",   99.00, 10.00),
        (5, "Priority Support",        "Service",  199.00, 50.00),
        (6, "Custom Data Model",       "Service",  999.00,300.00),
        (7, "B2B Contact Database",    "Data",     399.00, 60.00),
        (8, "Technographics Module",   "Add-on",   249.00, 35.00),
    ])

    # ── ORDERS ────────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id    INTEGER PRIMARY KEY,
        customer_id INTEGER,
        rep_id      INTEGER,
        order_date  TEXT,
        status      TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
        FOREIGN KEY (rep_id)      REFERENCES sales_reps(rep_id)
    )""")

    # ── ORDER ITEMS ───────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        item_id    INTEGER PRIMARY KEY,
        order_id   INTEGER,
        product_id INTEGER,
        quantity   INTEGER,
        unit_price REAL,
        FOREIGN KEY (order_id)   REFERENCES orders(order_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )""")

    # Generate ~120 orders over 2 years
    random.seed(42)
    base_date = datetime(2023, 1, 1)
    order_id = 1
    item_id  = 1
    for _ in range(120):
        cust_id  = random.randint(1, 15)
        rep_id   = random.randint(1, 6)
        days_ago = random.randint(0, 730)
        order_date = (base_date + timedelta(days=days_ago)).strftime("%Y-%m-%d")
        status = random.choice(["completed","completed","completed","pending","refunded"])
        cur.execute("INSERT OR IGNORE INTO orders VALUES (?,?,?,?,?)",
                    (order_id, cust_id, rep_id, order_date, status))
        # 1-3 items per order
        for _ in range(random.randint(1, 3)):
            prod_id  = random.randint(1, 8)
            qty      = random.randint(1, 5)
            price    = [299,149,499,99,199,999,399,249][prod_id-1]
            cur.execute("INSERT OR IGNORE INTO order_items VALUES (?,?,?,?,?)",
                        (item_id, order_id, prod_id, qty, price))
            item_id += 1
        order_id += 1

    conn.commit()
    conn.close()
    print(f"✅ Database created at {DB_PATH}")
    print(f"   Tables: regions, sales_reps, customers, products, orders, order_items")

if __name__ == "__main__":
    setup()

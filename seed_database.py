import random
import sqlite3
import config

rng = random.Random(42)
config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
if config.DB_PATH.exists():
    config.DB_PATH.unlink()

conn = sqlite3.connect(config.DB_PATH)
cur = conn.cursor()
cur.executescript("""
CREATE TABLE sales(id INTEGER PRIMARY KEY, region TEXT, product TEXT, revenue REAL, date TEXT, units_sold INTEGER);
CREATE TABLE customers(id INTEGER PRIMARY KEY, name TEXT, industry TEXT, churn_date TEXT, satisfaction_score REAL);
CREATE TABLE employees(id INTEGER PRIMARY KEY, department TEXT, satisfaction_score REAL, tenure_years REAL);
""")

products = {"Starter Plan": (12000, 49), "Pro Plan": (28000, 149),
            "Enterprise Suite": (60000, 899), "Support Add-on": (8000, 29)}
regions = {"North": 1.1, "South": 0.8, "East": 1.0, "West": 1.2}
for region, rf in regions.items():
    for product, (base, price) in products.items():
        for m in range(1, 13):
            growth = 1 + 0.02 * (m - 1)
            q4 = 1.15 if m >= 10 else 1.0
            revenue = round(base * rf * growth * q4 * rng.uniform(0.9, 1.1), 2)
            cur.execute("INSERT INTO sales(region,product,revenue,date,units_sold) VALUES (?,?,?,?,?)",
                        (region, product, revenue, f"2025-{m:02d}-15", int(revenue / price)))

industries = ["Healthcare", "Retail", "Finance", "Education", "Manufacturing", "Logistics", "Media"]
for i in range(1, 201):
    churned = rng.random() < 0.17
    churn_date = f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}" if churned else None
    score = rng.gauss(5.5 if churned else 7.8, 1.2)
    cur.execute("INSERT INTO customers(name,industry,churn_date,satisfaction_score) VALUES (?,?,?,?)",
                (f"Customer {i:03d}", rng.choice(industries), churn_date, round(min(10, max(1, score)), 1)))

dept_mean = {"Engineering": 7.0, "Sales": 6.6, "Support": 6.2, "Marketing": 7.4, "People": 8.0, "Finance": 7.2}
for i in range(1, 121):
    dept = rng.choice(list(dept_mean))
    score = rng.gauss(dept_mean[dept], 1.0)
    cur.execute("INSERT INTO employees(department,satisfaction_score,tenure_years) VALUES (?,?,?)",
                (dept, round(min(10, max(1, score)), 1), round(rng.expovariate(1 / 3.0), 1)))

conn.commit()
for t in ("sales", "customers", "employees"):
    print(t, cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0], "rows")
conn.close()


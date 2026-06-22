"""
Seeds the PostgreSQL legacy database with the German Credit dataset.
Re-runnable: drops and recreates the customers table on each run.

Usage:
  # With Docker postgres running:
  python legacy_simulator/seed_db.py

  # Custom connection:
  LEGACY_DB_HOST=myhost LEGACY_DB_PORT=5433 python legacy_simulator/seed_db.py
"""
import os
import ssl
import sys

import pandas as pd
import psycopg2

# Corporate SSL fix — same issue that affects npm and OpenML downloads
ssl._create_default_https_context = ssl._create_unverified_context

CLEAN_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "german_credit", "german_credit_clean.csv")

conn_params = dict(
    host=os.getenv("LEGACY_DB_HOST", "localhost"),
    port=int(os.getenv("LEGACY_DB_PORT", 5432)),
    database=os.getenv("LEGACY_DB_NAME", "legacy_bank"),
    user=os.getenv("LEGACY_DB_USER", "admin"),
    password=os.getenv("LEGACY_DB_PASSWORD", "admin123"),
)

try:
    conn = psycopg2.connect(**conn_params)
except Exception as exc:
    print(f"Cannot connect to PostgreSQL: {exc}")
    print("Start the database with: docker compose up -d")
    sys.exit(1)

cur = conn.cursor()

# Drop and recreate for idempotency
cur.execute("DROP TABLE IF EXISTS customers;")
cur.execute("""
    CREATE TABLE customers (
        customer_id     SERIAL PRIMARY KEY,
        age             INT,
        sex             SMALLINT,          -- 1=male 0=female (fairness attribute)
        job             VARCHAR(50),
        housing         VARCHAR(30),
        savings_status  VARCHAR(50),
        checking_status VARCHAR(50),
        credit_amount   INT,
        duration        INT,
        purpose         VARCHAR(50),
        credit_history  VARCHAR(50),
        target          SMALLINT           -- 1=good 0=bad (ground truth label)
    );
""")

df = pd.read_csv(CLEAN_CSV)

rows = [
    (
        int(row["age"]),
        int(row["sex"]),
        str(row["job"]),
        str(row["housing"]),
        str(row["savings_status"]),
        str(row["checking_status"]),
        int(row["credit_amount"]),
        int(row["duration"]),
        str(row["purpose"]),
        str(row["credit_history"]),
        int(row["target"]),
    )
    for _, row in df.iterrows()
]

cur.executemany("""
    INSERT INTO customers
        (age, sex, job, housing, savings_status, checking_status,
         credit_amount, duration, purpose, credit_history, target)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
""", rows)

conn.commit()
cur.close()
conn.close()
print(f"Legacy DB seeded with {len(rows)} customers.")

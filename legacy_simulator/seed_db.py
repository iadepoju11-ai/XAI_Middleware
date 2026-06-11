import os
import psycopg2
import pandas as pd
from sklearn.datasets import fetch_openml

# Load German Credit dataset as a proxy for legacy customer data
german = fetch_openml('german', as_frame=True, parser='pandas')
df = german.frame

conn = psycopg2.connect(
    host=os.getenv('LEGACY_DB_HOST', 'localhost'),
    port=int(os.getenv('LEGACY_DB_PORT', 5432)),
    database=os.getenv('LEGACY_DB_NAME', 'legacy_bank'),
    user=os.getenv('LEGACY_DB_USER', 'admin'),
    password=os.getenv('LEGACY_DB_PASSWORD', 'admin123'),
)
cur = conn.cursor()

cur.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        customer_id SERIAL PRIMARY KEY,
        age INT,
        sex VARCHAR(10),
        job INT,
        housing VARCHAR(20),
        savings_account VARCHAR(20),
        checking_account VARCHAR(20),
        credit_amount INT,
        duration INT,
        purpose VARCHAR(50),
        credit_history VARCHAR(50)
    );
''')

for _, row in df.iterrows():
    cur.execute('''
        INSERT INTO customers (age, sex, job, housing, savings_account,
                               checking_account, credit_amount, duration,
                               purpose, credit_history)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ''', (
        row['age'], row['personal_status_sex'], row['job'], row['housing'],
        row['savings_status'], row['checking_status'], row['credit_amount'],
        row['duration'], row['purpose'], row['credit_history']
    ))
conn.commit()
cur.close()
conn.close()
print("Legacy DB seeded with 1000 synthetic customers.")
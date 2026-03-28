import sqlite3
import os
import sys

# This file is assumed to be inside backend_core/app/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'data', 'kumar_core.db')

if not os.path.exists(DB_PATH):
    print(f"Database not found at: {DB_PATH}")
    sys.exit(2)

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

try:
    cur.execute("PRAGMA table_info(production_items)")
    cols = [row[1] for row in cur.fetchall()]

    if 'is_completed' in cols:
        print("Column `is_completed` already exists in production_items.")
        sys.exit(0)

    cur.execute(
        "ALTER TABLE production_items ADD COLUMN is_completed BOOLEAN DEFAULT 0"
    )
    conn.commit()
    print("Added column `is_completed` to production_items successfully.")
    sys.exit(0)

except sqlite3.OperationalError as e:
    print("SQLite OperationalError:", e)
    sys.exit(3)

except Exception as e:
    print("Error:", e)
    sys.exit(4)

finally:
    conn.close()

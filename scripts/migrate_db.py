"""
Database Migration Script
Run this script to add new columns to existing tables for the enhanced tracking system.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend_core.app.db import engine
from sqlalchemy import text

def run_migrations():
    """Add new columns to production_items table for enhanced tracking."""
    
    migrations = [
        # ProductionItem new columns
        ("production_items", "quantity", "REAL DEFAULT 1.0"),
        ("production_items", "unit", "TEXT"),
        ("production_items", "weight_per_unit", "REAL"),
        ("production_items", "material_requirements", "TEXT"),
        ("production_items", "checklist", "TEXT"),
        ("production_items", "notes", "TEXT"),
        ("production_items", "fabrication_deducted", "BOOLEAN DEFAULT 0"),
        ("production_items", "created_at", "DATETIME DEFAULT CURRENT_TIMESTAMP"),
    ]
    
    with engine.connect() as conn:
        for table, column, col_type in migrations:
            try:
                # Check if column exists
                result = conn.execute(text(f"PRAGMA table_info({table})"))
                existing_cols = [row[1] for row in result.fetchall()]
                
                if column not in existing_cols:
                    print(f"Adding column {column} to {table}...")
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                    conn.commit()
                    print(f"  ✓ Added {column}")
                else:
                    print(f"  - Column {column} already exists in {table}")
            except Exception as e:
                print(f"  ! Error adding {column} to {table}: {e}")
    
    print("\n✓ Migration completed!")

if __name__ == "__main__":
    print("Running database migrations for KumarBrothers ERP...")
    print("=" * 50)
    run_migrations()

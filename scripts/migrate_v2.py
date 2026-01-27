"""
Database migration script to add missing columns from version 2.
Run this script to update the database schema.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend_core.app.db import engine
from sqlalchemy import text

def migrate():
    """Add missing columns to support version 2 features."""
    
    migrations = [
        # Customer table - add email, phone, is_active
        ("customers", "email", "ALTER TABLE customers ADD COLUMN email TEXT"),
        ("customers", "phone", "ALTER TABLE customers ADD COLUMN phone TEXT"),
        ("customers", "is_active", "ALTER TABLE customers ADD COLUMN is_active BOOLEAN DEFAULT 1"),
        
        # ProductionItem table - add current_stage tracking fields
        ("production_items", "current_stage", "ALTER TABLE production_items ADD COLUMN current_stage TEXT DEFAULT 'fabrication'"),
        ("production_items", "stage_updated_at", "ALTER TABLE production_items ADD COLUMN stage_updated_at DATETIME"),
        ("production_items", "stage_updated_by", "ALTER TABLE production_items ADD COLUMN stage_updated_by INTEGER"),
        ("production_items", "material_deducted", "ALTER TABLE production_items ADD COLUMN material_deducted BOOLEAN DEFAULT 0"),
        
        # StageTracking table - add is_checked
        ("stage_tracking", "is_checked", "ALTER TABLE stage_tracking ADD COLUMN is_checked BOOLEAN DEFAULT 0"),
        
        # Instruction table - add updated_at
        ("instructions", "updated_at", "ALTER TABLE instructions ADD COLUMN updated_at DATETIME"),
        
        # MaterialUsage table - add applied
        ("material_usage", "applied", "ALTER TABLE material_usage ADD COLUMN applied BOOLEAN DEFAULT 0"),
    ]
    
    new_tables = [
        # MaterialConsumption table
        """
        CREATE TABLE IF NOT EXISTS material_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_usage_id INTEGER NOT NULL,
            inventory_id INTEGER NOT NULL,
            qty REAL NOT NULL,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (material_usage_id) REFERENCES material_usage(id),
            FOREIGN KEY (inventory_id) REFERENCES inventory(id)
        )
        """,
        # TrackingStageHistory table
        """
        CREATE TABLE IF NOT EXISTS tracking_stage_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            from_stage TEXT,
            to_stage TEXT,
            changed_by INTEGER,
            changed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            remarks TEXT,
            FOREIGN KEY (material_id) REFERENCES production_items(id),
            FOREIGN KEY (changed_by) REFERENCES users(id)
        )
        """
    ]
    
    with engine.connect() as conn:
        # Create new tables first
        for table_sql in new_tables:
            try:
                conn.execute(text(table_sql))
                print(f"Created table if not exists")
            except Exception as e:
                print(f"Table creation note: {e}")
        
        # Add columns to existing tables
        for table, column, sql in migrations:
            try:
                # Check if column already exists
                result = conn.execute(text(f"PRAGMA table_info({table})"))
                columns = [row[1] for row in result.fetchall()]
                
                if column not in columns:
                    conn.execute(text(sql))
                    print(f"Added column {column} to {table}")
                else:
                    print(f"Column {column} already exists in {table}")
            except Exception as e:
                print(f"Error adding {column} to {table}: {e}")
        
        conn.commit()
    
    print("\nMigration complete!")

if __name__ == "__main__":
    migrate()

import os
import sys
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend_core.app.db import SessionLocal, create_db_and_tables
from backend_core.app import models

parser = argparse.ArgumentParser(description='Change a user\'s role')
parser.add_argument('--username', default='admin', help='Username to modify')
parser.add_argument('--role', default='Software Supervisor', help='New role to assign')
args = parser.parse_args()

create_db_and_tables()
db = SessionLocal()
try:
    user = db.query(models.User).filter(models.User.username == args.username).first()
    if not user:
        print(f"User not found: {args.username}")
        sys.exit(2)
    old = getattr(user, 'role', None)
    user.role = args.role
    db.add(user)
    db.commit()
    print(f"Updated user '{args.username}' role: '{old}' -> '{args.role}'")
finally:
    db.close()

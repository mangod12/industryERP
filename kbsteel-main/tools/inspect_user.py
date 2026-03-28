import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend_core.app.db import SessionLocal
from backend_core.app import models

db = SessionLocal()
user = db.query(models.User).filter(models.User.username == 'admin').first()
if not user:
    print('No admin user found')
else:
    print('username:', user.username)
    print('role:', getattr(user, 'role', None))
    pwd = getattr(user, 'password_hash', None)
    print('password_hash type:', type(pwd))
    print('password_hash len:', len(pwd) if pwd else None)
    print('first 200 chars of hash:\n', (pwd[:200] if pwd else ''))
    print('full repr:\n', repr(pwd)[:400])

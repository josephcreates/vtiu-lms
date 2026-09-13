import sys
sys.path.insert(0, '.')
from app import app, db
from models import Admin

with app.app_context():
    admins = Admin.query.all()
    print(f'Total admins: {len(admins)}')
    for admin in admins[:5]:
        print(f'  - {admin.username}: role={admin.role}, is_finance_admin={admin.is_finance_admin}, is_superadmin={admin.is_superadmin}')

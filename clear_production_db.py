"""
Clear Production Database (PostgreSQL)
This script will clear all data while preserving table structure
"""

import os
import sys
from sqlalchemy import text

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db

def clear_production_database():
    """Clear all data from production PostgreSQL database"""
    
    print("🌐 Clearing PRODUCTION database...")
    print("⚠️  WARNING: This will delete ALL production data!")
    
    confirm = input("Type 'PRODUCTION-RESET' to confirm: ")
    if confirm != 'PRODUCTION-RESET':
        print("❌ Reset cancelled.")
        return False
    
    with app.app_context():
        try:
            # Get all table names
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"📋 Found {len(tables)} tables")
            
            # Disable foreign key constraints temporarily
            db.session.execute(text("SET session_replication_role = replica;"))
            
            # Clear data from all tables
            for table in tables:
                if table != 'alembic_version':  # Keep migration history
                    try:
                        db.session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                        print(f"✅ Cleared table: {table}")
                    except Exception as e:
                        print(f"⚠️  Could not clear {table}: {e}")
            
            # Re-enable foreign key constraints
            db.session.execute(text("SET session_replication_role = DEFAULT;"))
            
            db.session.commit()
            print("🎉 Production database cleared!")
            
            # Create SuperAdmin account
            from models import Admin
            superadmin = Admin(
                admin_id='SUP001',
                username='superadmin',
                email='superadmin@vtiu.edu.gh',
                first_name='System',
                last_name='Administrator',
                role='superadmin'
            )
            superadmin.set_password('admin123')
            db.session.add(superadmin)
            db.session.commit()
            
            print("👤 Created SuperAdmin account in production")
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()
            return False

if __name__ == "__main__":
    clear_production_database()

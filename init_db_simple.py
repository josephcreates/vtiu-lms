#!/usr/bin/env python3
"""
Simple database initialization for Railway
"""
import os
from flask import Flask
from flask_migrate import init, migrate, upgrade
from config import Config
from utils.extensions import db

def init_database():
    """Initialize database with all tables"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    with app.app_context():
        # Import all models to ensure they're registered
        from models import User, Admin, StudentProfile, StudentFeeTransaction, StudentFeeBalance
        
        # Create all tables
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")

if __name__ == "__main__":
    try:
        init_database()
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

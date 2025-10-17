"""
Reset Database Script
---------------------
Drops all tables and recreates them (CLEARS ALL DATA!)

Usage:
    python reset_db.py
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.database.database import drop_db, init_db

def confirm_reset():
    """Ask for confirmation before resetting database"""
    print("⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("\nThis includes:")
    print("  - All companies")
    print("  - All analyses")
    print("  - All pain points")
    print("  - All product matches")
    print("  - All pitches")
    print("  - All analysis jobs")
    print("  - All system metrics")
    
    response = input("\n❓ Are you sure you want to continue? (yes/no): ")
    return response.lower() in ['yes', 'y']

if __name__ == "__main__":
    print("🗑️  Database Reset Utility")
    print("=" * 50)
    
    if not confirm_reset():
        print("\n❌ Reset cancelled. Database unchanged.")
        sys.exit(0)
    
    try:
        print("\n🔄 Dropping all tables...")
        drop_db()
        print("✅ All tables dropped")
        
        print("\n🔧 Creating fresh tables...")
        init_db()
        print("✅ Database reset complete!")
        
        print("\n🎉 Database is now empty and ready for fresh data!")
        print("\nNext steps:")
        print("1. Start the API: start_all.bat")
        print("2. Add companies via the UI")
        print("3. Run analyses")
        
    except Exception as e:
        print(f"\n❌ Error resetting database: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure PostgreSQL is running: docker-compose ps postgres")
        print("2. Check DATABASE_URL in .env file")
        print("3. Stop API server if running (it may lock the database)")
        sys.exit(1)

"""
Database migration: Add continuous mode to scheduler config.

Run this script to add the new continuous_mode fields to existing databases.
"""
from sqlalchemy import text
from src.database.database import get_db

def migrate():
    print("🔄 Adding continuous mode fields to scheduler_config...")
    
    try:
        with get_db() as db:
            # Check if columns already exist
            result = db.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='scheduler_config' AND column_name='continuous_mode'
            """))
            
            if result.fetchone():
                print("✅ Columns already exist, skipping migration")
                return
            
            # Add new columns
            db.execute(text("""
                ALTER TABLE scheduler_config 
                ADD COLUMN continuous_mode BOOLEAN DEFAULT FALSE NOT NULL
            """))
            
            db.execute(text("""
                ALTER TABLE scheduler_config 
                ADD COLUMN continuous_delay_minutes INTEGER DEFAULT 5
            """))
            
            db.commit()
            print("✅ Migration completed successfully!")
            print("")
            print("New fields added:")
            print("  - continuous_mode: Run jobs continuously (one after another)")
            print("  - continuous_delay_minutes: Delay between runs in continuous mode")
            print("")
            print("To enable continuous mode, update your scheduler config:")
            print("  PUT /scheduler/config")
            print('  { "continuous_mode": true, "continuous_delay_minutes": 5 }')
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("")
        print("This is normal if:")
        print("  1. The columns already exist")
        print("  2. You're using a fresh database (init_db.py handles this)")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    migrate()

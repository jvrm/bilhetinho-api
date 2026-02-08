"""
Password Migration Script
Migrates existing SHA256 password hashes to bcrypt

This script should be run ONCE after upgrading to bcrypt.
It will re-hash all admin passwords using the original passwords from seed data.

WARNING: This script assumes you know the original passwords.
For production, you may need to force password resets instead.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.admin_user import AdminUser
from database.connection import DATABASE_URL

# Known passwords from seed data
KNOWN_PASSWORDS = {
    "bar_central": "senha123",
    "noite_bilhetinho": "senha123",
    "casa_tropical": "senha123"
}

def migrate_passwords():
    """Migrate all admin passwords from SHA256 to bcrypt"""
    
    # Create database connection
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Get all admin users
        admin_users = db.query(AdminUser).all()
        
        print(f"Found {len(admin_users)} admin users to migrate")
        
        migrated = 0
        for admin in admin_users:
            if admin.username in KNOWN_PASSWORDS:
                # Re-hash password with bcrypt
                new_hash = AdminUser.hash_password(KNOWN_PASSWORDS[admin.username])
                admin.password_hash = new_hash
                migrated += 1
                print(f"✅ Migrated: {admin.username}")
            else:
                print(f"⚠️  Skipped: {admin.username} (password unknown)")
        
        # Commit changes
        db.commit()
        print(f"\n✅ Migration complete! Migrated {migrated}/{len(admin_users)} users")
        print("\n⚠️  Users not migrated will need to reset their passwords")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("PASSWORD MIGRATION: SHA256 → bcrypt")
    print("=" * 60)
    print("\nThis will re-hash all admin passwords using bcrypt.")
    print("Only users with known passwords will be migrated.")
    print()
    
    response = input("Continue? (yes/no): ")
    if response.lower() == "yes":
        migrate_passwords()
    else:
        print("Migration cancelled")

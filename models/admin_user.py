from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid
import bcrypt
from database.connection import Base


class AdminUser(Base):
    """
    AdminUser model - represents an admin user for an establishment
    Each establishment can have multiple admin users
    Password hashing uses bcrypt with automatic salt generation
    """
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    establishment_id = Column(String, ForeignKey("establishments.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt with automatic salt generation
        bcrypt is designed for password hashing and includes:
        - Automatic salt generation
        - Key stretching (slow by design)
        - Protection against rainbow tables
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str) -> bool:
        """
        Verify password against stored bcrypt hash
        Returns True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                self.password_hash.encode('utf-8')
            )
        except Exception:
            return False

    def __repr__(self):
        return f"<AdminUser(username={self.username}, establishment_id={self.establishment_id})>"

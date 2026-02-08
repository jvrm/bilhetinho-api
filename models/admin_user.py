from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime
import uuid
import hashlib
from database.connection import Base


class AdminUser(Base):
    """
    AdminUser model - represents an admin user for an establishment
    Each establishment can have multiple admin users
    """
    __tablename__ = "admin_users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    establishment_id = Column(String, ForeignKey("establishments.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Verify password against stored hash"""
        return self.password_hash == self.hash_password(password)

    def __repr__(self):
        return f"<AdminUser(username={self.username}, establishment_id={self.establishment_id})>"

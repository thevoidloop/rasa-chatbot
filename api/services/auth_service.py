"""
Authentication service
"""
from datetime import datetime
from sqlalchemy.orm import Session
from api.schemas.db_models import PlatformUser, ActivityLog
from api.models.auth import UserCreate, User
from api.utils.security import get_password_hash, verify_password, create_access_token
from typing import Optional


def get_user_by_username(db: Session, username: str) -> Optional[PlatformUser]:
    """Get user by username"""
    return db.query(PlatformUser).filter(PlatformUser.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[PlatformUser]:
    """Get user by email"""
    return db.query(PlatformUser).filter(PlatformUser.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[PlatformUser]:
    """Get user by ID"""
    return db.query(PlatformUser).filter(PlatformUser.id == user_id).first()


def create_user(db: Session, user: UserCreate, created_by: Optional[int] = None) -> PlatformUser:
    """Create a new user"""
    hashed_password = get_password_hash(user.password)
    
    db_user = PlatformUser(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        role=user.role,
        full_name=user.full_name,
        created_by=created_by
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=db_user.id,
        username=db_user.username,
        action="user_created",
        entity_type="user",
        entity_id=db_user.id,
        details={"role": db_user.role}
    )
    
    return db_user


def authenticate_user(db: Session, username: str, password: str) -> Optional[PlatformUser]:
    """Authenticate a user"""
    user = get_user_by_username(db, username)
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not verify_password(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # Log activity
    log_activity(
        db=db,
        user_id=user.id,
        username=user.username,
        action="login",
        entity_type="auth",
        entity_id=user.id
    )
    
    return user


def create_user_token(user: PlatformUser) -> str:
    """Create access token for user"""
    token_data = {
        "sub": user.username,
        "user_id": user.id,
        "role": user.role
    }
    
    return create_access_token(token_data)


def log_activity(
    db: Session,
    user_id: Optional[int],
    username: str,
    action: str,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None
):
    """Log user activity"""
    activity = ActivityLog(
        user_id=user_id,
        username=username,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        error_message=error_message
    )
    
    db.add(activity)
    db.commit()

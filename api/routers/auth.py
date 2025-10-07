"""
Authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.database.connection import get_db
from api.models.auth import UserLogin, Token, User, UserCreate
from api.services.auth_service import authenticate_user, create_user_token, create_user, get_user_by_username
from api.dependencies import get_current_user, require_role
from api.schemas.db_models import PlatformUser

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Login endpoint
    
    Authenticate user and return JWT token
    """
    # Authenticate user
    user = authenticate_user(db, user_credentials.username, user_credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create token
    access_token = create_user_token(user)
    
    # Convert SQLAlchemy model to Pydantic
    user_data = User.from_orm(user)
    
    return Token(access_token=access_token, user=user_data)


@router.post("/register", response_model=User, dependencies=[Depends(require_role("admin"))])
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Register new user
    
    Only accessible by admin users
    """
    # Check if username already exists
    existing_user = get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create user
    new_user = create_user(db, user_data, created_by=current_user.id)
    
    return User.from_orm(new_user)


@router.get("/me", response_model=User)
def get_current_user_info(current_user: PlatformUser = Depends(get_current_user)):
    """
    Get current user information
    """
    return User.from_orm(current_user)


@router.post("/logout")
def logout(current_user: PlatformUser = Depends(get_current_user)):
    """
    Logout endpoint
    
    Note: With JWT, logout is handled client-side by removing the token.
    This endpoint is for logging purposes.
    """
    return {"message": "Successfully logged out"}

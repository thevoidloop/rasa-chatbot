"""
Session management utilities
"""
import streamlit as st
from typing import Optional, Dict, Any
from utils.api_client import APIClient


def init_session():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    if "token" not in st.session_state:
        st.session_state.token = None

    if "api_client" not in st.session_state:
        st.session_state.api_client = APIClient()


def login(username: str, password: str) -> tuple[bool, str]:
    """
    Login user and store session

    Args:
        username: Username
        password: Password

    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        api_client = APIClient()
        response = api_client.login(username, password)

        # Store in session
        st.session_state.authenticated = True
        st.session_state.user = response["user"]
        st.session_state.token = response["access_token"]
        st.session_state.api_client = api_client

        return True, f"¡Bienvenido, {response['user']['full_name']}!"

    except Exception as e:
        return False, f"Error de autenticación: {str(e)}"


def logout():
    """Logout user and clear session"""
    if st.session_state.get("api_client"):
        st.session_state.api_client.logout()

    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.token = None
    st.session_state.api_client = APIClient()


def require_auth():
    """
    Require authentication for a page.
    Redirect to login if not authenticated.
    """
    init_session()

    if not st.session_state.authenticated:
        st.warning("⚠️ Debes iniciar sesión para acceder a esta página")
        st.stop()


def get_current_user() -> Optional[Dict[str, Any]]:
    """Get current logged in user"""
    init_session()
    return st.session_state.user


def is_authenticated() -> bool:
    """Check if user is authenticated"""
    init_session()
    return st.session_state.authenticated

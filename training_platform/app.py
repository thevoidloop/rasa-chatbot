"""
Training Platform - Streamlit Frontend
Main Application Entry Point
"""
import streamlit as st
import os
import sys
from pathlib import Path

# Add utils to path
sys.path.append(str(Path(__file__).parent))

from utils.session import init_session, is_authenticated, get_current_user, logout
from utils.api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="RASA Training Platform",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session
init_session()

# Sidebar - Authentication status
with st.sidebar:
    st.markdown("### Estado de Sesión")

    if is_authenticated():
        user = get_current_user()
        st.success(f"✅ Conectado como:")
        st.markdown(f"**{user['full_name']}**")
        st.caption(f"Rol: {user['role']}")

        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()
            st.success("Sesión cerrada exitosamente")
            st.rerun()
    else:
        st.warning("⚠️ No autenticado")
        st.info("👉 Ve a la página de **Login** para iniciar sesión")

    st.markdown("---")

# Title
st.title("🤖 RASA Training Platform")
st.markdown("---")

# Welcome message
st.markdown("""
## Bienvenido a la Plataforma de Entrenamiento

Esta plataforma permite gestionar y mejorar el chatbot RASA de forma visual e intuitiva.

### Características:
- 📊 **Dashboard**: Visualiza métricas del chatbot en tiempo real
- 💬 **Conversaciones**: Revisa conversaciones de usuarios
- ✏️ **Anotaciones**: Corrige intents y entities fácilmente
- 📝 **Datos de Entrenamiento**: Gestiona ejemplos NLU y responses
- 🎓 **Entrenamiento**: Re-entrena el modelo con un click
- 🧪 **Testing**: Prueba el modelo antes de desplegar
- 📈 **Reportes**: Genera reportes automáticos

### Estado del Sistema:
""")

# API connection status
api_url = os.getenv("API_URL", "http://api-server:8000")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("API Backend", "Conectando...", "8000")

with col2:
    st.metric("RASA Server", "Conectando...", "5005")

with col3:
    st.metric("Base de Datos", "Conectando...", "PostgreSQL")

st.markdown("---")
st.info("👈 Usa el menú lateral para navegar entre las diferentes secciones")

# Footer
st.markdown("---")
st.caption("RASA Training Platform v1.0.0 | Powered by Streamlit + FastAPI")

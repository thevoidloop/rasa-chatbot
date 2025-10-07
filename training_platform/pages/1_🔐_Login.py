"""
Login Page
"""
import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.session import init_session, login, is_authenticated

# Page configuration
st.set_page_config(
    page_title="Login - RASA Training Platform",
    page_icon="🔐",
    layout="centered"
)

# Initialize session
init_session()

# Redirect if already authenticated
if is_authenticated():
    st.success(f"✅ Ya has iniciado sesión como {st.session_state.user['username']}")
    st.info("👈 Usa el menú lateral para navegar a otras páginas")
    st.stop()

# Title
st.title("🔐 Iniciar Sesión")
st.markdown("---")

# Login form
with st.form("login_form"):
    st.markdown("### Credenciales de Acceso")

    username = st.text_input(
        "Usuario",
        placeholder="admin",
        help="Ingresa tu nombre de usuario"
    )

    password = st.text_input(
        "Contraseña",
        type="password",
        placeholder="********",
        help="Ingresa tu contraseña"
    )

    submitted = st.form_submit_button("Iniciar Sesión", use_container_width=True)

    if submitted:
        if not username or not password:
            st.error("❌ Por favor completa todos los campos")
        else:
            with st.spinner("Autenticando..."):
                success, message = login(username, password)

                if success:
                    st.success(message)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(message)

# Footer
st.markdown("---")
st.markdown("""
### Credenciales por defecto:
- **Usuario:** admin
- **Contraseña:** Admin123!

⚠️ **Importante:** Cambia la contraseña después del primer inicio de sesión.
""")

st.caption("RASA Training Platform v1.0.0")

"""
Conversaciones - Conversation History Viewer
"""
import streamlit as st
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime, timedelta
import json
import pytz

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.session import require_auth, get_current_user
from utils.api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="Conversaciones - RASA Training Platform",
    page_icon="💬",
    layout="wide"
)

# Require authentication
require_auth()

# Get current user and API client
user = get_current_user()
api_client = st.session_state.api_client

# Guatemala timezone
GUATEMALA_TZ = pytz.timezone('America/Guatemala')

# Initialize session state
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# Title
st.title("💬 Historial de Conversaciones")
st.markdown("Visualiza, filtra y analiza todas las conversaciones del chatbot")
st.markdown("---")

# === LOAD AVAILABLE INTENTS ===
try:
    available_intents = api_client._make_request("GET", "/api/v1/conversations/intents")
except Exception as e:
    st.error(f"❌ Error al cargar intents: {str(e)}")
    available_intents = []

# === FILTROS EN SIDEBAR ===
with st.sidebar:
    st.markdown("### 🔍 Filtros")

    # Date range filter
    st.markdown("#### Rango de Fechas")
    date_preset = st.selectbox(
        "Preselección",
        options=["hoy", "7_dias", "30_dias", "90_dias", "personalizado"],
        format_func=lambda x: {
            "hoy": "Hoy",
            "7_dias": "Últimos 7 días",
            "30_dias": "Últimos 30 días",
            "90_dias": "Últimos 90 días",
            "personalizado": "Personalizado"
        }[x],
        index=1  # Default: 7 días
    )

    # Calculate date range based on preset
    now_guatemala = datetime.now(GUATEMALA_TZ)

    if date_preset == "personalizado":
        col_date1, col_date2 = st.columns(2)
        with col_date1:
            date_from = st.date_input(
                "Desde",
                value=now_guatemala.date() - timedelta(days=7),
                max_value=now_guatemala.date()
            )
        with col_date2:
            date_to = st.date_input(
                "Hasta",
                value=now_guatemala.date(),
                max_value=now_guatemala.date()
            )
    else:
        days_map = {
            "hoy": 0,
            "7_dias": 7,
            "30_dias": 30,
            "90_dias": 90
        }
        days = days_map[date_preset]
        date_from = (now_guatemala - timedelta(days=days)).date()
        date_to = now_guatemala.date()

        st.caption(f"📅 {date_from.strftime('%Y-%m-%d')} hasta {date_to.strftime('%Y-%m-%d')}")

    # Intent filter
    st.markdown("#### Intent")
    intent_filter = st.multiselect(
        "Filtrar por intent",
        options=available_intents,
        default=None,
        help="Deja vacío para ver todos los intents"
    )

    # Confidence filter
    st.markdown("#### Confianza")
    confidence_min = st.slider(
        "Confianza mínima (%)",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
        help="Filtra conversaciones con confianza mayor o igual al valor seleccionado"
    )

    # User search
    st.markdown("#### Usuario")
    user_search = st.text_input(
        "Buscar por sender_id",
        placeholder="Ej: 50123456789",
        help="Buscar conversaciones de un usuario específico"
    )

    # Text search
    st.markdown("#### Búsqueda en Mensajes")
    text_search = st.text_input(
        "Buscar texto",
        placeholder="Buscar en mensajes...",
        help="Busca texto en los mensajes del usuario"
    )

    # Pagination
    st.markdown("---")
    st.markdown("#### Paginación")
    items_per_page = st.selectbox(
        "Items por página",
        options=[25, 50, 100, 200],
        index=1  # Default: 50
    )

    st.markdown("---")

    # Action buttons
    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()

    if st.button("🗑️ Limpiar Filtros", use_container_width=True):
        st.session_state.current_page = 1
        st.rerun()

# === FETCH CONVERSATIONS DATA ===
try:
    with st.spinner("Cargando conversaciones..."):
        # Build query parameters
        params = {
            "date_from": date_from.isoformat(),
            "date_to": date_to.isoformat(),
            "confidence_min": confidence_min / 100,  # Convert to 0-1 range
            "page": st.session_state.current_page,
            "limit": items_per_page
        }

        if intent_filter:
            params["intents"] = ",".join(intent_filter)

        if user_search:
            params["sender_id"] = user_search

        if text_search:
            params["search"] = text_search

        # Fetch conversations from API
        conversations_data = api_client._make_request("GET", "/api/v1/conversations", params=params)

except Exception as e:
    st.error(f"❌ Error al cargar conversaciones: {str(e)}")
    st.info("💡 Asegúrate de que el servidor API esté corriendo correctamente.")
    st.stop()

# === STATISTICS SUMMARY ===
if conversations_data.get("total", 0) > 0:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Total Conversaciones",
            value=conversations_data["total"],
            help="Total de conversaciones encontradas con los filtros aplicados"
        )

    with col2:
        st.metric(
            label="Página Actual",
            value=f"{conversations_data['page']} / {conversations_data['pages']}",
            help="Página actual de resultados"
        )

    with col3:
        # Calculate average confidence from current page
        items = conversations_data.get("items", [])
        if items:
            avg_conf = sum(item.get("avg_confidence", 0) for item in items) / len(items)
            st.metric(
                label="Confianza Promedio",
                value=f"{avg_conf:.1f}%",
                help="Confianza promedio en esta página"
            )
        else:
            st.metric(label="Confianza Promedio", value="N/A")

    with col4:
        # Count unique senders in current page
        unique_senders = len(set(item.get("sender_id") for item in items))
        st.metric(
            label="Usuarios Únicos",
            value=unique_senders,
            help="Usuarios únicos en los resultados actuales"
        )

    st.markdown("---")

# === CONVERSATIONS TABLE ===
st.markdown("### 📋 Resultados")

if conversations_data.get("total", 0) > 0:
    # Create DataFrame
    items = conversations_data["items"]
    df_conversations = pd.DataFrame(items)

    # Format columns
    if not df_conversations.empty:
        # Rename columns for display
        df_display = df_conversations.rename(columns={
            "sender_id": "Usuario",
            "created_at": "Fecha",
            "message_count": "Mensajes",
            "primary_intent": "Intent Principal",
            "avg_confidence": "Confianza (%)",
            "last_message": "Último Mensaje",
            "active": "Activo"
        })

        # Show interactive table
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Usuario": st.column_config.TextColumn(width="medium"),
                "Fecha": st.column_config.TextColumn(width="medium"),
                "Mensajes": st.column_config.NumberColumn(format="%d"),
                "Intent Principal": st.column_config.TextColumn(width="medium"),
                "Confianza (%)": st.column_config.ProgressColumn(
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                ),
                "Último Mensaje": st.column_config.TextColumn(width="large"),
                "Activo": st.column_config.CheckboxColumn()
            }
        )

        # Pagination controls
        st.markdown("---")
        col_prev, col_info, col_next = st.columns([1, 2, 1])

        with col_prev:
            if conversations_data["page"] > 1:
                if st.button("⬅️ Anterior", use_container_width=True):
                    st.session_state.current_page = conversations_data["page"] - 1
                    st.rerun()

        with col_info:
            st.markdown(
                f"<center>Página {conversations_data['page']} de {conversations_data['pages']}</center>",
                unsafe_allow_html=True
            )

        with col_next:
            if conversations_data["page"] < conversations_data["pages"]:
                if st.button("Siguiente ➡️", use_container_width=True):
                    st.session_state.current_page = conversations_data["page"] + 1
                    st.rerun()

        # === CONVERSATION DETAIL MODAL ===
        st.markdown("---")
        st.markdown("### 🔍 Detalle de Conversación")

        selected_sender = st.selectbox(
            "Selecciona una conversación para ver detalles",
            options=[""] + df_conversations["sender_id"].tolist(),
            format_func=lambda x: "-- Selecciona un usuario --" if x == "" else x
        )

        if selected_sender:
            with st.spinner("Cargando detalles..."):
                try:
                    # Fetch detailed conversation from API
                    conversation_detail = api_client._make_request(
                        "GET",
                        f"/api/v1/conversations/{selected_sender}"
                    )

                    # Display conversation header
                    col_h1, col_h2, col_h3 = st.columns(3)
                    with col_h1:
                        st.info(f"**Usuario:** {conversation_detail['sender_id']}")
                    with col_h2:
                        st.info(f"**Mensajes:** {conversation_detail['total_messages']}")
                    with col_h3:
                        st.info(f"**Confidence:** {conversation_detail['avg_confidence']}%")

                    # Display unique intents
                    if conversation_detail.get("unique_intents"):
                        st.caption(f"🎯 **Intents detectados:** {', '.join(conversation_detail['unique_intents'])}")

                    st.markdown("---")

                    # Display messages chronologically
                    st.markdown("#### 💬 Historial de Mensajes")

                    messages = conversation_detail.get("messages", [])
                    for msg in messages:
                        if msg["type"] == "user":
                            # User message
                            col1, col2 = st.columns([1, 4])
                            with col1:
                                st.markdown("**👤 Usuario**")
                            with col2:
                                st.info(msg.get("text", ""))
                                intent = msg.get("intent", "N/A")
                                confidence = msg.get("confidence", 0)
                                entities = msg.get("entities", [])

                                caption_parts = [f"🎯 Intent: `{intent}`"]
                                if confidence:
                                    caption_parts.append(f"Confidence: {confidence*100:.1f}%")
                                if entities:
                                    entities_str = ", ".join([f"{e.get('entity')}={e.get('value')}" for e in entities[:3]])
                                    caption_parts.append(f"Entities: {entities_str}")

                                st.caption(" | ".join(caption_parts))

                        elif msg["type"] == "bot":
                            # Bot message
                            col3, col4 = st.columns([4, 1])
                            with col3:
                                st.success(msg.get("text", ""))
                                if msg.get("action"):
                                    st.caption(f"🤖 Acción: `{msg['action']}`")
                            with col4:
                                st.markdown("**🤖 Bot**")

                        st.markdown("")  # Spacing

                    # Action buttons
                    st.markdown("---")
                    col_act1, col_act2, col_act3 = st.columns(3)

                    with col_act1:
                        if st.button("🏷️ Marcar para Revisión", use_container_width=True):
                            try:
                                result = api_client._make_request(
                                    "POST",
                                    f"/api/v1/conversations/{selected_sender}/flag",
                                    json={"reason": "Marcado desde UI", "priority": "normal"}
                                )
                                st.success("✅ Conversación marcada para revisión")
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")

                    with col_act2:
                        if st.button("✍️ Anotar", use_container_width=True):
                            st.info("🚧 Funcionalidad en desarrollo (FASE 2)")

                    with col_act3:
                        if st.button("🔗 Ver en RASA", use_container_width=True):
                            st.info("🚧 Funcionalidad en desarrollo")

                except Exception as e:
                    st.error(f"❌ Error al cargar detalle: {str(e)}")

        # === EXPORT FUNCTIONALITY ===
        st.markdown("---")
        st.markdown("### 📥 Exportar Datos")

        col_export1, col_export2 = st.columns(2)

        with col_export1:
            if st.button("📄 Exportar a CSV", use_container_width=True):
                try:
                    # Build export params with filters
                    export_params = {
                        "date_from": date_from.isoformat(),
                        "date_to": date_to.isoformat()
                    }
                    if intent_filter:
                        export_params["intents"] = ",".join(intent_filter)

                    # Make authenticated request to download CSV
                    with st.spinner("Generando archivo CSV..."):
                        csv_data = api_client._make_request(
                            "GET",
                            "/api/v1/conversations/export/csv",
                            params=export_params,
                            return_response=True  # Get raw response
                        )

                        # Provide download button
                        filename = f"conversations_{date_from.isoformat()}_{date_to.isoformat()}.csv"
                        st.download_button(
                            label="⬇️ Descargar CSV",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv",
                            use_container_width=True
                        )
                        st.success("✅ Archivo CSV generado correctamente")

                except Exception as e:
                    st.error(f"❌ Error al generar exportación: {str(e)}")

        with col_export2:
            if st.button("📊 Exportar a Excel", use_container_width=True):
                st.info("🚧 Exportación a Excel en desarrollo")
                st.caption("Por ahora, puedes usar CSV y convertirlo en Excel")

else:
    # No results found
    st.info("🔍 No se encontraron conversaciones con los filtros aplicados.")
    st.markdown("""
    **Sugerencias:**
    - Amplía el rango de fechas
    - Reduce el filtro de confianza mínima
    - Verifica que los filtros de intent y usuario sean correctos
    - Limpia los filtros y vuelve a intentar
    """)

# Footer
st.markdown("---")
st.caption(
    f"Última actualización: {datetime.now(GUATEMALA_TZ).strftime('%Y-%m-%d %H:%M:%S')} | "
    f"Usuario: {user['username']} ({user['role']})"
)

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
                        if st.button("✍️ Anotar", use_container_width=True, type="primary"):
                            # Store conversation data in session state for annotation modal
                            st.session_state.annotate_conversation = {
                                "sender_id": selected_sender,
                                "messages": messages
                            }
                            st.session_state.show_annotation_modal = True
                            st.rerun()

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

# === ANNOTATION MODAL ===
if st.session_state.get("show_annotation_modal"):
    conversation_data = st.session_state.get("annotate_conversation", {})
    messages = conversation_data.get("messages", [])

    st.markdown("---")
    st.subheader("✍️ Crear Anotación")
    st.markdown(f"**Conversación:** `{conversation_data.get('sender_id')}`")

    # Let user select which message to annotate
    user_messages = [msg for msg in messages if msg["type"] == "user"]

    if user_messages:
        selected_message_idx = st.selectbox(
            "Selecciona el mensaje a anotar",
            options=range(len(user_messages)),
            format_func=lambda i: f"Mensaje {i+1}: {user_messages[i].get('text', '')[:60]}..."
        )

        selected_message = user_messages[selected_message_idx]

        # Pre-fill annotation form
        with st.form("quick_annotation_form"):
            st.markdown("**Mensaje seleccionado:**")
            st.info(selected_message.get("text", ""))

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Detección Original:**")
                st.code(f"Intent: {selected_message.get('intent', 'N/A')}\nConfianza: {selected_message.get('confidence', 0)*100:.1f}%")

                # Get available intents
                try:
                    intents_response = api_client._make_request("GET", "/api/v1/export/intents")
                    # API returns {"intents": [...], "total": X}, extract the list
                    if isinstance(intents_response, dict) and "intents" in intents_response:
                        available_intents = intents_response["intents"]
                    elif isinstance(intents_response, list):
                        available_intents = intents_response
                    else:
                        available_intents = []
                except Exception as e:
                    st.warning(f"⚠️ No se pudieron cargar intents: {str(e)}")
                    available_intents = []

            with col2:
                st.markdown("**Corrección:**")
                corrected_intent = st.selectbox(
                    "Intent Corregido *",
                    options=available_intents,
                    index=available_intents.index(selected_message.get("intent", ""))
                        if selected_message.get("intent") in available_intents else 0
                )

            # Annotation type
            annotation_type = st.radio(
                "Tipo de corrección",
                options=["intent", "both"],
                format_func=lambda x: "Solo Intent" if x == "intent" else "Intent + Entities",
                horizontal=True
            )

            # Entities (if both)
            entities_json = "[]"
            if annotation_type == "both":
                entities_json = st.text_area(
                    "Entities Corregidas (JSON)",
                    value=json.dumps(selected_message.get("entities", []), indent=2),
                    height=120,
                    help='Formato: [{"entity": "producto", "value": "blusa", "start": 0, "end": 5}]'
                )

            # Notes
            notes = st.text_area(
                "Notas (opcional)",
                placeholder="Explica por qué se necesita esta corrección...",
                height=80
            )

            # Buttons
            col_btn1, col_btn2, col_btn3 = st.columns(3)

            with col_btn1:
                submitted = st.form_submit_button("💾 Guardar Anotación", type="primary", use_container_width=True)

            with col_btn2:
                if st.form_submit_button("🔗 Ir a Anotaciones", use_container_width=True):
                    st.session_state.show_annotation_modal = False
                    st.session_state.go_to_annotations = True
                    st.rerun()

            with col_btn3:
                cancelled = st.form_submit_button("❌ Cancelar", use_container_width=True)

            if cancelled:
                st.session_state.show_annotation_modal = False
                st.rerun()

            if submitted:
                # Validate that we have data to send
                if not corrected_intent:
                    st.error("❌ Debes seleccionar un intent corregido")
                    st.stop()

                # Parse entities
                try:
                    corrected_entities = json.loads(entities_json) if annotation_type == "both" else []
                except Exception as e:
                    st.error(f"Error al parsear entities: {str(e)}")
                    st.stop()

                # Build annotation payload
                annotation_data = {
                    "conversation_id": conversation_data.get("sender_id"),
                    "message_text": selected_message.get("text", ""),
                    "original_intent": selected_message.get("intent"),
                    "corrected_intent": corrected_intent,  # Always include this
                    "original_confidence": selected_message.get("confidence", 0),
                    "annotation_type": annotation_type,
                }

                # Add optional fields
                if selected_message.get("entities"):
                    annotation_data["original_entities"] = selected_message.get("entities", [])

                # Only add corrected_entities if annotation type is "both" and we have entities
                if annotation_type == "both" and corrected_entities:
                    annotation_data["corrected_entities"] = corrected_entities

                if notes:
                    annotation_data["notes"] = notes

                # Create annotation via API
                try:
                    with st.spinner("Creando anotación..."):
                        response = api_client._make_request(
                            "POST",
                            "/api/v1/annotations",
                            json=annotation_data
                        )
                        if response:
                            st.success(f"✅ Anotación creada exitosamente (ID: {response.get('id')})")
                            st.session_state.annotation_created = True
                            st.session_state.annotation_id = response.get('id')
                            st.session_state.show_annotation_modal = False
                            st.rerun()  # Rerun to exit form and show balloons
                except Exception as e:
                    st.error(f"❌ Error al crear anotación: {str(e)}")
    else:
        st.warning("No hay mensajes del usuario en esta conversación para anotar.")
        if st.button("❌ Cerrar"):
            st.session_state.show_annotation_modal = False
            st.rerun()

# === HANDLE NAVIGATION TO ANNOTATIONS ===
if st.session_state.get("go_to_annotations"):
    st.session_state.go_to_annotations = False
    st.switch_page("pages/4_✏️_Anotaciones.py")

# === SHOW SUCCESS MESSAGE AFTER ANNOTATION CREATED ===
if st.session_state.get("annotation_created"):
    st.balloons()
    st.success(f"✅ Anotación creada exitosamente (ID: {st.session_state.get('annotation_id')})")

    col_success1, col_success2 = st.columns(2)
    with col_success1:
        if st.button("📋 Ver todas las anotaciones", type="primary", use_container_width=True):
            st.session_state.annotation_created = False  # Clear flag
            st.switch_page("pages/4_✏️_Anotaciones.py")
    with col_success2:
        if st.button("✅ Continuar", use_container_width=True):
            st.session_state.annotation_created = False  # Clear flag
            st.rerun()

# Footer
st.markdown("---")
st.caption(
    f"Última actualización: {datetime.now(GUATEMALA_TZ).strftime('%Y-%m-%d %H:%M:%S')} | "
    f"Usuario: {user['username']} ({user['role']})"
)

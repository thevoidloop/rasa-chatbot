"""
Página de Gestión de Anotaciones.

Funcionalidades:
- Listar anotaciones con filtros avanzados
- Crear nueva anotación
- Editar anotaciones pendientes/rechazadas
- Aprobar/rechazar anotaciones (qa_lead+)
- Ver detalles con comparación lado a lado
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import sys
import os

# Añadir path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth, get_current_user
from utils.annotation_helpers import (
    format_entities_display,
    highlight_entities,
    validate_entity_spans,
    get_intent_suggestions,
    get_entity_types,
    format_annotation_status,
    format_annotation_type,
    calculate_entity_positions,
)


# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================

st.set_page_config(
    page_title="Anotaciones - Training Platform",
    page_icon="✏️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Requerir autenticación
require_auth()

# Obtener usuario actual
user = get_current_user()
api_client = st.session_state.api_client


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def load_annotation_stats() -> Optional[Dict]:
    """Carga estadísticas de anotaciones desde el API."""
    try:
        with st.spinner("Cargando estadísticas..."):
            response = api_client._make_request("GET", "/api/v1/annotations/stats")
            return response
    except Exception as e:
        st.error(f"Error al cargar estadísticas: {str(e)}")
        return None


def load_annotations(
    page: int = 1,
    page_size: int = 25,
    status: Optional[str] = None,
    intent: Optional[str] = None,
    conversation_id: Optional[str] = None,
    annotated_by: Optional[str] = None,
    approved_by: Optional[str] = None
) -> Optional[Dict]:
    """Carga anotaciones con filtros."""
    try:
        params = {"page": page, "page_size": page_size}

        if status:
            params["status"] = status
        if intent:
            params["intent"] = intent
        if conversation_id:
            params["conversation_id"] = conversation_id
        if annotated_by:
            params["annotated_by"] = annotated_by
        if approved_by:
            params["approved_by"] = approved_by

        with st.spinner("Cargando anotaciones..."):
            response = api_client._make_request(
                "GET",
                "/api/v1/annotations",
                params=params
            )
            return response
    except Exception as e:
        st.error(f"Error al cargar anotaciones: {str(e)}")
        return None


def create_annotation(data: Dict) -> bool:
    """Crea una nueva anotación."""
    try:
        with st.spinner("Creando anotación..."):
            response = api_client._make_request(
                "POST",
                "/api/v1/annotations",
                json=data
            )
            if response:
                st.success(f"✅ Anotación creada exitosamente (ID: {response.get('id')})")
                return True
    except Exception as e:
        st.error(f"❌ Error al crear anotación: {str(e)}")
    return False


def update_annotation(annotation_id: int, data: Dict) -> bool:
    """Actualiza una anotación existente."""
    try:
        with st.spinner("Actualizando anotación..."):
            response = api_client._make_request(
                "PUT",
                f"/api/v1/annotations/{annotation_id}",
                json=data
            )
            if response:
                st.success("✅ Anotación actualizada exitosamente")
                return True
    except Exception as e:
        st.error(f"❌ Error al actualizar anotación: {str(e)}")
    return False


def approve_annotation(annotation_id: int, approved: bool, rejection_reason: str = "") -> bool:
    """Aprueba o rechaza una anotación."""
    try:
        data = {"approved": approved}  # FIX: cambiar 'approve' a 'approved'
        if not approved and rejection_reason:
            data["rejection_reason"] = rejection_reason

        with st.spinner("Procesando..."):
            response = api_client._make_request(
                "POST",
                f"/api/v1/annotations/{annotation_id}/approve",
                json=data
            )
            if response:
                action = "aprobada" if approved else "rechazada"
                st.success(f"✅ Anotación {action} exitosamente")
                return True
    except Exception as e:
        st.error(f"❌ Error al procesar anotación: {str(e)}")
    return False


def delete_annotation(annotation_id: int) -> bool:
    """Elimina una anotación."""
    try:
        with st.spinner("Eliminando anotación..."):
            api_client._make_request(
                "DELETE",
                f"/api/v1/annotations/{annotation_id}"
            )
            st.success("✅ Anotación eliminada exitosamente")
            return True
    except Exception as e:
        st.error(f"❌ Error al eliminar anotación: {str(e)}")
    return False


def can_edit_annotation(annotation: Dict, user: Dict) -> bool:
    """Verifica si el usuario puede editar la anotación."""
    # Admin puede editar todo
    if user["role"] == "admin":
        return True

    # Solo se puede editar si está pending o rejected
    if annotation["status"] not in ["pending", "rejected"]:
        return False

    # El creador puede editar sus propias anotaciones
    return annotation["annotated_by_username"] == user["username"]


def can_approve_annotation(user: Dict) -> bool:
    """Verifica si el usuario puede aprobar anotaciones."""
    return user["role_level"] >= 4  # qa_lead (4) o admin (5)


# ============================================
# HEADER CON MÉTRICAS
# ============================================

st.title("✏️ Gestión de Anotaciones")
st.markdown("Crea, edita y gestiona las correcciones de intents y entities para mejorar el entrenamiento del bot.")

# Cargar estadísticas
stats = load_annotation_stats()

if stats:
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📊 Total Anotaciones",
            value=stats.get("total", 0)
        )

    with col2:
        st.metric(
            label="⏳ Pendientes",
            value=stats.get("pending", 0),
            delta="Requieren revisión" if stats.get("pending", 0) > 0 else None
        )

    with col3:
        st.metric(
            label="✅ Aprobadas",
            value=stats.get("approved", 0)
        )

    with col4:
        approval_rate = stats.get("approval_rate", 0)
        st.metric(
            label="📈 Tasa de Aprobación",
            value=f"{approval_rate:.1f}%",
            delta="Buena" if approval_rate >= 80 else "Mejorar"
        )

st.markdown("---")


# ============================================
# SIDEBAR CON FILTROS
# ============================================

st.sidebar.header("🔍 Filtros")

# Filtro por estado
status_options = {
    "Todos": None,
    "Pendiente": "pending",
    "Aprobada": "approved",
    "Rechazada": "rejected",
    "Entrenada": "trained",
    "Desplegada": "deployed"
}
selected_status_label = st.sidebar.selectbox(
    "Estado",
    options=list(status_options.keys()),
    index=0
)
selected_status = status_options[selected_status_label]

# Filtro por intent
intents = get_intent_suggestions(api_client)
selected_intent = st.sidebar.selectbox(
    "Intent",
    options=["Todos"] + intents,
    index=0
)
selected_intent = None if selected_intent == "Todos" else selected_intent

# Filtro por conversation_id
conversation_id_filter = st.sidebar.text_input(
    "Conversation ID",
    placeholder="Ej: user_12345"
)

# Filtro por creador
annotated_by_filter = st.sidebar.text_input(
    "Creado por (username)",
    placeholder="Ej: qa_analyst"
)

# Filtro por aprobador
approved_by_filter = st.sidebar.text_input(
    "Aprobado por (username)",
    placeholder="Ej: qa_lead"
)

# Paginación
page_size = st.sidebar.selectbox(
    "Items por página",
    options=[10, 25, 50, 100],
    index=1
)

# Botón de actualizar
if st.sidebar.button("🔄 Actualizar", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")

# Botón de crear nueva anotación
if st.sidebar.button("➕ Nueva Anotación", use_container_width=True, type="primary"):
    st.session_state.show_create_modal = True


# ============================================
# CARGAR DATOS
# ============================================

# Inicializar página en session_state
if "annotation_page" not in st.session_state:
    st.session_state.annotation_page = 1

# Cargar anotaciones
annotations_data = load_annotations(
    page=st.session_state.annotation_page,
    page_size=page_size,
    status=selected_status,
    intent=selected_intent,
    conversation_id=conversation_id_filter if conversation_id_filter else None,
    annotated_by=annotated_by_filter if annotated_by_filter else None,
    approved_by=approved_by_filter if approved_by_filter else None
)


# ============================================
# TABLA DE ANOTACIONES
# ============================================

if annotations_data and annotations_data.get("items"):
    annotations = annotations_data["items"]
    total = annotations_data.get("total", 0)
    total_pages = annotations_data.get("total_pages", 1)
    current_page = annotations_data.get("page", 1)

    st.subheader(f"📋 Anotaciones ({total} total)")

    # Mostrar cada anotación como un card
    for annotation in annotations:
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                # Header del card
                st.markdown(
                    f"**#{annotation['id']}** - Conversación: `{annotation['conversation_id']}`",
                    unsafe_allow_html=True
                )

                # Información principal
                col_info1, col_info2, col_info3 = st.columns(3)

                with col_info1:
                    st.markdown(
                        f"**Intent:** {annotation.get('original_intent', 'N/A')} → "
                        f"**{annotation.get('corrected_intent', 'N/A')}**"
                    )

                with col_info2:
                    st.markdown(
                        format_annotation_type(annotation.get("annotation_type", "unknown")),
                        unsafe_allow_html=True
                    )

                with col_info3:
                    st.markdown(
                        format_annotation_status(annotation.get("status", "unknown")),
                        unsafe_allow_html=True
                    )

                # Mensaje
                st.markdown(f"💬 *{annotation.get('message_text', '')[:100]}...*")

                # Metadata
                created_at = annotation.get("created_at", "")
                created_by = annotation.get("annotated_by_username", "Desconocido")
                st.caption(f"📅 {created_at} | 👤 {created_by}")

            with col2:
                # Botones de acción
                st.markdown("**Acciones:**")

                # Ver detalles
                if st.button("👁️ Ver", key=f"view_{annotation['id']}", use_container_width=True):
                    st.session_state.view_annotation_id = annotation["id"]
                    st.session_state.show_detail_modal = True

                # Editar (si tiene permisos)
                if can_edit_annotation(annotation, user):
                    if st.button("✏️ Editar", key=f"edit_{annotation['id']}", use_container_width=True):
                        st.session_state.edit_annotation_id = annotation["id"]
                        st.session_state.show_edit_modal = True

                # Aprobar/Rechazar (si tiene permisos y está pending)
                if can_approve_annotation(user) and annotation["status"] == "pending":
                    if st.button("✓ Revisar", key=f"approve_{annotation['id']}", use_container_width=True, type="primary"):
                        st.session_state.approve_annotation_id = annotation["id"]
                        st.session_state.show_approve_modal = True

                # Eliminar (si tiene permisos)
                if can_edit_annotation(annotation, user) and annotation["status"] == "pending":
                    if st.button("🗑️ Eliminar", key=f"delete_{annotation['id']}", use_container_width=True):
                        if delete_annotation(annotation["id"]):
                            st.rerun()

            st.markdown("---")

    # Paginación
    col_prev, col_info, col_next = st.columns([1, 2, 1])

    with col_prev:
        if current_page > 1:
            if st.button("⬅️ Anterior", use_container_width=True):
                st.session_state.annotation_page -= 1
                st.rerun()

    with col_info:
        st.markdown(f"<center>Página {current_page} de {total_pages}</center>", unsafe_allow_html=True)

    with col_next:
        if current_page < total_pages:
            if st.button("Siguiente ➡️", use_container_width=True):
                st.session_state.annotation_page += 1
                st.rerun()

else:
    st.info("📭 No se encontraron anotaciones con los filtros seleccionados.")
    st.markdown("Intenta ajustar los filtros o crea una nueva anotación.")


# ============================================
# MODAL: CREAR/EDITAR ANOTACIÓN
# ============================================

if st.session_state.get("show_create_modal") or st.session_state.get("show_edit_modal"):
    st.markdown("---")
    st.subheader("✏️ Crear/Editar Anotación")

    # Determinar si es edición
    is_edit = st.session_state.get("show_edit_modal", False)
    annotation_to_edit = None

    if is_edit:
        edit_id = st.session_state.get("edit_annotation_id")
        # Buscar la anotación en los datos cargados
        annotation_to_edit = next(
            (a for a in annotations if a["id"] == edit_id),
            None
        )

        if not annotation_to_edit:
            st.error("No se pudo cargar la anotación para editar")
            st.session_state.show_edit_modal = False
            st.rerun()

    # Formulario
    with st.form("annotation_form"):
        col1, col2 = st.columns(2)

        with col1:
            conversation_id = st.text_input(
                "Conversation ID *",
                value=annotation_to_edit.get("conversation_id", "") if annotation_to_edit else "",
                placeholder="Ej: user_12345"
            )

            message_text = st.text_area(
                "Texto del Mensaje *",
                value=annotation_to_edit.get("message_text", "") if annotation_to_edit else "",
                placeholder="Texto original del mensaje del usuario",
                height=100
            )

            annotation_type = st.radio(
                "Tipo de Anotación *",
                options=["intent", "entity", "both"],
                format_func=lambda x: {"intent": "Solo Intent", "entity": "Solo Entity", "both": "Ambos"}[x],
                index=["intent", "entity", "both"].index(annotation_to_edit.get("annotation_type", "intent"))
                    if annotation_to_edit else 0,
                horizontal=True
            )

        with col2:
            # Intent
            if annotation_type in ["intent", "both"]:
                st.markdown("**Intent:**")

                # Intent Original - Solo lectura (muestra lo que detectó el bot)
                original_intent_value = annotation_to_edit.get("original_intent", "N/A") if annotation_to_edit else "N/A"
                st.text_input(
                    "Intent Original (solo lectura)",
                    value=original_intent_value,
                    disabled=True,
                    help="Intent detectado originalmente por el bot - no editable"
                )
                original_intent = original_intent_value  # Guardar para usar en el payload

                # Intent Corregido - Editable
                corrected_intent = st.selectbox(
                    "Intent Corregido *",
                    options=intents,
                    index=intents.index(annotation_to_edit.get("corrected_intent"))
                        if annotation_to_edit and annotation_to_edit.get("corrected_intent") in intents else 0
                )

                # Confianza Original - Solo lectura
                original_confidence_value = float(annotation_to_edit.get("original_confidence", 0.0)) if annotation_to_edit else 0.0
                st.slider(
                    "Confianza Original (solo lectura)",
                    min_value=0.0,
                    max_value=1.0,
                    value=original_confidence_value,
                    disabled=True,
                    help="Confianza del bot en el intent original - no editable"
                )
                original_confidence = original_confidence_value  # Guardar para usar en el payload

            # Entities
            if annotation_type in ["entity", "both"]:
                st.markdown("**Entities:**")

                # Entities originales
                original_entities_str = st.text_area(
                    "Entities Originales (JSON)",
                    value=str(annotation_to_edit.get("original_entities", [])) if annotation_to_edit else "[]",
                    height=80,
                    help="Lista de entities en formato JSON: [{\"entity\": \"producto\", \"value\": \"blusa\", \"start\": 0, \"end\": 5}]"
                )

                # Entities corregidas
                corrected_entities_str = st.text_area(
                    "Entities Corregidas (JSON) *",
                    value=str(annotation_to_edit.get("corrected_entities", [])) if annotation_to_edit else "[]",
                    height=80,
                    help="Lista de entities corregidas en formato JSON"
                )

        # Notas
        notes = st.text_area(
            "Notas",
            value=annotation_to_edit.get("notes", "") if annotation_to_edit else "",
            placeholder="Explicación de por qué se hizo esta corrección (opcional)",
            height=80
        )

        # Botones
        col_btn1, col_btn2 = st.columns(2)

        with col_btn1:
            submitted = st.form_submit_button("💾 Guardar", type="primary", use_container_width=True)

        with col_btn2:
            cancelled = st.form_submit_button("❌ Cancelar", use_container_width=True)

        if cancelled:
            st.session_state.show_create_modal = False
            st.session_state.show_edit_modal = False
            st.rerun()

        if submitted:
            # Validaciones
            errors = []

            if not conversation_id:
                errors.append("Conversation ID es obligatorio")

            if not message_text:
                errors.append("Texto del mensaje es obligatorio")

            if annotation_type in ["intent", "both"] and not corrected_intent:
                errors.append("Intent corregido es obligatorio")

            # FIX: Inicializar variables de entities
            original_entities = []
            corrected_entities = []

            # Parsear entities solo si el tipo de anotación lo requiere
            if annotation_type in ["entity", "both"]:
                try:
                    import ast
                    original_entities = ast.literal_eval(original_entities_str) if original_entities_str else []
                    corrected_entities = ast.literal_eval(corrected_entities_str) if corrected_entities_str else []
                except Exception as e:
                    errors.append(f"Error al parsear entities: {str(e)}")
                    original_entities = []
                    corrected_entities = []

                # Validar entities
                is_valid, validation_errors = validate_entity_spans(message_text, corrected_entities)
                if not is_valid:
                    errors.extend(validation_errors)

            if errors:
                for error in errors:
                    st.error(error)
            else:
                # Construir payload
                data = {
                    "conversation_id": conversation_id,
                    "message_text": message_text,
                    "annotation_type": annotation_type,
                    "notes": notes if notes else None
                }

                if annotation_type in ["intent", "both"]:
                    data["original_intent"] = original_intent if original_intent else None
                    data["corrected_intent"] = corrected_intent
                    data["original_confidence"] = original_confidence

                if annotation_type in ["entity", "both"]:
                    data["original_entities"] = original_entities
                    data["corrected_entities"] = corrected_entities

                # Crear o actualizar
                if is_edit:
                    success = update_annotation(annotation_to_edit["id"], data)
                else:
                    success = create_annotation(data)

                if success:
                    st.session_state.show_create_modal = False
                    st.session_state.show_edit_modal = False
                    st.rerun()


# ============================================
# MODAL: DETALLES
# ============================================

if st.session_state.get("show_detail_modal"):
    view_id = st.session_state.get("view_annotation_id")
    annotation = next((a for a in annotations if a["id"] == view_id), None)

    if annotation:
        st.markdown("---")
        st.subheader(f"👁️ Detalles de Anotación #{annotation['id']}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🔴 Original")
            st.markdown(f"**Conversation ID:** `{annotation.get('conversation_id')}`")
            st.markdown(f"**Mensaje:** {annotation.get('message_text')}")
            st.markdown(f"**Intent:** `{annotation.get('original_intent', 'N/A')}`")
            st.markdown(f"**Confianza:** {annotation.get('original_confidence', 0):.2f}")
            st.markdown("**Entities:**")
            st.markdown(
                format_entities_display(annotation.get("original_entities", []), mode="list"),
                unsafe_allow_html=True
            )

        with col2:
            st.markdown("#### 🟢 Corregido")
            st.markdown(f"**Status:** {format_annotation_status(annotation.get('status'))}", unsafe_allow_html=True)
            st.markdown(f"**Intent:** `{annotation.get('corrected_intent')}`")
            st.markdown("**Entities:**")
            st.markdown(
                format_entities_display(annotation.get("corrected_entities", []), mode="list"),
                unsafe_allow_html=True
            )

            # Preview con highlighting
            if annotation.get("corrected_entities"):
                st.markdown("**Preview:**")
                highlighted = highlight_entities(
                    annotation.get("message_text", ""),
                    annotation.get("corrected_entities", [])
                )
                st.markdown(highlighted, unsafe_allow_html=True)

        # Metadata
        st.markdown("---")
        st.markdown(f"**Tipo:** {format_annotation_type(annotation.get('annotation_type'))}", unsafe_allow_html=True)
        st.markdown(f"**Creado por:** {annotation.get('annotated_by_username')} el {annotation.get('created_at')}")

        if annotation.get("approved_by_username"):
            st.markdown(f"**Aprobado por:** {annotation.get('approved_by_username')} el {annotation.get('approved_at')}")

        if annotation.get("rejection_reason"):
            st.warning(f"**Razón de rechazo:** {annotation.get('rejection_reason')}")

        if annotation.get("notes"):
            st.info(f"**Notas:** {annotation.get('notes')}")

        if st.button("✖️ Cerrar", use_container_width=True):
            st.session_state.show_detail_modal = False
            st.rerun()


# ============================================
# MODAL: APROBAR/RECHAZAR
# ============================================

if st.session_state.get("show_approve_modal"):
    approve_id = st.session_state.get("approve_annotation_id")
    annotation = next((a for a in annotations if a["id"] == approve_id), None)

    if annotation and can_approve_annotation(user):
        st.markdown("---")
        st.subheader(f"✓ Revisar Anotación #{annotation['id']}")

        # Mostrar resumen
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Original:**")
            st.code(f"Intent: {annotation.get('original_intent')}\nConfianza: {annotation.get('original_confidence'):.2f}")

        with col2:
            st.markdown("**Corregido:**")
            st.code(f"Intent: {annotation.get('corrected_intent')}")

        st.markdown(f"**Mensaje:** {annotation.get('message_text')}")

        # Formulario de aprobación
        with st.form("approve_form"):
            decision = st.radio(
                "Decisión",
                options=["approve", "reject"],
                format_func=lambda x: "✅ Aprobar" if x == "approve" else "❌ Rechazar",
                horizontal=True
            )

            # FIX 2: Mostrar siempre el campo rejection_reason
            # (los formularios de Streamlit no soportan widgets reactivos)
            rejection_reason = st.text_area(
                "Razón de Rechazo (requerido solo si se rechaza)",
                placeholder="Explica por qué se rechaza esta anotación",
                height=100,
                help="Este campo es obligatorio solo si seleccionas 'Rechazar'"
            )

            col_btn1, col_btn2 = st.columns(2)

            with col_btn1:
                submitted = st.form_submit_button("💾 Confirmar", type="primary", use_container_width=True)

            with col_btn2:
                cancelled = st.form_submit_button("❌ Cancelar", use_container_width=True)

            if cancelled:
                st.session_state.show_approve_modal = False
                st.rerun()

            if submitted:
                if decision == "reject" and not rejection_reason:
                    st.error("La razón de rechazo es obligatoria")
                else:
                    # FIX 3: Cambiar 'approve' a 'approved'
                    approved = decision == "approve"
                    if approve_annotation(approve_id, approved, rejection_reason):
                        st.session_state.show_approve_modal = False
                        st.rerun()

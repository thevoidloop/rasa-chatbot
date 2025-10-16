"""
Utilidades para el sistema de anotaciones.

Este módulo provee funciones auxiliares para:
- Formateo y visualización de entities
- Validación de entity spans
- Sugerencias de intents desde el API
- Highlighting de texto con entities marcadas
"""

from typing import List, Dict, Tuple, Optional, Any
import streamlit as st
import re


# Colores para entities (consistentes con el sistema)
ENTITY_COLORS = {
    "producto": "#FF6B6B",      # Rojo suave
    "cantidad": "#4ECDC4",      # Turquesa
    "default": "#95E1D3",       # Verde menta
}


def format_entities_display(entities: List[Dict[str, Any]], mode: str = "badge") -> str:
    """
    Formatea entities para visualización.

    Args:
        entities: Lista de entities con formato [{entity, value, start, end}, ...]
        mode: Modo de visualización ('badge', 'inline', 'list')

    Returns:
        HTML string con entities formateadas
    """
    if not entities:
        return "<span style='color: #888;'>Sin entities</span>"

    if mode == "badge":
        badges = []
        for ent in entities:
            entity_type = ent.get("entity", "unknown")
            value = ent.get("value", "")
            color = ENTITY_COLORS.get(entity_type, ENTITY_COLORS["default"])

            badge_html = f"""
            <span style='
                background-color: {color};
                color: white;
                padding: 3px 8px;
                border-radius: 12px;
                font-size: 0.85em;
                font-weight: 500;
                margin-right: 5px;
                display: inline-block;
                margin-bottom: 5px;
            '>
                {entity_type}: {value}
            </span>
            """
            badges.append(badge_html)
        return "".join(badges)

    elif mode == "inline":
        inline_parts = []
        for ent in entities:
            entity_type = ent.get("entity", "unknown")
            value = ent.get("value", "")
            inline_parts.append(f"<b>{entity_type}</b>: {value}")
        return " | ".join(inline_parts)

    elif mode == "list":
        list_items = []
        for ent in entities:
            entity_type = ent.get("entity", "unknown")
            value = ent.get("value", "")
            start = ent.get("start", "?")
            end = ent.get("end", "?")
            list_items.append(
                f"<li><b>{entity_type}</b>: \"{value}\" (pos: {start}-{end})</li>"
            )
        return f"<ul style='margin: 5px 0; padding-left: 20px;'>{''.join(list_items)}</ul>"

    return str(entities)


def highlight_entities(text: str, entities: List[Dict[str, Any]]) -> str:
    """
    Resalta entities en el texto usando HTML.

    Args:
        text: Texto original
        entities: Lista de entities con posiciones start/end

    Returns:
        HTML string con texto resaltado
    """
    if not entities or not text:
        return text

    # Ordenar entities por posición (de atrás hacia adelante para mantener índices)
    sorted_entities = sorted(entities, key=lambda e: e.get("start", 0), reverse=True)

    highlighted_text = text
    for ent in sorted_entities:
        start = ent.get("start")
        end = ent.get("end")
        entity_type = ent.get("entity", "unknown")

        if start is None or end is None:
            continue

        # Validar que las posiciones sean válidas
        if start < 0 or end > len(text) or start >= end:
            continue

        value = text[start:end]
        color = ENTITY_COLORS.get(entity_type, ENTITY_COLORS["default"])

        # Crear span con tooltip
        highlighted_span = f"""<span style='
            background-color: {color};
            color: white;
            padding: 2px 4px;
            border-radius: 3px;
            font-weight: 500;
        ' title='{entity_type}: {value}'>{value}</span>"""

        highlighted_text = (
            highlighted_text[:start] +
            highlighted_span +
            highlighted_text[end:]
        )

    return highlighted_text


def validate_entity_spans(
    text: str,
    entities: List[Dict[str, Any]]
) -> Tuple[bool, List[str]]:
    """
    Valida que los entity spans sean correctos.

    Args:
        text: Texto completo del mensaje
        entities: Lista de entities a validar

    Returns:
        (is_valid, errors) - Tupla con validez y lista de errores
    """
    errors = []

    if not text:
        errors.append("El texto no puede estar vacío")
        return False, errors

    if not entities:
        # Sin entities es válido
        return True, []

    text_length = len(text)

    for idx, ent in enumerate(entities):
        entity_type = ent.get("entity")
        value = ent.get("value")
        start = ent.get("start")
        end = ent.get("end")

        # Validar campos obligatorios
        if not entity_type:
            errors.append(f"Entity #{idx+1}: Falta el campo 'entity'")

        if value is None or value == "":
            errors.append(f"Entity #{idx+1}: Falta el campo 'value'")

        if start is None:
            errors.append(f"Entity #{idx+1}: Falta el campo 'start'")
            continue

        if end is None:
            errors.append(f"Entity #{idx+1}: Falta el campo 'end'")
            continue

        # Validar rangos
        if start < 0:
            errors.append(f"Entity #{idx+1}: 'start' no puede ser negativo (start={start})")

        if end > text_length:
            errors.append(f"Entity #{idx+1}: 'end' ({end}) excede la longitud del texto ({text_length})")

        if start >= end:
            errors.append(f"Entity #{idx+1}: 'start' ({start}) debe ser menor que 'end' ({end})")
            continue

        # Validar que el value coincida con el texto extraído
        if 0 <= start < end <= text_length:
            extracted = text[start:end]
            if extracted != value:
                errors.append(
                    f"Entity #{idx+1}: El value '{value}' no coincide con el texto "
                    f"en posición {start}-{end}: '{extracted}'"
                )

    # Verificar overlaps
    sorted_entities = sorted(entities, key=lambda e: e.get("start", 0))
    for i in range(len(sorted_entities) - 1):
        current = sorted_entities[i]
        next_ent = sorted_entities[i + 1]

        current_end = current.get("end", 0)
        next_start = next_ent.get("start", 0)

        if current_end > next_start:
            errors.append(
                f"Entities se solapan: '{current.get('value')}' ({current.get('start')}-{current_end}) "
                f"con '{next_ent.get('value')}' ({next_start}-{next_ent.get('end')})"
            )

    is_valid = len(errors) == 0
    return is_valid, errors


def get_intent_suggestions(api_client, query: str = "") -> List[str]:
    """
    Obtiene lista de intents disponibles desde el API.

    Args:
        api_client: Cliente API configurado
        query: Query opcional para filtrar intents (case-insensitive)

    Returns:
        Lista de nombres de intents
    """
    try:
        response = api_client._make_request("GET", "/api/v1/export/intents")

        if response and response.get("intents"):
            intents = response["intents"]

            # Filtrar por query si se proporciona
            if query:
                query_lower = query.lower()
                intents = [i for i in intents if query_lower in i.lower()]

            return sorted(intents)

        return []

    except Exception as e:
        st.error(f"Error al obtener intents: {str(e)}")
        return []


def get_entity_types(api_client) -> List[str]:
    """
    Obtiene lista de entity types disponibles desde el API.

    Args:
        api_client: Cliente API configurado

    Returns:
        Lista de tipos de entities
    """
    try:
        response = api_client._make_request("GET", "/api/v1/export/entities")

        if response and response.get("entities"):
            return sorted(response["entities"])

        return []

    except Exception as e:
        st.error(f"Error al obtener entity types: {str(e)}")
        return []


def extract_entities_from_text(
    text: str,
    selection_start: int,
    selection_end: int,
    entity_type: str
) -> Dict[str, Any]:
    """
    Crea un objeto entity a partir de una selección de texto.

    Args:
        text: Texto completo
        selection_start: Posición inicial de la selección
        selection_end: Posición final de la selección
        entity_type: Tipo de entity

    Returns:
        Diccionario con entity {entity, value, start, end}
    """
    if selection_start >= selection_end or selection_start < 0 or selection_end > len(text):
        raise ValueError("Selección inválida")

    value = text[selection_start:selection_end]

    return {
        "entity": entity_type,
        "value": value,
        "start": selection_start,
        "end": selection_end
    }


def format_annotation_status(status: str) -> str:
    """
    Formatea el status de una anotación con colores.

    Args:
        status: Status de la anotación (pending, approved, rejected, trained, deployed)

    Returns:
        HTML string con badge coloreado
    """
    status_config = {
        "pending": {"label": "Pendiente", "color": "#FFA500", "icon": "⏳"},
        "approved": {"label": "Aprobada", "color": "#28A745", "icon": "✓"},
        "rejected": {"label": "Rechazada", "color": "#DC3545", "icon": "✗"},
        "trained": {"label": "Entrenada", "color": "#007BFF", "icon": "🎓"},
        "deployed": {"label": "Desplegada", "color": "#6F42C1", "icon": "🚀"},
    }

    config = status_config.get(status, {"label": status, "color": "#6C757D", "icon": "●"})

    return f"""
    <span style='
        background-color: {config['color']};
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85em;
        font-weight: 500;
        display: inline-block;
    '>
        {config['icon']} {config['label']}
    </span>
    """


def format_annotation_type(annotation_type: str) -> str:
    """
    Formatea el tipo de anotación con badge.

    Args:
        annotation_type: Tipo (intent, entity, both)

    Returns:
        HTML string con badge
    """
    type_config = {
        "intent": {"label": "Intent", "color": "#17A2B8"},
        "entity": {"label": "Entity", "color": "#FFC107"},
        "both": {"label": "Ambos", "color": "#6610F2"},
    }

    config = type_config.get(annotation_type, {"label": annotation_type, "color": "#6C757D"})

    return f"""
    <span style='
        background-color: {config['color']};
        color: white;
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.8em;
        font-weight: 500;
    '>
        {config['label']}
    </span>
    """


def calculate_entity_positions(text: str, entity_value: str) -> Optional[Dict[str, int]]:
    """
    Encuentra automáticamente las posiciones start/end de un entity value en el texto.

    Args:
        text: Texto completo
        entity_value: Valor del entity a buscar

    Returns:
        Dict con {start, end} o None si no se encuentra
    """
    if not text or not entity_value:
        return None

    # Buscar coincidencia exacta (case-sensitive)
    index = text.find(entity_value)

    if index != -1:
        return {
            "start": index,
            "end": index + len(entity_value)
        }

    # Intentar búsqueda case-insensitive
    text_lower = text.lower()
    entity_lower = entity_value.lower()
    index = text_lower.find(entity_lower)

    if index != -1:
        # Retornar el texto original (no el lower)
        return {
            "start": index,
            "end": index + len(entity_value)
        }

    return None


def build_entity_editor_ui(
    text: str,
    current_entities: List[Dict[str, Any]],
    available_entity_types: List[str],
    key_prefix: str = ""
) -> List[Dict[str, Any]]:
    """
    Construye una UI interactiva para editar entities.

    Args:
        text: Texto del mensaje
        current_entities: Entities actuales
        available_entity_types: Tipos disponibles
        key_prefix: Prefijo para keys de Streamlit (evitar colisiones)

    Returns:
        Lista actualizada de entities
    """
    st.markdown("#### Entities")

    # Inicializar en session_state si no existe
    state_key = f"{key_prefix}_entities"
    if state_key not in st.session_state:
        st.session_state[state_key] = current_entities.copy() if current_entities else []

    entities = st.session_state[state_key]

    # Mostrar preview con highlighting
    if entities:
        st.markdown("**Preview:**")
        highlighted = highlight_entities(text, entities)
        st.markdown(highlighted, unsafe_allow_html=True)

    st.markdown("**Listado:**")

    # Editor de entities existentes
    entities_to_remove = []
    for idx, entity in enumerate(entities):
        col1, col2, col3, col4, col5 = st.columns([2, 2, 1, 1, 1])

        with col1:
            entity["entity"] = st.selectbox(
                "Tipo",
                options=available_entity_types,
                index=available_entity_types.index(entity["entity"])
                    if entity["entity"] in available_entity_types else 0,
                key=f"{key_prefix}_ent_type_{idx}"
            )

        with col2:
            entity["value"] = st.text_input(
                "Valor",
                value=entity["value"],
                key=f"{key_prefix}_ent_value_{idx}"
            )

        with col3:
            entity["start"] = st.number_input(
                "Inicio",
                value=entity["start"],
                min_value=0,
                key=f"{key_prefix}_ent_start_{idx}"
            )

        with col4:
            entity["end"] = st.number_input(
                "Fin",
                value=entity["end"],
                min_value=entity["start"] + 1,
                key=f"{key_prefix}_ent_end_{idx}"
            )

        with col5:
            if st.button("🗑️", key=f"{key_prefix}_ent_remove_{idx}", help="Eliminar"):
                entities_to_remove.append(idx)

    # Eliminar entities marcados
    for idx in reversed(entities_to_remove):
        entities.pop(idx)

    # Botón para añadir nueva entity
    if st.button("➕ Añadir Entity", key=f"{key_prefix}_add_entity"):
        new_entity = {
            "entity": available_entity_types[0] if available_entity_types else "producto",
            "value": "",
            "start": 0,
            "end": 0
        }
        entities.append(new_entity)
        st.rerun()

    # Validar entities
    is_valid, errors = validate_entity_spans(text, entities)

    if not is_valid:
        st.error("**Errores de validación:**")
        for error in errors:
            st.markdown(f"- {error}")

    # Actualizar session_state
    st.session_state[state_key] = entities

    return entities

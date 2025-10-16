"""
Página de Exportación de Datos NLU.

Funcionalidades:
- Preview de anotaciones aprobadas en formato RASA NLU
- Filtros por fecha e intent
- Validación de YAML y dominio
- Estadísticas de exportación
- Descarga de archivo NLU .yml
- Instrucciones de aplicación

Acceso: Solo qa_lead (nivel 4+) y admin (nivel 5)
"""

import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import sys
import os

# Añadir path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.session import require_auth, get_current_user


# ============================================
# CONFIGURACIÓN DE PÁGINA
# ============================================

st.set_page_config(
    page_title="Exportar NLU - Training Platform",
    page_icon="📤",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Requerir autenticación
require_auth()

# Obtener usuario actual
user = get_current_user()
api_client = st.session_state.api_client


# ============================================
# VALIDACIÓN DE PERMISOS
# ============================================

def has_export_permission(user: Dict) -> bool:
    """Verifica si el usuario tiene permisos de exportación."""
    return user["role_level"] >= 4  # qa_lead (4) o admin (5)


if not has_export_permission(user):
    st.error("🚫 No tienes permisos para acceder a esta página")
    st.info("Solo usuarios con rol **qa_lead** o **admin** pueden exportar datos NLU.")
    st.stop()


# ============================================
# FUNCIONES AUXILIARES
# ============================================

def load_intents() -> list:
    """Carga lista de intents disponibles."""
    try:
        response = api_client._make_request("GET", "/api/v1/export/intents")
        return response.get("intents", []) if isinstance(response, dict) else response
    except Exception as e:
        st.error(f"Error al cargar intents: {str(e)}")
        return []


def get_export_preview(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    intent_filter: Optional[str] = None
) -> Optional[Dict]:
    """Obtiene preview de exportación con validación."""
    try:
        params = {}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if intent_filter:
            params["intent_filter"] = intent_filter

        with st.spinner("Generando preview..."):
            response = api_client._make_request(
                "GET",
                "/api/v1/export/nlu/preview",
                params=params
            )
            return response
    except Exception as e:
        st.error(f"Error al generar preview: {str(e)}")
        return None


def download_nlu_yaml(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    intent_filter: Optional[str] = None
) -> Optional[str]:
    """Descarga archivo YAML de exportación."""
    try:
        params = {}
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if intent_filter:
            params["intent_filter"] = intent_filter

        with st.spinner("Generando archivo YAML..."):
            # Get raw text response
            import requests
            token = st.session_state.token
            headers = {"Authorization": f"Bearer {token}"}

            api_url = os.getenv("API_URL", "http://api-server:8000")
            url = f"{api_url}/api/v1/export/nlu/download"

            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 200:
                return response.text
            else:
                st.error(f"Error al descargar: {response.status_code} - {response.text}")
                return None

    except Exception as e:
        st.error(f"Error al descargar YAML: {str(e)}")
        return None


# ============================================
# HEADER
# ============================================

st.title("📤 Exportar Datos de Entrenamiento NLU")
st.markdown("""
Esta herramienta te permite exportar las anotaciones aprobadas en formato **RASA NLU** (YAML)
para incorporarlas al entrenamiento del chatbot.

**Flujo de trabajo:**
1. Filtra las anotaciones que deseas exportar
2. Genera un preview con validación
3. Revisa las estadísticas y warnings
4. Descarga el archivo `.yml`
5. Aplica los cambios siguiendo las instrucciones
""")

st.markdown("---")


# ============================================
# SIDEBAR CON FILTROS
# ============================================

st.sidebar.header("🔍 Filtros de Exportación")

# Filtro de rango de fechas
st.sidebar.markdown("### Rango de Fechas")

date_preset = st.sidebar.selectbox(
    "Preselección",
    options=["todo", "30_dias", "90_dias", "personalizado"],
    format_func=lambda x: {
        "todo": "Todas las fechas",
        "30_dias": "Últimos 30 días",
        "90_dias": "Últimos 90 días",
        "personalizado": "Personalizado"
    }[x],
    index=0
)

from_date = None
to_date = None

if date_preset == "personalizado":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        date_from_input = st.date_input(
            "Desde",
            value=datetime.now().date() - timedelta(days=30)
        )
        from_date = date_from_input.isoformat()

    with col2:
        date_to_input = st.date_input(
            "Hasta",
            value=datetime.now().date()
        )
        to_date = date_to_input.isoformat()

elif date_preset != "todo":
    days_map = {"30_dias": 30, "90_dias": 90}
    days = days_map.get(date_preset, 0)

    from_date = (datetime.now() - timedelta(days=days)).date().isoformat()
    to_date = datetime.now().date().isoformat()

    st.sidebar.caption(f"📅 {from_date} hasta {to_date}")

# Filtro por intent
st.sidebar.markdown("### Intent")
available_intents = load_intents()

intent_filter_options = st.sidebar.multiselect(
    "Filtrar por intent",
    options=available_intents,
    default=None,
    help="Deja vacío para exportar todos los intents"
)

intent_filter = ",".join(intent_filter_options) if intent_filter_options else None

st.sidebar.markdown("---")

# Botón de generar preview
generate_preview = st.sidebar.button(
    "🔍 Generar Preview",
    use_container_width=True,
    type="primary"
)

# Botón de actualizar
if st.sidebar.button("🔄 Actualizar", use_container_width=True):
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.info(
    f"👤 **{user['username']}** ({user['role']})\n\n"
    f"Tienes permisos de exportación ✓"
)


# ============================================
# INICIALIZAR SESSION STATE
# ============================================

if "preview_data" not in st.session_state:
    st.session_state.preview_data = None


# ============================================
# GENERAR PREVIEW
# ============================================

if generate_preview:
    st.session_state.preview_data = get_export_preview(
        from_date=from_date,
        to_date=to_date,
        intent_filter=intent_filter
    )


# ============================================
# MOSTRAR PREVIEW Y ESTADÍSTICAS
# ============================================

preview_data = st.session_state.preview_data

if preview_data:
    # Mostrar estadísticas principales
    stats = preview_data.get("stats", {})
    is_valid = preview_data.get("is_valid", False)
    can_export = preview_data.get("can_export", False)

    st.subheader("📊 Resumen de Exportación")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="Intents",
            value=stats.get("total_intents", 0),
            help="Número total de intents en la exportación"
        )

    with col2:
        st.metric(
            label="Ejemplos",
            value=stats.get("total_examples", 0),
            help="Número total de ejemplos de entrenamiento"
        )

    with col3:
        st.metric(
            label="Entities Usados",
            value=stats.get("total_entities_used", 0),
            help="Número de entities diferentes utilizados"
        )

    with col4:
        avg_examples = stats.get("avg_examples_per_intent", 0)
        st.metric(
            label="Promedio/Intent",
            value=f"{avg_examples:.1f}",
            help="Promedio de ejemplos por intent",
            delta="Bueno" if avg_examples >= 10 else "Poco"
        )

    st.markdown("---")

    # Tabs para diferentes vistas
    tab1, tab2, tab3 = st.tabs(["📄 YAML Preview", "📊 Estadísticas Detalladas", "⚠️ Validación"])

    with tab1:
        st.markdown("### Vista Previa del YAML")

        yaml_content = preview_data.get("yaml_content", "")

        if yaml_content:
            # Mostrar con syntax highlighting
            st.code(yaml_content, language="yaml", line_numbers=True)

            # Información adicional
            st.caption(f"**Total de líneas:** {len(yaml_content.splitlines())}")
            st.caption(f"**Total de anotaciones:** {stats.get('total_annotations', 0)}")

        else:
            st.warning("No hay contenido YAML disponible. Verifica que haya anotaciones aprobadas.")

    with tab2:
        st.markdown("### Estadísticas Detalladas")

        col_stats1, col_stats2 = st.columns(2)

        with col_stats1:
            st.markdown("#### Distribución de Intents")

            if stats.get("total_intents", 0) > 0:
                st.metric("Total de intents únicos", stats["total_intents"])
                st.metric("Total de ejemplos", stats.get("total_examples", 0))
                st.metric(
                    "Ejemplos por intent (promedio)",
                    f"{stats.get('avg_examples_per_intent', 0):.2f}"
                )

                # Recommendation
                avg = stats.get("avg_examples_per_intent", 0)
                if avg < 5:
                    st.warning("⚠️ Se recomienda al menos 5 ejemplos por intent")
                elif avg < 10:
                    st.info("💡 Considera añadir más ejemplos para mejor entrenamiento")
                else:
                    st.success("✅ Buena cantidad de ejemplos por intent")
            else:
                st.info("No hay intents en esta exportación")

        with col_stats2:
            st.markdown("#### Uso de Entities")

            entity_usage = stats.get("entity_usage", {})

            if entity_usage:
                st.markdown("**Conteo por tipo:**")

                # Crear tabla de entity usage
                import pandas as pd
                df_entities = pd.DataFrame([
                    {"Entity": entity, "Ocurrencias": count}
                    for entity, count in sorted(entity_usage.items(), key=lambda x: x[1], reverse=True)
                ])

                st.dataframe(
                    df_entities,
                    use_container_width=True,
                    hide_index=True
                )

                # Total
                total_entity_occurrences = sum(entity_usage.values())
                st.metric("Total de ocurrencias de entities", total_entity_occurrences)

            else:
                st.info("No hay entities en esta exportación")

    with tab3:
        st.markdown("### Validación del YAML")

        # Estado de validación
        if is_valid and can_export:
            st.success("✅ El YAML es válido y puede ser exportado")
        elif is_valid and not can_export:
            st.warning("⚠️ El YAML tiene formato válido pero hay advertencias")
        else:
            st.error("❌ El YAML tiene errores y NO puede ser exportado")

        # Mostrar errores
        errors = preview_data.get("validation_errors", [])
        if errors:
            st.markdown("#### ❌ Errores Críticos")
            for error in errors:
                st.error(error)

            st.markdown("""
            **Los errores críticos deben resolverse antes de exportar.**
            Verifica que:
            - Los intents existan en el dominio
            - Los entity types estén definidos
            - El formato YAML sea correcto
            """)

        # Mostrar warnings
        warnings = preview_data.get("validation_warnings", [])
        if warnings:
            st.markdown("#### ⚠️ Advertencias")
            for warning in warnings:
                st.warning(warning)

            st.markdown("""
            **Las advertencias no bloquean la exportación** pero debes revisarlas:
            - Intents nuevos que no existen en el dominio actual
            - Entity types que no se han usado antes
            - Considera actualizar domain.yml antes de entrenar
            """)

        if not errors and not warnings:
            st.success("✓ No se encontraron errores ni advertencias")

    st.markdown("---")

    # ============================================
    # BOTÓN DE DESCARGA
    # ============================================

    st.subheader("⬇️ Descargar Archivo NLU")

    if can_export:
        col_dl1, col_dl2 = st.columns([2, 1])

        with col_dl1:
            st.markdown("""
            El archivo descargado contendrá todas las anotaciones aprobadas en formato RASA NLU.
            Puedes aplicarlo directamente en tu proyecto RASA.
            """)

        with col_dl2:
            if st.button("📥 Descargar NLU YAML", type="primary", use_container_width=True):
                yaml_content = download_nlu_yaml(
                    from_date=from_date,
                    to_date=to_date,
                    intent_filter=intent_filter
                )

                if yaml_content:
                    # Generar filename con timestamp
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"nlu_annotations_{timestamp}.yml"

                    st.download_button(
                        label=f"💾 Guardar como {filename}",
                        data=yaml_content,
                        file_name=filename,
                        mime="application/x-yaml",
                        use_container_width=True
                    )

                    st.success(f"✅ Archivo generado: {filename}")

        st.markdown("---")

        # ============================================
        # INSTRUCCIONES DE APLICACIÓN
        # ============================================

        st.subheader("📖 Instrucciones de Aplicación")

        with st.expander("🔧 Cómo aplicar el archivo NLU descargado", expanded=True):
            st.markdown("""
            ### Pasos para aplicar las anotaciones al chatbot RASA:

            #### 1. Preparar el archivo
            ```bash
            # Descargar el archivo desde el botón de arriba
            # El archivo se llamará algo como: nlu_annotations_20251014_235900.yml
            ```

            #### 2. Copiar al proyecto RASA
            ```bash
            # Opción A: Sobrescribir el archivo NLU existente (CUIDADO: hace backup primero)
            cp data/nlu.yml data/nlu.yml.backup
            cp ~/Downloads/nlu_annotations_*.yml data/nlu.yml

            # Opción B: Crear archivo separado y mergear manualmente
            cp ~/Downloads/nlu_annotations_*.yml data/nlu_annotated.yml
            # Luego merge manualmente los contenidos
            ```

            #### 3. Validar el formato
            ```bash
            # Validar que el archivo YAML sea correcto
            docker exec -it rasa_server rasa data validate
            ```

            #### 4. Entrenar el modelo
            ```bash
            # Entrenar el modelo con los nuevos datos
            docker exec -it rasa_server rasa train

            # Esto generará un nuevo modelo en models/
            ```

            #### 5. Reiniciar el servidor RASA
            ```bash
            # Reiniciar para cargar el nuevo modelo
            docker compose restart rasa-server

            # Verificar que el modelo se cargó correctamente
            docker compose logs -f rasa-server
            ```

            #### 6. Probar los cambios
            ```bash
            # Probar en modo interactivo
            docker exec -it rasa_server rasa shell

            # O probar via API
            curl -X POST http://localhost:5005/webhooks/rest/webhook \\
              -H "Content-Type: application/json" \\
              -d '{"sender":"test","message":"tu mensaje de prueba"}'
            ```

            ### ⚠️ Recomendaciones Importantes:

            - **Siempre haz backup** del archivo `nlu.yml` antes de sobrescribir
            - **Valida el archivo** antes de entrenar para evitar errores
            - **Prueba el nuevo modelo** antes de desplegarlo en producción
            - **Documenta los cambios** que hiciste en las anotaciones
            - **Monitorea las métricas** después de desplegar para verificar mejoras

            ### 📊 Métricas a Monitorear:

            - Intent accuracy (precisión de intents)
            - Entity recognition F1 score
            - Confidence scores promedio
            - Casos de fallback
            """)

    else:
        st.error("""
        ❌ **No se puede exportar debido a errores de validación**

        Por favor:
        1. Revisa la pestaña "Validación" para ver los errores
        2. Corrige los errores en las anotaciones
        3. Vuelve a generar el preview
        """)

else:
    # No hay preview generado
    st.info("""
    👆 **Usa los filtros del sidebar y haz clic en "Generar Preview"**

    Esto cargará las anotaciones aprobadas y generará una vista previa del archivo NLU
    que se exportará.

    **Filtros disponibles:**
    - Rango de fechas (por defecto: todas las fechas)
    - Intent específico (opcional)
    """)

    st.markdown("---")

    # Mostrar información útil mientras tanto
    st.markdown("### 📚 Información sobre el Formato NLU")

    col_info1, col_info2 = st.columns(2)

    with col_info1:
        st.markdown("""
        #### Estructura del YAML

        El archivo NLU exportado sigue el formato RASA 3.x:

        ```yaml
        version: "3.1"

        nlu:
        - intent: consultar_catalogo
          examples: |
            - quiero ver productos
            - muéstrame el catálogo
            - necesito comprar algo

        - intent: agregar_al_carrito
          examples: |
            - añade [2](cantidad) [blusas](producto)
            - quiero [una](cantidad) [camisa](producto)
        ```
        """)

    with col_info2:
        st.markdown("""
        #### Entities en Formato Markdown

        Los entities se marcan con la sintaxis:

        ```
        [texto](entity_type)
        ```

        **Ejemplos:**
        - `[blusa](producto)` → entity "producto" con valor "blusa"
        - `[2](cantidad)` → entity "cantidad" con valor "2"
        - `[rojo](color)` → entity "color" con valor "rojo"

        Este formato permite a RASA aprender a extraer entities
        de los mensajes del usuario.
        """)

# Footer
st.markdown("---")
st.caption(
    f"Exportación de Datos NLU | "
    f"Usuario: {user['username']} ({user['role']}) | "
    f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
)

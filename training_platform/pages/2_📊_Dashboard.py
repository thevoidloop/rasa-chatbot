"""
Dashboard - Main Metrics Page
"""
import streamlit as st
import sys
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.session import require_auth, get_current_user
from utils.api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="Dashboard - RASA Training Platform",
    page_icon="📊",
    layout="wide"
)

# Require authentication
require_auth()

# Get current user and API client
user = get_current_user()
api_client = st.session_state.api_client

# Title
st.title("📊 Dashboard de Métricas")
st.markdown("---")

# Sidebar - Filters
with st.sidebar:
    st.markdown("### Filtros")
    days_filter = st.selectbox(
        "Período de tiempo",
        options=[7, 14, 30, 90],
        format_func=lambda x: f"Últimos {x} días",
        index=0
    )

    if st.button("🔄 Actualizar", use_container_width=True):
        st.rerun()

# Fetch metrics data
try:
    with st.spinner("Cargando métricas..."):
        summary = api_client._make_request("GET", f"/api/v1/metrics/summary?days={days_filter}")
        timeline = api_client._make_request("GET", f"/api/v1/metrics/timeline?days=30")
        intents = api_client._make_request("GET", f"/api/v1/metrics/intents?days={days_filter}")
        heatmap_data = api_client._make_request("GET", f"/api/v1/metrics/heatmap?days={days_filter}")
        funnel = api_client._make_request("GET", f"/api/v1/metrics/funnel?days={days_filter}")

except Exception as e:
    st.error(f"❌ Error al cargar métricas: {str(e)}")
    st.info("💡 Asegúrate de que el servidor API esté corriendo y que haya datos disponibles.")
    st.stop()

# === MÉTRICAS CLAVE ===
st.markdown("### 📈 Métricas Clave")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Total Conversaciones",
        value=summary.get("total_conversations", 0),
        delta=f"{days_filter} días",
        help=f"Conversaciones únicas en los últimos {days_filter} días"
    )

with col2:
    st.metric(
        label="Confianza Promedio",
        value=f"{summary.get('avg_confidence', 0)}%",
        delta="Alta" if summary.get('avg_confidence', 0) > 70 else "Baja",
        delta_color="normal" if summary.get('avg_confidence', 0) > 70 else "inverse",
        help="Confidence promedio del modelo en las predicciones"
    )

with col3:
    st.metric(
        label="Intents Detectados",
        value=summary.get("total_intents_detected", 0),
        help="Total de intents procesados en el período"
    )

with col4:
    st.metric(
        label="Pendientes de Revisión",
        value=summary.get("pending_reviews", 0),
        delta="⚠️" if summary.get("pending_reviews", 0) > 10 else "✅",
        help="Conversaciones marcadas para revisión manual"
    )

st.markdown("---")

# === TOP INTENTS ===
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### 🎯 Top 5 Intents")

    top_intents = summary.get("top_intents", [])

    if top_intents:
        df_intents = pd.DataFrame(top_intents)

        # Create horizontal bar chart
        fig_intents = px.bar(
            df_intents,
            x="count",
            y="intent",
            orientation="h",
            title="Intents Más Frecuentes",
            labels={"count": "Frecuencia", "intent": "Intent"},
            color="count",
            color_continuous_scale="Blues"
        )

        fig_intents.update_layout(
            showlegend=False,
            height=300,
            yaxis={'categoryorder':'total ascending'}
        )

        st.plotly_chart(fig_intents, use_container_width=True)
    else:
        st.info("No hay datos de intents disponibles")

with col_right:
    st.markdown("### 📊 Distribución de Intents")

    if intents:
        df_dist = pd.DataFrame(intents)

        # Create pie chart
        fig_pie = px.pie(
            df_dist.head(5),
            values="count",
            names="intent",
            title="Top 5 Intents por Volumen",
            hole=0.4
        )

        fig_pie.update_layout(height=300)

        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No hay datos de distribución disponibles")

st.markdown("---")

# === TIMELINE ===
st.markdown("### 📅 Timeline de Conversaciones (Últimos 30 días)")

if timeline:
    df_timeline = pd.DataFrame(timeline)
    df_timeline['date'] = pd.to_datetime(df_timeline['date'])

    fig_timeline = px.line(
        df_timeline,
        x="date",
        y="conversations",
        title="Conversaciones por Día",
        labels={"date": "Fecha", "conversations": "Conversaciones"},
        markers=True
    )

    fig_timeline.update_traces(line_color='#1f77b4', line_width=3)
    fig_timeline.update_layout(height=400)

    st.plotly_chart(fig_timeline, use_container_width=True)
else:
    st.info("No hay datos de timeline disponibles")

st.markdown("---")

# === HEATMAP ===
st.markdown("### 🔥 Heatmap de Uso por Hora")

if heatmap_data:
    # Prepare data for heatmap
    df_heatmap = pd.DataFrame(heatmap_data)

    # Create pivot table
    pivot = df_heatmap.pivot_table(
        values='count',
        index='day',
        columns='hour',
        fill_value=0
    )

    # Reorder days
    day_order = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    fig_heatmap = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"{h}:00" for h in range(24)],
        y=pivot.index,
        colorscale='YlOrRd',
        hoverongaps=False
    ))

    fig_heatmap.update_layout(
        title="Conversaciones por Día y Hora",
        xaxis_title="Hora del Día",
        yaxis_title="Día de la Semana",
        height=400
    )

    st.plotly_chart(fig_heatmap, use_container_width=True)
else:
    st.info("No hay datos de heatmap disponibles")

st.markdown("---")

# === FUNNEL ===
st.markdown("### 🎯 Funnel de Conversaciones")

col_funnel, col_stats = st.columns([2, 1])

with col_funnel:
    if funnel:
        # Create funnel chart
        fig_funnel = go.Figure(go.Funnel(
            y=['Iniciadas', 'Alta Confianza (>70%)', 'Resueltas'],
            x=[
                funnel.get('total_started', 0),
                funnel.get('high_confidence', 0),
                funnel.get('resolved', 0)
            ],
            textinfo="value+percent initial",
            marker={"color": ["#636EFA", "#00CC96", "#19D3F3"]}
        ))

        fig_funnel.update_layout(
            title="Progresión de Conversaciones",
            height=400
        )

        st.plotly_chart(fig_funnel, use_container_width=True)
    else:
        st.info("No hay datos de funnel disponibles")

with col_stats:
    st.markdown("#### Estadísticas")

    if funnel:
        st.metric(
            "Tasa de Conversión",
            f"{funnel.get('conversion_rate', 0)}%",
            help="Porcentaje de conversaciones resueltas exitosamente"
        )

        st.metric(
            "Total Iniciadas",
            funnel.get('total_started', 0)
        )

        st.metric(
            "Alta Confianza",
            funnel.get('high_confidence', 0)
        )

        st.metric(
            "Resueltas",
            funnel.get('resolved', 0)
        )

st.markdown("---")

# === MODELO ACTUAL ===
st.markdown("### 🤖 Modelo Actual")

current_model = summary.get("current_model")

if current_model:
    col_model1, col_model2, col_model3 = st.columns(3)

    with col_model1:
        st.info(f"**Nombre:** {current_model.get('name', 'N/A')}")

    with col_model2:
        trained_at = current_model.get('trained_at')
        if trained_at:
            st.info(f"**Entrenado:** {trained_at[:10]}")
        else:
            st.info("**Entrenado:** N/A")

    with col_model3:
        accuracy = current_model.get('accuracy', 0)
        st.info(f"**Precisión:** {accuracy}%")
else:
    st.warning("⚠️ No hay modelo desplegado actualmente")

# Footer
st.markdown("---")
st.caption(f"Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Usuario: {user['username']} ({user['role']})")

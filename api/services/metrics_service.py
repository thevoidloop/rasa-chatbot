"""
Metrics service for dashboard
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import json
import pytz

# Timezone de Guatemala
GUATEMALA_TZ = pytz.timezone('America/Guatemala')


def get_summary_metrics(db: Session, days: int = 7) -> Dict[str, Any]:
    """
    Get summary metrics for dashboard

    Args:
        db: Database session
        days: Number of days to look back

    Returns:
        dict: Summary metrics
    """
    # Usar hora de Guatemala
    now_guatemala = datetime.now(GUATEMALA_TZ)
    since_date = now_guatemala - timedelta(days=days)
    # Convertir a naive datetime para queries (PostgreSQL ya tiene TZ configurado)
    since_date_naive = since_date.replace(tzinfo=None)
    since_timestamp = since_date.timestamp()

    # Get total conversations from rasa_conversations table
    total_conversations = db.execute(text("""
        SELECT COUNT(DISTINCT sender_id) as total
        FROM rasa_conversations
        WHERE created_at >= :since_date
    """), {"since_date": since_date_naive}).fetchone()

    # Get intent statistics from events table using Unix timestamp
    intent_stats = db.execute(text("""
        SELECT
            COUNT(*) as total_intents,
            AVG(CAST(data::jsonb->'parse_data'->'intent'->>'confidence' AS FLOAT)) as avg_confidence
        FROM events
        WHERE type_name = 'user'
        AND timestamp >= :since_timestamp
        AND data::jsonb->'parse_data'->'intent' IS NOT NULL
    """), {"since_timestamp": since_timestamp}).fetchone()

    # Get most common intents
    top_intents = db.execute(text("""
        SELECT
            intent_name,
            COUNT(*) as count
        FROM events
        WHERE type_name = 'user'
        AND timestamp >= :since_timestamp
        AND intent_name IS NOT NULL
        GROUP BY intent_name
        ORDER BY count DESC
        LIMIT 5
    """), {"since_timestamp": since_timestamp}).fetchall()

    # Get entity statistics
    entity_stats = db.execute(text("""
        SELECT COUNT(*) as total_entities
        FROM events
        WHERE type_name = 'user'
        AND timestamp >= :since_timestamp
        AND jsonb_array_length(COALESCE(data::jsonb->'parse_data'->'entities', '[]'::jsonb)) > 0
    """), {"since_timestamp": since_timestamp}).fetchone()

    # Get conversations count (no pending_reviews in actual schema)
    active_conversations = db.execute(text("""
        SELECT COUNT(*) as total
        FROM rasa_conversations
        WHERE active = true
    """)).fetchone()

    # Get current model info
    current_model = db.execute(text("""
        SELECT model_name, deployed_at, performance_metrics
        FROM deployed_models
        WHERE is_active = true
        ORDER BY deployed_at DESC
        LIMIT 1
    """)).fetchone()

    return {
        "period_days": days,
        "total_conversations": total_conversations[0] if total_conversations else 0,
        "avg_confidence": round(intent_stats[1] * 100, 2) if intent_stats and intent_stats[1] else 0,
        "total_intents_detected": intent_stats[0] if intent_stats else 0,
        "total_entities_detected": entity_stats[0] if entity_stats else 0,
        "pending_reviews": active_conversations[0] if active_conversations else 0,
        "top_intents": [
            {"intent": row[0], "count": row[1]}
            for row in top_intents
        ] if top_intents else [],
        "current_model": {
            "name": current_model[0] if current_model else "N/A",
            "trained_at": current_model[1].isoformat() if current_model and current_model[1] else None,
            "accuracy": current_model[2].get('accuracy', 0) * 100 if current_model and current_model[2] and isinstance(current_model[2], dict) else 0
        } if current_model else None
    }


def get_conversations_timeline(db: Session, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get conversation count by day

    Args:
        db: Database session
        days: Number of days

    Returns:
        list: Timeline data
    """
    now_guatemala = datetime.now(GUATEMALA_TZ)
    since_date = (now_guatemala - timedelta(days=days)).replace(tzinfo=None)

    result = db.execute(text("""
        SELECT
            DATE(created_at) as date,
            COUNT(DISTINCT sender_id) as conversations
        FROM rasa_conversations
        WHERE created_at >= :since_date
        GROUP BY DATE(created_at)
        ORDER BY date
    """), {"since_date": since_date}).fetchall()

    return [
        {
            "date": row[0].isoformat(),
            "conversations": row[1]
        }
        for row in result
    ]


def get_intent_distribution(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get distribution of intents

    Args:
        db: Database session
        days: Number of days

    Returns:
        list: Intent distribution
    """
    now_guatemala = datetime.now(GUATEMALA_TZ)
    since_date = now_guatemala - timedelta(days=days)
    since_timestamp = since_date.timestamp()

    result = db.execute(text("""
        SELECT
            intent_name,
            COUNT(*) as count,
            AVG(CAST(data::jsonb->'parse_data'->'intent'->>'confidence' AS FLOAT)) as avg_confidence
        FROM events
        WHERE type_name = 'user'
        AND timestamp >= :since_timestamp
        AND intent_name IS NOT NULL
        GROUP BY intent_name
        ORDER BY count DESC
        LIMIT 10
    """), {"since_timestamp": since_timestamp}).fetchall()

    return [
        {
            "intent": row[0],
            "count": row[1],
            "avg_confidence": round(row[2] * 100, 2) if row[2] else 0
        }
        for row in result
    ]


def get_hourly_heatmap(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get conversation count by hour of day and day of week

    Args:
        db: Database session
        days: Number of days

    Returns:
        list: Heatmap data
    """
    now_guatemala = datetime.now(GUATEMALA_TZ)
    since_date = (now_guatemala - timedelta(days=days)).replace(tzinfo=None)

    result = db.execute(text("""
        SELECT
            EXTRACT(DOW FROM created_at) as day_of_week,
            EXTRACT(HOUR FROM created_at) as hour,
            COUNT(*) as count
        FROM rasa_conversations
        WHERE created_at >= :since_date
        GROUP BY day_of_week, hour
        ORDER BY day_of_week, hour
    """), {"since_date": since_date}).fetchall()

    # Map day of week to names
    day_names = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

    return [
        {
            "day": day_names[int(row[0])],
            "hour": int(row[1]),
            "count": row[2]
        }
        for row in result
    ]


def get_success_rate_funnel(db: Session, days: int = 7) -> Dict[str, Any]:
    """
    Get conversation success rate funnel

    Args:
        db: Database session
        days: Number of days

    Returns:
        dict: Funnel data
    """
    now_guatemala = datetime.now(GUATEMALA_TZ)
    since_date = now_guatemala - timedelta(days=days)
    since_date_naive = since_date.replace(tzinfo=None)
    since_timestamp = since_date.timestamp()

    # Total conversations started
    total = db.execute(text("""
        SELECT COUNT(DISTINCT sender_id)
        FROM rasa_conversations
        WHERE created_at >= :since_date
    """), {"since_date": since_date_naive}).fetchone()

    # Conversations with high confidence (>0.7)
    high_confidence = db.execute(text("""
        SELECT COUNT(DISTINCT e.sender_id)
        FROM events e
        WHERE e.type_name = 'user'
        AND e.timestamp >= :since_timestamp
        AND CAST(e.data::jsonb->'parse_data'->'intent'->>'confidence' AS FLOAT) > 0.7
    """), {"since_timestamp": since_timestamp}).fetchone()

    # Active conversations (using existing schema)
    resolved = db.execute(text("""
        SELECT COUNT(DISTINCT sender_id)
        FROM rasa_conversations
        WHERE created_at >= :since_date
        AND active = true
    """), {"since_date": since_date_naive}).fetchone()

    total_count = total[0] if total else 1  # Avoid division by zero

    return {
        "total_started": total[0] if total else 0,
        "high_confidence": high_confidence[0] if high_confidence else 0,
        "resolved": resolved[0] if resolved else 0,
        "conversion_rate": round((resolved[0] / total_count * 100) if resolved and total_count > 0 else 0, 2)
    }

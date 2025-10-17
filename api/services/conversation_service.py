"""
Conversation service for managing and retrieving conversation data
"""
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import math
import pytz

# Timezone de Guatemala
GUATEMALA_TZ = pytz.timezone('America/Guatemala')


def get_conversations_list(
    db: Session,
    page: int = 1,
    limit: int = 50,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    intents: Optional[str] = None,
    confidence_min: Optional[float] = None,
    confidence_max: Optional[float] = None,
    sender_id: Optional[str] = None,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get paginated list of conversations with filters

    Args:
        db: Database session
        page: Page number (1-indexed)
        limit: Items per page
        date_from: Start date (ISO format)
        date_to: End date (ISO format)
        intents: Comma-separated list of intents to filter
        confidence_min: Minimum confidence score (0-1)
        confidence_max: Maximum confidence score (0-1)
        sender_id: Filter by specific sender_id
        search: Text search in messages

    Returns:
        dict: Paginated conversation list with metadata
    """
    # Calculate offset
    offset = (page - 1) * limit

    # Build WHERE clauses
    where_clauses = []
    params = {}

    if date_from:
        where_clauses.append("rc.updated_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("rc.updated_at <= :date_to")
        params["date_to"] = f"{date_to} 23:59:59"  # Include full day

    if sender_id:
        where_clauses.append("rc.sender_id = :sender_id")
        params["sender_id"] = sender_id

    # Build WHERE string
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Base query for conversation summaries with aggregated data
    base_query = f"""
        WITH conversation_stats AS (
            SELECT
                e.sender_id,
                COUNT(*) as msg_count,
                MAX(e.timestamp) as last_timestamp,
                AVG(CASE
                    WHEN e.data::jsonb->'parse_data'->'intent'->>'confidence' IS NOT NULL
                    THEN CAST(e.data::jsonb->'parse_data'->'intent'->>'confidence' AS FLOAT)
                    ELSE NULL
                END) as avg_conf,
                MODE() WITHIN GROUP (ORDER BY e.intent_name) as primary_intent,
                MAX(CASE
                    WHEN e.type_name = 'user'
                    THEN e.data::jsonb->'parse_data'->>'text'
                    ELSE NULL
                END) as last_user_msg
            FROM events e
            WHERE e.type_name = 'user'
            GROUP BY e.sender_id
        )
        SELECT
            rc.sender_id,
            rc.created_at,
            rc.updated_at,
            rc.customer_id,
            rc.active,
            COALESCE(cs.msg_count, 0) as message_count,
            cs.primary_intent,
            cs.avg_conf as avg_confidence,
            cs.last_user_msg as last_message,
            FALSE as is_flagged
        FROM rasa_conversations rc
        LEFT JOIN conversation_stats cs ON rc.sender_id = cs.sender_id
        {where_sql}
    """

    # Additional filters that require data from the CTE
    # These need to be added to WHERE clause, not HAVING (since there's no GROUP BY in outer query)
    additional_where = []

    if intents:
        intent_list = [i.strip() for i in intents.split(",")]
        intent_placeholders = ", ".join([f":intent_{i}" for i in range(len(intent_list))])
        additional_where.append(f"cs.primary_intent IN ({intent_placeholders})")
        for i, intent in enumerate(intent_list):
            params[f"intent_{i}"] = intent

    if confidence_min is not None:
        additional_where.append("cs.avg_conf >= :confidence_min")
        params["confidence_min"] = confidence_min

    if confidence_max is not None:
        additional_where.append("cs.avg_conf <= :confidence_max")
        params["confidence_max"] = confidence_max

    if search:
        # Text search in messages (simplified - full text search would be better)
        additional_where.append("cs.last_user_msg ILIKE :search")
        params["search"] = f"%{search}%"

    # Add additional WHERE conditions if needed
    if additional_where:
        if where_sql:
            base_query += " AND " + " AND ".join(additional_where)
        else:
            base_query += " WHERE " + " AND ".join(additional_where)

    # Count total matching records
    count_query = f"SELECT COUNT(*) FROM ({base_query}) as filtered"
    total_result = db.execute(text(count_query), params).fetchone()
    total = total_result[0] if total_result else 0

    # Calculate pages
    pages = math.ceil(total / limit) if total > 0 else 1

    # Get paginated results
    paginated_query = f"""
        {base_query}
        ORDER BY rc.updated_at DESC
        LIMIT :limit OFFSET :offset
    """
    params["limit"] = limit
    params["offset"] = offset

    results = db.execute(text(paginated_query), params).fetchall()

    # Format results
    items = []
    for row in results:
        items.append({
            "sender_id": row[0],
            "created_at": row[1].isoformat() if row[1] else None,
            "updated_at": row[2].isoformat() if row[2] else None,
            "message_count": row[5] or 0,
            "primary_intent": row[6],
            "avg_confidence": round(row[7] * 100, 2) if row[7] else 0,
            "last_message": row[8][:100] if row[8] else None,  # Truncate to 100 chars
            "is_flagged": row[9] or False,
            "active": row[4] or True
        })

    return {
        "total": total,
        "page": page,
        "pages": pages,
        "limit": limit,
        "items": items
    }


def get_conversation_detail(db: Session, sender_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed view of a single conversation with all messages

    Args:
        db: Database session
        sender_id: Sender ID to retrieve

    Returns:
        dict: Detailed conversation data or None if not found
    """
    # Check if conversation exists
    conversation = db.execute(text("""
        SELECT sender_id, created_at, updated_at, customer_id, active
        FROM rasa_conversations
        WHERE sender_id = :sender_id
    """), {"sender_id": sender_id}).fetchone()

    if not conversation:
        return None

    # Get all events for this conversation
    events = db.execute(text("""
        SELECT
            id,
            type_name,
            timestamp,
            intent_name,
            action_name,
            data
        FROM events
        WHERE sender_id = :sender_id
        ORDER BY timestamp ASC
    """), {"sender_id": sender_id}).fetchall()

    # Parse messages
    messages = []
    intents_set = set()
    confidence_scores = []

    for event in events:
        event_type = event[1]
        timestamp = event[2]
        intent_name = event[3]
        action_name = event[4]
        data_str = event[5]

        # Parse JSON data
        try:
            data = json.loads(data_str) if data_str else {}
        except:
            data = {}

        # Process user messages
        if event_type == "user":
            parse_data = data.get("parse_data", {})
            user_text = parse_data.get("text", "")
            intent_data = parse_data.get("intent", {})
            intent = intent_data.get("name", intent_name)
            confidence = intent_data.get("confidence", 0)
            entities = parse_data.get("entities", [])

            if intent:
                intents_set.add(intent)
            if confidence:
                confidence_scores.append(confidence)

            messages.append({
                "timestamp": timestamp,
                "type": "user",
                "text": user_text,
                "intent": intent,
                "confidence": confidence,
                "entities": entities,
                "action": None
            })

        # Process bot messages
        elif event_type == "bot":
            bot_text = data.get("text", "")
            messages.append({
                "timestamp": timestamp,
                "type": "bot",
                "text": bot_text,
                "intent": None,
                "confidence": None,
                "entities": [],
                "action": action_name
            })

        # Skip other event types (session_started, action, etc.)

    # Calculate average confidence
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

    return {
        "sender_id": conversation[0],
        "created_at": conversation[1].isoformat() if conversation[1] else None,
        "updated_at": conversation[2].isoformat() if conversation[2] else None,
        "customer_id": conversation[3],
        "active": conversation[4],
        "messages": messages,
        "total_messages": len(messages),
        "unique_intents": list(intents_set),
        "avg_confidence": round(avg_confidence * 100, 2),
        "is_flagged": False  # TODO: Add flagging functionality
    }


def flag_conversation(
    db: Session,
    sender_id: str,
    reason: Optional[str] = None,
    priority: str = "normal"
) -> Dict[str, Any]:
    """
    Flag a conversation for review

    Args:
        db: Database session
        sender_id: Sender ID to flag
        reason: Reason for flagging
        priority: Priority level (low, normal, high)

    Returns:
        dict: Result of flagging operation
    """
    # Check if conversation exists
    conversation = db.execute(text("""
        SELECT sender_id FROM rasa_conversations WHERE sender_id = :sender_id
    """), {"sender_id": sender_id}).fetchone()

    if not conversation:
        raise ValueError(f"Conversation not found: {sender_id}")

    # Mark conversation for review using conversation_reviews table
    # Note: conversation_reviews table schema:
    # - conversation_id (VARCHAR sender_id, UNIQUE, NOT NULL)
    # - reviewed_by (INTEGER FK to platform_users)
    # - reviewed_at (TIMESTAMP)
    # - status (VARCHAR: 'reviewed', 'needs_work', 'escalated')
    # - notes (TEXT)
    # - has_issues, issue_count, conversation_start, message_count

    now_guatemala = datetime.now(GUATEMALA_TZ).replace(tzinfo=None)

    # Use 'needs_work' status to indicate conversation is flagged for review
    db.execute(text("""
        INSERT INTO conversation_reviews (
            conversation_id,
            status,
            notes,
            reviewed_at,
            has_issues
        )
        VALUES (
            :sender_id,
            'needs_work',
            :reason,
            :reviewed_at,
            true
        )
        ON CONFLICT (conversation_id) DO UPDATE
        SET
            status = 'needs_work',
            notes = CASE
                WHEN conversation_reviews.notes IS NOT NULL
                THEN conversation_reviews.notes || E'\\n---\\n' || :reason
                ELSE :reason
            END,
            reviewed_at = :reviewed_at,
            has_issues = true,
            issue_count = conversation_reviews.issue_count + 1
    """), {
        "sender_id": sender_id,
        "reason": reason or "Marcado desde UI",
        "reviewed_at": now_guatemala
    })

    db.commit()

    return {
        "success": True,
        "message": "Conversation flagged for review",
        "sender_id": sender_id,
        "flagged_at": now_guatemala.isoformat()
    }


def get_available_intents(db: Session) -> List[str]:
    """
    Get list of all unique intents in the system

    Args:
        db: Database session

    Returns:
        list: List of intent names
    """
    result = db.execute(text("""
        SELECT DISTINCT intent_name
        FROM events
        WHERE intent_name IS NOT NULL
        AND type_name = 'user'
        ORDER BY intent_name
    """)).fetchall()

    return [row[0] for row in result if row[0]]


def export_conversations_csv(
    db: Session,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    intents: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Export conversations to CSV format (returns data, actual CSV generation in router)

    Args:
        db: Database session
        date_from: Start date filter
        date_to: End date filter
        intents: Comma-separated intent filter

    Returns:
        list: Conversation data for CSV export
    """
    # Build WHERE clauses
    where_clauses = []
    params = {}

    if date_from:
        where_clauses.append("rc.updated_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("rc.updated_at <= :date_to")
        params["date_to"] = f"{date_to} 23:59:59"

    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Query for export (no pagination, but limited to reasonable size)
    query = f"""
        WITH conversation_stats AS (
            SELECT
                e.sender_id,
                COUNT(*) as msg_count,
                AVG(CASE
                    WHEN e.data::jsonb->'parse_data'->'intent'->>'confidence' IS NOT NULL
                    THEN CAST(e.data::jsonb->'parse_data'->'intent'->>'confidence' AS FLOAT)
                    ELSE NULL
                END) as avg_conf,
                MODE() WITHIN GROUP (ORDER BY e.intent_name) as primary_intent
            FROM events e
            WHERE e.type_name = 'user'
            GROUP BY e.sender_id
        )
        SELECT
            rc.sender_id,
            rc.created_at,
            COALESCE(cs.msg_count, 0) as message_count,
            cs.primary_intent,
            cs.avg_conf as avg_confidence,
            rc.active
        FROM rasa_conversations rc
        LEFT JOIN conversation_stats cs ON rc.sender_id = cs.sender_id
        {where_sql}
        ORDER BY rc.updated_at DESC
        LIMIT 10000
    """

    results = db.execute(text(query), params).fetchall()

    # Format for CSV
    export_data = []
    for row in results:
        export_data.append({
            "sender_id": row[0],
            "created_at": row[1].isoformat() if row[1] else "",
            "message_count": row[2] or 0,
            "primary_intent": row[3] or "",
            "avg_confidence": round(row[4] * 100, 2) if row[4] else 0,
            "active": row[5] or False
        })

    return export_data

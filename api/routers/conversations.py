"""
Conversations endpoints for viewing and managing conversation history
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from api.database.connection import get_db
from api.dependencies import get_current_user
from api.schemas.db_models import PlatformUser
from api.services.conversation_service import (
    get_conversations_list,
    get_conversation_detail,
    flag_conversation,
    get_available_intents,
    export_conversations_csv
)
from api.models.conversations import (
    ConversationList,
    ConversationDetail,
    ConversationFlagRequest,
    ConversationFlagResponse
)
from typing import Optional, List
import csv
import io

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@router.get("", response_model=ConversationList)
def list_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Items per page"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    intents: Optional[str] = Query(None, description="Comma-separated list of intents"),
    confidence_min: Optional[float] = Query(None, ge=0, le=1, description="Minimum confidence (0-1)"),
    confidence_max: Optional[float] = Query(None, ge=0, le=1, description="Maximum confidence (0-1)"),
    sender_id: Optional[str] = Query(None, description="Filter by sender ID"),
    search: Optional[str] = Query(None, description="Text search in messages"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get paginated list of conversations with filters

    Returns a paginated list of conversation summaries with the following filters:
    - **date_from/date_to**: Filter by date range
    - **intents**: Filter by comma-separated intent names
    - **confidence_min/max**: Filter by confidence score range
    - **sender_id**: Filter by specific user
    - **search**: Search text in messages
    - **page/limit**: Pagination controls
    """
    try:
        result = get_conversations_list(
            db=db,
            page=page,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
            intents=intents,
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            sender_id=sender_id,
            search=search
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")


@router.get("/intents", response_model=List[str])
def list_available_intents(
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get list of all available intents in the system

    Returns a sorted list of unique intent names from all conversations.
    Useful for populating filter dropdowns in the UI.
    """
    try:
        return get_available_intents(db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving intents: {str(e)}")


@router.get("/{sender_id}", response_model=ConversationDetail)
def get_conversation(
    sender_id: str,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get detailed view of a single conversation

    Returns full conversation history including:
    - All messages (user and bot)
    - Intent and entity information
    - Confidence scores
    - Timestamps
    """
    try:
        conversation = get_conversation_detail(db, sender_id)

        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation not found: {sender_id}")

        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving conversation: {str(e)}")


@router.post("/{sender_id}/flag", response_model=ConversationFlagResponse)
def flag_conversation_for_review(
    sender_id: str,
    flag_data: ConversationFlagRequest,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Flag a conversation for manual review

    Marks a conversation for QA review with an optional reason and priority level.
    Requires at least qa_analyst role (level 3).
    """
    # Check permission (qa_analyst or higher)
    role_levels = {
        "viewer": 1,
        "developer": 2,
        "qa_analyst": 3,
        "qa_lead": 4,
        "admin": 5
    }

    user_level = role_levels.get(current_user.role, 0)
    if user_level < 3:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Requires qa_analyst role or higher."
        )

    try:
        result = flag_conversation(
            db=db,
            sender_id=sender_id,
            reason=flag_data.reason,
            priority=flag_data.priority
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error flagging conversation: {str(e)}")


@router.get("/export/csv")
def export_conversations(
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    intents: Optional[str] = Query(None, description="Comma-separated list of intents"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Export conversations to CSV

    Returns a CSV file with conversation data filtered by date and intent.
    Limited to 10,000 records for performance.
    """
    try:
        # Get data for export
        data = export_conversations_csv(
            db=db,
            date_from=date_from,
            date_to=date_to,
            intents=intents
        )

        # Create CSV in memory
        output = io.StringIO()
        if data:
            fieldnames = ["sender_id", "created_at", "message_count", "primary_intent", "avg_confidence", "active"]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        # Prepare response
        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=conversations_export_{date_from or 'all'}_{date_to or 'all'}.csv"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting conversations: {str(e)}")

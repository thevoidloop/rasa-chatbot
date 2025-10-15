"""
Annotations Router

REST API endpoints for managing annotations (intent/entity corrections).
Implements CRUD operations and approval workflow for QA team.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import math

from api.database.connection import get_db
from api.dependencies import get_current_user
from api.schemas.db_models import PlatformUser
from api.services import annotation_service
from api.models.annotations import (
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationResponse,
    AnnotationListResponse,
    AnnotationApprovalRequest,
    AnnotationStats,
    AnnotationFilters
)


router = APIRouter(prefix="/api/v1/annotations", tags=["Annotations"])


# ============================================
# Helper Functions
# ============================================

def _check_role_permission(user: PlatformUser, min_role: str) -> None:
    """
    Check if user has required role level.

    Args:
        user: Current user
        min_role: Minimum required role

    Raises:
        HTTPException: 403 if user doesn't have permission
    """
    role_levels = {
        "viewer": 1,
        "developer": 2,
        "qa_analyst": 3,
        "qa_lead": 4,
        "admin": 5
    }

    user_level = role_levels.get(user.role, 0)
    min_level = role_levels.get(min_role, 999)

    if user_level < min_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Requires {min_role} role or higher."
        )


# ============================================
# Endpoints
# ============================================

@router.post("", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
def create_annotation(
    annotation: AnnotationCreate,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Create a new annotation.

    Allows qa_analyst, qa_lead, or admin to annotate a conversation message.
    The annotation starts in 'pending' status and requires approval from qa_lead.

    **Required role:** qa_analyst (level 3) or higher

    **Request body:**
    - **conversation_id**: Sender ID of the conversation
    - **message_text**: Original message text from user
    - **corrected_intent**: Corrected intent name (optional if correcting entities only)
    - **corrected_entities**: List of corrected entities (optional if correcting intent only)
    - **annotation_type**: 'intent', 'entity', or 'both'
    - **notes**: Optional notes from annotator

    **Returns:** Created annotation with status 'pending'
    """
    # Check permission
    _check_role_permission(current_user, "qa_analyst")

    try:
        result = annotation_service.create_annotation(
            db=db,
            annotation=annotation,
            user_id=current_user.id,
            username=current_user.username
        )

        # Manually attach username for response
        result.annotated_by_username = current_user.username
        result.approved_by_username = None
        result.reviewed_by_username = None

        return result

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating annotation: {str(e)}"
        )


@router.get("", response_model=AnnotationListResponse)
def list_annotations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(25, ge=1, le=200, description="Items per page"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    conversation_id: Optional[str] = Query(None, description="Filter by conversation ID"),
    intent: Optional[str] = Query(None, description="Filter by corrected intent"),
    annotated_by: Optional[int] = Query(None, description="Filter by annotator user ID"),
    approved_by: Optional[int] = Query(None, description="Filter by approver user ID"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get paginated list of annotations with filters.

    Returns a paginated list of annotations with optional filtering by:
    - **status**: pending, approved, rejected, trained, deployed
    - **conversation_id**: Specific conversation
    - **intent**: Corrected intent name
    - **annotated_by**: User who created the annotation
    - **approved_by**: User who approved/rejected the annotation

    **Required role:** viewer (level 1) or higher

    **Returns:** Paginated list of annotations with total count
    """
    try:
        filters = AnnotationFilters(
            page=page,
            page_size=page_size,
            status=status_filter,
            conversation_id=conversation_id,
            intent=intent,
            annotated_by=annotated_by,
            approved_by=approved_by
        )

        annotations, total = annotation_service.get_annotations(
            db=db,
            filters=filters,
            user_role=current_user.role
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return AnnotationListResponse(
            items=annotations,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving annotations: {str(e)}"
        )


@router.get("/stats", response_model=AnnotationStats)
def get_annotation_statistics(
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get statistics about annotations.

    Returns counts for each status and approval rate.
    Useful for dashboard metrics.

    **Required role:** viewer (level 1) or higher

    **Returns:**
    - **total**: Total number of annotations
    - **pending**: Annotations awaiting approval
    - **approved**: Approved annotations
    - **rejected**: Rejected annotations
    - **trained**: Annotations included in training
    - **deployed**: Annotations in deployed model
    - **approval_rate**: Percentage of approved annotations (0-100)
    """
    try:
        stats = annotation_service.get_annotation_stats(db)
        return AnnotationStats(**stats)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving annotation statistics: {str(e)}"
        )


@router.get("/{annotation_id}", response_model=AnnotationResponse)
def get_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get annotation by ID.

    Returns detailed information about a specific annotation.

    **Required role:** viewer (level 1) or higher

    **Returns:** Annotation with full details including usernames
    """
    try:
        annotation = annotation_service.get_annotation_by_id(
            db=db,
            annotation_id=annotation_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        return annotation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving annotation: {str(e)}"
        )


@router.put("/{annotation_id}", response_model=AnnotationResponse)
def update_annotation(
    annotation_id: int,
    annotation_update: AnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Update an existing annotation.

    Only the creator or admin can update. Only allowed when status is 'pending' or 'rejected'.

    **Required role:** qa_analyst (level 3) or higher (and must be creator or admin)

    **Request body:** All fields optional, only provided fields will be updated

    **Returns:** Updated annotation
    """
    # Permission check is done in service layer
    try:
        annotation = annotation_service.update_annotation(
            db=db,
            annotation_id=annotation_id,
            annotation_update=annotation_update,
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role
        )

        # Fetch full annotation with usernames
        annotation = annotation_service.get_annotation_by_id(
            db=db,
            annotation_id=annotation_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        return annotation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating annotation: {str(e)}"
        )


@router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Delete an annotation.

    Only the creator or admin can delete. Only allowed when status is 'pending'.

    **Required role:** qa_analyst (level 3) or higher (and must be creator or admin)

    **Returns:** 204 No Content on success
    """
    # Permission check is done in service layer
    try:
        annotation_service.delete_annotation(
            db=db,
            annotation_id=annotation_id,
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role
        )

        return None

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting annotation: {str(e)}"
        )


@router.post("/{annotation_id}/approve", response_model=AnnotationResponse)
def approve_annotation(
    annotation_id: int,
    approval: AnnotationApprovalRequest,
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Approve or reject an annotation.

    Only qa_lead or admin can approve/reject annotations.
    Changes status to 'approved' or 'rejected'.

    **Required role:** qa_lead (level 4) or admin (level 5)

    **Request body:**
    - **approved**: True to approve, False to reject
    - **rejection_reason**: Required when rejecting

    **Returns:** Updated annotation with new status and approver information
    """
    # Check permission
    _check_role_permission(current_user, "qa_lead")

    try:
        annotation = annotation_service.approve_annotation(
            db=db,
            annotation_id=annotation_id,
            approval=approval,
            user_id=current_user.id,
            username=current_user.username,
            user_role=current_user.role
        )

        # Fetch full annotation with usernames
        annotation = annotation_service.get_annotation_by_id(
            db=db,
            annotation_id=annotation_id,
            user_id=current_user.id,
            user_role=current_user.role
        )

        return annotation

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving/rejecting annotation: {str(e)}"
        )

"""
Annotation Service

Business logic for handling annotations (intent/entity corrections).
Implements CRUD operations and approval workflow for QA team.
"""

from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from fastapi import HTTPException, status

from api.schemas.db_models import Annotation, PlatformUser
from api.models.annotations import (
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationApprovalRequest,
    AnnotationFilters
)
from api.services.auth_service import log_activity


# ============================================
# Helper Functions
# ============================================

def _check_annotation_exists(db: Session, annotation_id: int) -> Annotation:
    """
    Check if annotation exists, raise 404 if not found.

    Args:
        db: Database session
        annotation_id: Annotation ID

    Returns:
        Annotation object

    Raises:
        HTTPException: 404 if annotation not found
    """
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Annotation with id {annotation_id} not found"
        )
    return annotation


def _check_user_permissions(
    annotation: Annotation,
    user_id: int,
    user_role: str,
    operation: str
) -> None:
    """
    Check if user has permission to perform operation on annotation.

    Args:
        annotation: Annotation object
        user_id: Current user ID
        user_role: Current user role
        operation: Operation type ('update', 'delete', 'approve')

    Raises:
        HTTPException: 403 if user doesn't have permission
    """
    # Admins can do anything
    if user_role == 'admin':
        return

    if operation in ['update', 'delete']:
        # Only creator or admin can update/delete
        if annotation.annotated_by != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the annotation creator or admin can perform this operation"
            )

        # Can only update/delete if status is pending or rejected
        if annotation.status not in ['pending', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot {operation} annotation with status '{annotation.status}'"
            )

    elif operation == 'approve':
        # Only qa_lead or admin can approve
        if user_role not in ['qa_lead', 'admin']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only QA Lead or Admin can approve/reject annotations"
            )


def _get_user_info(db: Session, user_id: Optional[int]) -> Tuple[Optional[int], Optional[str]]:
    """
    Get user ID and username. Returns (None, None) if user_id is None.

    Args:
        db: Database session
        user_id: User ID (can be None)

    Returns:
        Tuple of (user_id, username)
    """
    if user_id is None:
        return None, None

    user = db.query(PlatformUser).filter(PlatformUser.id == user_id).first()
    if user:
        return user.id, user.username
    return user_id, None


# ============================================
# CRUD Operations
# ============================================

def create_annotation(
    db: Session,
    annotation: AnnotationCreate,
    user_id: int,
    username: str
) -> Annotation:
    """
    Create a new annotation.

    Args:
        db: Database session
        annotation: Annotation data
        user_id: ID of user creating annotation
        username: Username of creator

    Returns:
        Created annotation object
    """
    # Convert entity models to dicts for JSON storage
    original_entities_data = [entity.model_dump() for entity in annotation.original_entities]
    corrected_entities_data = [entity.model_dump() for entity in annotation.corrected_entities]

    db_annotation = Annotation(
        conversation_id=annotation.conversation_id,
        message_text=annotation.message_text,
        message_timestamp=annotation.message_timestamp,
        original_intent=annotation.original_intent,
        corrected_intent=annotation.corrected_intent,
        original_confidence=annotation.original_confidence,
        original_entities=original_entities_data,
        corrected_entities=corrected_entities_data,
        annotation_type=annotation.annotation_type,
        status='pending',  # Always starts as pending
        notes=annotation.notes,
        annotated_by=user_id
    )

    db.add(db_annotation)
    db.commit()
    db.refresh(db_annotation)

    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action="annotation_created",
        entity_type="annotation",
        entity_id=db_annotation.id,
        details={
            "conversation_id": annotation.conversation_id,
            "annotation_type": annotation.annotation_type,
            "corrected_intent": annotation.corrected_intent
        }
    )

    return db_annotation


def get_annotations(
    db: Session,
    filters: AnnotationFilters,
    user_role: str
) -> Tuple[List[Annotation], int]:
    """
    Get paginated list of annotations with filters.

    Args:
        db: Database session
        filters: Filter parameters
        user_role: Current user role (for access control)

    Returns:
        Tuple of (list of annotations, total count)
    """
    # Base query with joins for usernames
    query = db.query(
        Annotation,
        PlatformUser.username.label('annotated_by_username')
    ).outerjoin(
        PlatformUser,
        Annotation.annotated_by == PlatformUser.id
    )

    # Apply filters
    if filters.status:
        query = query.filter(Annotation.status == filters.status)

    if filters.conversation_id:
        query = query.filter(Annotation.conversation_id == filters.conversation_id)

    if filters.intent:
        query = query.filter(Annotation.corrected_intent == filters.intent)

    if filters.annotated_by:
        query = query.filter(Annotation.annotated_by == filters.annotated_by)

    if filters.approved_by:
        query = query.filter(Annotation.approved_by == filters.approved_by)

    # Get total count before pagination
    total = query.count()

    # Apply ordering (newest first)
    query = query.order_by(Annotation.annotated_at.desc())

    # Apply pagination
    offset = (filters.page - 1) * filters.page_size
    query = query.offset(offset).limit(filters.page_size)

    # Execute query
    results = query.all()

    # Build annotation objects with joined data
    annotations = []
    for annotation, annotated_by_username in results:
        # Attach username as attribute (will be used in response)
        annotation.annotated_by_username = annotated_by_username

        # Get approver username if exists
        if annotation.approved_by:
            approver = db.query(PlatformUser).filter(PlatformUser.id == annotation.approved_by).first()
            annotation.approved_by_username = approver.username if approver else None
        else:
            annotation.approved_by_username = None

        # Get reviewer username if exists
        if annotation.reviewed_by:
            reviewer = db.query(PlatformUser).filter(PlatformUser.id == annotation.reviewed_by).first()
            annotation.reviewed_by_username = reviewer.username if reviewer else None
        else:
            annotation.reviewed_by_username = None

        annotations.append(annotation)

    return annotations, total


def get_annotation_by_id(
    db: Session,
    annotation_id: int,
    user_id: int,
    user_role: str
) -> Annotation:
    """
    Get annotation by ID with permission check.

    Args:
        db: Database session
        annotation_id: Annotation ID
        user_id: Current user ID
        user_role: Current user role

    Returns:
        Annotation object with joined usernames

    Raises:
        HTTPException: 404 if not found, 403 if no permission
    """
    annotation = _check_annotation_exists(db, annotation_id)

    # Viewers and developers can see all annotations
    # (no additional permission check needed for read operations)

    # Attach usernames
    if annotation.annotated_by:
        annotator = db.query(PlatformUser).filter(PlatformUser.id == annotation.annotated_by).first()
        annotation.annotated_by_username = annotator.username if annotator else None
    else:
        annotation.annotated_by_username = None

    if annotation.approved_by:
        approver = db.query(PlatformUser).filter(PlatformUser.id == annotation.approved_by).first()
        annotation.approved_by_username = approver.username if approver else None
    else:
        annotation.approved_by_username = None

    if annotation.reviewed_by:
        reviewer = db.query(PlatformUser).filter(PlatformUser.id == annotation.reviewed_by).first()
        annotation.reviewed_by_username = reviewer.username if reviewer else None
    else:
        annotation.reviewed_by_username = None

    return annotation


def update_annotation(
    db: Session,
    annotation_id: int,
    annotation_update: AnnotationUpdate,
    user_id: int,
    username: str,
    user_role: str
) -> Annotation:
    """
    Update an existing annotation.

    Only creator or admin can update.
    Only allowed when status is 'pending' or 'rejected'.

    Args:
        db: Database session
        annotation_id: Annotation ID
        annotation_update: Update data
        user_id: Current user ID
        username: Current username
        user_role: Current user role

    Returns:
        Updated annotation object

    Raises:
        HTTPException: 404/403/400 based on validation
    """
    annotation = _check_annotation_exists(db, annotation_id)
    _check_user_permissions(annotation, user_id, user_role, 'update')

    # Apply updates (only non-None fields)
    update_data = annotation_update.model_dump(exclude_unset=True)

    # Convert entity models to dicts if provided
    if 'original_entities' in update_data and update_data['original_entities'] is not None:
        update_data['original_entities'] = [
            entity.model_dump() for entity in annotation_update.original_entities
        ]

    if 'corrected_entities' in update_data and update_data['corrected_entities'] is not None:
        update_data['corrected_entities'] = [
            entity.model_dump() for entity in annotation_update.corrected_entities
        ]

    for field, value in update_data.items():
        setattr(annotation, field, value)

    db.commit()
    db.refresh(annotation)

    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action="annotation_updated",
        entity_type="annotation",
        entity_id=annotation.id,
        details={"updated_fields": list(update_data.keys())}
    )

    return annotation


def delete_annotation(
    db: Session,
    annotation_id: int,
    user_id: int,
    username: str,
    user_role: str
) -> None:
    """
    Delete an annotation.

    Only creator or admin can delete.
    Only allowed when status is 'pending'.

    Args:
        db: Database session
        annotation_id: Annotation ID
        user_id: Current user ID
        username: Current username
        user_role: Current user role

    Raises:
        HTTPException: 404/403/400 based on validation
    """
    annotation = _check_annotation_exists(db, annotation_id)
    _check_user_permissions(annotation, user_id, user_role, 'delete')

    # Store conversation_id for logging
    conversation_id = annotation.conversation_id

    db.delete(annotation)
    db.commit()

    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action="annotation_deleted",
        entity_type="annotation",
        entity_id=annotation_id,
        details={"conversation_id": conversation_id}
    )


def approve_annotation(
    db: Session,
    annotation_id: int,
    approval: AnnotationApprovalRequest,
    user_id: int,
    username: str,
    user_role: str
) -> Annotation:
    """
    Approve or reject an annotation.

    Only qa_lead or admin can approve/reject.
    Changes status to 'approved' or 'rejected'.

    Args:
        db: Database session
        annotation_id: Annotation ID
        approval: Approval decision
        user_id: Current user ID (approver)
        username: Current username
        user_role: Current user role

    Returns:
        Updated annotation object

    Raises:
        HTTPException: 404/403/400 based on validation
    """
    annotation = _check_annotation_exists(db, annotation_id)
    _check_user_permissions(annotation, user_id, user_role, 'approve')

    # Can only approve/reject if status is pending
    if annotation.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve/reject annotation with status '{annotation.status}'"
        )

    # Update annotation
    annotation.status = 'approved' if approval.approved else 'rejected'
    annotation.approved_by = user_id
    annotation.approved_at = datetime.utcnow()
    annotation.rejection_reason = approval.rejection_reason if not approval.approved else None

    db.commit()
    db.refresh(annotation)

    # Log activity
    log_activity(
        db=db,
        user_id=user_id,
        username=username,
        action="annotation_approved" if approval.approved else "annotation_rejected",
        entity_type="annotation",
        entity_id=annotation.id,
        details={
            "conversation_id": annotation.conversation_id,
            "status": annotation.status,
            "rejection_reason": approval.rejection_reason
        }
    )

    return annotation


def get_annotation_stats(db: Session) -> dict:
    """
    Get statistics about annotations for dashboard.

    Args:
        db: Database session

    Returns:
        Dictionary with annotation statistics
    """
    # Count by status
    total = db.query(func.count(Annotation.id)).scalar() or 0
    pending = db.query(func.count(Annotation.id)).filter(Annotation.status == 'pending').scalar() or 0
    approved = db.query(func.count(Annotation.id)).filter(Annotation.status == 'approved').scalar() or 0
    rejected = db.query(func.count(Annotation.id)).filter(Annotation.status == 'rejected').scalar() or 0
    trained = db.query(func.count(Annotation.id)).filter(Annotation.status == 'trained').scalar() or 0
    deployed = db.query(func.count(Annotation.id)).filter(Annotation.status == 'deployed').scalar() or 0

    # Calculate approval rate
    reviewed_count = approved + rejected
    approval_rate = (approved / reviewed_count * 100) if reviewed_count > 0 else 0.0

    return {
        "total": total,
        "pending": pending,
        "approved": approved,
        "rejected": rejected,
        "trained": trained,
        "deployed": deployed,
        "approval_rate": round(approval_rate, 2)
    }


def get_pending_annotations_count(db: Session) -> int:
    """
    Get count of pending annotations for dashboard metric.

    Args:
        db: Database session

    Returns:
        Count of pending annotations
    """
    return db.query(func.count(Annotation.id)).filter(Annotation.status == 'pending').scalar() or 0

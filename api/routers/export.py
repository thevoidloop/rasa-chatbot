"""
Export Router

REST API endpoints for exporting annotations to RASA NLU format.
Provides preview, validation, and download capabilities.
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from api.database.connection import get_db
from api.dependencies import get_current_user
from api.schemas.db_models import PlatformUser
from api.services import export_service
from api.models.export import (
    NLUPreviewResponse,
    NLUExportStats,
    IntentListResponse,
    EntityListResponse,
    NLUExportRequest
)


router = APIRouter(prefix="/api/v1/export", tags=["Export"])


# ============================================
# Helper Functions
# ============================================

def _check_export_permission(user: PlatformUser) -> None:
    """
    Check if user has permission to export (qa_lead or admin).

    Args:
        user: Current user

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
    if user_level < 4:  # qa_lead level
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Requires qa_lead role or higher."
        )


# ============================================
# Endpoints
# ============================================

@router.get("/nlu/preview", response_model=NLUPreviewResponse)
def preview_nlu_export(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    intent_filter: Optional[str] = Query(None, description="Filter by specific intent"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Preview NLU export with validation.

    Returns YAML content, statistics, and validation results without creating a file.
    Allows QA Lead to review before downloading.

    **Required role:** qa_lead (level 4) or admin (level 5)

    **Query parameters:**
    - **from_date**: Start date for filtering (format: YYYY-MM-DD)
    - **to_date**: End date for filtering (format: YYYY-MM-DD)
    - **intent_filter**: Filter by specific intent name

    **Returns:**
    - YAML content preview
    - Statistics (intents, examples, entities)
    - Validation errors and warnings
    - Boolean flags for validity and exportability
    """
    # Check permission
    _check_export_permission(current_user)

    try:
        # Parse dates if provided
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None

        # Get approved annotations
        annotations = export_service.get_approved_annotations(
            db=db,
            from_date=from_date_obj,
            to_date=to_date_obj,
            intent_filter=intent_filter
        )

        if not annotations:
            # Return empty preview
            return NLUPreviewResponse(
                yaml_content="# No approved annotations found for the specified criteria",
                stats=NLUExportStats(
                    total_intents=0,
                    total_examples=0,
                    total_entities_used=0,
                    avg_examples_per_intent=0.0,
                    total_annotations=0
                ),
                validation_errors=[],
                validation_warnings=["No annotations available for export"],
                is_valid=False,
                can_export=False
            )

        # Convert to NLU dictionary
        nlu_dict = export_service.convert_annotations_to_nlu_dict(annotations)

        # Generate YAML
        yaml_content = export_service.convert_to_rasa_nlu_yaml(nlu_dict)

        # Validate YAML format
        is_valid, format_errors, format_warnings = export_service.validate_nlu_yaml(yaml_content)

        # Validate against existing data
        data_errors, data_warnings = export_service.validate_annotations_export(db, nlu_dict)

        # Combine all errors and warnings
        all_errors = format_errors + data_errors
        all_warnings = format_warnings + data_warnings

        # Get statistics
        stats_dict = export_service.get_nlu_export_stats(nlu_dict)
        stats_dict['total_annotations'] = len(annotations)

        stats = NLUExportStats(**stats_dict)

        # Can export if no critical errors (warnings are OK)
        can_export = len(all_errors) == 0

        return NLUPreviewResponse(
            yaml_content=yaml_content,
            stats=stats,
            validation_errors=all_errors,
            validation_warnings=all_warnings,
            is_valid=is_valid,
            can_export=can_export
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating preview: {str(e)}"
        )


@router.get("/nlu/download")
def download_nlu_export(
    from_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    intent_filter: Optional[str] = Query(None, description="Filter by specific intent"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Download NLU export as YAML file.

    Generates and downloads a YAML file with approved annotations in RASA format.
    File can be merged with existing nlu.yml manually.

    **Required role:** qa_lead (level 4) or admin (level 5)

    **Query parameters:**
    - **from_date**: Start date for filtering (format: YYYY-MM-DD)
    - **to_date**: End date for filtering (format: YYYY-MM-DD)
    - **intent_filter**: Filter by specific intent name

    **Returns:** YAML file download (Content-Type: application/x-yaml)
    """
    # Check permission
    _check_export_permission(current_user)

    try:
        # Parse dates if provided
        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d") if from_date else None
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d") if to_date else None

        # Get approved annotations
        annotations = export_service.get_approved_annotations(
            db=db,
            from_date=from_date_obj,
            to_date=to_date_obj,
            intent_filter=intent_filter
        )

        if not annotations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No approved annotations found for the specified criteria"
            )

        # Convert to NLU dictionary
        nlu_dict = export_service.convert_annotations_to_nlu_dict(annotations)

        # Generate YAML
        yaml_content = export_service.convert_to_rasa_nlu_yaml(nlu_dict)

        # Validate before export
        is_valid, errors, _ = export_service.validate_nlu_yaml(yaml_content)

        if not is_valid or errors:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot export invalid YAML. Errors: {', '.join(errors)}"
            )

        # Generate filename
        date_suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nlu_annotations_{date_suffix}.yml"

        # Return as downloadable file
        return Response(
            content=yaml_content,
            media_type="application/x-yaml",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Type": "application/x-yaml; charset=utf-8"
            }
        )

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating export: {str(e)}"
        )


@router.get("/intents", response_model=IntentListResponse)
def list_available_intents(
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get list of available intents from database.

    Returns unique intent names detected in RASA conversations.
    Useful for filtering and autocomplete in UI.

    **Required role:** viewer (level 1) or higher

    **Returns:** List of unique intent names sorted alphabetically
    """
    try:
        intents = export_service.get_existing_intents_from_db(db)

        return IntentListResponse(
            intents=intents,
            total=len(intents),
            source="database"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving intents: {str(e)}"
        )


@router.get("/entities", response_model=EntityListResponse)
def list_available_entities(
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get list of available entity types from database.

    Returns unique entity type names detected in RASA conversations.
    Useful for validation and autocomplete in UI.

    **Required role:** viewer (level 1) or higher

    **Returns:** List of unique entity type names sorted alphabetically
    """
    try:
        entities = export_service.get_existing_entities_from_db(db)

        return EntityListResponse(
            entities=entities,
            total=len(entities),
            source="database"
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving entities: {str(e)}"
        )

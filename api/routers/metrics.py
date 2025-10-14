"""
Metrics endpoints for dashboard
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from api.database.connection import get_db
from api.dependencies import get_current_user
from api.schemas.db_models import PlatformUser
from api.services.metrics_service import (
    get_summary_metrics,
    get_conversations_timeline,
    get_intent_distribution,
    get_hourly_heatmap,
    get_success_rate_funnel
)
from typing import Dict, Any, List

router = APIRouter(prefix="/api/v1/metrics", tags=["Metrics"])


@router.get("/summary", response_model=Dict[str, Any])
def get_summary(
    days: int = Query(7, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get summary metrics for dashboard

    Returns key metrics like total conversations, avg confidence, top intents, etc.
    """
    return get_summary_metrics(db, days)


@router.get("/timeline", response_model=List[Dict[str, Any]])
def get_timeline(
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get conversation count timeline

    Returns daily conversation counts for the specified period.
    """
    return get_conversations_timeline(db, days)


@router.get("/intents", response_model=List[Dict[str, Any]])
def get_intents(
    days: int = Query(7, ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get intent distribution

    Returns intent counts and average confidence scores.
    """
    return get_intent_distribution(db, days)


@router.get("/heatmap", response_model=List[Dict[str, Any]])
def get_heatmap(
    days: int = Query(7, ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get hourly usage heatmap

    Returns conversation counts by day of week and hour.
    """
    return get_hourly_heatmap(db, days)


@router.get("/funnel", response_model=Dict[str, Any])
def get_funnel(
    days: int = Query(7, ge=1, le=365, description="Number of days"),
    db: Session = Depends(get_db),
    current_user: PlatformUser = Depends(get_current_user)
):
    """
    Get conversation success funnel

    Returns funnel data showing conversation progression from start to resolution.
    """
    return get_success_rate_funnel(db, days)

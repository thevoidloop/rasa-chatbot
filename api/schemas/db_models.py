"""
SQLAlchemy Database Models
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, JSON
from sqlalchemy.sql import func
from api.database.connection import Base

class PlatformUser(Base):
    """Platform users table"""
    __tablename__ = "platform_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, index=True)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True))
    created_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"))


class Annotation(Base):
    """Annotations table"""
    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(255), index=True)
    message_text = Column(Text, nullable=False)
    message_timestamp = Column(DateTime(timezone=True))
    
    # Intent annotation
    original_intent = Column(String(100))
    corrected_intent = Column(String(100), index=True)
    original_confidence = Column(Float)
    
    # Entity annotations
    original_entities = Column(JSON, default=[])
    corrected_entities = Column(JSON, default=[])
    
    # Metadata
    annotation_type = Column(String(20))
    status = Column(String(20), default="pending", index=True)
    notes = Column(Text)
    
    # Auditoría
    annotated_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"), index=True)
    annotated_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reviewed_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"))
    reviewed_at = Column(DateTime(timezone=True))
    
    # Training tracking
    included_in_training_job = Column(Integer, ForeignKey("training_jobs.id", ondelete="SET NULL"))


class TrainingJob(Base):
    """Training jobs table"""
    __tablename__ = "training_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_uuid = Column(String(36), unique=True, index=True)
    
    # Status
    status = Column(String(20), default="pending", index=True)
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Model info
    model_name = Column(String(100))
    model_path = Column(Text)
    
    # Training configuration snapshot
    config_snapshot = Column(JSON)
    domain_snapshot = Column(JSON)
    nlu_examples_count = Column(Integer)
    stories_count = Column(Integer)
    
    # Metrics
    metrics = Column(JSON)
    
    # Logs
    logs = Column(Text)
    error_message = Column(Text)
    
    # Cambios incluidos
    annotations_included = Column(Integer, default=0)
    new_examples_added = Column(Integer, default=0)
    
    # Auditoría
    started_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"), index=True)
    
    # Backup info
    backup_path = Column(Text)
    backup_created = Column(Boolean, default=False)


class DeployedModel(Base):
    """Deployed models table"""
    __tablename__ = "deployed_models"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String(100), unique=True, nullable=False)
    model_path = Column(Text, nullable=False)
    
    # Deployment info
    deployed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    deployed_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=False, index=True)
    
    # Relation to training job
    training_job_id = Column(Integer, ForeignKey("training_jobs.id", ondelete="SET NULL"), index=True)
    
    # Rollback capability
    previous_model_id = Column(Integer, ForeignKey("deployed_models.id", ondelete="SET NULL"))
    rollback_enabled = Column(Boolean, default=True)
    
    # Performance metrics
    performance_metrics = Column(JSON, default={})
    
    # Metadata
    version = Column(String(50))
    description = Column(Text)
    tags = Column(JSON, default=[])
    
    # Deactivation info
    deactivated_at = Column(DateTime(timezone=True))
    deactivated_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"))
    deactivation_reason = Column(Text)


class ActivityLog(Base):
    """Activity logs table"""
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"), index=True)
    username = Column(String(50))
    
    # Action details
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(50), index=True)
    entity_id = Column(Integer)
    
    # Details
    details = Column(JSON, default={})
    
    # Request info
    ip_address = Column(String(45))
    user_agent = Column(Text)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Result
    success = Column(Boolean, default=True)
    error_message = Column(Text)


class TestCase(Base):
    """Test cases table"""
    __tablename__ = "test_cases"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100))
    description = Column(Text)
    
    # Test input
    message_text = Column(Text, nullable=False)
    
    # Expected output
    expected_intent = Column(String(100), nullable=False)
    expected_entities = Column(JSON, default=[])
    min_confidence = Column(Float, default=0.7)
    
    # Metadata
    category = Column(String(50), index=True)
    priority = Column(String(20), default="medium", index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # Auditoría
    created_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TestResult(Base):
    """Test results table"""
    __tablename__ = "test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_case_id = Column(Integer, ForeignKey("test_cases.id", ondelete="CASCADE"))
    training_job_id = Column(Integer, ForeignKey("training_jobs.id", ondelete="SET NULL"), index=True)
    
    # Actual output
    actual_intent = Column(String(100))
    actual_entities = Column(JSON, default=[])
    actual_confidence = Column(Float)
    
    # Result
    passed = Column(Boolean, index=True)
    error_message = Column(Text)
    
    # Timing
    executed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    execution_time_ms = Column(Integer)


class ConversationReview(Base):
    """Conversation reviews table"""
    __tablename__ = "conversation_reviews"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Review info
    reviewed_by = Column(Integer, ForeignKey("platform_users.id", ondelete="SET NULL"), index=True)
    reviewed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Status
    status = Column(String(20), index=True)
    notes = Column(Text)
    
    # Issues found
    has_issues = Column(Boolean, default=False)
    issue_count = Column(Integer, default=0)
    
    # Metadata
    conversation_start = Column(DateTime(timezone=True))
    message_count = Column(Integer)

-- ============================================
-- TRAINING PLATFORM - Database Schema
-- ============================================
-- Este script crea las tablas adicionales necesarias para la plataforma de entrenamiento
-- Se ejecuta después de init-db.sql (tablas principales de RASA)
-- ============================================

-- Extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- TABLA: platform_users
-- Descripción: Usuarios de la plataforma de entrenamiento
-- ============================================
CREATE TABLE IF NOT EXISTS platform_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('admin', 'qa_lead', 'qa_analyst', 'developer', 'viewer')),
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    created_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL
);

-- Índices para platform_users
CREATE INDEX idx_platform_users_username ON platform_users(username);
CREATE INDEX idx_platform_users_email ON platform_users(email);
CREATE INDEX idx_platform_users_role ON platform_users(role);
CREATE INDEX idx_platform_users_active ON platform_users(is_active);

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_platform_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_platform_users_updated_at
    BEFORE UPDATE ON platform_users
    FOR EACH ROW
    EXECUTE FUNCTION update_platform_users_updated_at();

-- ============================================
-- TABLA: annotations
-- Descripción: Anotaciones/correcciones de intents y entities
-- ============================================
CREATE TABLE IF NOT EXISTS annotations (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255),  -- sender_id de la conversación
    message_text TEXT NOT NULL,
    message_timestamp TIMESTAMP,

    -- Intent annotation
    original_intent VARCHAR(100),
    corrected_intent VARCHAR(100),
    original_confidence FLOAT,

    -- Entity annotations (JSON array)
    original_entities JSONB DEFAULT '[]'::jsonb,
    corrected_entities JSONB DEFAULT '[]'::jsonb,

    -- Metadata
    annotation_type VARCHAR(20) CHECK (annotation_type IN ('intent', 'entity', 'both')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'trained', 'deployed')),
    notes TEXT,

    -- Auditoría
    annotated_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    annotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,

    -- Training tracking
    included_in_training_job INTEGER,  -- FK a training_jobs (creada después)

    CONSTRAINT check_corrected_intent_or_entities
        CHECK (corrected_intent IS NOT NULL OR corrected_entities != '[]'::jsonb)
);

-- Índices para annotations
CREATE INDEX idx_annotations_conversation_id ON annotations(conversation_id);
CREATE INDEX idx_annotations_status ON annotations(status);
CREATE INDEX idx_annotations_annotated_by ON annotations(annotated_by);
CREATE INDEX idx_annotations_annotated_at ON annotations(annotated_at DESC);
CREATE INDEX idx_annotations_corrected_intent ON annotations(corrected_intent);

-- ============================================
-- TABLA: training_jobs
-- Descripción: Registro de entrenamientos del modelo
-- ============================================
CREATE TABLE IF NOT EXISTS training_jobs (
    id SERIAL PRIMARY KEY,
    job_uuid UUID DEFAULT uuid_generate_v4() UNIQUE,

    -- Status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),

    -- Timing
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    duration_seconds INTEGER,

    -- Model info
    model_name VARCHAR(100),
    model_path TEXT,

    -- Training configuration snapshot
    config_snapshot JSONB,  -- Copia de config.yml
    domain_snapshot JSONB,  -- Copia de domain.yml
    nlu_examples_count INTEGER,
    stories_count INTEGER,

    -- Metrics del modelo entrenado
    metrics JSONB,  -- Accuracy, F1, etc.

    -- Logs
    logs TEXT,
    error_message TEXT,

    -- Cambios incluidos
    annotations_included INTEGER DEFAULT 0,
    new_examples_added INTEGER DEFAULT 0,

    -- Auditoría
    started_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,

    -- Backup info
    backup_path TEXT,
    backup_created BOOLEAN DEFAULT false
);

-- Índices para training_jobs
CREATE INDEX idx_training_jobs_status ON training_jobs(status);
CREATE INDEX idx_training_jobs_started_at ON training_jobs(started_at DESC);
CREATE INDEX idx_training_jobs_started_by ON training_jobs(started_by);
CREATE INDEX idx_training_jobs_job_uuid ON training_jobs(job_uuid);

-- Trigger para calcular duración
CREATE OR REPLACE FUNCTION calculate_training_duration()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.completed_at IS NOT NULL AND NEW.started_at IS NOT NULL THEN
        NEW.duration_seconds = EXTRACT(EPOCH FROM (NEW.completed_at - NEW.started_at))::INTEGER;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_calculate_training_duration
    BEFORE UPDATE ON training_jobs
    FOR EACH ROW
    WHEN (NEW.completed_at IS NOT NULL AND OLD.completed_at IS NULL)
    EXECUTE FUNCTION calculate_training_duration();

-- ============================================
-- TABLA: deployed_models
-- Descripción: Modelos desplegados en producción
-- ============================================
CREATE TABLE IF NOT EXISTS deployed_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) UNIQUE NOT NULL,
    model_path TEXT NOT NULL,

    -- Deployment info
    deployed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deployed_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT false,  -- Solo un modelo activo a la vez

    -- Relation to training job
    training_job_id INTEGER REFERENCES training_jobs(id) ON DELETE SET NULL,

    -- Rollback capability
    previous_model_id INTEGER REFERENCES deployed_models(id) ON DELETE SET NULL,
    rollback_enabled BOOLEAN DEFAULT true,

    -- Performance metrics (actualizado en tiempo real)
    performance_metrics JSONB DEFAULT '{}'::jsonb,

    -- Metadata
    version VARCHAR(50),
    description TEXT,
    tags JSONB DEFAULT '[]'::jsonb,

    -- Deactivation info
    deactivated_at TIMESTAMP,
    deactivated_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    deactivation_reason TEXT
);

-- Índices para deployed_models
CREATE INDEX idx_deployed_models_is_active ON deployed_models(is_active);
CREATE INDEX idx_deployed_models_deployed_at ON deployed_models(deployed_at DESC);
CREATE INDEX idx_deployed_models_training_job_id ON deployed_models(training_job_id);

-- Constraint: Solo un modelo activo a la vez
CREATE UNIQUE INDEX idx_one_active_model
    ON deployed_models(is_active)
    WHERE is_active = true;

-- ============================================
-- TABLA: activity_logs
-- Descripción: Logs de auditoría de actividades
-- ============================================
CREATE TABLE IF NOT EXISTS activity_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    username VARCHAR(50),  -- Denormalizado para histórico

    -- Action details
    action VARCHAR(100) NOT NULL,  -- 'login', 'annotate_intent', 'train_model', etc.
    entity_type VARCHAR(50),       -- 'annotation', 'training_job', 'user', etc.
    entity_id INTEGER,

    -- Details
    details JSONB DEFAULT '{}'::jsonb,

    -- Request info
    ip_address INET,
    user_agent TEXT,

    -- Timing
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Result
    success BOOLEAN DEFAULT true,
    error_message TEXT
);

-- Índices para activity_logs
CREATE INDEX idx_activity_logs_user_id ON activity_logs(user_id);
CREATE INDEX idx_activity_logs_action ON activity_logs(action);
CREATE INDEX idx_activity_logs_timestamp ON activity_logs(timestamp DESC);
CREATE INDEX idx_activity_logs_entity_type ON activity_logs(entity_type);

-- Particionamiento por mes (opcional para producción)
-- CREATE TABLE activity_logs_y2025m03 PARTITION OF activity_logs
--     FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');

-- ============================================
-- TABLA: test_cases
-- Descripción: Casos de prueba para testing del modelo
-- ============================================
CREATE TABLE IF NOT EXISTS test_cases (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    description TEXT,

    -- Test input
    message_text TEXT NOT NULL,

    -- Expected output
    expected_intent VARCHAR(100) NOT NULL,
    expected_entities JSONB DEFAULT '[]'::jsonb,
    min_confidence FLOAT DEFAULT 0.7,

    -- Metadata
    category VARCHAR(50),  -- 'regression', 'new_feature', 'edge_case'
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    is_active BOOLEAN DEFAULT true,

    -- Auditoría
    created_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para test_cases
CREATE INDEX idx_test_cases_is_active ON test_cases(is_active);
CREATE INDEX idx_test_cases_category ON test_cases(category);
CREATE INDEX idx_test_cases_priority ON test_cases(priority);

-- ============================================
-- TABLA: test_results
-- Descripción: Resultados de ejecución de tests
-- ============================================
CREATE TABLE IF NOT EXISTS test_results (
    id SERIAL PRIMARY KEY,
    test_case_id INTEGER REFERENCES test_cases(id) ON DELETE CASCADE,
    training_job_id INTEGER REFERENCES training_jobs(id) ON DELETE SET NULL,

    -- Actual output
    actual_intent VARCHAR(100),
    actual_entities JSONB DEFAULT '[]'::jsonb,
    actual_confidence FLOAT,

    -- Result
    passed BOOLEAN,
    error_message TEXT,

    -- Timing
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER
);

-- Índices para test_results
CREATE INDEX idx_test_results_test_case_id ON test_results(test_case_id);
CREATE INDEX idx_test_results_training_job_id ON test_results(training_job_id);
CREATE INDEX idx_test_results_passed ON test_results(passed);
CREATE INDEX idx_test_results_executed_at ON test_results(executed_at DESC);

-- ============================================
-- TABLA: conversation_reviews
-- Descripción: Marcas de conversaciones revisadas por QA
-- ============================================
CREATE TABLE IF NOT EXISTS conversation_reviews (
    id SERIAL PRIMARY KEY,
    conversation_id VARCHAR(255) UNIQUE NOT NULL,  -- sender_id

    -- Review info
    reviewed_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Status
    status VARCHAR(20) CHECK (status IN ('reviewed', 'needs_work', 'escalated')),
    notes TEXT,

    -- Issues found
    has_issues BOOLEAN DEFAULT false,
    issue_count INTEGER DEFAULT 0,

    -- Metadata
    conversation_start TIMESTAMP,
    message_count INTEGER
);

-- Índices para conversation_reviews
CREATE INDEX idx_conversation_reviews_conversation_id ON conversation_reviews(conversation_id);
CREATE INDEX idx_conversation_reviews_reviewed_by ON conversation_reviews(reviewed_by);
CREATE INDEX idx_conversation_reviews_reviewed_at ON conversation_reviews(reviewed_at DESC);
CREATE INDEX idx_conversation_reviews_status ON conversation_reviews(status);

-- ============================================
-- FOREIGN KEY: Añadir FK de annotations a training_jobs
-- ============================================
ALTER TABLE annotations
    ADD CONSTRAINT fk_annotations_training_job
    FOREIGN KEY (included_in_training_job)
    REFERENCES training_jobs(id)
    ON DELETE SET NULL;

-- ============================================
-- VISTAS ÚTILES
-- ============================================

-- Vista: Anotaciones pendientes de entrenamiento
CREATE OR REPLACE VIEW v_pending_annotations AS
SELECT
    a.id,
    a.conversation_id,
    a.message_text,
    a.corrected_intent,
    a.corrected_entities,
    a.annotation_type,
    a.annotated_at,
    u.username as annotated_by_username
FROM annotations a
LEFT JOIN platform_users u ON a.annotated_by = u.id
WHERE a.status = 'pending'
ORDER BY a.annotated_at DESC;

-- Vista: Últimos entrenamientos
CREATE OR REPLACE VIEW v_recent_trainings AS
SELECT
    t.id,
    t.job_uuid,
    t.status,
    t.started_at,
    t.completed_at,
    t.duration_seconds,
    t.model_name,
    t.annotations_included,
    t.new_examples_added,
    u.username as started_by_username
FROM training_jobs t
LEFT JOIN platform_users u ON t.started_by = u.id
ORDER BY t.started_at DESC
LIMIT 20;

-- Vista: Modelo activo actual
CREATE OR REPLACE VIEW v_active_model AS
SELECT
    d.id,
    d.model_name,
    d.model_path,
    d.deployed_at,
    d.version,
    d.performance_metrics,
    u.username as deployed_by_username,
    t.job_uuid as training_job_uuid
FROM deployed_models d
LEFT JOIN platform_users u ON d.deployed_by = u.id
LEFT JOIN training_jobs t ON d.training_job_id = t.id
WHERE d.is_active = true;

-- Vista: Estadísticas de anotaciones por usuario
CREATE OR REPLACE VIEW v_annotation_stats_by_user AS
SELECT
    u.id as user_id,
    u.username,
    COUNT(a.id) as total_annotations,
    COUNT(CASE WHEN a.status = 'pending' THEN 1 END) as pending_annotations,
    COUNT(CASE WHEN a.status = 'trained' THEN 1 END) as trained_annotations,
    COUNT(CASE WHEN a.status = 'deployed' THEN 1 END) as deployed_annotations,
    MIN(a.annotated_at) as first_annotation,
    MAX(a.annotated_at) as last_annotation
FROM platform_users u
LEFT JOIN annotations a ON u.id = a.annotated_by
WHERE u.is_active = true
GROUP BY u.id, u.username;

-- ============================================
-- FUNCIONES ÚTILES
-- ============================================

-- Función: Obtener count de anotaciones pendientes
CREATE OR REPLACE FUNCTION get_pending_annotations_count()
RETURNS INTEGER AS $$
    SELECT COUNT(*)::INTEGER FROM annotations WHERE status = 'pending';
$$ LANGUAGE SQL;

-- Función: Marcar conversación como revisada
CREATE OR REPLACE FUNCTION mark_conversation_reviewed(
    p_conversation_id VARCHAR(255),
    p_reviewed_by INTEGER,
    p_status VARCHAR(20),
    p_notes TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO conversation_reviews (conversation_id, reviewed_by, status, notes)
    VALUES (p_conversation_id, p_reviewed_by, p_status, p_notes)
    ON CONFLICT (conversation_id)
    DO UPDATE SET
        reviewed_by = EXCLUDED.reviewed_by,
        reviewed_at = CURRENT_TIMESTAMP,
        status = EXCLUDED.status,
        notes = EXCLUDED.notes;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- COMENTARIOS EN TABLAS
-- ============================================
COMMENT ON TABLE platform_users IS 'Usuarios de la plataforma de entrenamiento con roles y permisos';
COMMENT ON TABLE annotations IS 'Correcciones de intents/entities realizadas por equipo QA';
COMMENT ON TABLE training_jobs IS 'Registro de trabajos de entrenamiento del modelo RASA';
COMMENT ON TABLE deployed_models IS 'Modelos desplegados en producción con tracking de versiones';
COMMENT ON TABLE activity_logs IS 'Logs de auditoría de todas las actividades de usuarios';
COMMENT ON TABLE test_cases IS 'Casos de prueba para validación del modelo';
COMMENT ON TABLE test_results IS 'Resultados de ejecución de test cases';
COMMENT ON TABLE conversation_reviews IS 'Seguimiento de conversaciones revisadas por QA';

-- ============================================
-- DATOS INICIALES
-- ============================================
-- Nota: El usuario admin se crea mediante script Python (scripts/create_admin_user.py)
-- para hashear correctamente la contraseña con bcrypt

-- ============================================
-- FIN DEL SCRIPT
-- ============================================

-- ============================================
-- MIGRATION: Add Annotation Approval Workflow
-- ============================================
-- Versión: 05
-- Fecha: 2025-10-14
-- Descripción: Añade campos de aprobación/rechazo a la tabla annotations
--              para soportar workflow QA (qa_analyst → qa_lead)
-- ============================================

-- IMPORTANTE: Este script es para bases de datos EXISTENTES.
-- Las nuevas instalaciones ya incluyen estos campos en init-platform-tables.sql

BEGIN;

-- 1. Añadir nuevos estados al CHECK constraint de status
-- Primero eliminamos el constraint existente
ALTER TABLE annotations
    DROP CONSTRAINT IF EXISTS annotations_status_check;

-- Añadimos el nuevo constraint con estados adicionales: 'approved', 'rejected'
ALTER TABLE annotations
    ADD CONSTRAINT annotations_status_check
    CHECK (status IN ('pending', 'approved', 'rejected', 'trained', 'deployed'));

-- 2. Añadir campos de aprobación
ALTER TABLE annotations
    ADD COLUMN IF NOT EXISTS approved_by INTEGER REFERENCES platform_users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS approved_at TIMESTAMP,
    ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- 3. Crear índices para los nuevos campos
CREATE INDEX IF NOT EXISTS idx_annotations_approved_by ON annotations(approved_by);
CREATE INDEX IF NOT EXISTS idx_annotations_approved_at ON annotations(approved_at DESC);

-- 4. Comentarios en columnas nuevas
COMMENT ON COLUMN annotations.approved_by IS 'Usuario (qa_lead o admin) que aprobó o rechazó la anotación';
COMMENT ON COLUMN annotations.approved_at IS 'Timestamp de cuando se aprobó/rechazó';
COMMENT ON COLUMN annotations.rejection_reason IS 'Razón del rechazo (obligatorio si status=rejected)';

-- 5. Actualizar vista de estadísticas para incluir estados approved/rejected
-- Primero eliminamos la vista existente
DROP VIEW IF EXISTS v_annotation_stats_by_user CASCADE;

-- Recreamos la vista con los nuevos estados
CREATE VIEW v_annotation_stats_by_user AS
SELECT
    u.id as user_id,
    u.username,
    COUNT(a.id) as total_annotations,
    COUNT(CASE WHEN a.status = 'pending' THEN 1 END) as pending_annotations,
    COUNT(CASE WHEN a.status = 'approved' THEN 1 END) as approved_annotations,
    COUNT(CASE WHEN a.status = 'rejected' THEN 1 END) as rejected_annotations,
    COUNT(CASE WHEN a.status = 'trained' THEN 1 END) as trained_annotations,
    COUNT(CASE WHEN a.status = 'deployed' THEN 1 END) as deployed_annotations,
    MIN(a.annotated_at) as first_annotation,
    MAX(a.annotated_at) as last_annotation
FROM platform_users u
LEFT JOIN annotations a ON u.id = a.annotated_by
WHERE u.is_active = true
GROUP BY u.id, u.username;

-- 6. Crear vista para anotaciones aprobadas pendientes de entrenamiento
CREATE OR REPLACE VIEW v_approved_annotations_for_training AS
SELECT
    a.id,
    a.conversation_id,
    a.message_text,
    a.corrected_intent,
    a.corrected_entities,
    a.annotation_type,
    a.annotated_at,
    a.approved_at,
    u_annotator.username as annotated_by_username,
    u_approver.username as approved_by_username
FROM annotations a
LEFT JOIN platform_users u_annotator ON a.annotated_by = u_annotator.id
LEFT JOIN platform_users u_approver ON a.approved_by = u_approver.id
WHERE a.status = 'approved'
  AND a.included_in_training_job IS NULL
ORDER BY a.approved_at ASC;

-- 7. Crear función auxiliar para obtener estadísticas de aprobación
CREATE OR REPLACE FUNCTION get_annotation_approval_stats(p_days INTEGER DEFAULT 30)
RETURNS TABLE (
    total_pending BIGINT,
    total_approved BIGINT,
    total_rejected BIGINT,
    approval_rate NUMERIC
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as total_pending,
        COUNT(CASE WHEN status = 'approved' THEN 1 END) as total_approved,
        COUNT(CASE WHEN status = 'rejected' THEN 1 END) as total_rejected,
        CASE
            WHEN COUNT(CASE WHEN status IN ('approved', 'rejected') THEN 1 END) > 0
            THEN ROUND(
                COUNT(CASE WHEN status = 'approved' THEN 1 END)::NUMERIC /
                COUNT(CASE WHEN status IN ('approved', 'rejected') THEN 1 END)::NUMERIC * 100,
                2
            )
            ELSE 0
        END as approval_rate
    FROM annotations
    WHERE annotated_at >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_annotation_approval_stats(INTEGER) IS 'Retorna estadísticas de aprobación de anotaciones para los últimos N días';

COMMIT;

-- ============================================
-- VERIFICACIÓN
-- ============================================
-- Para verificar que la migración fue exitosa, ejecutar:
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'annotations' AND column_name IN ('approved_by', 'approved_at', 'rejection_reason');

-- ============================================
-- ROLLBACK (si es necesario)
-- ============================================
-- BEGIN;
-- ALTER TABLE annotations DROP COLUMN IF EXISTS approved_by;
-- ALTER TABLE annotations DROP COLUMN IF EXISTS approved_at;
-- ALTER TABLE annotations DROP COLUMN IF EXISTS rejection_reason;
-- ALTER TABLE annotations DROP CONSTRAINT IF EXISTS annotations_status_check;
-- ALTER TABLE annotations ADD CONSTRAINT annotations_status_check
--     CHECK (status IN ('pending', 'trained', 'deployed'));
-- COMMIT;

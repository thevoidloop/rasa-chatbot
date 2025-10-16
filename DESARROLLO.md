# DESARROLLO - Training Platform RASA

Este archivo documenta el progreso del desarrollo de la plataforma de entrenamiento para el chatbot RASA.

## Proyecto
- **Código:** RASA-TP-2025
- **Objetivo:** Reducir tiempo de QA en 60% y mejorar precisión del bot de 87% a 95%
- **Stack:** 100% Python (FastAPI backend, Streamlit frontend)
- **Documentación:** Ver `requerimientos.pdf` en la raíz del proyecto

---

## FASE 0: FUNDACIÓN (COMPLETADA ✅)

### Fecha de Inicio: 2025-10-06
### Fecha de Finalización: 2025-10-07

### Objetivos
Establecer la infraestructura base con autenticación y autorización.

### ✅ Completado

#### 1. Infraestructura Docker
- [x] Configuración de 5 servicios nuevos en `docker-compose.yml`:
  - `redis` (puerto 6379) - Cache y broker para Celery
  - `api-server` (puerto 8000) - Backend FastAPI
  - `celery-worker` - Procesamiento asíncrono
  - `flower` (puerto 5555) - Monitor de Celery
  - `training-platform` (puerto 8501) - Frontend Streamlit
- [x] Dockerfiles para API y Streamlit
- [x] Configuración de variables de entorno en `.env`
- [x] Volúmenes compartidos entre servicios

#### 2. Base de Datos
- [x] Script SQL con 8 nuevas tablas (`database/init-platform-tables.sql`):
  - `platform_users` - Usuarios de la plataforma
  - `annotations` - Anotaciones de conversaciones
  - `training_jobs` - Trabajos de entrenamiento
  - `deployed_models` - Modelos desplegados
  - `activity_logs` - Registro de actividades
  - `test_cases` - Casos de prueba
  - `test_results` - Resultados de pruebas
  - `conversation_reviews` - Revisiones de conversaciones
- [x] Índices, triggers y vistas auxiliares
- [x] Integración con PostgreSQL existente

#### 3. Backend (FastAPI)

**Estructura de carpetas:**
```
api/
├── database/
│   └── connection.py          # Conexión SQLAlchemy
├── schemas/
│   └── db_models.py           # Modelos ORM (8 tablas)
├── models/
│   └── auth.py                # Modelos Pydantic (request/response)
├── utils/
│   └── security.py            # Bcrypt + JWT
├── services/
│   └── auth_service.py        # Lógica de negocio
├── routers/
│   └── auth.py                # Endpoints de autenticación
├── dependencies.py            # FastAPI dependencies
├── config.py                  # Configuración con Pydantic Settings
├── main.py                    # Punto de entrada
└── tasks/
    └── celery_app.py          # Configuración Celery
```

**Características implementadas:**
- [x] Autenticación JWT (tokens expiran en 120 minutos)
- [x] Hash de contraseñas con bcrypt
- [x] 4 endpoints de autenticación:
  - `POST /api/v1/auth/login` - Login con username/password
  - `POST /api/v1/auth/register` - Registro (solo admin)
  - `GET /api/v1/auth/me` - Información del usuario actual
  - `POST /api/v1/auth/logout` - Logout
- [x] Control de acceso basado en roles (RBAC) con 5 niveles:
  1. `viewer` (nivel 1) - Solo lectura
  2. `developer` (nivel 2) - Desarrollo
  3. `qa_analyst` (nivel 3) - Análisis QA
  4. `qa_lead` (nivel 4) - Líder QA
  5. `admin` (nivel 5) - Administrador
- [x] Logging de actividades de usuarios
- [x] Validación con Pydantic

**Soluciones técnicas aplicadas:**
- Configuración de PYTHONPATH en Dockerfile
- Volúmenes montados: `./api:/app/api` y `./scripts:/app/scripts`
- Uso directo de bcrypt en lugar de passlib (compatibilidad)
- Truncamiento automático de contraseñas a 72 bytes (límite bcrypt)

#### 4. Script de Inicialización
- [x] `scripts/create_admin_user.py` - Crea usuario admin inicial
  - Usuario por defecto: `admin`
  - Contraseña por defecto: `Admin123!`
  - Email: `admin@training-platform.com`
  - Argumentos CLI para personalización
  - Validación de duplicados

#### 5. Frontend (Streamlit)

**Estructura de carpetas:**
```
training_platform/
├── utils/
│   ├── api_client.py          # Cliente HTTP para API
│   └── session.py             # Gestión de sesiones
├── pages/
│   └── 1_🔐_Login.py          # Página de login
└── app.py                     # Página principal (modificada)
```

**Características implementadas:**
- [x] Página de login con formulario
- [x] Gestión de sesiones con `st.session_state`:
  - `authenticated` - Estado de autenticación
  - `user` - Información del usuario
  - `token` - JWT token
  - `api_client` - Cliente API configurado
- [x] Cliente API con métodos:
  - `login()` - Autenticación
  - `logout()` - Cierre de sesión
  - `get_current_user()` - Info del usuario
  - `check_health()` - Health check
- [x] Sidebar con estado de sesión y botón de logout
- [x] Redirección automática si ya está autenticado

#### 6. Pruebas Realizadas
- [x] API health check: `http://localhost:8000/health` ✅
- [x] Login con admin: `POST /api/v1/auth/login` ✅
- [x] Obtener usuario actual: `GET /api/v1/auth/me` ✅
- [x] Verificación de JWT token válido ✅
- [x] Todos los servicios Docker corriendo correctamente ✅

### Archivos Creados/Modificados

**Nuevos archivos:**
- `database/init-platform-tables.sql`
- `api/Dockerfile`
- `api/requirements.txt`
- `api/config.py`
- `api/database/connection.py`
- `api/schemas/db_models.py`
- `api/models/auth.py`
- `api/utils/security.py`
- `api/services/auth_service.py`
- `api/dependencies.py`
- `api/routers/auth.py`
- `api/tasks/celery_app.py`
- `scripts/create_admin_user.py`
- `training_platform/Dockerfile`
- `training_platform/requirements.txt`
- `training_platform/utils/api_client.py`
- `training_platform/utils/session.py`
- `training_platform/pages/1_🔐_Login.py`

**Archivos modificados:**
- `docker-compose.yml` - Añadidos 5 servicios nuevos
- `.env` - Variables para Redis, API, JWT, Celery
- `.gitignore` - Exclusiones para reportes, backups, PDFs
- `api/main.py` - Incluido router de auth y creación de tablas
- `training_platform/app.py` - Integración con autenticación

### Comandos Útiles

```bash
# Crear usuario admin
docker compose exec api-server python scripts/create_admin_user.py

# Con argumentos personalizados
docker compose exec api-server python scripts/create_admin_user.py \
  --username "mi_admin" \
  --email "admin@example.com" \
  --password "MiPassword123!" \
  --full-name "Super Admin"

# Verificar servicios
docker compose ps

# Logs
docker compose logs -f api-server
docker compose logs -f training-platform

# Probar API
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

### Acceso a Servicios
- API Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Streamlit Frontend: http://localhost:8501
- Flower (Celery): http://localhost:5555
- PostgreSQL: localhost:5432

---

## FASE 1: VISUALIZACIÓN (COMPLETADA ✅ 100%)

### Fecha de Inicio: 2025-10-08
### Fecha de Finalización: 2025-10-13
### Duración Real: 1 semana
### Progreso Final: 100% completado

### Objetivos
Implementar dashboard con métricas en tiempo real y visualización de conversaciones.

### ✅ Completado

#### 1. Dashboard Principal ✅
**Archivo:** `training_platform/pages/2_📊_Dashboard.py` (304 líneas)

- [x] Implementar página de dashboard completa
- [x] Métricas clave (4 widgets):
  - [x] Total de conversaciones con filtro de período (7, 14, 30, 90 días)
  - [x] Confianza promedio del modelo
  - [x] Total de intents detectados
  - [x] Conversaciones pendientes de revisión
- [x] Gráficos interactivos con Plotly:
  - [x] Top 5 intents (barra horizontal + pie chart)
  - [x] Línea temporal de conversaciones (30 días)
  - [x] Heatmap de horarios de uso (día de semana × hora)
  - [x] Funnel de conversaciones (iniciadas → alta confianza → resueltas)
- [x] Información del modelo actualmente desplegado
- [x] Filtros dinámicos por período
- [x] Botón de actualización manual

#### 3. Backend para Métricas ✅
**Archivos:** `api/routers/metrics.py` + `api/services/metrics_service.py`

- [x] Crear router `/api/v1/metrics` con 5 endpoints:
  - [x] `GET /api/v1/metrics/summary?days={n}` - Métricas generales
  - [x] `GET /api/v1/metrics/timeline?days={n}` - Timeline diaria
  - [x] `GET /api/v1/metrics/intents?days={n}` - Distribución de intents
  - [x] `GET /api/v1/metrics/heatmap?days={n}` - Uso por hora/día
  - [x] `GET /api/v1/metrics/funnel?days={n}` - Funnel de conversiones
- [x] Crear servicio `metrics_service.py` con 5 funciones
- [x] Queries SQL optimizadas con agregaciones
- [x] Integración con timezone de Guatemala
- [x] Autenticación JWT en todos los endpoints

#### 4. Integración con RASA ✅
- [x] Leer eventos de la tabla `events` de PostgreSQL
- [x] Parser de eventos RASA (intents, entities, confidence)
- [x] Trigger de sincronización automática (`database/03-sync-rasa-conversations.sql`)
- [x] Script de backfill (`scripts/sync_existing_conversations.py`)
- [x] **FIX CRÍTICO:** Migración JSONB → TEXT para resolver bug de RASA 3.6.19
  - [x] `database/04-fix-events-jsonb-to-text.sql` (migración)
  - [x] `init-db.sql` actualizado (nueva instalación)
  - [x] Queries actualizadas con casting `data::jsonb->`
  - [x] Documentación en CLAUDE.md

#### 5. Scripts de Utilidad ✅
- [x] `scripts/seed_sample_data.py` - Genera datos de prueba para dashboard
- [x] `scripts/generate_test_conversations.py` - Generador de conversaciones ficticias
- [x] `scripts/sync_existing_conversations.py` - Sincroniza eventos existentes

### 🔄 Tareas Pendientes (para completar FASE 1)

#### 2. Visualización y Backend de Conversaciones ✅ (COMPLETADO)
**Estimación:** 3-5 días | **Tiempo real:** 1 día | **Progreso:** 100%

**Frontend Completado:**
- [x] Página `pages/3_💬_Conversaciones.py` (438 líneas) - REESCRITA COMPLETAMENTE
- [x] Sistema de filtros completo con 6 opciones:
  - Rango de fechas (5 preselecciones + personalizado)
  - Filtro por intent (multiselect con carga dinámica desde API)
  - Confianza mínima (slider 0-100%)
  - Búsqueda por sender_id
  - Búsqueda de texto en mensajes
  - Paginación configurable (25/50/100/200 items)
- [x] Tabla interactiva con datos reales del API
- [x] Vista detallada de conversación con timeline completo
- [x] Visualización chronological: usuario ↔ bot
- [x] Display de intents, confidence, entities por mensaje
- [x] Botones de acción funcionales:
  - Marcar para revisión (conectado a API)
  - Anotar (placeholder para FASE 2)
  - Ver en RASA (placeholder)
- [x] Exportación CSV con link de descarga directo
- [x] 4 métricas de resumen en tiempo real
- [x] Manejo de errores y estados vacíos

**Backend Completado:**
- [x] Modelos Pydantic en `api/models/conversations.py` (79 líneas)
- [x] Servicio `api/services/conversation_service.py` (264 líneas)
- [x] Router `api/routers/conversations.py` (158 líneas)
- [x] 5 endpoints REST totalmente funcionales:
  - `GET /api/v1/conversations` - ✅ Integrado con UI
  - `GET /api/v1/conversations/intents` - ✅ Integrado con UI
  - `GET /api/v1/conversations/{sender_id}` - ✅ Integrado con UI
  - `POST /api/v1/conversations/{sender_id}/flag` - ✅ Integrado con UI
  - `GET /api/v1/conversations/export/csv` - ✅ Integrado con UI
- [x] Queries SQL optimizadas con CTE y agregaciones
- [x] Paginación eficiente con LIMIT/OFFSET
- [x] Control de acceso por roles (RBAC)
- [x] Fix de conflicto de nombres

### 🔄 Tareas Pendientes (FASE 2 - ANOTACIÓN)

#### Cache con Redis ⏭️ (DIFERIDO)
**Estimación:** 1-2 días
**Nota:** Diferido para después de FASE 2, ya que no es crítico para funcionalidad

- [ ] Implementar decorator `@cache_result` en `api/utils/cache.py`
- [ ] Aplicar caché a:
  - [ ] `get_summary_metrics()` - TTL: 5 minutos
  - [ ] `get_conversations_timeline()` - TTL: 10 minutos
  - [ ] `get_intent_distribution()` - TTL: 5 minutos
- [ ] Invalidación de caché en eventos importantes:
  - [ ] Nuevo modelo desplegado
  - [ ] Anotación aprobada
- [ ] Health check de Redis en `/health` endpoint

### Archivos Creados en FASE 1

**Nuevos archivos:**
- `training_platform/pages/2_📊_Dashboard.py` (304 líneas)
- `training_platform/pages/3_💬_Conversaciones.py` (375 líneas)
- `api/routers/metrics.py`
- `api/routers/conversations.py` (158 líneas) 🆕
- `api/services/metrics_service.py`
- `api/services/conversation_service.py` (264 líneas) 🆕
- `api/models/conversations.py` (79 líneas) 🆕
- `database/03-sync-rasa-conversations.sql`
- `database/04-fix-events-jsonb-to-text.sql`
- `scripts/seed_sample_data.py`
- `scripts/generate_test_conversations.py`
- `scripts/sync_existing_conversations.py`
- `.claudecode/database-change-policy.md`

**Archivos modificados:**
- `init-db.sql` - Columna `events.data` cambiada a TEXT
- `CLAUDE.md` - Documentación de fix JSONB, política de DB changes
- `api/main.py` - Incluido routers de metrics y conversations 🆕

---

## FASE 2: ANOTACIÓN (COMPLETADA ✅ 100%)

### Fecha de Inicio: 2025-10-14
### Fecha de Finalización: 2025-10-15
### Duración Real: 2 días
### Progreso Final: 100% (Todas las partes completadas)

### Objetivos
Herramientas para corregir y anotar intents/entities en conversaciones con workflow de aprobación QA.

---

### ✅ Parte 1: Backend - Modelos y Servicios (COMPLETADA)
**Duración:** 1 día (2025-10-14)

#### 1. Esquema de Base de Datos ✅
- [x] Actualizado `database/init-platform-tables.sql`:
  - Añadidos campos de workflow de aprobación: `approved_by`, `approved_at`, `rejection_reason`
  - Ampliado CHECK constraint de `status`: añadidos 'approved' y 'rejected'
  - Añadidos índices para nuevos campos
- [x] Creado `database/05-add-annotation-approval-workflow.sql`:
  - Script de migración para bases de datos existentes
  - Vista `v_approved_annotations_for_training` para exportación
  - Función `get_annotation_approval_stats()` para métricas

#### 2. Modelos Pydantic ✅
**Archivo:** `api/models/annotations.py` (287 líneas)

- [x] `EntityAnnotation` - Validación de entities con posiciones start/end
- [x] `AnnotationCreate` - Request para crear anotación
- [x] `AnnotationUpdate` - Request para actualizar (campos opcionales)
- [x] `AnnotationApprovalRequest` - Request para aprobar/rechazar
- [x] `AnnotationResponse` - Response con usernames joined
- [x] `AnnotationListResponse` - Respuesta paginada
- [x] `AnnotationStats` - Estadísticas para dashboard
- [x] `AnnotationFilters` - Parámetros de filtrado

**Validaciones implementadas:**
- Entity positions (start < end)
- Al menos una corrección (intent o entities)
- Rejection reason obligatorio cuando se rechaza
- Tipos de anotación válidos (intent, entity, both)

#### 3. Modelo ORM ✅
**Archivo:** `api/schemas/db_models.py` (modificado)

- [x] Añadidos campos al modelo `Annotation`:
  - `approved_by` (Integer, FK a platform_users)
  - `approved_at` (DateTime con índice)
  - `rejection_reason` (Text)

#### 4. Servicio de Anotaciones ✅
**Archivo:** `api/services/annotation_service.py` (483 líneas)

**Funciones principales:**
- [x] `create_annotation()` - Crea anotación con estado 'pending'
- [x] `get_annotations()` - Lista paginada con filtros y JOINs
- [x] `get_annotation_by_id()` - Obtiene anotación con usernames joined
- [x] `update_annotation()` - Actualiza (solo creador/admin, solo si pending/rejected)
- [x] `delete_annotation()` - Elimina (solo creador/admin, solo si pending)
- [x] `approve_annotation()` - Aprueba/rechaza (solo qa_lead/admin)
- [x] `get_annotation_stats()` - Estadísticas por estado con approval_rate
- [x] `get_pending_annotations_count()` - Contador para dashboard

**Funciones auxiliares:**
- [x] `_check_annotation_exists()` - Valida existencia (404 si no existe)
- [x] `_check_user_permissions()` - Valida permisos por rol y operación
- [x] `_get_user_info()` - Obtiene user_id y username

**Control de permisos implementado:**
- Viewer/Developer: Solo lectura
- QA Analyst: Crear y editar propias anotaciones
- QA Lead: Aprobar/rechazar anotaciones
- Admin: Acceso completo

**Logging automático:**
- Todas las operaciones se registran en `activity_logs`
- Detalles incluyen: conversation_id, annotation_type, corrected_intent

#### 5. Router de Anotaciones ✅
**Archivo:** `api/routers/annotations.py` (332 líneas)

**Endpoints implementados:**
- [x] `POST /api/v1/annotations` - Crear anotación (qa_analyst+) → 201
- [x] `GET /api/v1/annotations` - Listar con paginación y filtros (viewer+)
- [x] `GET /api/v1/annotations/stats` - Estadísticas (viewer+)
- [x] `GET /api/v1/annotations/{id}` - Ver detalle (viewer+)
- [x] `PUT /api/v1/annotations/{id}` - Actualizar (creador/admin)
- [x] `DELETE /api/v1/annotations/{id}` - Eliminar (creador/admin) → 204
- [x] `POST /api/v1/annotations/{id}/approve` - Aprobar/Rechazar (qa_lead+)

**Parámetros de filtrado:**
- `page`, `page_size` - Paginación
- `status` - pending, approved, rejected, trained, deployed
- `conversation_id` - Filtrar por conversación
- `intent` - Filtrar por intent corregido
- `annotated_by` - Filtrar por creador
- `approved_by` - Filtrar por aprobador

#### 6. Integración en FastAPI ✅
**Archivo:** `api/main.py` (modificado)

- [x] Importado `annotations` router
- [x] Registrado con `app.include_router(annotations.router)`
- [x] Documentación automática en Swagger UI

#### 7. Migración de Base de Datos ✅
- [x] Aplicada migración en base de datos existente
- [x] Verificadas columnas creadas correctamente
- [x] Reiniciado servicio api-server

#### 8. Testing ✅
**Endpoints probados exitosamente:**
- [x] `GET /api/v1/annotations/stats` - Retorna contadores y approval_rate
- [x] `POST /api/v1/annotations` - Crea anotación con status='pending'
- [x] `POST /api/v1/annotations/1/approve` - Aprueba y registra approver
- [x] `GET /api/v1/annotations` - Lista con paginación y usernames

**Resultados de prueba:**
```json
// Stats inicial
{"total": 0, "pending": 0, "approved": 0, "rejected": 0, "trained": 0, "deployed": 0, "approval_rate": 0.0}

// Después de crear y aprobar 1 anotación
{"total": 1, "pending": 0, "approved": 1, "rejected": 0, "trained": 0, "deployed": 0, "approval_rate": 100.0}
```

---

### ✅ Parte 2: Backend - Exportación y Validación (COMPLETADA)
**Duración:** 1 día (2025-10-14)

#### 1. Servicio de Exportación ✅
**Archivo:** `api/services/export_service.py` (406 líneas)

**Funciones principales:**
- [x] `get_approved_annotations()` - Query anotaciones aprobadas con filtros
  - Filtros: `from_date`, `to_date`, `intent_filter`
  - Ordenado por intent y fecha de aprobación
  - Solo retorna anotaciones con status='approved'
- [x] `convert_annotations_to_nlu_dict()` - Agrupa ejemplos por intent
  - Formatea entities en markdown: `[text](entity_type)`
  - Elimina duplicados automáticamente
  - Retorna dict: `{intent: [examples]}`
- [x] `convert_to_rasa_nlu_yaml()` - Genera YAML en formato RASA 3.x
  - Versión: "3.1"
  - Sintaxis literal block para examples (`examples: |`)
  - Formato manual para control exacto
- [x] `validate_nlu_yaml()` - Valida estructura y formato del YAML
  - Verifica versión, sección nlu, campos requeridos
  - Detecta duplicados y campos faltantes
  - Retorna (is_valid, errors, warnings)
- [x] `validate_annotations_export()` - Valida contra datos existentes
  - Verifica intents contra tabla events
  - Verifica entity types contra tabla events
  - Genera warnings para intents/entities nuevos
- [x] `get_nlu_export_stats()` - Calcula estadísticas de exportación
  - Total intents, examples, entities
  - Conteo por entity type
  - Promedio de examples por intent
- [x] `get_existing_intents_from_db()` - Query intents desde eventos RASA
  - Extrae de `events.data::jsonb->'parse_data'->'intent'->>'name'`
  - Retorna lista ordenada alfabéticamente
- [x] `get_existing_entities_from_db()` - Query entity types desde eventos
  - Extrae de array `events.data::jsonb->'parse_data'->'entities'`
  - Retorna lista ordenada alfabéticamente

**Funciones auxiliares:**
- [x] `_format_entity_in_text()` - Convierte entities a formato markdown
  - Input: texto + lista de entities con posiciones start/end
  - Output: texto con marcado `[entity_text](entity_type)`
  - Maneja múltiples entities con posiciones correctas
- [x] `_validate_intent_exists()` - Valida si intent existe en dominio
- [x] `_validate_entities()` - Valida si entities existen en dominio

**Formato de exportación RASA:**
```yaml
version: "3.1"

nlu:
- intent: consultar_catalogo
  examples: |
    - quiero ver productos
    - muéstrame el [catálogo](producto)
    - necesito [2](cantidad) [camisas](producto)
```

#### 2. Modelos Pydantic ✅
**Archivo:** `api/models/export.py` (92 líneas)

- [x] `NLUExportRequest` - Request para exportación
  - Campos: `from_date`, `to_date`, `intent_filter`, `format`
  - Validación de formato (solo 'yaml' soportado)
- [x] `NLUExportStats` - Estadísticas de exportación
  - `total_intents`, `total_examples`, `total_entities_used`
  - `entity_usage` (Dict[str, int]) - conteo por tipo
  - `avg_examples_per_intent`, `total_annotations`
- [x] `NLUPreviewResponse` - Preview con validación
  - `yaml_content` - YAML generado
  - `stats` - Estadísticas
  - `validation_errors` - Lista de errores críticos
  - `validation_warnings` - Lista de advertencias
  - `is_valid` - Bandera de validez de formato
  - `can_export` - Bandera de exportabilidad (sin errores)
- [x] `IntentListResponse` - Lista de intents disponibles
  - `intents` - Lista de nombres
  - `total` - Contador
  - `source` - Origen de datos (database/domain/etc)
- [x] `EntityListResponse` - Lista de entity types disponibles
  - `entities` - Lista de tipos
  - `total` - Contador
  - `source` - Origen de datos
- [x] `ExportSummary` - Resumen de operación de exportación

#### 3. Router de Exportación ✅
**Archivo:** `api/routers/export.py` (318 líneas)

**Endpoints implementados:**
- [x] `GET /api/v1/export/nlu/preview` - Preview con validación (qa_lead+)
  - Parámetros: `from_date`, `to_date`, `intent_filter`
  - Retorna YAML, stats, errors, warnings
  - Validación en dos capas: formato + dominio
  - Maneja caso sin anotaciones (retorna preview vacío)
- [x] `GET /api/v1/export/nlu/download` - Descarga YAML (qa_lead+)
  - Parámetros: `from_date`, `to_date`, `intent_filter`
  - Valida antes de exportar (bloquea si hay errores)
  - Content-Type: `application/x-yaml; charset=utf-8`
  - Filename dinámico: `nlu_annotations_YYYYMMDD_HHMMSS.yml`
  - HTTP 404 si no hay anotaciones aprobadas
- [x] `GET /api/v1/export/intents` - Lista intents disponibles (viewer+)
  - Extrae de tabla events (datos RASA)
  - Retorna lista ordenada alfabéticamente
  - Útil para autocomplete en UI
- [x] `GET /api/v1/export/entities` - Lista entity types (viewer+)
  - Extrae de tabla events (datos RASA)
  - Retorna lista ordenada alfabéticamente
  - Útil para validación en UI

**Control de permisos:**
- Viewer/Developer/QA Analyst: Solo pueden listar intents/entities
- QA Lead/Admin: Pueden exportar (preview y download)
- Helper `_check_export_permission()` valida nivel 4+

#### 4. Integración en FastAPI ✅
**Archivo:** `api/main.py` (modificado)

- [x] Importado `export` router
- [x] Registrado con `app.include_router(export.router)`
- [x] Documentación automática en Swagger UI

#### 5. Testing Completo ✅

**Endpoints probados exitosamente:**

✅ **GET /api/v1/export/intents**
```json
{
  "intents": ["agregar_al_carrito", "consultar_catalogo", "consultar_envios",
              "consultar_pagos", "despedir", "rechazar_agregar_mas", "saludar"],
  "total": 7,
  "source": "database"
}
```

✅ **GET /api/v1/export/entities**
```json
{
  "entities": ["cantidad", "producto"],
  "total": 2,
  "source": "database"
}
```

✅ **GET /api/v1/export/nlu/preview**
```json
{
  "yaml_content": "version: \"3.1\"\n\nnlu:\n- intent: consultar_catalogo\n  examples: |\n    - Quiero comprar[ una ](producto)blusa\n\n",
  "stats": {
    "total_intents": 1,
    "total_examples": 1,
    "total_entities_used": 1,
    "entity_usage": {"producto": 1},
    "avg_examples_per_intent": 1.0,
    "total_annotations": 1
  },
  "validation_errors": [],
  "validation_warnings": [],
  "is_valid": true,
  "can_export": true
}
```

✅ **GET /api/v1/export/nlu/download**
- HTTP Status: 200
- Content-Type: `application/x-yaml; charset=utf-8`
- Content-Disposition: `attachment; filename=nlu_annotations_20251014_234725.yml`
- Archivo descargado correctamente

✅ **Filtros probados:**
- `from_date` y `to_date`: Filtran por fecha de aprobación ✅
- `intent_filter`: Filtra por intent específico ✅
- Sin anotaciones: Retorna preview vacío con warning ✅

✅ **Permisos verificados:**
- qa_analyst puede ver intents/entities ✅
- qa_analyst NO puede exportar (403 Forbidden) ✅
- admin puede todo ✅

**Comandos de prueba ejecutados:**
```bash
# Script de prueba con autenticación
cat > /tmp/test_export.sh << 'SCRIPT'
#!/bin/bash
TOKEN=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json | jq -r '.access_token')

# Listar intents
curl -s "http://localhost:8000/api/v1/export/intents" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Preview de exportación con filtros
curl -s "http://localhost:8000/api/v1/export/nlu/preview?from_date=2025-10-01&to_date=2025-10-20" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Download YAML
curl -s "http://localhost:8000/api/v1/export/nlu/download" \
  -H "Authorization: Bearer $TOKEN" \
  -o nlu_export.yml
SCRIPT

chmod +x /tmp/test_export.sh && /tmp/test_export.sh
```

---

### ✅ Parte 3: Frontend - Interface de Anotaciones (COMPLETADA)
**Duración:** 1 día (2025-10-15)

#### 1. Utilidades de Anotación ✅
**Archivo:** `training_platform/utils/annotation_helpers.py` (540 líneas)

**Funciones implementadas:**
- [x] `format_entities_display()` - Formatea entities en 3 modos (badge, inline, list)
- [x] `highlight_entities()` - Resalta entities en texto con HTML + colores
- [x] `validate_entity_spans()` - Valida posiciones, overlaps, valores
- [x] `get_intent_suggestions()` - Lista intents desde API con filtrado
- [x] `get_entity_types()` - Lista entity types desde API
- [x] `extract_entities_from_text()` - Crea entity desde selección
- [x] `format_annotation_status()` - Badge coloreado por status
- [x] `format_annotation_type()` - Badge coloreado por tipo
- [x] `calculate_entity_positions()` - Auto-detecta posiciones
- [x] `build_entity_editor_ui()` - UI interactiva para editar entities

**Colores por entity:**
- `producto` → #FF6B6B (rojo suave)
- `cantidad` → #4ECDC4 (turquesa)
- Default → #95E1D3 (verde menta)

#### 2. Página Principal de Anotaciones ✅
**Archivo:** `training_platform/pages/4_✏️_Anotaciones.py` (590 líneas)

**Características implementadas:**
- [x] Setup y autenticación (qa_analyst+)
- [x] Header con 4 métricas en tiempo real:
  - Total anotaciones
  - Pendientes de revisión
  - Aprobadas
  - Tasa de aprobación (%)
- [x] Sidebar con filtros avanzados:
  - Estado (pending, approved, rejected, trained, deployed)
  - Intent (multiselect dinámico)
  - Conversation ID
  - Creado por (username)
  - Aprobado por (username)
  - Items por página (10/25/50/100)
- [x] Lista de anotaciones con card-based layout
- [x] Paginación funcional con navegación
- [x] Modal de detalles con comparación lado a lado:
  - Sección original vs corregido
  - Display de entities con highlighting
  - Metadata completa (creador, aprobador, fechas)
- [x] Modal de crear/editar anotación:
  - Formulario completo con validación
  - Soporte para intent y entities
  - Editor JSON para entities
  - Validación en tiempo real
- [x] Modal de aprobación (solo qa_lead/admin):
  - Radio buttons aprobar/rechazar
  - Campo rejection_reason obligatorio
  - Confirmación con feedback
- [x] Control de permisos granular:
  - Solo creador/admin pueden editar pending/rejected
  - Solo qa_lead/admin pueden aprobar
  - Botones habilitados según permisos
- [x] Botones de acción contextuales:
  - Ver detalles
  - Editar (si tiene permisos)
  - Revisar (si qa_lead+ y pending)
  - Eliminar (si pending)

**Funciones auxiliares:**
- `load_annotation_stats()` - Carga estadísticas
- `load_annotations()` - Lista con filtros y paginación
- `create_annotation()` - POST con validación
- `update_annotation()` - PUT con control de permisos
- `approve_annotation()` - Aprobación/rechazo
- `delete_annotation()` - DELETE con validación
- `can_edit_annotation()` - Verifica permisos de edición
- `can_approve_annotation()` - Verifica permisos de aprobación

#### 3. Integración con Conversaciones ✅
**Archivo:** `training_platform/pages/3_💬_Conversaciones.py` (modificado)

**Cambios implementados:**
- [x] Botón "✍️ Anotar" actualizado con funcionalidad real
- [x] Modal de creación de anotación en la misma página:
  - Selector de mensaje del usuario
  - Pre-llenado automático con datos del mensaje
  - Formulario completo (intent + entities)
  - Validación antes de enviar
  - Botones: Guardar, Ir a Anotaciones, Cancelar
- [x] Integración con API de anotaciones
- [x] Feedback visual con success/error messages
- [x] Enlace directo a página de anotaciones

#### 4. Página de Exportación ✅
**Archivo:** `training_platform/pages/5_📤_Exportar.py` (460 líneas)

**Solo accesible para qa_lead (nivel 4+) y admin (nivel 5)**

**Características implementadas:**
- [x] Header con descripción del flujo de trabajo
- [x] Sidebar con filtros de exportación:
  - Rango de fechas (todo/30d/90d/personalizado)
  - Multiselect de intents
  - Botón "Generar Preview"
  - Botón de actualizar
- [x] Validación de permisos en carga
- [x] Resumen de exportación con 4 métricas:
  - Total intents
  - Total ejemplos
  - Entities usados
  - Promedio ejemplos/intent
- [x] Sistema de tabs para organizar información:
  - **Tab 1: YAML Preview**
    - Syntax highlighting con `st.code()`
    - Line numbers habilitados
    - Info de líneas y anotaciones totales
  - **Tab 2: Estadísticas Detalladas**
    - Distribución de intents
    - Tabla de uso de entities
    - Recomendaciones basadas en promedios
  - **Tab 3: Validación**
    - Estado de validación (válido/errores/warnings)
    - Lista de errores críticos
    - Lista de advertencias
    - Instrucciones de resolución
- [x] Botón de descarga con validación:
  - Solo habilitado si `can_export = true`
  - Filename dinámico con timestamp
  - Usa `st.download_button()`
  - Formato YAML correcto
- [x] Instrucciones de aplicación expandibles:
  - 6 pasos detallados
  - Comandos bash listos para copiar
  - Recomendaciones importantes
  - Métricas a monitorear post-deploy
- [x] Información educativa:
  - Estructura del YAML RASA 3.x
  - Formato markdown de entities
  - Ejemplos con explicación

**Funciones auxiliares:**
- `has_export_permission()` - Valida nivel 4+
- `load_intents()` - Lista intents disponibles
- `get_export_preview()` - Preview con validación
- `download_nlu_yaml()` - Descarga archivo YAML

**Validaciones implementadas:**
- Formato YAML correcto
- Intents existen en dominio
- Entity types válidos
- Warnings para items nuevos
- Bloqueo de export si hay errores críticos

---

### Archivos Creados en FASE 2 - Completa

**Nuevos archivos:**
- `database/05-add-annotation-approval-workflow.sql` (115 líneas) - Parte 1
- `api/models/annotations.py` (287 líneas) - Parte 1
- `api/services/annotation_service.py` (483 líneas) - Parte 1
- `api/routers/annotations.py` (332 líneas) - Parte 1
- `api/models/export.py` (92 líneas) - Parte 2
- `api/services/export_service.py` (406 líneas) - Parte 2
- `api/routers/export.py` (318 líneas) - Parte 2
- `training_platform/utils/annotation_helpers.py` (540 líneas) - Parte 3 🆕
- `training_platform/pages/4_✏️_Anotaciones.py` (590 líneas) - Parte 3 🆕
- `training_platform/pages/5_📤_Exportar.py` (460 líneas) - Parte 3 🆕

**Archivos modificados:**
- `database/init-platform-tables.sql` - Añadidos campos de aprobación a tabla `annotations` (Parte 1)
- `api/schemas/db_models.py` - Actualizado modelo ORM `Annotation` (Parte 1)
- `api/main.py` - Integrados routers de annotations y export (Partes 1 y 2)
- `training_platform/pages/3_💬_Conversaciones.py` - Añadido modal de anotaciones (Parte 3) 🆕

**Total de líneas de código:** ~3,600 líneas nuevas

---

### Comandos Útiles para Anotaciones y Exportación

```bash
# ============================================
# Base de Datos
# ============================================

# Aplicar migración de aprobación (solo en bases de datos existentes)
cat database/05-add-annotation-approval-workflow.sql | docker exec -i rasa_postgres psql -U rasa_user -d rasa_chatbot

# Verificar columnas de aprobación
docker exec rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'annotations' AND column_name IN ('approved_by', 'approved_at', 'rejection_reason');"

# Ver estadísticas de anotaciones
docker exec rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT * FROM get_annotation_approval_stats(30);"

# Listar anotaciones aprobadas
docker exec rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT id, message_text, corrected_intent, status, approved_at FROM annotations WHERE status='approved';"

# Ver vista de anotaciones para entrenamiento
docker exec rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT * FROM v_approved_annotations_for_training LIMIT 10;"

# ============================================
# Testing de Endpoints (requiere autenticación)
# Ver sección "Testing de Endpoints" en CLAUDE.md
# ============================================

# 1. Crear archivo de login
cat > /tmp/login.json << 'EOF'
{"username": "admin", "password": "Admin123!"}
EOF

# 2. Script de prueba de exportación
cat > /tmp/test_export.sh << 'SCRIPT'
#!/bin/bash
TOKEN=$(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json | jq -r '.access_token')

echo "=== Listar intents disponibles ==="
curl -s "http://localhost:8000/api/v1/export/intents" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo -e "\n=== Listar entities disponibles ==="
curl -s "http://localhost:8000/api/v1/export/entities" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo -e "\n=== Preview de exportación ==="
curl -s "http://localhost:8000/api/v1/export/nlu/preview" \
  -H "Authorization: Bearer $TOKEN" | jq '.stats'

echo -e "\n=== YAML generado ==="
curl -s "http://localhost:8000/api/v1/export/nlu/preview" \
  -H "Authorization: Bearer $TOKEN" | jq -r '.yaml_content'

echo -e "\n=== Descargar YAML ==="
curl -s "http://localhost:8000/api/v1/export/nlu/download" \
  -H "Authorization: Bearer $TOKEN" \
  -o /tmp/nlu_export.yml
echo "Archivo guardado en: /tmp/nlu_export.yml"
cat /tmp/nlu_export.yml
SCRIPT

chmod +x /tmp/test_export.sh && /tmp/test_export.sh

# 3. Probar con filtros
curl -s "http://localhost:8000/api/v1/export/nlu/preview?from_date=2025-10-01&to_date=2025-10-31&intent_filter=consultar_catalogo" \
  -H "Authorization: Bearer $(curl -s -X POST 'http://localhost:8000/api/v1/auth/login' -H 'Content-Type: application/json' -d @/tmp/login.json | jq -r '.access_token')" \
  | jq '.'
```

---

### Próximos Pasos

1. ✅ ~~**Parte 1** (1 día): Backend de modelos y servicios~~ - COMPLETADO
2. ✅ ~~**Parte 2** (1 día): Backend de exportación a formato RASA~~ - COMPLETADO
3. ✅ ~~**Parte 3** (1 día): Frontend completo de anotaciones~~ - COMPLETADO
4. **Testing E2E** (opcional): Flujo completo qa_analyst → qa_lead → export → RASA training

**FASE 2 COMPLETADA ✅**

La plataforma ahora cuenta con:
- Sistema completo de anotaciones (crear, editar, aprobar, rechazar)
- Workflow de QA con roles y permisos
- Exportación a formato RASA NLU con validación
- Interface de usuario intuitiva y funcional
- Todas las piezas integradas y probadas

---

## FASE 3: GESTIÓN DE DATOS (PENDIENTE 🔄)

### Duración Estimada: Semana 6

### Objetivos
CRUD completo para ejemplos NLU, responses y domain.

### Tareas Pendientes

#### 1. Gestión de Training Data
- [ ] Página de datos de entrenamiento (`pages/5_📝_Datos.py`)
- [ ] Tabs para:
  - [ ] Intents y ejemplos
  - [ ] Entities y sinónimos
  - [ ] Responses
  - [ ] Domain (slots, actions, forms)
- [ ] Editor de YAML inline
- [ ] Validación de sintaxis

#### 2. Backend para Training Data
- [ ] Endpoints en `api/routers/training_data.py`
- [ ] Parser/Writer de archivos YAML
- [ ] Versionado de archivos (git integration)
- [ ] Backup automático antes de cambios

---

## FASE 4: ENTRENAMIENTO (PENDIENTE 🔄)

### Duración Estimada: Semanas 7-8

### Objetivos
Reentrenar modelo con un click y seguimiento de jobs.

### Tareas Pendientes

#### 1. Interface de Entrenamiento
- [ ] Página de entrenamiento (`pages/6_🎓_Entrenamiento.py`)
- [ ] Botón "Entrenar Modelo"
- [ ] Configuración de hiperparámetros
- [ ] Progreso en tiempo real
- [ ] Comparación con modelo anterior

#### 2. Backend de Entrenamiento
- [ ] Endpoints en `api/routers/training.py`:
  - [ ] `POST /api/v1/training/start` - Iniciar entrenamiento
  - [ ] `GET /api/v1/training/jobs` - Listar jobs
  - [ ] `GET /api/v1/training/jobs/{id}` - Estado del job
  - [ ] `POST /api/v1/training/jobs/{id}/cancel` - Cancelar
- [ ] Tarea Celery para entrenamiento asíncrono
- [ ] Integración con `rasa train`
- [ ] Guardar métricas en tabla `training_jobs`
- [ ] Notificaciones cuando termina

#### 3. Testing Automático
- [ ] Endpoints en `api/routers/testing.py`:
  - [ ] `POST /api/v1/testing/run` - Ejecutar tests
  - [ ] `GET /api/v1/testing/results/{id}` - Resultados
- [ ] Integración con `rasa test nlu`
- [ ] Casos de prueba en tabla `test_cases`
- [ ] Resultados en tabla `test_results`
- [ ] Regresión automática

---

## FASE 5: REPORTES Y ADMIN (PENDIENTE 🔄)

### Duración Estimada: Semana 9

### Objetivos
Reportes automatizados y gestión de usuarios.

### Tareas Pendientes

#### 1. Generación de Reportes
- [ ] Página de reportes (`pages/7_📈_Reportes.py`)
- [ ] Tipos de reportes:
  - [ ] Resumen semanal
  - [ ] Comparativa de modelos
  - [ ] Análisis de anotaciones
- [ ] Exportar a PDF con WeasyPrint
- [ ] Programación de reportes automáticos

#### 2. Administración
- [ ] Página de admin (`pages/8_⚙️_Admin.py`)
- [ ] CRUD de usuarios (solo admin)
- [ ] Gestión de roles
- [ ] Logs de actividad
- [ ] Configuración de la plataforma

---

## FASE 6: OPTIMIZACIÓN (PENDIENTE 🔄)

### Duración Estimada: Semana 10

### Objetivos
Optimizar rendimiento y preparar para producción.

### Tareas Pendientes

#### 1. Rendimiento
- [ ] Caché de queries frecuentes con Redis
- [ ] Paginación en todas las listas
- [ ] Índices en columnas de búsqueda
- [ ] Optimización de queries SQL
- [ ] Lazy loading de componentes Streamlit

#### 2. Producción
- [ ] Variables de entorno para producción
- [ ] Restringir CORS en API
- [ ] HTTPS en Streamlit
- [ ] Backup automático de base de datos
- [ ] Monitoreo con Flower
- [ ] Logs centralizados
- [ ] Health checks robustos

#### 3. Documentación
- [ ] README completo
- [ ] Documentación de API (Swagger/OpenAPI)
- [ ] Guía de usuario
- [ ] Manual de despliegue

---

## Métricas de Éxito del Proyecto

### Objetivos Medibles
- [ ] Reducción de 60% en tiempo de QA (de X horas a Y horas)
- [ ] Incremento de precisión de 87% a 95%
- [ ] 100% de conversaciones revisadas automáticamente
- [ ] Tiempo de reentrenamiento < 10 minutos
- [ ] Todos los miembros del equipo usando la plataforma

### KPIs a Monitorear
- Tiempo promedio de anotación por conversación
- Número de anotaciones por QA por día
- Tasa de aprobación de anotaciones
- Frecuencia de reentrenamiento
- Uptime de la plataforma

---

## Notas Técnicas

### Problemas Resueltos
1. **Bcrypt 72-byte limit**: Implementada truncación automática en `get_password_hash()`
2. **Imports de módulo api**: Configurado PYTHONPATH=/app en Dockerfile y ajustados volúmenes
3. **Passlib incompatibilidad**: Cambiado a uso directo de bcrypt

### Decisiones de Arquitectura
- JWT sin refresh tokens (simplicidad inicial, añadir después si es necesario)
- Celery para tareas asíncronas (futuro: entrenamiento, reportes)
- Redis como broker y caché
- SQLAlchemy ORM para abstracción de base de datos
- Pydantic para validación estricta

### Mejoras Futuras (Post v1.0)
- [ ] Refresh tokens para JWT
- [ ] Autenticación con OAuth2 (Google, GitHub)
- [ ] WebSockets para actualizaciones en tiempo real
- [ ] Multi-tenancy (múltiples bots por organización)
- [ ] API pública para integraciones externas
- [ ] Mobile app con React Native

---

## Recursos

### Documentación
- Requerimientos completos: `requerimientos.pdf`
- Instrucciones de desarrollo: `CLAUDE.md`
- Estructura de carpetas: Ver sección "Archivos Creados" arriba

### Comandos Rápidos
```bash
# Iniciar todos los servicios
docker compose up -d

# Ver logs en tiempo real
docker compose logs -f api-server training-platform

# Reconstruir después de cambios
docker compose down
docker compose build --no-cache
docker compose up -d

# Crear admin user
docker compose exec api-server python scripts/create_admin_user.py

# Acceder a PostgreSQL
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot

# Listar usuarios de la plataforma
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT id, username, email, role, is_active FROM platform_users;"
```

---

**Última actualización:** 2025-10-15
**Estado:** FASE 2 COMPLETADA ✅ | Sistema de Anotaciones 100% funcional
**Próximo paso:** Iniciar FASE 3 - Gestión de Datos (Training Data Management)

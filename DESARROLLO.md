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

## FASE 1: VISUALIZACIÓN (PENDIENTE 🔄)

### Duración Estimada: Semanas 2-3

### Objetivos
Implementar dashboard con métricas en tiempo real y visualización de conversaciones.

### Tareas Pendientes

#### 1. Dashboard Principal
- [ ] Implementar página de dashboard (`pages/2_📊_Dashboard.py`)
- [ ] Métricas clave:
  - [ ] Total de conversaciones (últimas 24h, 7 días, 30 días)
  - [ ] Tasa de acierto del bot (confidence promedio)
  - [ ] Intents más frecuentes
  - [ ] Entities detectadas
  - [ ] Conversaciones pendientes de revisión
  - [ ] Estado del modelo actual
- [ ] Gráficos con Plotly:
  - [ ] Línea temporal de conversaciones
  - [ ] Distribución de intents
  - [ ] Heatmap de horarios de uso
  - [ ] Funnel de conversaciones exitosas vs fallidas

#### 2. Visualización de Conversaciones
- [ ] Implementar página de conversaciones (`pages/3_💬_Conversaciones.py`)
- [ ] Tabla interactiva con AgGrid:
  - [ ] Filtros por fecha, intent, confidence, usuario
  - [ ] Búsqueda de texto completo
  - [ ] Paginación
  - [ ] Exportar a CSV/Excel
- [ ] Detalle de conversación:
  - [ ] Vista de mensajes (usuario vs bot)
  - [ ] Confidence scores
  - [ ] Entities detectadas
  - [ ] Botones de acción (anotar, marcar para revisión)

#### 3. Backend para Métricas
- [ ] Crear endpoints en `api/routers/metrics.py`:
  - [ ] `GET /api/v1/metrics/summary` - Métricas generales
  - [ ] `GET /api/v1/metrics/intents` - Estadísticas de intents
  - [ ] `GET /api/v1/metrics/entities` - Estadísticas de entities
  - [ ] `GET /api/v1/metrics/conversations` - Datos de conversaciones
- [ ] Crear servicio `api/services/metrics_service.py`
- [ ] Queries SQL optimizadas con agregaciones
- [ ] Cache con Redis para métricas pesadas

#### 4. Integración con RASA
- [ ] Cliente para RASA API en `api/utils/rasa_client.py`
- [ ] Leer eventos de la tabla `events` de PostgreSQL
- [ ] Parser de eventos RASA a formato interno
- [ ] Sincronización de datos en background con Celery

---

## FASE 2: ANOTACIÓN (PENDIENTE 🔄)

### Duración Estimada: Semanas 4-5

### Objetivos
Herramientas para corregir y anotar intents/entities en conversaciones.

### Tareas Pendientes

#### 1. Interface de Anotación
- [ ] Página de anotación (`pages/4_✏️_Anotaciones.py`)
- [ ] Selector de conversaciones pendientes
- [ ] Editor de intent con autocomplete
- [ ] Editor de entities con highlight
- [ ] Validación de formato NLU
- [ ] Guardar anotaciones en tabla `annotations`

#### 2. Backend de Anotaciones
- [ ] Endpoints CRUD en `api/routers/annotations.py`:
  - [ ] `POST /api/v1/annotations` - Crear anotación
  - [ ] `GET /api/v1/annotations` - Listar anotaciones
  - [ ] `PUT /api/v1/annotations/{id}` - Actualizar
  - [ ] `DELETE /api/v1/annotations/{id}` - Eliminar
  - [ ] `POST /api/v1/annotations/{id}/approve` - Aprobar
- [ ] Servicio `api/services/annotation_service.py`
- [ ] Workflow de aprobación (qa_analyst → qa_lead)
- [ ] Logging de cambios

#### 3. Exportación a Formato RASA
- [ ] Convertir anotaciones a formato `nlu.yml`
- [ ] Validación con RASA CLI
- [ ] Preview antes de aplicar
- [ ] Merge con datos existentes

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

**Última actualización:** 2025-10-07
**Próximo paso:** Iniciar FASE 1 - Visualización

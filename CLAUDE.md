# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **dual-component system** consisting of:

1. **RASA Chatbot**: Spanish-language conversational AI for an e-commerce clothing store (RASA 3.6.19)
2. **Training Platform**: Web-based QA and training management platform (FastAPI + Streamlit)

The system uses Docker containers for orchestration, PostgreSQL for data persistence, and includes custom actions for order processing, inventory management, customer interactions, plus a full training/analytics platform for improving the bot.

## Architecture

### Multi-Container Docker Setup

The system runs 10 services organized into two subsystems (see docker-compose.yml:1):

**RASA Chatbot Services (5):**
1. **postgres** (port 5432): PostgreSQL 15 database with pre-initialized schema and sample data
2. **rasa-action-server** (port 5055): Custom action server handling business logic and database operations
3. **rasa-server** (port 5005): Main RASA NLU/Core server with REST API
4. **telegram-bot**: Telegram bot connector using aiogram that communicates with RASA via REST API
5. **portainer** (ports 9000/9443): Container management UI

**Training Platform Services (5):**
6. **redis** (port 6379): Cache and message broker for Celery
7. **api-server** (port 8000): FastAPI backend for training platform with JWT authentication
8. **celery-worker**: Background task processor for async operations (training, reporting)
9. **flower** (port 5555): Celery monitoring dashboard
10. **training-platform** (port 8501): Streamlit frontend for QA analysts and developers

### Database Schema

The PostgreSQL database contains two main schema groups:

**E-commerce Tables (init-db.sql:1):**
- **Core business tables**: `customers`, `products`, `inventory`, `orders`, `order_details`, `shipping_data`, `product_characteristics`
- **RASA-specific tables**: `events` (tracker store), `rasa_conversations`, `conversaciones_chatbot` (logging)
- **Sample data**: 5 products with inventory, characteristics (sizes/colors), and pricing tiers (individual, wholesale, bundle)

Key business logic:
- Products have 3 pricing tiers: individual, wholesale (6+ units), bundle (12 units)
- Automatic order number generation via trigger: `ORD-YYYYMMDD-000001` format
- Inventory tracking with `available_quantity` and `reserved_quantity`

**Training Platform Tables (database/init-platform-tables.sql):**
- **platform_users**: Authentication with bcrypt passwords, role-based access (viewer, developer, qa_analyst, qa_lead, admin)
- **annotations**: Manual corrections of intents/entities for improving training data
- **training_jobs**: History of training runs with metrics (accuracy, F1, loss)
- **deployed_models**: Deployed model registry with performance tracking
- **activity_logs**: Audit trail for all user actions
- **test_cases**: Test suite for regression testing
- **test_results**: Test execution results linked to models
- **conversation_reviews**: QA review workflow for flagged conversations

**Data Synchronization (database/03-sync-rasa-conversations.sql):**
- **Automatic sync trigger**: PostgreSQL trigger that automatically populates `rasa_conversations` from `events` table
- **How it works**: Every time RASA inserts an event, the trigger creates/updates a record in `rasa_conversations`
- **When applied**: Automatically on fresh database creation (docker-compose.yml:17), or manually on existing databases
- **Backfill script**: `scripts/sync_existing_conversations.py` syncs existing events data (run once after applying trigger)
- **Purpose**: Enables dashboard metrics for conversation counts, timelines, and heatmaps without manual intervention

### Custom Actions

Actions are organized in a modular structure under `actions/` directory. See actions/README.md for full documentation.

**Module Structure:**
- `actions/database/`: Database connection management (DatabaseConnection class) and SQL queries
- `actions/catalog/`: Catalog-related actions (ActionMostrarCatalogo)
- `actions/cart/`: Shopping cart actions and utilities (ActionAgregarAlCarrito, ActionRecuperarCarrito)
- `actions/orders/`: Placeholder for future order processing actions
- `actions/utils/`: Shared helper functions (normalize_product_name)

**Key Actions:**
- **ActionMostrarCatalogo** (actions/catalog/catalog_actions.py): Displays full product catalog with prices, stock availability
- **ActionAgregarAlCarrito** (actions/cart/cart_actions.py): Adds products to cart, calculates pricing tiers (individual/wholesale/bundle)
- **ActionRecuperarCarrito** (actions/cart/cart_actions.py): Recovers cart from previous session using events table

Database connection uses environment variables: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (docker-compose.yml:32-37)

### RASA Configuration

- **Language**: Spanish (config.yml:1)
- **NLU Pipeline** (config.yml:3-21): WhitespaceTokenizer, RegexFeaturizer, LexicalSyntacticFeaturizer, CountVectorsFeaturizer (word + char n-grams), DIETClassifier (100 epochs), EntitySynonymMapper, ResponseSelector, FallbackClassifier (0.3 threshold)
- **Policies** (config.yml:23-36): Default policies (commented out in config, auto-configured by RASA: MemoizationPolicy, RulePolicy, UnexpecTEDIntentPolicy, TEDPolicy)
- **Intents** (domain.yml:3-10): saludar, despedir, consultar_catalogo, agregar_al_carrito, consultar_envios, consultar_pagos
- **Entities** (domain.yml:11-13): producto, cantidad
- **Slots** (domain.yml:15-47):
  - `producto_seleccionado` (text): Tracks product user wants to add
  - `cantidad` (float): Quantity of product
  - `carrito_productos` (list): Full shopping cart state with product details
  - `carrito_total` (float): Total cart value
  - `carrito_cantidad_items` (float): Total item count in cart
- **Session config** (domain.yml:79-81): 24-hour expiration with slot carry-over enabled

### Training Platform Architecture

The Training Platform is a full-stack Python application designed to reduce QA time by 60% and improve bot accuracy from 87% to 95%.

**Backend (FastAPI):**
- **api/main.py**: FastAPI app with CORS, health checks, and router registration
- **api/routers/**: REST API endpoints
  - `auth.py`: JWT authentication (login, register, logout, me)
  - `metrics.py`: Dashboard metrics (summary, timeline, intents, heatmap, funnel)
  - `conversations.py`: Conversation viewing and filtering with pagination
  - `annotations.py`: Annotation CRUD with approval workflow (qa_analyst → qa_lead)
  - `export.py`: Export annotations to RASA NLU format (YAML download)
- **api/services/**: Business logic layer
  - `auth_service.py`: User authentication and authorization
  - `metrics_service.py`: Complex queries for dashboard analytics using Guatemala timezone
  - `conversation_service.py`: Conversation queries with filtering and CSV export
  - `annotation_service.py`: Annotation management with permission checks and activity logging
  - `export_service.py`: Converts annotations to RASA NLU YAML format with validation
- **api/database/connection.py**: SQLAlchemy engine and session management
- **api/schemas/db_models.py**: ORM models for all 8 platform tables
- **api/models/auth.py**: Pydantic models for request/response validation
- **api/utils/security.py**: Bcrypt password hashing and JWT token generation
- **api/dependencies.py**: FastAPI dependency injection (get_db, get_current_user)
- **api/config.py**: Pydantic Settings for environment configuration

**Frontend (Streamlit):**
- **training_platform/app.py**: Main entry point with authentication check
- **training_platform/pages/**: Multi-page app structure
  - `1_🔐_Login.py`: Login page with form and session management
  - `2_📊_Dashboard.py`: Metrics dashboard with Plotly charts (timeline, intents, heatmap, funnel)
- **training_platform/utils/**: Shared utilities
  - `api_client.py`: HTTP client for FastAPI backend (login, logout, get_current_user, _make_request)
  - `session.py`: Session management with `require_auth()` and `get_current_user()`

**Key Implementation Details:**
- JWT tokens expire after 120 minutes (configurable in api/config.py)
- Passwords are hashed with bcrypt (72-byte limit, auto-truncated)
- Role-based access control (RBAC) with 5 levels: viewer(1), developer(2), qa_analyst(3), qa_lead(4), admin(5)
- Metrics service uses Guatemala timezone (America/Guatemala) for date calculations
- Dashboard queries the `events` table (RASA tracker store) for intent/entity statistics
- Sample data can be seeded using `scripts/seed_sample_data.py`

## Common Commands

### Starting/Stopping Services

```bash
# Start all services
./start-rasa.sh

# Stop all services
./stop-rasa.sh

# Quick rebuild (preserves DB by default)
./quick-rebuild.sh

# View logs
./logs-rasa.sh
docker compose logs -f rasa-server
docker compose logs -f rasa-action-server
```

### Training and Testing

```bash
# Train model (inside rasa-server container)
docker exec -it rasa_server rasa train

# Test NLU
docker exec -it rasa_server rasa test nlu --nlu data/nlu.yml

# Interactive testing
docker exec -it rasa_server rasa shell

# Test via API
curl -X POST http://localhost:5005/webhooks/rest/webhook \
  -H "Content-Type: application/json" \
  -d '{"sender":"test_user","message":"hola"}'
```

### Database Operations

```bash
# Connect to PostgreSQL
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot

# View products
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT * FROM products;"

# Check inventory
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT p.name, i.available_quantity FROM products p JOIN inventory i ON p.id = i.product_id;"

# View platform users
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "SELECT id, username, email, role, is_active FROM platform_users;"
```

### Training Platform Operations

```bash
# Create admin user (default: admin/Admin123!)
docker compose exec api-server python scripts/create_admin_user.py

# Create custom admin user
docker compose exec api-server python scripts/create_admin_user.py \
  --username "mi_admin" \
  --email "admin@example.com" \
  --password "MiPassword123!" \
  --full-name "Super Admin"

# Seed sample data for dashboard testing
docker compose exec api-server python scripts/seed_sample_data.py

# Apply rasa_conversations sync trigger (one-time setup)
cat database/03-sync-rasa-conversations.sql | docker exec -i rasa_postgres psql -U rasa_user -d rasa_chatbot

# Sync existing events to rasa_conversations (after applying trigger)
docker compose exec api-server python scripts/sync_existing_conversations.py

# View API logs
docker compose logs -f api-server

# View Streamlit logs
docker compose logs -f training-platform

# Test API health
curl http://localhost:8000/health

# Test login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'

# View Celery tasks (Flower UI)
# Open browser: http://localhost:5555
```

### Development Workflow

```bash
# === RASA Development ===

# After modifying actions/ code (any module)
docker compose restart rasa-action-server

# Verify actions are registered correctly
curl http://localhost:5055/actions

# After modifying domain.yml, config.yml, or data/
docker exec -it rasa_server rasa train
docker compose restart rasa-server

# === Training Platform Development ===

# After modifying api/ code (backend)
docker compose restart api-server

# After modifying api/ schemas or models (requires table recreation)
docker compose down api-server
docker compose up -d api-server

# After modifying training_platform/ code (frontend)
docker compose restart training-platform

# After modifying database/init-platform-tables.sql
# WARNING: This drops all platform data!
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -c "DROP TABLE IF EXISTS activity_logs, test_results, test_cases, conversation_reviews, annotations, training_jobs, deployed_models, platform_users CASCADE;"
docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot \
  -f /docker-entrypoint-initdb.d/init-platform-tables.sql
docker compose exec api-server python scripts/create_admin_user.py

# === Complete Rebuild ===

# Rebuild all services (preserves database)
docker compose down
docker compose build --no-cache
docker compose up -d

# Rebuild with fresh database (WARNING: Deletes all data!)
docker compose down -v
docker compose build --no-cache
docker compose up -d

# Wait for services to be healthy
sleep 10

# Initialize platform data (run these in order)
docker compose exec api-server python scripts/create_admin_user.py
docker compose exec api-server python scripts/sync_existing_conversations.py  # Sync any RASA events
docker compose exec api-server python scripts/seed_sample_data.py  # Optional: add sample data
```

## Key Files and Their Roles

**RASA Chatbot:**
- **domain.yml:1**: Defines intents, entities, slots, responses, actions, forms - the core conversational model
- **config.yml:1**: NLU pipeline and policy configuration for Spanish language
- **data/nlu.yml**: Training examples for intent classification and entity extraction
- **data/stories.yml:1**: Conversation flows and dialogue management patterns
- **data/rules.yml**: Rule-based dialogue patterns (greetings, fallbacks)
- **actions/**: Modular custom action server (see actions/README.md for details)
  - **actions.py**: Entry point compatible with RASA
  - **database/**: Connection management and SQL queries
  - **catalog/**, **cart/**, **orders/**, **forms/**: Domain-specific action modules
  - **utils/**: Shared helper functions
- **endpoints.yml:1**: Configuration for action server endpoint (no tracker store - uses in-memory)
- **init-db.sql:1**: PostgreSQL schema initialization with sample data for e-commerce
- **telegram_bot.py**: Telegram bot integration using aiogram library

**Training Platform:**
- **api/main.py**: FastAPI application entry point with router registration
- **api/routers/**: REST API endpoints (auth, metrics)
- **api/services/**: Business logic layer (auth_service, metrics_service)
- **api/database/connection.py**: SQLAlchemy database connection
- **api/schemas/db_models.py**: ORM models for 8 platform tables
- **api/models/auth.py**: Pydantic request/response models
- **api/utils/security.py**: Bcrypt and JWT implementation
- **api/config.py**: Pydantic Settings for environment variables
- **training_platform/app.py**: Streamlit main page
- **training_platform/pages/**: Multi-page Streamlit app (Login, Dashboard)
- **training_platform/utils/**: API client and session management
- **database/init-platform-tables.sql**: Platform database schema (8 tables)
- **database/03-sync-rasa-conversations.sql**: PostgreSQL trigger for automatic conversation sync
- **scripts/create_admin_user.py**: Admin user creation script
- **scripts/seed_sample_data.py**: Sample data generator for testing dashboard
- **scripts/sync_existing_conversations.py**: Backfill script to sync existing events to rasa_conversations

**Configuration:**
- **docker-compose.yml**: Orchestrates 10 services (5 RASA + 5 Training Platform)
- **.env**: Environment variables (database, JWT, Redis, Telegram token)
- **DESARROLLO.md**: Development progress tracking and phase documentation

## Important Development Notes

### Action Server Development

- All actions must inherit from `rasa_sdk.Action` and implement `name()` and `run()` methods
- Actions are organized by domain: catalog/, cart/, orders/, etc. See actions/README.md for details
- Use the shared `db` instance from `actions.database` for queries: `from actions.database import db`
- The `execute_query()` method returns `RealDictCursor` results (dict-like rows) when `fetch=True`
- Always use parameterized queries to prevent SQL injection: `db.execute_query(query, (param1, param2), fetch=True)`
- SQL queries should be defined as constants in `actions/database/queries.py` for reusability
- Return `SlotSet` events from actions to update conversation state: `return [SlotSet("slot_name", value)]`
- Shopping cart logic: Products are stored in `carrito_productos` slot as list of dicts with product_id, quantity, unit_price, subtotal
- Business logic should be extracted to utility functions (e.g., cart_utils.py) for testability

### Training Data Guidelines

- NLU examples in data/nlu.yml should be in Spanish with realistic user variations
- Stories in data/stories.yml define multi-turn conversation flows
- Use `slot_was_set` in stories to track entity extraction
- Add rules in data/rules.yml for deterministic responses (greetings, fallbacks)

### Training Platform Development

**Backend (FastAPI) Guidelines:**
- All database operations use SQLAlchemy ORM (api/schemas/db_models.py)
- Business logic goes in `api/services/`, NOT in routers (thin controllers pattern)
- All endpoints require authentication via `Depends(get_current_user)` except login/register
- Use Pydantic models in `api/models/` for request/response validation
- Complex queries with raw SQL use `text()` from SQLAlchemy and parameterized queries
- Timezone-aware: All date operations use Guatemala timezone (`pytz.timezone('America/Guatemala')`)
- RASA events table uses Unix timestamps (float), convert with `.timestamp()` for queries
- Activity logging: All user actions should create entries in `activity_logs` table
- Password security: Bcrypt automatically handles salt, max 72 bytes (truncated in security.py)

**Frontend (Streamlit) Guidelines:**
- All pages must call `require_auth()` at the top to enforce authentication
- API calls use `api_client._make_request(method, endpoint, **kwargs)` for authenticated requests
- Session state management: `st.session_state.authenticated`, `st.session_state.user`, `st.session_state.token`
- Charts use Plotly for interactivity (px for simple charts, go for complex ones)
- Use `st.spinner()` for loading states during API calls
- Error handling: Wrap API calls in try/except and use `st.error()` to display friendly messages
- Sidebar pattern: Show user info and logout button in sidebar on all authenticated pages

**Database Schema Changes:**
- Platform tables are in `database/init-platform-tables.sql`
- After modifying SQL schema, must drop and recreate tables (see Development Workflow section)
- ORM models in `api/schemas/db_models.py` must match SQL schema exactly
- Foreign keys: Use `deployed_by` references `platform_users(id)`, etc.
- JSONB fields: `performance_metrics`, `training_config` use PostgreSQL JSONB for flexibility

**Metrics Service Implementation:**
- Summary metrics aggregate from multiple tables (rasa_conversations, events, deployed_models)
- Intent stats query the `events` table where `type_name = 'user'`
- Confidence scores: Use `data::jsonb->'parse_data'->'intent'->>'confidence'` (explicit casting from TEXT)
- Timeline queries use `DATE()` grouping for daily aggregations
- Heatmap uses `EXTRACT(DOW)` and `EXTRACT(HOUR)` for day-of-week and hour extraction

**IMPORTANT: events.data Column Type (TEXT vs JSONB):**
- The `events.data` column is defined as **TEXT** (not JSONB) for RASA compatibility
- **Reason**: RASA 3.6.19 with psycopg2 has a deserialization bug with JSONB columns
- **Symptom**: Error "the JSON object must be str, bytes or bytearray, not dict" → fallback to InMemoryTrackerStore → loss of 80-90% of conversation events
- **Solution**: Changed from JSONB to TEXT in init-db.sql:126-137 and database/04-fix-events-jsonb-to-text.sql
- **Query Pattern**: Always use explicit casting `data::jsonb->` when querying JSON properties (e.g., `data::jsonb->'parse_data'->'intent'->>'confidence'`)
- **Performance**: Casting adds ~0.1ms per query, negligible for dashboard use cases
- **Migration**: For existing databases, apply database/04-fix-events-jsonb-to-text.sql and update api/services/metrics_service.py queries

**Annotation and Export System Implementation:**
- **Approval Workflow**: qa_analyst creates annotations → qa_lead approves/rejects → approved annotations ready for export
- **Status States**: pending (initial) → approved/rejected (qa_lead action) → trained/deployed (after training)
- **Permission Layers**: Implemented in service layer with helper functions (`_check_user_permissions`, `_check_annotation_exists`)
- **Activity Logging**: All CRUD operations automatically logged to `activity_logs` table with user, action, details
- **Entity Format**: Stored as JSONB array with structure: `[{entity, value, start, end}]`
- **RASA NLU Export**: Converts annotations to YAML format with markdown entities: `[text](entity_type)`
- **YAML Generation**: Manual string construction for precise format control (not PyYAML dump)
- **Validation Layers**: (1) Format validation (YAML structure), (2) Domain validation (intents/entities exist in events table)
- **Export Filters**: Support date ranges (`from_date`, `to_date`) and intent filtering
- **Export Service Pattern**: Service layer returns data structures, router layer handles HTTP concerns
- **Example YAML Output**:
  ```yaml
  version: "3.1"
  nlu:
  - intent: consultar_catalogo
    examples: |
      - quiero ver productos
      - muéstrame el [catálogo](producto)
  ```

### Database Modifications

**⚠️ CRITICAL POLICY: All database changes MUST follow this checklist:**

When making ANY database schema changes, you MUST complete ALL of the following steps to ensure the solution works on fresh installations and other machines:

1. **Update Init Scripts** (MANDATORY):
   - [ ] Update `init-db.sql` (for RASA/e-commerce tables) OR `database/init-platform-tables.sql` (for platform tables)
   - [ ] Add comments explaining WHY the schema is designed this way (especially for non-obvious decisions)
   - [ ] Test fresh installation: `docker compose down -v && docker compose up -d`

2. **Create Migration Script** (if database already exists):
   - [ ] Create numbered migration file in `database/` (e.g., `05-add-new-column.sql`)
   - [ ] Include both UP and DOWN migration paths if possible
   - [ ] Test migration on existing database

3. **Update Application Code**:
   - [ ] Update ORM models in `api/schemas/db_models.py` (if using SQLAlchemy)
   - [ ] Update any raw SQL queries that reference the modified tables
   - [ ] Update Pydantic models if API contracts changed

4. **Update Documentation**:
   - [ ] Document the change in this CLAUDE.md file (in relevant section)
   - [ ] Add troubleshooting notes if the change might cause issues
   - [ ] Update DESARROLLO.md if it's a significant milestone

5. **Verification**:
   - [ ] Test on fresh database: `docker compose down -v && docker compose up -d`
   - [ ] Test migration on existing database
   - [ ] Verify all related queries still work
   - [ ] Check that dashboard/API endpoints return expected data

**General Guidelines:**
- Schema changes require updating init-db.sql:1 and rebuilding with `docker compose down -v`
- The `rasa_user` has full privileges on all tables
- Use English table/column names (recent migration from Spanish names)
- Triggers auto-update `updated_at` timestamps on customers, products, inventory, orders
- PostgreSQL extension `pg_trgm` enabled for fuzzy product name matching (init-db.sql:10)

**Important: rasa_conversations Sync Trigger**
- Fresh database: Trigger applies automatically via docker-compose.yml:17
- Existing database: Apply manually with `cat database/03-sync-rasa-conversations.sql | docker exec -i rasa_postgres psql -U rasa_user -d rasa_chatbot`
- After applying trigger: Run `docker compose exec api-server python scripts/sync_existing_conversations.py` to backfill
- Verification: Check trigger exists with `\df sync_rasa_conversations_from_events` in psql

### Environment Configuration

- Copy `.env` file (use `.env` as template) for environment variables
- Database credentials in docker-compose.yml:6-10:
  ```
  POSTGRES_DB: rasa_chatbot
  POSTGRES_USER: rasa_user
  POSTGRES_PASSWORD: rasa_password_2024
  ```
- Same credentials must be used in action-server environment (docker-compose.yml:32-37)
- Telegram bot requires `TELEGRAM_TOKEN` and `RASA_URL` in .env file (docker-compose.yml:87-91)

### Access Points

**RASA Chatbot:**
- **Portainer UI**: https://localhost:9443 (container management)
- **RASA API**: http://localhost:5005 (chat endpoint: /webhooks/rest/webhook)
- **Action Server**: http://localhost:5055/health (health check), http://localhost:5055/actions (list registered actions)
- **PostgreSQL**: localhost:5432 (from host machine)
- **Telegram Bot**: Connects via environment variable RASA_URL (typically http://rasa-server:5005/webhooks/rest/webhook)

**Training Platform:**
- **Streamlit Frontend**: http://localhost:8501 (login page, dashboard, future pages)
- **FastAPI Backend**: http://localhost:8000 (API root)
- **API Documentation**: http://localhost:8000/docs (Swagger UI), http://localhost:8000/redoc (ReDoc)
- **Flower Dashboard**: http://localhost:5555 (Celery task monitoring)
- **Redis**: localhost:6379 (not exposed to host by default)

## Testing de Endpoints

### ⚠️ IMPORTANTE: Evitar Desbordamiento de Tokens

Cuando pruebas endpoints de API con curl, **NUNCA** uses JSON inline con comillas escapadas ya que esto puede causar errores de parsing y desperdiciar tokens en múltiples intentos.

**❌ INCORRECTO** (causa errores de JSON decode):
```bash
# NO HACER ESTO - Las comillas causan problemas de escape
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin123!"}'
```

**✅ CORRECTO** (usa archivos temporales):
```bash
# Método 1: Crear archivo JSON temporal y usarlo
cat > /tmp/login.json << 'EOF'
{
  "username": "admin",
  "password": "Admin123!"
}
EOF

curl -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json | jq '.'
```

**✅ TAMBIÉN CORRECTO** (usa heredoc inline):
```bash
# Método 2: Heredoc inline con cat
curl -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @- << 'EOF' | jq '.'
{
  "username": "admin",
  "password": "Admin123!"
}
EOF
```

### Patrón Recomendado para Testing de Endpoints

**1. Obtener Token de Autenticación:**
```bash
# Guardar token en variable
TOKEN=$(cat > /tmp/login.json << 'EOF'
{
  "username": "admin",
  "password": "Admin123!"
}
EOF
curl -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json 2>/dev/null | jq -r '.access_token')

# Verificar que el token se obtuvo correctamente
echo "Token: $TOKEN"
```

**2. Probar Endpoint GET con Autenticación:**
```bash
curl -X GET 'http://localhost:8000/api/v1/annotations/stats' \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null | jq '.'
```

**3. Probar Endpoint POST con JSON Complejo:**
```bash
# Crear archivo con payload complejo
cat > /tmp/annotation.json << 'EOF'
{
  "conversation_id": "test_user_123",
  "message_text": "Quiero comprar una blusa",
  "original_intent": "saludar",
  "corrected_intent": "consultar_catalogo",
  "original_confidence": 0.45,
  "original_entities": [],
  "corrected_entities": [
    {
      "entity": "producto",
      "value": "blusa",
      "start": 14,
      "end": 19
    }
  ],
  "annotation_type": "both",
  "notes": "El usuario claramente quiere consultar el catálogo, no saludar"
}
EOF

# Hacer request
curl -X POST 'http://localhost:8000/api/v1/annotations' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d @/tmp/annotation.json 2>/dev/null | jq '.'
```

**4. Probar Múltiples Endpoints en Secuencia:**
```bash
# Guardar token
TOKEN=$(cat > /tmp/login.json << 'EOF'
{"username": "admin", "password": "Admin123!"}
EOF
curl -X POST 'http://localhost:8000/api/v1/auth/login' \
  -H 'Content-Type: application/json' \
  -d @/tmp/login.json 2>/dev/null | jq -r '.access_token')

# Test 1: Stats
echo "=== Estadísticas ==="
curl -X GET 'http://localhost:8000/api/v1/annotations/stats' \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null | jq '.'

# Test 2: Crear anotación
echo "=== Crear Anotación ==="
cat > /tmp/annotation.json << 'EOF'
{"conversation_id": "test", "message_text": "hola", "corrected_intent": "saludar", "annotation_type": "intent"}
EOF
curl -X POST 'http://localhost:8000/api/v1/annotations' \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d @/tmp/annotation.json 2>/dev/null | jq '.id'

# Test 3: Listar
echo "=== Listar Anotaciones ==="
curl -X GET 'http://localhost:8000/api/v1/annotations?page=1&page_size=10' \
  -H "Authorization: Bearer $TOKEN" 2>/dev/null | jq '.items | length'
```

### Usar Swagger UI para Testing Manual

**Alternativa recomendada:** Usa Swagger UI en http://localhost:8000/docs para testing manual:

1. Abrir http://localhost:8000/docs en el navegador
2. Click en "Authorize" en la esquina superior derecha
3. Hacer login con `POST /api/v1/auth/login`
4. Copiar el `access_token` de la respuesta
5. Pegar en el campo "Value" con el formato: `Bearer YOUR_TOKEN_HERE`
6. Click "Authorize" y luego "Close"
7. Ahora todos los endpoints autenticados se pueden probar directamente desde la UI

**Ventajas de Swagger UI:**
- No hay problemas de escape de JSON
- Validación automática de esquemas
- Documentación inline
- Menor consumo de tokens
- Más rápido para testing exploratorio

### Testing Automatizado

Para testing más robusto, considera crear scripts de prueba en Python:

```python
# scripts/test_annotations_api.py
import requests
import json

BASE_URL = "http://localhost:8000"

# Login
login_data = {"username": "admin", "password": "Admin123!"}
response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)
token = response.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

# Test stats
response = requests.get(f"{BASE_URL}/api/v1/annotations/stats", headers=headers)
print("Stats:", response.json())

# Test create
annotation = {
    "conversation_id": "test_001",
    "message_text": "quiero una blusa",
    "corrected_intent": "consultar_catalogo",
    "annotation_type": "intent"
}
response = requests.post(f"{BASE_URL}/api/v1/annotations", json=annotation, headers=headers)
print("Created:", response.json()["id"])
```

### Resumen de Mejores Prácticas

1. **Usar archivos temporales** para JSON payloads (evita problemas de escape)
2. **Guardar tokens en variables** para reutilización
3. **Usar jq para formatear** respuestas JSON (más legible)
4. **Redirigir stderr** con `2>/dev/null` para ocultar progress de curl
5. **Usar Swagger UI** para testing exploratorio manual
6. **Crear scripts Python** para testing repetitivo o CI/CD
7. **Nunca hacer múltiples intentos** con inline JSON si falla - cambiar a archivo temporal inmediatamente

---

## Troubleshooting

### Services won't start
- Check Docker is running: `docker info`
- View logs: `docker compose logs`
- Ensure ports 5005, 5055, 5432, 9000, 9443 are not in use

### Action server can't connect to database
- Verify postgres service is healthy: `docker compose ps`
- Check environment variables in docker-compose.yml:32-37
- Ensure postgres service starts before action-server (depends_on with health check)

### Model not loading
- Ensure models/ directory exists with trained model: `ls -la models/`
- Train if needed: `docker exec -it rasa_server rasa train`
- Check rasa-server logs for errors

### Database connection errors in actions
- The action server waits for postgres health check (docker-compose.yml:42-44)
- Connection details in DatabaseConnection class (actions/database/connection.py:12-19)
- Test connection: `docker exec -it rasa_action_server python -c "from actions.database import db; print(db.get_connection())"`

### Telegram bot issues
- Ensure .env file exists with valid `TELEGRAM_TOKEN` and `RASA_URL`
- Check logs: `docker compose logs -f telegram-bot`
- Verify rasa-server is running and accessible from telegram-bot container
- Bot uses aiogram library and connects via REST API (telegram_bot.py:1-101)

### Training Platform API issues
- Check if all services are healthy: `docker compose ps`
- Verify environment variables in .env file (SECRET_KEY, JWT_SECRET_KEY, API_URL)
- Test API health: `curl http://localhost:8000/health`
- View detailed logs: `docker compose logs -f api-server`
- Common issue: Import errors - ensure PYTHONPATH=/app is set in Dockerfile

### Training Platform authentication issues
- Ensure admin user is created: `docker compose exec api-server python scripts/create_admin_user.py`
- Check if platform_users table exists: `docker exec -it rasa_postgres psql -U rasa_user -d rasa_chatbot -c "SELECT * FROM platform_users;"`
- JWT token issues: Verify SECRET_KEY matches between api-server and training-platform containers
- Password issues: Remember bcrypt 72-byte limit, special characters may cause issues in shell

### Dashboard showing no data
- Seed sample data: `docker compose exec api-server python scripts/seed_sample_data.py`
- Check if rasa_conversations and events tables have data
- Verify metrics service timezone (should use America/Guatemala)
- Check API logs for SQL errors: `docker compose logs -f api-server | grep ERROR`

### Celery/Redis issues
- Verify Redis is running: `docker compose ps redis`
- Check Celery worker logs: `docker compose logs -f celery-worker`
- View tasks in Flower: http://localhost:5555
- Redis connection: Celery uses redis://redis:6379/0 as broker URL
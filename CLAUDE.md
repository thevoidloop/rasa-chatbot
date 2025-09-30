# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Spanish-language RASA chatbot for an e-commerce clothing store. The system uses RASA 3.6.19 with Docker containers for orchestration, PostgreSQL for data persistence, and includes custom actions for order processing, inventory management, and customer interactions.

## Architecture

### Multi-Container Docker Setup

The system runs 4 main services (see docker-compose.yml:1):

1. **postgres** (port 5432): PostgreSQL 15 database with pre-initialized schema and sample data
2. **rasa-action-server** (port 5055): Custom action server handling business logic and database operations
3. **rasa-server** (port 5005): Main RASA NLU/Core server with REST API
4. **portainer** (ports 9000/9443): Container management UI

### Database Schema

The PostgreSQL database (init-db.sql:1) contains:

- **Core business tables**: `customers`, `products`, `inventory`, `orders`, `order_details`, `shipping_data`, `product_characteristics`
- **RASA-specific tables**: `events` (tracker store), `rasa_conversations`, `conversaciones_chatbot` (logging)
- **Sample data**: 5 products with inventory, characteristics (sizes/colors), and pricing tiers (individual, wholesale, bundle)

Key business logic:
- Products have 3 pricing tiers: individual, wholesale (6+ units), bundle (12 units)
- Automatic order number generation via trigger: `ORD-YYYYMMDD-000001` format
- Inventory tracking with `available_quantity` and `reserved_quantity`

### Custom Actions

All custom actions are in actions/actions.py:1 and use a shared `DatabaseConnection` class (actions/actions.py:15):

- **ActionMostrarCatalogo**: Displays full product catalog with prices, stock, sizes, colors
- **ActionMostrarCatalogoPorCategoria**: Filters products by category using flexible search
- **ActionConsultarPrecio**: Shows detailed pricing with savings calculations for bulk purchases
- **ActionVerificarDisponibilidad**: Checks stock availability for requested quantities
- **ActionLogConversacion**: Logs user interactions with intents/entities for analytics

Database connection uses environment variables: `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (docker-compose.yml:32-37)

### RASA Configuration

- **Language**: Spanish (config.yml:1)
- **NLU Pipeline** (config.yml:3-20): WhitespaceTokenizer, DIETClassifier (100 epochs), ResponseSelector, FallbackClassifier (0.3 threshold)
- **Intents** (domain.yml:3-17): saludar, consultar_catalogo, consultar_precio, hacer_pedido, etc.
- **Entities** (domain.yml:19-27): producto, categoria, cantidad, talla, color, telefono, nombre, direccion
- **Slots** (domain.yml:29-108): Conversation slots for product selection, order data, customer information
- **Form** (domain.yml:201-206): `form_datos_cliente` collects name, phone, address for orders

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
```

### Development Workflow

```bash
# After modifying actions/actions.py
docker compose restart rasa-action-server

# After modifying domain.yml, config.yml, or data/
docker exec -it rasa_server rasa train
docker compose restart rasa-server

# Complete rebuild (development)
docker compose down -v
docker compose build --no-cache
docker compose up -d
```

## Key Files and Their Roles

- **domain.yml:1**: Defines intents, entities, slots, responses, actions, forms - the core conversational model
- **config.yml:1**: NLU pipeline and policy configuration for Spanish language
- **data/nlu.yml**: Training examples for intent classification and entity extraction
- **data/stories.yml:1**: Conversation flows and dialogue management patterns
- **data/rules.yml**: Rule-based dialogue patterns (greetings, fallbacks)
- **actions/actions.py:1**: Custom action server with database integration
- **endpoints.yml:1**: Configuration for action server endpoint (no tracker store - uses in-memory)
- **init-db.sql:1**: PostgreSQL schema initialization with sample data

## Important Development Notes

### Action Server Development

- All actions must inherit from `rasa_sdk.Action` and implement `name()` and `run()` methods
- Use the shared `db = DatabaseConnection()` instance (actions/actions.py:58) for queries
- The `execute_query()` method returns `RealDictCursor` results (dict-like rows)
- Always use parameterized queries to prevent SQL injection: `db.execute_query(query, (param1, param2), fetch=True)`

### Training Data Guidelines

- NLU examples in data/nlu.yml should be in Spanish with realistic user variations
- Stories in data/stories.yml define multi-turn conversation flows
- Use `slot_was_set` in stories to track entity extraction
- Add rules in data/rules.yml for deterministic responses (greetings, fallbacks)

### Database Modifications

- Schema changes require updating init-db.sql:1 and rebuilding with `docker compose down -v`
- The `rasa_user` has full privileges on all tables (init-db.sql:308)
- Use English table/column names (recent migration from Spanish names)
- Triggers auto-update `updated_at` timestamps on customers, products, inventory, orders

### Environment Configuration

Database credentials in docker-compose.yml:6-10:
```
POSTGRES_DB: rasa_chatbot
POSTGRES_USER: rasa_user
POSTGRES_PASSWORD: rasa_password_2024
```

Same credentials must be used in action-server environment (docker-compose.yml:32-37).

### Access Points

- **Portainer UI**: https://localhost:9443 (container management)
- **RASA API**: http://localhost:5005 (chat endpoint: /webhooks/rest/webhook)
- **Action Server Health**: http://localhost:5055/health
- **PostgreSQL**: localhost:5432 (from host machine)

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
- Connection details in DatabaseConnection class (actions/actions.py:19-25)
- Test connection: `docker exec -it rasa_action_server python -c "from actions.actions import db; print(db.get_connection())"`
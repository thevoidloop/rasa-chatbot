# 🗄️ Database Change Policy

> **This file defines the mandatory process for ALL database schema changes**
>
> Claude Code reads this policy automatically from CLAUDE.md

## 📋 Mandatory Checklist

Every database change MUST complete ALL 5 steps:

### ✅ Step 1: Update Init Scripts
```bash
# For RASA/e-commerce tables:
📝 Edit: init-db.sql

# For Training Platform tables:
📝 Edit: database/init-platform-tables.sql

# Add explanatory comments for non-obvious decisions
# Test: docker compose down -v && docker compose up -d
```

### ✅ Step 2: Create Migration Script
```bash
# Create numbered file in database/
📝 Create: database/XX-descriptive-name.sql

# Include UP and DOWN migrations if possible
# Test on existing database
```

### ✅ Step 3: Update Application Code
```bash
# If using SQLAlchemy:
📝 Update: api/schemas/db_models.py

# If using raw SQL:
📝 Update: api/services/*.py (any queries referencing changed tables)

# If API contracts changed:
📝 Update: api/models/*.py (Pydantic models)
```

### ✅ Step 4: Update Documentation
```bash
# Document the change:
📝 Update: CLAUDE.md (relevant section)

# Add troubleshooting notes if needed:
📝 Update: CLAUDE.md (Troubleshooting section)

# If significant milestone:
📝 Update: DESARROLLO.md
```

### ✅ Step 5: Verification
```bash
# Test fresh install:
docker compose down -v && docker compose up -d

# Test migration (on copy of existing database):
cat database/XX-migration.sql | docker exec -i rasa_postgres psql -U rasa_user -d rasa_chatbot

# Verify queries work:
# - Test API endpoints
# - Check dashboard metrics
# - Run any affected scripts
```

## 🚨 Why This Matters

**Without following this checklist:**
- ❌ Fresh installations will fail on other machines
- ❌ Other developers will have broken databases
- ❌ Production deployments will require manual intervention
- ❌ You'll forget why you made the change in 6 months

**By following this checklist:**
- ✅ Works on ANY machine from day 1
- ✅ Self-documenting codebase
- ✅ Easy rollback if issues arise
- ✅ Future-you will thank present-you

## 📚 Examples

### Example 1: Adding a New Column
```sql
-- Step 1: Update init-db.sql
ALTER TABLE products ADD COLUMN barcode VARCHAR(50);

-- Step 2: Create migration (database/05-add-product-barcode.sql)
-- UP:
ALTER TABLE products ADD COLUMN IF NOT EXISTS barcode VARCHAR(50);
-- DOWN:
ALTER TABLE products DROP COLUMN IF EXISTS barcode;

-- Step 3: Update ORM model
class Product(Base):
    barcode = Column(String(50), nullable=True)

-- Step 4: Document in CLAUDE.md
-- Step 5: Test both scenarios
```

### Example 2: Changing Column Type (like JSONB → TEXT)
```sql
-- Step 1: Update init-db.sql
data TEXT  -- Changed from JSONB for RASA compatibility

-- Step 2: Create migration (database/04-fix-events-jsonb-to-text.sql)
ALTER TABLE events ALTER COLUMN data TYPE TEXT USING data::TEXT;

-- Step 3: Update all queries
-- Before: data->'parse_data'
-- After:  data::jsonb->'parse_data'

-- Step 4: Document WHY in CLAUDE.md (RASA bug)
-- Step 5: Test queries still return correct data
```

## 💡 Quick Reference Commands

```bash
# Fresh install test:
docker compose down -v && docker compose up -d && sleep 10 && docker compose ps

# Migration test:
cat database/XX-migration.sql | docker exec -i rasa_postgres psql -U rasa_user -d rasa_chatbot

# Verify table structure:
docker exec -i rasa_postgres psql -U rasa_user -d rasa_chatbot -c "\d table_name"

# Test API health:
curl http://localhost:8000/health

# Test dashboard queries:
docker compose logs -f api-server | grep ERROR
```

## 🎯 Remember

> "A database change without updating init scripts is a time bomb for future deployments."

**ALWAYS complete all 5 steps. No exceptions.**

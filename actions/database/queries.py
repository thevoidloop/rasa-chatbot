"""
SQL queries para el chatbot de e-commerce
Todas las queries están definidas como constantes para facilitar mantenimiento
"""

# Queries para catálogo de productos
GET_AVAILABLE_PRODUCTS = """
SELECT p.id, p.name, p.code, p.description,
       p.individual_price, p.wholesale_price, p.bundle_price,
       p.wholesale_quantity, p.bundle_quantity,
       i.available_quantity
FROM products p
LEFT JOIN inventory i ON p.id = i.product_id
WHERE p.active = true AND i.available_quantity > 0
ORDER BY p.name
"""

# Queries para búsqueda de productos con fuzzy matching
# Usa pg_trgm para calcular similitud de trigramas (tolerante a typos)
# Threshold: 0.2 = 20% de similitud mínima (balanceado para nombres compuestos)
FUZZY_SEARCH_PRODUCT = """
SELECT p.id, p.name, p.code, p.individual_price, p.wholesale_price,
       p.bundle_price, p.wholesale_quantity, p.bundle_quantity,
       i.available_quantity,
       similarity(LOWER(p.name), LOWER(%s)) AS match_score
FROM products p
LEFT JOIN inventory i ON p.id = i.product_id
WHERE p.active = true
  AND similarity(LOWER(p.name), LOWER(%s)) > 0.2
ORDER BY match_score DESC
LIMIT 1
"""

# Búsqueda LIKE tradicional (fallback si fuzzy matching no encuentra nada)
# Sin ELSE en ORDER BY para evitar devolver productos aleatorios
SEARCH_PRODUCT_BY_NAME = """
SELECT p.id, p.name, p.code, p.individual_price, p.wholesale_price,
       p.bundle_price, p.wholesale_quantity, p.bundle_quantity,
       i.available_quantity
FROM products p
LEFT JOIN inventory i ON p.id = i.product_id
WHERE p.active = true
  AND (
    translate(LOWER(p.name), 'áéíóúñ', 'aeioun') LIKE %s
    OR LOWER(p.name) LIKE %s
  )
ORDER BY
    CASE
        WHEN translate(LOWER(p.name), 'áéíóúñ', 'aeioun') LIKE %s THEN 1
        WHEN LOWER(p.name) LIKE %s THEN 2
    END
LIMIT 1
"""

# Queries para recuperación de carrito
GET_LAST_CART_STATE = """
SELECT data->>'value' as carrito_data
FROM events
WHERE sender_id = %s
  AND type_name = 'slot'
  AND data->>'name' = 'carrito_productos'
  AND data->>'value' != 'null'
ORDER BY timestamp DESC
LIMIT 1
"""

# Queries para gestión de clientes y envíos
GET_OR_CREATE_CUSTOMER = """
INSERT INTO customers (name, phone)
VALUES (%s, %s)
ON CONFLICT (phone)
DO UPDATE SET
    name = EXCLUDED.name,
    updated_at = CURRENT_TIMESTAMP
RETURNING id, name, phone
"""

CREATE_SHIPPING_DATA = """
INSERT INTO shipping_data (
    customer_id,
    department,
    municipality,
    address_line1,
    delivery_phone,
    receiver_name,
    is_primary_address
)
VALUES (%s, 'Guatemala', 'Ciudad', %s, %s, %s, true)
RETURNING id
"""

# Queries para creación de órdenes
CREATE_ORDER = """
INSERT INTO orders (
    order_number,
    customer_id,
    shipping_data_id,
    subtotal,
    shipping_cost,
    total,
    status,
    notes,
    source
)
VALUES (%s, %s, %s, %s, %s, %s, 'pendiente', %s, 'chatbot')
RETURNING id, order_number
"""

CREATE_ORDER_DETAIL = """
INSERT INTO order_details (
    order_id,
    product_id,
    quantity,
    unit_price,
    subtotal
)
VALUES (%s, %s, %s, %s, %s)
"""

UPDATE_INVENTORY_RESERVE = """
UPDATE inventory
SET reserved_quantity = reserved_quantity + %s,
    available_quantity = available_quantity - %s,
    updated_at = CURRENT_TIMESTAMP
WHERE product_id = %s
  AND available_quantity >= %s
"""

GET_NEXT_ORDER_NUMBER = """
SELECT 'ORD-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' ||
       LPAD((COUNT(*) + 1)::TEXT, 6, '0') as next_number
FROM orders
WHERE order_number LIKE 'ORD-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '%'
"""

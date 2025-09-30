"""
SQL queries para el chatbot de e-commerce
Todas las queries están definidas como constantes para facilitar mantenimiento
"""

# Queries para catálogo de productos
GET_AVAILABLE_PRODUCTS = """
SELECT p.id, p.name, p.code, p.description,
       p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity,
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
       p.bundle_price, p.wholesale_quantity, i.available_quantity,
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
       p.bundle_price, p.wholesale_quantity, i.available_quantity
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

# Actions Module Structure

Esta es la estructura modular del servidor de acciones customizadas para RASA.

## Estructura de Directorios

```
actions/
├── __init__.py                 # Entry point - centraliza imports
├── actions.py                  # Punto de entrada compatible con RASA
├── database/
│   ├── __init__.py
│   ├── connection.py          # DatabaseConnection class
│   └── queries.py             # SQL queries como constantes
├── catalog/
│   ├── __init__.py
│   └── catalog_actions.py     # ActionMostrarCatalogo
├── cart/
│   ├── __init__.py
│   ├── cart_actions.py        # ActionAgregarAlCarrito, ActionRecuperarCarrito
│   └── cart_utils.py          # Lógica de pricing tiers, validaciones
├── orders/
│   ├── __init__.py
│   └── (futuras acciones de pedidos)
└── utils/
    ├── __init__.py
    └── helpers.py             # Funciones compartidas (normalización, formateo)
```

## Módulos

### database/
Gestión de conexiones a PostgreSQL y queries SQL.
- `connection.py`: Clase `DatabaseConnection` con métodos `get_connection()` y `execute_query()`
- `queries.py`: Constantes SQL para reutilización (GET_AVAILABLE_PRODUCTS, SEARCH_PRODUCT_BY_NAME, etc.)

### catalog/
Acciones relacionadas con el catálogo de productos.
- `ActionMostrarCatalogo`: Muestra productos disponibles con precios y stock

### cart/
Acciones y utilidades del carrito de compras.
- `cart_actions.py`:
  - `ActionAgregarAlCarrito`: Agrega productos al carrito
  - `ActionRecuperarCarrito`: Recupera carrito de sesiones anteriores
- `cart_utils.py`: Lógica de negocio
  - `calculate_unit_price()`: Calcula precio según tier (individual/wholesale/bundle)
  - `calculate_cart_totals()`: Calcula totales del carrito
  - `add_or_update_cart_item()`: Gestiona items en el carrito
  - `format_cart_summary()`: Formatea resumen para usuario

### orders/
Placeholder para futuras acciones de pedidos (checkout, confirmación, cancelación).

### utils/
Funciones helper compartidas entre módulos.
- `normalize_product_name()`: Normaliza nombres removiendo acentos y plurales

## Cómo Agregar Nuevas Acciones

### 1. Crear la acción en el módulo correspondiente

```python
# actions/catalog/catalog_actions.py
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from actions.database import db

class ActionNuevaAccion(Action):
    def name(self) -> str:
        return "action_nueva_accion"

    def run(self, dispatcher, tracker, domain):
        # Tu lógica aquí
        return []
```

### 2. Exportar en __init__.py del módulo

```python
# actions/catalog/__init__.py
from .catalog_actions import ActionMostrarCatalogo, ActionNuevaAccion

__all__ = ['ActionMostrarCatalogo', 'ActionNuevaAccion']
```

### 3. Importar en actions/actions.py

```python
# actions/actions.py
from actions.catalog import ActionMostrarCatalogo, ActionNuevaAccion
```

### 4. Registrar en domain.yml

```yaml
actions:
  - action_nueva_accion
```

### 5. Reiniciar el action server

```bash
docker compose restart rasa-action-server
```

## Ventajas de esta Arquitectura

- **Separación de responsabilidades**: Cada módulo maneja su propio dominio
- **Reutilización**: Funciones compartidas en `database/` y `utils/`
- **Escalabilidad**: Fácil agregar nuevos módulos (shipping, payments, customers)
- **Mantenibilidad**: Código organizado y fácil de navegar
- **Testing**: Cada módulo se puede testear independientemente

## Testing

Para probar que las acciones están registradas correctamente:

```bash
# Health check
curl http://localhost:5055/health

# Listar acciones registradas
curl http://localhost:5055/actions
```

Deberías ver:
```json
[
  {"name": "action_mostrar_catalogo"},
  {"name": "action_recuperar_carrito"},
  {"name": "action_agregar_al_carrito"}
]
```

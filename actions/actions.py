import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import psycopg2
import psycopg2.extras
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Clase para manejar la conexión a PostgreSQL"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'postgres'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'rasa_chatbot'),
            'user': os.getenv('DB_USER', 'rasa_user'),
            'password': os.getenv('DB_PASSWORD', 'rasa_password_2024')
        }

    def get_connection(self):
        """Obtiene una conexión a la base de datos"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Error conectando a la base de datos: {e}")
            return None

    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """Ejecuta una consulta en la base de datos"""
        conn = self.get_connection()
        if not conn:
            return None

        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(query, params)
                if fetch:
                    result = cur.fetchall()
                    return result
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error ejecutando consulta: {e}")
            conn.rollback()
            return None
        finally:
            conn.close()

# Instancia global de conexión a BD
db = DatabaseConnection()


def normalize_product_name(name: str) -> str:
    """
    Normaliza nombres de productos eliminando plurales comunes en español
    y removiendo acentos para búsqueda flexible
    """
    import unicodedata

    name = name.lower().strip()

    # Remover acentos para búsqueda más flexible
    name_no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )

    # Plurales comunes en español
    # Reglas de pluralización en orden de prioridad
    plural_rules = [
        ('ces', 'z'),      # luces -> luz, peces -> pez
        ('nes', 'n'),      # pantalones -> pantalon
        ('ses', 's'),      # blusas -> blusa (pero esto ya está cubierto por 's')
        ('ies', 'y'),      # No común en español pero por si acaso
        ('as', 'a'),       # camisas -> camisa, blusas -> blusa
        ('os', 'o'),       # pantalones -> pantalon (ya cubierto), vestidos -> vestido
        ('es', ''),        # jeans -> jean (si termina en consonante + es)
        ('s', ''),         # remover 's' simple al final
    ]

    # Aplicar reglas de pluralización
    for plural_suffix, singular_suffix in plural_rules:
        if name_no_accents.endswith(plural_suffix):
            # Para evitar casos como "tres" -> "tre", verificar longitud mínima
            if len(name_no_accents) > len(plural_suffix) + 1:
                return name_no_accents[:-len(plural_suffix)] + singular_suffix

    return name_no_accents


class ActionMostrarCatalogo(Action):
    """Muestra el catálogo completo de productos disponibles"""

    def name(self) -> Text:
        return "action_mostrar_catalogo"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        logger.info("Ejecutando action_mostrar_catalogo")

        # Consultar productos disponibles
        query = """
        SELECT p.id, p.name, p.code, p.description,
               p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity,
               i.available_quantity
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        WHERE p.active = true AND i.available_quantity > 0
        ORDER BY p.name
        """

        productos = db.execute_query(query, fetch=True)

        if productos and len(productos) > 0:
            catalogo_mensaje = "🛍️ **CATÁLOGO DE PRODUCTOS DISPONIBLES**\n\n"

            for i, producto in enumerate(productos, 1):
                catalogo_mensaje += f"**{i}. {producto['name']}** (Código: {producto['code']})\n"

                if producto['description']:
                    catalogo_mensaje += f"   📝 {producto['description']}\n"

                catalogo_mensaje += f"   💰 Precio: Q{producto['individual_price']:.2f}\n"
                catalogo_mensaje += f"   📦 Stock: {producto['available_quantity']} unidades\n"
                catalogo_mensaje += "\n"

            catalogo_mensaje += "¿Qué producto te interesa agregar al carrito? 🛒"

        else:
            catalogo_mensaje = "😔 No tenemos productos disponibles en este momento."

        dispatcher.utter_message(text=catalogo_mensaje)

        logger.info(f"Catálogo mostrado con {len(productos) if productos else 0} productos")

        return []


class ActionRecuperarCarrito(Action):
    """Recupera el carrito de la última sesión del cliente"""

    def name(self) -> Text:
        return "action_recuperar_carrito"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sender_id = tracker.sender_id
        logger.info(f"Intentando recuperar carrito para sender_id: {sender_id}")

        # Buscar el último estado del carrito en la BD de eventos
        query = """
        SELECT data->>'value' as carrito_data
        FROM events
        WHERE sender_id = %s
          AND type_name = 'slot'
          AND data->>'name' = 'carrito_productos'
          AND data->>'value' != 'null'
        ORDER BY timestamp DESC
        LIMIT 1
        """

        resultado = db.execute_query(query, (sender_id,), fetch=True)

        if resultado and resultado[0]['carrito_data']:
            import json
            try:
                carrito_anterior = json.loads(resultado[0]['carrito_data'])

                if carrito_anterior and len(carrito_anterior) > 0:
                    # Calcular totales del carrito recuperado
                    total_carrito = sum(float(item['subtotal']) for item in carrito_anterior)
                    cantidad_items = sum(int(item['quantity']) for item in carrito_anterior)

                    mensaje = "🔄 **Carrito recuperado de tu última sesión:**\n\n"
                    for item in carrito_anterior:
                        mensaje += f"   • {item['quantity']} {item['product_name']} Q{float(item['subtotal']):.2f}\n"

                    mensaje += f"\n   💵 **Total: Q{total_carrito:.2f}**\n\n"
                    mensaje += "¿Quieres continuar con tu compra o modificar el carrito? 🛒"

                    dispatcher.utter_message(text=mensaje)

                    logger.info(f"Carrito recuperado: {len(carrito_anterior)} items, total: Q{total_carrito:.2f}")

                    return [
                        SlotSet("carrito_productos", carrito_anterior),
                        SlotSet("carrito_total", total_carrito),
                        SlotSet("carrito_cantidad_items", cantidad_items)
                    ]
            except Exception as e:
                logger.error(f"Error al recuperar carrito: {e}")

        logger.info("No se encontró carrito anterior para recuperar")
        return []


class ActionAgregarAlCarrito(Action):
    """Agrega un producto al carrito de compras"""

    def name(self) -> Text:
        return "action_agregar_al_carrito"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        producto = tracker.get_slot("producto_seleccionado")
        cantidad_solicitada = tracker.get_slot("cantidad")

        if not producto:
            dispatcher.utter_message(text="🤔 ¿Qué producto quieres agregar al carrito?")
            return []

        if not cantidad_solicitada:
            cantidad_solicitada = 1
        else:
            cantidad_solicitada = int(float(cantidad_solicitada))

        # Normalizar nombre de producto (manejar plurales y acentos)
        producto_normalizado = normalize_product_name(producto)

        # Buscar producto en BD con búsqueda flexible usando unaccent
        query = """
        SELECT p.id, p.name, p.code, p.individual_price, p.wholesale_price,
               p.bundle_price, p.wholesale_quantity, i.available_quantity
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        WHERE p.active = true
        ORDER BY
            CASE
                WHEN translate(LOWER(p.name), 'áéíóúñ', 'aeioun') LIKE %s THEN 1
                WHEN LOWER(p.name) LIKE %s THEN 2
                ELSE 3
            END
        LIMIT 1
        """

        # Búsqueda: primero normalizada (sin acentos/plurales), luego original
        resultado = db.execute_query(
            query,
            (f"%{producto_normalizado}%", f"%{producto.lower()}%"),
            fetch=True
        )

        if not resultado:
            mensaje = f"❌ No encontré '{producto}' en nuestro catálogo.\n"
            mensaje += "¿Quieres ver el catálogo completo? 📋"
            dispatcher.utter_message(text=mensaje)
            return []

        prod = resultado[0]

        # Verificar disponibilidad
        if cantidad_solicitada > prod['available_quantity']:
            mensaje = f"⚠️ **Stock insuficiente**\n\n"
            mensaje += f"Solo tenemos {prod['available_quantity']} unidades de **{prod['name']}** disponibles.\n"
            mensaje += f"Solicitaste: {cantidad_solicitada} unidades"
            dispatcher.utter_message(text=mensaje)
            return []

        # Calcular precio según cantidad (convertir Decimal a float)
        if cantidad_solicitada >= 12 and prod['bundle_price']:
            precio_unitario = float(prod['bundle_price']) / 12
            precio_tipo = "bundle"
        elif cantidad_solicitada >= prod['wholesale_quantity'] and prod['wholesale_price']:
            precio_unitario = float(prod['wholesale_price']) / float(prod['wholesale_quantity'])
            precio_tipo = "wholesale"
        else:
            precio_unitario = float(prod['individual_price'])
            precio_tipo = "individual"

        subtotal_item = precio_unitario * cantidad_solicitada

        # Obtener carrito actual
        carrito = tracker.get_slot("carrito_productos") or []

        # Verificar si el producto ya está en el carrito
        producto_existente = False
        for item in carrito:
            if item['product_id'] == prod['id']:
                item['quantity'] += cantidad_solicitada
                item['subtotal'] = float(item['unit_price']) * item['quantity']
                producto_existente = True
                break

        # Si no existe, agregar nuevo item
        if not producto_existente:
            carrito.append({
                'product_id': prod['id'],
                'product_name': prod['name'],
                'product_code': prod['code'],
                'quantity': cantidad_solicitada,
                'unit_price': precio_unitario,
                'subtotal': subtotal_item,
                'price_type': precio_tipo
            })

        # Calcular totales (convertir Decimal a float)
        total_carrito = sum(float(item['subtotal']) for item in carrito)
        cantidad_items = sum(int(item['quantity']) for item in carrito)

        mensaje = f"✅ **{cantidad_solicitada} x {prod['name']}** agregado al carrito\n\n"
        mensaje += f"💰 Precio unitario: Q{precio_unitario:.2f}\n"
        mensaje += f"💵 Subtotal: Q{subtotal_item:.2f}\n\n"
        mensaje += f"🛒 **Resumen del carrito:**\n"

        # Listar productos en el carrito
        for item in carrito:
            mensaje += f"   • {item['quantity']} {item['product_name']} Q{float(item['subtotal']):.2f}\n"

        mensaje += f"\n   💵 **Total: Q{total_carrito:.2f}**\n\n"
        mensaje += "¿Quieres seguir comprando o ver más productos? 🛍️"

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("carrito_productos", carrito),
            SlotSet("carrito_total", total_carrito),
            SlotSet("carrito_cantidad_items", cantidad_items)
        ]
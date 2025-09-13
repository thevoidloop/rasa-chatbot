import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, FollowupAction
import psycopg2
import psycopg2.extras
from datetime import datetime
import logging
import json

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

class ActionAgregarProductoCarrito(Action):
    """Agrega productos al carrito de compras virtual"""
    
    def name(self) -> Text:
        return "action_agregar_producto_carrito"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extraer información del producto desde entities
        entities = tracker.latest_message.get('entities', [])
        producto = tracker.get_slot("producto_seleccionado")
        cantidad = tracker.get_slot("cantidad") or 1
        color = tracker.get_slot("color_seleccionado")
        
        # Si no hay producto en slot, buscar en entities del mensaje actual
        if not producto:
            for entity in entities:
                if entity['entity'] == 'producto':
                    producto = entity['value']
                elif entity['entity'] == 'cantidad':
                    cantidad = float(entity['value'])
                elif entity['entity'] == 'color':
                    color = entity['value']
        
        if not producto:
            dispatcher.utter_message(text="No pude identificar el producto. ¿Podrías especificarlo de nuevo?")
            return []
        
        # Obtener carrito actual
        carrito_actual = tracker.get_slot("productos_carrito") or []
        
        # Crear item del producto
        item_producto = {
            'producto': producto,
            'cantidad': int(cantidad),
            'color': color or 'sin especificar'
        }
        
        # Verificar disponibilidad en BD
        query = """
        SELECT nombre, individual_price, available_quantity 
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        WHERE LOWER(p.name) = LOWER(%s) AND p.active = true
        """
        
        resultado = db.execute_query(query, (producto,), fetch=True)
        
        if resultado and len(resultado) > 0:
            prod = resultado[0]
            if prod['available_quantity'] >= cantidad:
                # Agregar al carrito
                carrito_actual.append(item_producto)
                
                mensaje = f"✅ Agregado al carrito: {cantidad} {producto}"
                if color:
                    mensaje += f" {color}"
                mensaje += f"\n💰 Precio: ${prod['individual_price']:,.0f} c/u"
                
                dispatcher.utter_message(text=mensaje)
                
                return [
                    SlotSet("productos_carrito", carrito_actual),
                    SlotSet("producto_seleccionado", producto),
                    SlotSet("cantidad", cantidad),
                    SlotSet("color_seleccionado", color)
                ]
            else:
                mensaje = f"⚠️ Solo tenemos {prod['available_quantity']} unidades de {producto} disponibles."
                dispatcher.utter_message(text=mensaje)
                return []
        else:
            dispatcher.utter_message(text=f"❌ El producto '{producto}' no está disponible en nuestro catálogo.")
            return []

class ActionVerificarDisponibilidadMultiple(Action):
    """Verifica disponibilidad de productos y maneja múltiples consultas"""
    
    def name(self) -> Text:
        return "action_verificar_disponibilidad_multiple"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Extraer productos mencionados en el mensaje
        entities = tracker.latest_message.get('entities', [])
        productos_consultar = []
        
        for entity in entities:
            if entity['entity'] == 'producto':
                productos_consultar.append(entity['value'])
        
        if not productos_consultar:
            producto_slot = tracker.get_slot("producto_seleccionado")
            if producto_slot:
                productos_consultar.append(producto_slot)
        
        if not productos_consultar:
            dispatcher.utter_message(text="¿Qué producto quieres que verifique?")
            return []
        
        # Verificar cada producto
        for producto in productos_consultar:
            query = """
            SELECT p.name, i.available_quantity, p.individual_price
            FROM products p
            JOIN inventory i ON p.id = i.product_id
            WHERE LOWER(p.name) = LOWER(%s) AND p.active = true
            """
            
            resultado = db.execute_query(query, (producto,), fetch=True)
            
            if resultado and len(resultado) > 0:
                prod = resultado[0]
                if prod['available_quantity'] > 0:
                    mensaje = f"✅ {prod['name']}: {prod['available_quantity']} disponibles (${prod['individual_price']:,.0f} c/u)"
                else:
                    mensaje = f"❌ {prod['name']}: Sin stock disponible"
                    # Activar sugerencia de alternativas
                    dispatcher.utter_message(text=mensaje)
                    return [FollowupAction("utter_sugerir_alternativa")]
            else:
                mensaje = f"❌ {producto}: No disponible en nuestro catálogo"
                dispatcher.utter_message(text=mensaje)
                return [FollowupAction("utter_sugerir_alternativa")]
            
            dispatcher.utter_message(text=mensaje)
        
        return [SlotSet("producto_seleccionado", productos_consultar[-1])]

class ActionGenerarCotizacion(Action):
    """Genera cotización basada en productos en carrito"""
    
    def name(self) -> Text:
        return "action_generar_cotizacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        carrito = tracker.get_slot("productos_carrito") or []
        
        if not carrito:
            # Si no hay carrito, usar producto individual
            producto = tracker.get_slot("producto_seleccionado")
            cantidad = tracker.get_slot("cantidad") or 1
            
            if producto:
                query = """
                SELECT name, individual_price, wholesale_price, bundle_price, wholesale_quantity
                FROM products 
                WHERE LOWER(name) = LOWER(%s) AND active = true
                """
                
                resultado = db.execute_query(query, (producto,), fetch=True)
                
                if resultado:
                    prod = resultado[0]
                    mensaje = f"💰 **COTIZACIÓN - {prod['name']}**\n\n"
                    mensaje += f"• 1 unidad: ${prod['individual_price']:,.0f}\n"
                    if prod['wholesale_price']:
                        mensaje += f"• {prod['wholesale_quantity']} unidades: ${prod['wholesale_price']:,.0f} (${prod['wholesale_price']/prod['wholesale_quantity']:,.0f} c/u)\n"
                    if prod['bundle_price']:
                        mensaje += f"• Docena: ${prod['bundle_price']:,.0f} (${prod['bundle_price']/12:,.0f} c/u)\n"
                    
                    dispatcher.utter_message(text=mensaje)
                    return []
            
            dispatcher.utter_message(text="No hay productos seleccionados para cotizar.")
            return []
        
        # Generar cotización del carrito
        mensaje = "🛒 **COTIZACIÓN DE SU PEDIDO**\n\n"
        total = 0
        
        for item in carrito:
            producto = item['producto']
            cantidad = item['cantidad']
            color = item.get('color', '')
            
            # Buscar precio del producto
            query = """
            SELECT name, individual_price, wholesale_price, bundle_price, wholesale_quantity
            FROM products 
            WHERE LOWER(name) = LOWER(%s) AND active = true
            """
            
            resultado = db.execute_query(query, (producto,), fetch=True)
            
            if resultado:
                prod = resultado[0]
                
                # Determinar precio según cantidad
                if cantidad >= 12 and prod['bundle_price']:
                    precio_unitario = prod['bundle_price'] / 12
                    tipo_precio = "precio por docena"
                elif cantidad >= prod['wholesale_quantity'] and prod['wholesale_price']:
                    precio_unitario = prod['wholesale_price'] / prod['wholesale_quantity']
                    tipo_precio = f"precio por {prod['wholesale_quantity']}"
                else:
                    precio_unitario = prod['individual_price']
                    tipo_precio = "precio unitario"
                
                subtotal = precio_unitario * cantidad
                total += subtotal
                
                mensaje += f"👕 **{prod['name']}**"
                if color and color != 'sin especificar':
                    mensaje += f" ({color})"
                mensaje += f"\n   Cantidad: {cantidad}\n"
                mensaje += f"   Precio: ${precio_unitario:,.0f} c/u ({tipo_precio})\n"
                mensaje += f"   Subtotal: ${subtotal:,.0f}\n\n"
        
        mensaje += f"💰 **TOTAL: ${total:,.0f}**\n\n"
        mensaje += "¿Confirma este pedido? ✅"
        
        dispatcher.utter_message(text=mensaje)
        
        return [SlotSet("total_estimado", total)]

class ActionConfirmarPedidoFinal(Action):
    """Confirma pedido final y lo guarda en BD"""
    
    def name(self) -> Text:
        return "action_confirmar_pedido_final"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener datos del cliente y carrito
        nombre = tracker.get_slot("nombre_cliente")
        telefono = tracker.get_slot("telefono_cliente") 
        direccion = tracker.get_slot("direccion_completa")
        carrito = tracker.get_slot("productos_carrito") or []
        total = tracker.get_slot("total_estimado") or 0
        
        if not all([nombre, telefono, direccion]) or not carrito:
            dispatcher.utter_message(text="❌ Faltan datos para confirmar el pedido.")
            return []
        
        try:
            conn = db.get_connection()
            if not conn:
                dispatcher.utter_message(text="❌ Error de conexión. Intente más tarde.")
                return []
            
            with conn.cursor() as cur:
                # Insertar/actualizar cliente
                query_cliente = """
                INSERT INTO customers (name, phone)
                VALUES (%s, %s)
                ON CONFLICT (phone) 
                DO UPDATE SET 
                    name = EXCLUDED.name,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """
                cur.execute(query_cliente, (nombre, telefono))
                cliente_id = cur.fetchone()[0]
                
                # Insertar dirección de envío
                query_direccion = """
                INSERT INTO shipping_data (customer_id, department, municipality, address_line1, receiver_name, is_primary_address)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
                """
                # Parsear dirección (simplificado)
                partes_direccion = direccion.split(',')
                departamento = partes_direccion[0].strip() if len(partes_direccion) > 1 else "Guatemala"
                municipio = partes_direccion[1].strip() if len(partes_direccion) > 1 else direccion.split()[0]
                direccion_linea1 = direccion
                
                cur.execute(query_direccion, (cliente_id, departamento, municipio, direccion_linea1, nombre, True))
                direccion_id = cur.fetchone()[0]
                
                # Crear pedido
                query_pedido = """
                INSERT INTO orders (customer_id, shipping_data_id, subtotal, total, status, source, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, order_number
                """
                notas = f"Pedido desde chatbot - {len(carrito)} productos"
                cur.execute(query_pedido, (cliente_id, direccion_id, total, total, 'confirmado', 'chatbot', notas))
                pedido_id, numero_pedido = cur.fetchone()
                
                # Insertar detalles del pedido
                for item in carrito:
                    # Buscar producto
                    cur.execute("SELECT id, individual_price FROM products WHERE LOWER(name) = LOWER(%s)", (item['producto'],))
                    producto_result = cur.fetchone()
                    
                    if producto_result:
                        producto_id, precio = producto_result
                        cantidad = item['cantidad']
                        subtotal = precio * cantidad
                        
                        query_detalle = """
                        INSERT INTO order_details (order_id, product_id, quantity, unit_price, line_subtotal, price_type)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cur.execute(query_detalle, (pedido_id, producto_id, cantidad, precio, subtotal, 'individual'))
                        
                        # Actualizar inventario
                        cur.execute("UPDATE inventory SET available_quantity = available_quantity - %s WHERE product_id = %s", 
                                  (cantidad, producto_id))
                
                conn.commit()
                
                # Mensaje de confirmación
                mensaje = f"""
🎉 **¡PEDIDO CONFIRMADO EXITOSAMENTE!**

📋 **Detalles del Pedido:**
• Número: #{numero_pedido}
• Cliente: {nombre}
• Teléfono: {telefono}
• Dirección: {direccion}
• Total: ${total:,.0f}

📦 Su pedido será procesado y nos pondremos en contacto para coordinar la entrega.

¡Gracias por su compra en China Expres! 🛍️

¿Hay algo más en lo que pueda ayudarle?
"""
                
                dispatcher.utter_message(text=mensaje)
                
                # Limpiar slots
                return [
                    SlotSet("productos_carrito", []),
                    SlotSet("total_estimado", None),
                    SlotSet("nombre_cliente", None),
                    SlotSet("telefono_cliente", None),
                    SlotSet("direccion_completa", None),
                    SlotSet("producto_seleccionado", None),
                    SlotSet("cantidad", None),
                    SlotSet("color_seleccionado", None)
                ]
                
        except Exception as e:
            logger.error(f"Error confirmando pedido: {e}")
            dispatcher.utter_message(text="❌ Error procesando su pedido. Por favor intente de nuevo.")
            return []
        finally:
            if conn:
                conn.close()

class ActionSugerirProductosSimilares(Action):
    """Sugiere productos similares cuando no hay stock"""
    
    def name(self) -> Text:
        return "action_sugerir_productos_similares"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener productos disponibles similares
        query = """
        SELECT name, individual_price, available_quantity
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        WHERE p.active = true AND i.available_quantity > 0
        ORDER BY i.available_quantity DESC
        LIMIT 5
        """
        
        productos = db.execute_query(query, fetch=True)
        
        if productos:
            mensaje = "🔍 **PRODUCTOS DISPONIBLES QUE PODRÍAN INTERESARLE:**\n\n"
            for prod in productos:
                mensaje += f"👕 **{prod['name']}**\n"
                mensaje += f"   💰 Precio: ${prod['individual_price']:,.0f}\n"
                mensaje += f"   📦 Stock: {prod['available_quantity']} disponibles\n\n"
            
            mensaje += "¿Le interesa alguno de estos productos? 🛍️"
        else:
            mensaje = "En este momento no tenemos productos similares disponibles. ¿Le puedo ayudar con algo más?"
        
        dispatcher.utter_message(text=mensaje)
        return []

class ValidateFormDatosCliente(FormValidationAction):
    """Validación del formulario de datos del cliente"""
    
    def name(self) -> Text:
        return "validate_form_datos_cliente"

    def validate_nombre_cliente(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        
        if len(slot_value) < 2:
            dispatcher.utter_message(text="Por favor proporcione un nombre válido.")
            return {"nombre_cliente": None}
        
        return {"nombre_cliente": slot_value}

    def validate_telefono_cliente(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        
        # Limpiar formato del teléfono
        telefono_limpio = ''.join(filter(str.isdigit, str(slot_value)))
        
        if len(telefono_limpio) < 8:
            dispatcher.utter_message(text="Por favor proporcione un número de teléfono válido.")
            return {"telefono_cliente": None}
        
        return {"telefono_cliente": telefono_limpio}

    def validate_direccion_completa(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Any]:
        
        if len(slot_value) < 10:
            dispatcher.utter_message(text="Por favor proporcione una dirección más detallada.")
            return {"direccion_completa": None}
        
        return {"direccion_completa": slot_value}
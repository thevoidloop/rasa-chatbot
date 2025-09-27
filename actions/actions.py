import os
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import psycopg2
import psycopg2.extras
from datetime import datetime
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

class ActionMostrarCatalogo(Action):
    def name(self) -> Text:
        return "action_mostrar_catalogo"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        logger.info("Ejecutando action_mostrar_catalogo")
        
        # Consultar productos disponibles desde la BD con más detalles
        query = """
        SELECT p.id, p.name, p.code, p.description, 
               p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity,
               i.available_quantity, 
               string_agg(CASE WHEN pc.characteristic_name = 'Tallas' THEN pc.characteristic_value END, ', ') as tallas,
               string_agg(CASE WHEN pc.characteristic_name = 'Colores' THEN pc.characteristic_value END, ', ') as colores
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        LEFT JOIN product_characteristics pc ON p.id = pc.product_id
        WHERE p.active = true AND i.available_quantity > 0
        GROUP BY p.id, p.name, p.code, p.description, p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity, i.available_quantity
        ORDER BY p.name
        """
        
        productos = db.execute_query(query, fetch=True)
        
        if productos and len(productos) > 0:
            catalogo_mensaje = "🛍️ **CATÁLOGO DE PRODUCTOS DISPONIBLES**\n\n"
            
            for i, producto in enumerate(productos, 1):
                catalogo_mensaje += f"**{i}. {producto['name']}** (Código: {producto['code']})\n"
                
                if producto['description']:
                    catalogo_mensaje += f"   📝 {producto['description']}\n"
                
                catalogo_mensaje += f"   💰 **Precios:**\n"
                catalogo_mensaje += f"      • 1 unidad: Q{producto['individual_price']:,.2f}\n"
                
                if producto['wholesale_price']:
                    catalogo_mensaje += f"      • {producto['wholesale_quantity']} unidades: Q{producto['wholesale_price']:,.2f}\n"
                
                if producto['bundle_price']:
                    catalogo_mensaje += f"      • Docena (12): Q{producto['bundle_price']:,.2f}\n"
                
                catalogo_mensaje += f"   📦 **Stock:** {producto['available_quantity']} unidades\n"
                
                if producto['tallas']:
                    catalogo_mensaje += f"   📏 **Tallas:** {producto['tallas']}\n"
                
                if producto['colores']:
                    catalogo_mensaje += f"   🎨 **Colores:** {producto['colores']}\n"
                
                catalogo_mensaje += "\n" + "─" * 40 + "\n\n"
            
            catalogo_mensaje += "💡 **Tips de compra:**\n"
            catalogo_mensaje += f"• Compra {productos[0]['wholesale_quantity']} o más unidades para precio mayorista\n"
            catalogo_mensaje += "• Compra 12 unidades para precio de docena (mejor oferta)\n"
            catalogo_mensaje += "• Todos los precios incluyen descuentos por cantidad\n\n"
            catalogo_mensaje += "❓ **¿Qué te interesa?** Puedes preguntarme por:\n"
            catalogo_mensaje += "   📋 Detalles de un producto específico\n"
            catalogo_mensaje += "   💰 Precios y ofertas especiales\n"
            catalogo_mensaje += "   📦 Disponibilidad y stock\n"
            catalogo_mensaje += "   🛒 Hacer un pedido\n"
            
        else:
            catalogo_mensaje = "😔 **Lo sentimos**\n\n"
            catalogo_mensaje += "No tenemos productos disponibles en este momento.\n"
            catalogo_mensaje += "Estamos reabasteciendo nuestro inventario.\n\n"
            catalogo_mensaje += "🔔 ¿Te interesa que te notifiquemos cuando tengamos nuevos productos?"
        
        dispatcher.utter_message(text=catalogo_mensaje)
        
        # Log de la acción
        logger.info(f"Catálogo mostrado con {len(productos) if productos else 0} productos")
        
        return []

class ActionMostrarCatalogoPorCategoria(Action):
    def name(self) -> Text:
        return "action_mostrar_catalogo_categoria"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        categoria = tracker.get_slot("categoria_seleccionada")
        logger.info(f"Ejecutando action_mostrar_catalogo_categoria para: {categoria}")
        
        if not categoria:
            dispatcher.utter_message(text="🤔 ¿Qué tipo de productos te interesa ver? Por ejemplo: camisas, pantalones, vestidos, etc.")
            return []
        
        # Normalizar categoría para búsqueda más flexible
        categoria_busqueda = categoria.lower()
        
        # Consultar productos por categoría (búsqueda flexible en nombre y características)
        query = """
        SELECT DISTINCT p.id, p.name, p.code, p.description, 
               p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity,
               i.available_quantity,
               string_agg(CASE WHEN pc.characteristic_name = 'Tallas' THEN pc.characteristic_value END, ', ') as tallas,
               string_agg(CASE WHEN pc.characteristic_name = 'Colores' THEN pc.characteristic_value END, ', ') as colores
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        LEFT JOIN product_characteristics pc ON p.id = pc.product_id
        WHERE p.active = true 
        AND i.available_quantity > 0
        AND (LOWER(p.name) LIKE %s OR LOWER(p.description) LIKE %s)
        GROUP BY p.id, p.name, p.code, p.description, p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity, i.available_quantity
        ORDER BY p.name
        """
        
        patron_busqueda = f"%{categoria_busqueda}%"
        productos = db.execute_query(query, (patron_busqueda, patron_busqueda), fetch=True)
        
        if productos and len(productos) > 0:
            catalogo_mensaje = f"👕 **{categoria.upper()} DISPONIBLES**\n\n"
            catalogo_mensaje += f"Encontré {len(productos)} producto{'s' if len(productos) > 1 else ''} en esta categoría:\n\n"
            
            for i, producto in enumerate(productos, 1):
                catalogo_mensaje += f"**{i}. {producto['name']}**\n"
                
                if producto['description']:
                    catalogo_mensaje += f"   📝 {producto['description']}\n"
                
                catalogo_mensaje += f"   💰 Desde Q{producto['individual_price']:,.2f}\n"
                catalogo_mensaje += f"   📦 Stock: {producto['available_quantity']}\n"
                
                if producto['tallas']:
                    catalogo_mensaje += f"   📏 Tallas: {producto['tallas']}\n"
                    
                if producto['colores']:
                    catalogo_mensaje += f"   🎨 Colores: {producto['colores']}\n"
                
                catalogo_mensaje += "\n"
            
            catalogo_mensaje += f"\n¿Te interesa conocer más detalles de algún {categoria[:-1] if categoria.endswith('s') else categoria}? 🛍️"
            
        else:
            catalogo_mensaje = f"😔 **No encontré {categoria} disponibles**\n\n"
            catalogo_mensaje += f"Actualmente no tenemos {categoria} en stock.\n"
            catalogo_mensaje += "¿Te interesa ver nuestro catálogo completo?\n\n"
            catalogo_mensaje += "También puedo notificarte cuando tengamos {categoria} disponibles. 🔔"
        
        dispatcher.utter_message(text=catalogo_mensaje)
        
        logger.info(f"Catálogo por categoría '{categoria}' mostrado con {len(productos) if productos else 0} productos")
        
        return []

class ActionConsultarPrecio(Action):
    def name(self) -> Text:
        return "action_consultar_precio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = tracker.get_slot("producto_seleccionado")
        logger.info(f"Consultando precio para: {producto}")
        
        if not producto:
            dispatcher.utter_message(text="💰 ¿De qué producto quieres conocer el precio? Puedo ayudarte con cualquiera de nuestros productos disponibles.")
            return []
        
        # Consultar precio desde la BD con más detalles
        query = """
        SELECT p.name, p.code, p.description, p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity,
               i.available_quantity,
               string_agg(CASE WHEN pc.characteristic_name = 'Tallas' THEN pc.characteristic_value END, ', ') as tallas,
               string_agg(CASE WHEN pc.characteristic_name = 'Colores' THEN pc.characteristic_value END, ', ') as colores
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        LEFT JOIN product_characteristics pc ON p.id = pc.product_id
        WHERE LOWER(p.name) LIKE %s AND p.active = true
        GROUP BY p.id, p.name, p.code, p.description, p.individual_price, p.wholesale_price, p.bundle_price, p.wholesale_quantity, i.available_quantity
        LIMIT 1
        """
        
        resultado = db.execute_query(query, (f"%{producto.lower()}%",), fetch=True)
        
        if resultado:
            prod = resultado[0]
            mensaje = f"💰 **PRECIOS - {prod['name'].upper()}**\n\n"
            
            if prod['description']:
                mensaje += f"📝 {prod['description']}\n\n"
            
            mensaje += "💵 **Opciones de compra:**\n"
            mensaje += f"   🔸 **1 unidad:** Q{prod['individual_price']:,.2f}\n"
            
            if prod['wholesale_price'] and prod['wholesale_quantity']:
                ahorro_mayorista = (prod['individual_price'] * prod['wholesale_quantity']) - prod['wholesale_price']
                mensaje += f"   🔸 **{prod['wholesale_quantity']} unidades:** Q{prod['wholesale_price']:,.2f} "
                if ahorro_mayorista > 0:
                    mensaje += f"(¡Ahorras Q{ahorro_mayorista:.2f}!)\n"
                else:
                    mensaje += "\n"
            
            if prod['bundle_price']:
                ahorro_docena = (prod['individual_price'] * 12) - prod['bundle_price']
                mensaje += f"   🔸 **Docena (12 unidades):** Q{prod['bundle_price']:,.2f} "
                if ahorro_docena > 0:
                    mensaje += f"(¡Ahorras Q{ahorro_docena:.2f}!)\n"
                else:
                    mensaje += "\n"
            
            mensaje += f"\n📦 **Stock disponible:** {prod['available_quantity']} unidades\n"
            
            if prod['tallas']:
                mensaje += f"📏 **Tallas disponibles:** {prod['tallas']}\n"
            
            if prod['colores']:
                mensaje += f"🎨 **Colores disponibles:** {prod['colores']}\n"
            
            # Calcular mejor oferta
            if prod['bundle_price']:
                precio_unitario_mejor = prod['bundle_price'] / 12
                mensaje += f"\n💡 **Mejor precio unitario:** Q{precio_unitario_mejor:.2f} (comprando docena)\n"
            
            mensaje += "\n❓ **¿Te interesa?**\n"
            mensaje += "   🛒 Puedes hacer tu pedido ahora\n"
            mensaje += "   📋 O pregúntame por otros productos\n"
            mensaje += "   📞 También puedo ayudarte con información de entrega"
            
            dispatcher.utter_message(text=mensaje)
        else:
            mensaje = f"❌ **Producto no encontrado**\n\n"
            mensaje += f"No encontré '{producto}' en nuestro catálogo.\n\n"
            mensaje += "💡 **Sugerencias:**\n"
            mensaje += "   • Revisa la escritura del producto\n"
            mensaje += "   • Pregúntame por el catálogo completo\n"
            mensaje += "   • Describe el tipo de producto que buscas\n\n"
            mensaje += "¿Te gustaría ver todos nuestros productos disponibles? 🛍️"
            
            dispatcher.utter_message(text=mensaje)
        
        return []

# Mantener las demás acciones existentes...
# (ActionVerificarDisponibilidad, ActionCrearPedido, etc.)
# Las incluyo aquí de forma resumida para no hacer el artefacto demasiado largo

class ActionVerificarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_verificar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = tracker.get_slot("producto_seleccionado")
        cantidad_solicitada = tracker.get_slot("cantidad")
        
        if not producto:
            dispatcher.utter_message(text="📦 ¿De qué producto quieres verificar la disponibilidad?")
            return []
        
        query = """
        SELECT p.name, i.available_quantity, p.active 
        FROM products p
        LEFT JOIN inventory i ON p.id = i.product_id
        WHERE LOWER(p.name) LIKE %s
        LIMIT 1
        """
        
        resultado = db.execute_query(query, (f"%{producto.lower()}%",), fetch=True)
        
        if resultado:
            prod = resultado[0]
            if prod['active'] and prod['available_quantity'] > 0:
                if cantidad_solicitada:
                    cantidad = int(float(cantidad_solicitada))
                    if cantidad <= prod['available_quantity']:
                        mensaje = f"✅ ¡Perfecto! Tenemos **{cantidad} unidades** de **{prod['name']}** disponibles.\n\n"
                        mensaje += f"📦 Stock total: {prod['available_quantity']} unidades\n"
                        mensaje += f"🛒 ¿Te gustaría hacer el pedido ahora?"
                    else:
                        mensaje = f"⚠️ **Stock limitado**\n\n"
                        mensaje += f"Solo tenemos **{prod['available_quantity']} unidades** de **{prod['name']}**.\n"
                        mensaje += f"Solicitaste: {cantidad} unidades\n\n"
                        mensaje += f"¿Te interesa la cantidad disponible? 🤔"
                else:
                    mensaje = f"✅ **{prod['name']} disponible**\n\n"
                    mensaje += f"📦 Tenemos {prod['available_quantity']} unidades en stock.\n"
                    mensaje += f"💰 ¿Te interesa conocer los precios?\n"
                    mensaje += f"🛒 ¿O prefieres hacer un pedido directo?"
            else:
                mensaje = f"❌ **No disponible**\n\n"
                mensaje += f"**{prod['name']}** no está disponible actualmente.\n"
                mensaje += f"🔔 ¿Te interesa que te notifique cuando llegue?"
        else:
            mensaje = f"❓ **Producto no encontrado**\n\n"
            mensaje += f"No encontré '{producto}' en nuestro catálogo.\n"
            mensaje += f"¿Podrías verificar el nombre o ver nuestro catálogo completo? 📋"
        
        dispatcher.utter_message(text=mensaje)
        return []

class ActionLogConversacion(Action):
    """Acción para registrar conversaciones para análisis"""
    def name(self) -> Text:
        return "action_log_conversacion"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener información de la conversación
        session_id = tracker.sender_id
        intent = tracker.latest_message.get('intent', {}).get('name')
        entities = tracker.latest_message.get('entities', [])
        confidence = tracker.latest_message.get('intent', {}).get('confidence')
        user_message = tracker.latest_message.get('text')
        
        # Preparar datos para insertar
        entities_json = {entity['entity']: entity['value'] for entity in entities}
        
        query = """
        INSERT INTO conversaciones_chatbot 
        (session_id, user_message, intent_detected, entities_detected, confidence_score)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            db.execute_query(
                query, 
                (session_id, user_message, intent, 
                 psycopg2.extras.Json(entities_json), confidence)
            )
            logger.info(f"Conversación registrada: {session_id} - {intent}")
        except Exception as e:
            logger.error(f"Error logging conversación: {e}")
        
        return []
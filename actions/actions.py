# actions/actions.py - CORREGIDO para usar tabla en inglés
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
        
        # CORREGIDO: usar tablas en inglés
        query = """
        SELECT p.name, p.individual_price, p.wholesale_price, p.bundle_price, i.available_quantity 
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        WHERE p.active = true AND i.available_quantity > 0
        ORDER BY p.name
        """
        
        productos = db.execute_query(query, fetch=True)
        
        if productos:
            catalogo_mensaje = "📋 **CATÁLOGO DE PRODUCTOS DISPONIBLES**\n\n"
            for producto in productos:
                catalogo_mensaje += f"👕 **{producto['name']}** (Stock: {producto['available_quantity']})\n"
                catalogo_mensaje += f"   • 1 unidad: ${producto['individual_price']:,.0f}\n"
                catalogo_mensaje += f"   • Media docena: ${producto['wholesale_price']:,.0f}\n"
                catalogo_mensaje += f"   • Docena: ${producto['bundle_price']:,.0f}\n\n"
            
            catalogo_mensaje += "¿Qué producto te interesa? 🛍️"
        else:
            catalogo_mensaje = "❌ Lo siento, no hay productos disponibles en este momento."
        
        dispatcher.utter_message(text=catalogo_mensaje)
        return []

class ActionConsultarPrecio(Action):
    def name(self) -> Text:
        return "action_consultar_precio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = tracker.get_slot("producto_seleccionado")
        
        if not producto:
            dispatcher.utter_message(text="¿De qué producto quieres conocer el precio? 💰")
            return []
        
        # CORREGIDO: usar tablas en inglés
        query = """
        SELECT p.name, p.individual_price, p.wholesale_price, p.bundle_price, 
               i.available_quantity, pc.characteristic_value as tallas,
               pc2.characteristic_value as colores
        FROM products p
        JOIN inventory i ON p.id = i.product_id
        LEFT JOIN product_characteristics pc ON p.id = pc.product_id AND pc.characteristic_name = 'Tallas'
        LEFT JOIN product_characteristics pc2 ON p.id = pc2.product_id AND pc2.characteristic_name = 'Colores'
        WHERE LOWER(p.name) = LOWER(%s) AND p.active = true
        """
        
        resultado = db.execute_query(query, (producto,), fetch=True)
        
        if resultado:
            prod = resultado[0]
            mensaje = f"""
💰 **Precios para {prod['name']}:**

• 1 unidad: ${prod['individual_price']:,.0f}
• Media docena (6): ${prod['wholesale_price']:,.0f}
• Docena (12): ${prod['bundle_price']:,.0f}

📦 Stock disponible: {prod['available_quantity']} unidades

"""
            if prod['tallas']:
                mensaje += f"📏 Tallas: {prod['tallas']}\n"
            
            if prod['colores']:
                mensaje += f"🎨 Colores: {prod['colores']}\n"
            
            mensaje += "\n¿Cuántas unidades necesitas? 🛒"
            
            dispatcher.utter_message(text=mensaje)
        else:
            dispatcher.utter_message(
                text=f"❌ No encontré información de precios para '{producto}'. "
                     "¿Podrías verificar el nombre del producto?"
            )
        
        return []

# Ejemplo de acción simplificada para testing
class ActionTestConnection(Action):
    def name(self) -> Text:
        return "action_test_connection"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        try:
            # Test simple de conexión
            query = "SELECT COUNT(*) as total FROM products"
            resultado = db.execute_query(query, fetch=True)
            
            if resultado:
                total = resultado[0]['total']
                dispatcher.utter_message(text=f"✅ Conexión exitosa. Productos en BD: {total}")
            else:
                dispatcher.utter_message(text="❌ Error en la consulta")
                
        except Exception as e:
            logger.error(f"Error en test de conexión: {e}")
            dispatcher.utter_message(text=f"❌ Error de conexión: {str(e)}")
        
        return []
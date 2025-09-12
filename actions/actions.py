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
        
        # Consultar productos disponibles desde la BD
        query = """
        SELECT nombre, precio_unidad, precio_media_docena, precio_docena, stock_actual 
        FROM productos 
        WHERE disponible = true AND stock_actual > 0
        ORDER BY categoria, nombre
        """
        
        productos = db.execute_query(query, fetch=True)
        
        if productos:
            catalogo_mensaje = "📋 **CATÁLOGO DE PRODUCTOS DISPONIBLES**\n\n"
            for producto in productos:
                catalogo_mensaje += f"👕 **{producto['nombre']}** (Stock: {producto['stock_actual']})\n"
                catalogo_mensaje += f"   • 1 unidad: ${producto['precio_unidad']:,.0f}\n"
                catalogo_mensaje += f"   • Media docena: ${producto['precio_media_docena']:,.0f}\n"
                catalogo_mensaje += f"   • Docena: ${producto['precio_docena']:,.0f}\n\n"
            
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
        
        # Consultar precio desde la BD
        query = """
        SELECT nombre, precio_unidad, precio_media_docena, precio_docena, 
               stock_actual, tallas_disponibles, colores_disponibles
        FROM productos 
        WHERE LOWER(nombre) = LOWER(%s) AND disponible = true
        """
        
        resultado = db.execute_query(query, (producto,), fetch=True)
        
        if resultado:
            prod = resultado[0]
            mensaje = f"""
💰 **Precios para {prod['nombre']}:**

• 1 unidad: ${prod['precio_unidad']:,.0f}
• Media docena (6): ${prod['precio_media_docena']:,.0f}
• Docena (12): ${prod['precio_docena']:,.0f}

📦 Stock disponible: {prod['stock_actual']} unidades

"""
            if prod['tallas_disponibles']:
                mensaje += f"📏 Tallas: {', '.join(prod['tallas_disponibles'])}\n"
            
            if prod['colores_disponibles']:
                mensaje += f"🎨 Colores: {', '.join(prod['colores_disponibles'])}\n"
            
            mensaje += "\n¿Cuántas unidades necesitas? 🛒"
            
            dispatcher.utter_message(text=mensaje)
        else:
            dispatcher.utter_message(
                text=f"❌ No encontré información de precios para '{producto}'. "
                     "¿Podrías verificar el nombre del producto?"
            )
        
        return []

class ActionVerificarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_verificar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = tracker.get_slot("producto_seleccionado")
        cantidad_solicitada = tracker.get_slot("cantidad")
        
        if not producto:
            dispatcher.utter_message(text="¿De qué producto quieres verificar la disponibilidad? 📦")
            return []
        
        # Consultar disponibilidad desde la BD
        query = """
        SELECT nombre, stock_actual, disponible 
        FROM productos 
        WHERE LOWER(nombre) = LOWER(%s)
        """
        
        resultado = db.execute_query(query, (producto,), fetch=True)
        
        if resultado:
            prod = resultado[0]
            if prod['disponible'] and prod['stock_actual'] > 0:
                if cantidad_solicitada:
                    cantidad = int(float(cantidad_solicitada))
                    if cantidad <= prod['stock_actual']:
                        mensaje = f"✅ ¡Excelente! Tenemos {cantidad} unidades de {prod['nombre']} disponibles."
                    else:
                        mensaje = f"⚠️ Solo tenemos {prod['stock_actual']} unidades de {prod['nombre']} disponibles. ¿Te interesa esa cantidad?"
                else:
                    mensaje = f"✅ ¡Perfecto! Tenemos {prod['stock_actual']} unidades de {prod['nombre']} en stock."
            else:
                mensaje = f"❌ Lo siento, {prod['nombre']} no está disponible actualmente."
        else:
            mensaje = f"❌ No encontré el producto '{producto}' en nuestro catálogo."
        
        dispatcher.utter_message(text=mensaje)
        return []

class ActionCrearPedido(Action):
    def name(self) -> Text:
        return "action_crear_pedido"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = tracker.get_slot("producto_seleccionado")
        cantidad = tracker.get_slot("cantidad")
        
        if not producto or not cantidad:
            dispatcher.utter_message(text="Necesito saber qué producto y cuánta cantidad deseas. 🛒")
            return []
        
        cantidad_int = int(float(cantidad))
        
        # Obtener información del producto y calcular precio
        query = """
        SELECT id, nombre, precio_unidad, precio_media_docena, precio_docena, stock_actual
        FROM productos 
        WHERE LOWER(nombre) = LOWER(%s) AND disponible = true
        """
        
        resultado = db.execute_query(query, (producto,), fetch=True)
        
        if not resultado:
            dispatcher.utter_message(text=f"❌ No encontré el producto '{producto}'.")
            return []
        
        prod = resultado[0]
        
        # Verificar stock
        if cantidad_int > prod['stock_actual']:
            dispatcher.utter_message(
                text=f"❌ Solo tenemos {prod['stock_actual']} unidades disponibles de {prod['nombre']}."
            )
            return []
        
        # Calcular precio según cantidad
        if cantidad_int >= 12:
            precio_unitario = prod['precio_docena'] / 12
            tipo_precio = "precio por docena"
        elif cantidad_int >= 6:
            precio_unitario = prod['precio_media_docena'] / 6
            tipo_precio = "precio por media docena"
        else:
            precio_unitario = prod['precio_unidad']
            tipo_precio = "precio unitario"
        
        total = precio_unitario * cantidad_int
        
        mensaje = f"""
🛒 **RESUMEN DE PEDIDO**

Producto: {prod['nombre']}
Cantidad: {cantidad_int} unidades
Precio unitario: ${precio_unitario:,.0f} ({tipo_precio})
**Total: ${total:,.0f}**

¿Confirmas este pedido? ✅

Responde 'sí' para continuar o 'no' para cancelar.
"""
        
        dispatcher.utter_message(text=mensaje)
        
        # Guardar información del pedido en slots para confirmación
        return [
            SlotSet("pedido_producto_id", prod['id']),
            SlotSet("pedido_precio_unitario", precio_unitario),
            SlotSet("pedido_total", total)
        ]

class ActionConfirmarPedido(Action):
    def name(self) -> Text:
        return "action_confirmar_pedido"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener datos del pedido desde los slots
        producto_id = tracker.get_slot("pedido_producto_id")
        cantidad = tracker.get_slot("cantidad")
        precio_unitario = tracker.get_slot("pedido_precio_unitario")
        total = tracker.get_slot("pedido_total")
        
        if not all([producto_id, cantidad, precio_unitario, total]):
            dispatcher.utter_message(text="❌ No encontré la información del pedido. Por favor, intenta de nuevo.")
            return []
        
        cantidad_int = int(float(cantidad))
        
        try:
            # Registrar pedido temporal (sin cliente por ahora)
            query_pedido = """
            INSERT INTO pedidos (total, estado, notas) 
            VALUES (%s, %s, %s) 
            RETURNING id
            """
            
            # Usar una conexión para ejecutar múltiples queries en transacción
            conn = db.get_connection()
            if not conn:
                dispatcher.utter_message(text="❌ Error de conexión. Por favor intenta más tarde.")
                return []
            
            try:
                with conn.cursor() as cur:
                    # Insertar pedido
                    cur.execute(query_pedido, (total, 'pendiente', f'Pedido desde chatbot - {datetime.now()}'))
                    pedido_id = cur.fetchone()[0]
                    
                    # Insertar detalle del pedido
                    query_detalle = """
                    INSERT INTO detalle_pedidos (pedido_id, producto_id, cantidad, precio_unitario, subtotal)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    cur.execute(query_detalle, (pedido_id, producto_id, cantidad_int, precio_unitario, total))
                    
                    # Actualizar stock
                    query_stock = """
                    UPDATE productos 
                    SET stock_actual = stock_actual - %s 
                    WHERE id = %s
                    """
                    cur.execute(query_stock, (cantidad_int, producto_id))
                    
                    conn.commit()
                    
                    mensaje = f"""
🎉 **¡PEDIDO CONFIRMADO!**

Número de pedido: #{pedido_id}
Total: ${total:,.0f}

Para completar tu pedido, necesitaré algunos datos:
📝 Tu nombre completo
📞 Número de teléfono  
📍 Dirección de entrega

¿Podrías proporcionarme tu nombre completo?
"""
                    
                    dispatcher.utter_message(text=mensaje)
                    return [SlotSet("pedido_id", pedido_id)]
                    
            except Exception as e:
                conn.rollback()
                logger.error(f"Error procesando pedido: {e}")
                dispatcher.utter_message(text="❌ Hubo un error procesando tu pedido. Por favor intenta de nuevo.")
                return []
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Error general en confirmación de pedido: {e}")
            dispatcher.utter_message(text="❌ Error interno. Por favor contacta al soporte.")
            return []

class ActionGuardarDatosCliente(Action):
    def name(self) -> Text:
        return "action_guardar_datos_cliente"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        nombre = tracker.get_slot("nombre_cliente")
        telefono = tracker.get_slot("telefono_cliente") 
        direccion = tracker.get_slot("direccion_cliente")
        pedido_id = tracker.get_slot("pedido_id")
        
        if not all([nombre, telefono, direccion, pedido_id]):
            dispatcher.utter_message(text="❌ Faltan algunos datos. Por favor completa toda la información.")
            return []
        
        try:
            conn = db.get_connection()
            if not conn:
                dispatcher.utter_message(text="❌ Error de conexión.")
                return []
            
            with conn.cursor() as cur:
                # Insertar o actualizar cliente
                query_cliente = """
                INSERT INTO clientes (nombre_completo, telefono, direccion)
                VALUES (%s, %s, %s)
                ON CONFLICT (telefono) 
                DO UPDATE SET 
                    nombre_completo = EXCLUDED.nombre_completo,
                    direccion = EXCLUDED.direccion,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """
                cur.execute(query_cliente, (nombre, telefono, direccion))
                cliente_id = cur.fetchone()[0]
                
                # Actualizar pedido con cliente
                query_update_pedido = """
                UPDATE pedidos 
                SET cliente_id = %s, estado = 'confirmado'
                WHERE id = %s
                """
                cur.execute(query_update_pedido, (cliente_id, pedido_id))
                
                conn.commit()
                
                mensaje = f"""
✅ **¡PEDIDO COMPLETADO CON ÉXITO!**

📋 **Resumen Final:**
• Número de pedido: #{pedido_id}
• Cliente: {nombre}
• Teléfono: {telefono}
• Dirección: {direccion}

📦 Tu pedido será procesado y te contactaremos pronto para coordinar la entrega.

¡Gracias por tu compra! 🎉

¿Hay algo más en lo que pueda ayudarte?
"""
                
                dispatcher.utter_message(text=mensaje)
                
                # Limpiar slots del pedido
                return [
                    SlotSet("pedido_id", None),
                    SlotSet("pedido_producto_id", None),
                    SlotSet("pedido_precio_unitario", None),
                    SlotSet("pedido_total", None),
                    SlotSet("nombre_cliente", None),
                    SlotSet("telefono_cliente", None),
                    SlotSet("direccion_cliente", None),
                    SlotSet("producto_seleccionado", None),
                    SlotSet("cantidad", None)
                ]
                
        except Exception as e:
            logger.error(f"Error guardando datos del cliente: {e}")
            dispatcher.utter_message(text="❌ Error guardando tus datos. Por favor intenta de nuevo.")
            return []
        finally:
            if conn:
                conn.close()

class ActionConsultarPedido(Action):
    def name(self) -> Text:
        return "action_consultar_pedido"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Obtener teléfono del slot o del mensaje del usuario
        telefono = tracker.get_slot("telefono_cliente")
        
        if not telefono:
            dispatcher.utter_message(text="📞 ¿Podrías proporcionarme tu número de teléfono para consultar tus pedidos?")
            return []
        
        # Consultar pedidos del cliente
        query = """
        SELECT p.id, p.total, p.estado, p.fecha_pedido, p.fecha_entrega,
               pr.nombre as producto, dp.cantidad
        FROM pedidos p
        JOIN clientes c ON p.cliente_id = c.id  
        JOIN detalle_pedidos dp ON p.id = dp.pedido_id
        JOIN productos pr ON dp.producto_id = pr.id
        WHERE c.telefono = %s
        ORDER BY p.fecha_pedido DESC
        LIMIT 10
        """
        
        pedidos = db.execute_query(query, (telefono,), fetch=True)
        
        if pedidos:
            mensaje = "📋 **TUS PEDIDOS RECIENTES:**\n\n"
            pedido_actual = None
            
            for pedido in pedidos:
                if pedido_actual != pedido['id']:
                    if pedido_actual is not None:
                        mensaje += "\n" + "─" * 30 + "\n"
                    
                    pedido_actual = pedido['id']
                    estado_emoji = {
                        'pendiente': '⏳',
                        'confirmado': '✅', 
                        'enviado': '🚚',
                        'entregado': '📦',
                        'cancelado': '❌'
                    }.get(pedido['estado'], '📋')
                    
                    mensaje += f"{estado_emoji} **Pedido #{pedido['id']}**\n"
                    mensaje += f"📅 Fecha: {pedido['fecha_pedido'].strftime('%d/%m/%Y %H:%M')}\n"
                    mensaje += f"💰 Total: ${pedido['total']:,.0f}\n"
                    mensaje += f"📊 Estado: {pedido['estado'].title()}\n"
                    if pedido['fecha_entrega']:
                        mensaje += f"🚚 Entrega: {pedido['fecha_entrega'].strftime('%d/%m/%Y')}\n"
                    mensaje += f"📦 Productos:\n"
                
                mensaje += f"   • {pedido['producto']} x{pedido['cantidad']}\n"
            
            mensaje += "\n¿Necesitas información específica sobre algún pedido? 🤔"
        else:
            mensaje = "❌ No encontré pedidos asociados a ese número de teléfono. ¿Estás seguro del número?"
        
        dispatcher.utter_message(text=mensaje)
        return []

class ActionEstadisticasVentas(Action):
    def name(self) -> Text:
        return "action_estadisticas_ventas"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Solo disponible para administradores (simplificado)
        query = """
        SELECT * FROM reporte_ventas
        ORDER BY revenue_total DESC NULLS LAST
        LIMIT 10
        """
        
        estadisticas = db.execute_query(query, fetch=True)
        
        if estadisticas:
            mensaje = "📊 **REPORTE DE VENTAS - TOP 10:**\n\n"
            for i, stat in enumerate(estadisticas, 1):
                revenue = stat['revenue_total'] or 0
                cantidad = stat['cantidad_total'] or 0
                veces = stat['veces_pedido'] or 0
                
                mensaje += f"{i}. **{stat['producto']}**\n"
                mensaje += f"   💰 Ingresos: ${revenue:,.0f}\n"
                mensaje += f"   📦 Cantidad vendida: {cantidad}\n" 
                mensaje += f"   🔢 Veces pedido: {veces}\n\n"
        else:
            mensaje = "📊 No hay datos de ventas disponibles aún."
        
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
        except Exception as e:
            logger.error(f"Error logging conversación: {e}")
        
        return []
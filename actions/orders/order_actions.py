"""
Acciones relacionadas con la confirmación y creación de pedidos
"""
from typing import Any, Text, Dict, List
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.database import db
from actions.database.queries import (
    GET_OR_CREATE_CUSTOMER,
    CREATE_SHIPPING_DATA,
    CREATE_ORDER,
    CREATE_ORDER_DETAIL,
    UPDATE_INVENTORY_RESERVE,
    GET_NEXT_ORDER_NUMBER
)

logger = logging.getLogger(__name__)


class ActionConfirmarPedido(Action):
    """Confirma el pedido y lo guarda en la base de datos"""

    def name(self) -> Text:
        return "action_confirmar_pedido"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        # Obtener información de envío desde los slots
        nombre_receptor = tracker.get_slot("nombre_receptor")
        telefono = tracker.get_slot("telefono")
        direccion = tracker.get_slot("direccion")

        # LIMPIEZA: Extraer solo los datos relevantes si vienen en multilínea
        # El usuario puede enviar todo junto en 3 líneas: nombre\nteléfono\ndirección
        if nombre_receptor and '\n' in str(nombre_receptor):
            lines = [line.strip() for line in str(nombre_receptor).split('\n') if line.strip()]
            if len(lines) >= 1:
                nombre_receptor = lines[0]  # Tomar solo la primera línea como nombre

        if telefono and '\n' in str(telefono):
            lines = [line.strip() for line in str(telefono).split('\n') if line.strip()]
            if len(lines) >= 1:
                telefono = lines[0]  # Tomar solo la primera línea

        if direccion and '\n' in str(direccion):
            # Para dirección, mantener todas las líneas pero unirlas con espacio
            direccion = ' '.join([line.strip() for line in str(direccion).split('\n') if line.strip()])

        # Obtener información del carrito
        carrito_productos = tracker.get_slot("carrito_productos")
        carrito_total = tracker.get_slot("carrito_total")

        # Validaciones básicas
        if not nombre_receptor or not telefono or not direccion:
            dispatcher.utter_message(
                text="Lo siento, necesito la información completa de envío para confirmar el pedido."
            )
            return []

        if not carrito_productos or len(carrito_productos) == 0:
            dispatcher.utter_message(
                text="No tienes productos en tu carrito. Agrega algunos productos primero."
            )
            return []

        try:
            # Iniciar transacción (conectar a DB)
            conn = db.get_connection()
            if not conn:
                raise Exception("No se pudo conectar a la base de datos")

            logger.info(f"Iniciando creación de pedido para {nombre_receptor}")

            # 1. Crear o actualizar cliente
            customer_result = db.execute_query(
                GET_OR_CREATE_CUSTOMER,
                (nombre_receptor, telefono),
                fetch=True
            )
            customer_id = customer_result[0]['id']
            logger.info(f"Cliente creado/actualizado: ID {customer_id}")

            # 2. Crear datos de envío
            shipping_result = db.execute_query(
                CREATE_SHIPPING_DATA,
                (customer_id, direccion, telefono, nombre_receptor),
                fetch=True
            )
            shipping_data_id = shipping_result[0]['id']
            logger.info(f"Datos de envío creados: ID {shipping_data_id}")

            # 3. Generar número de orden
            order_number_result = db.execute_query(
                GET_NEXT_ORDER_NUMBER,
                fetch=True
            )
            order_number = order_number_result[0]['next_number']
            logger.info(f"Número de orden generado: {order_number}")

            # 4. Calcular subtotal y total
            subtotal = float(carrito_total)
            shipping_cost = 0.00  # TODO: Calcular según lógica de negocio
            total = subtotal + shipping_cost

            # 5. Crear orden
            order_notes = f"Pedido realizado vía chatbot. Total de {len(carrito_productos)} productos."
            order_result = db.execute_query(
                CREATE_ORDER,
                (order_number, customer_id, shipping_data_id, subtotal,
                 shipping_cost, total, order_notes),
                fetch=True
            )
            order_id = order_result[0]['id']
            logger.info(f"Orden creada: ID {order_id}, Número {order_number}")

            # 6. Crear detalles de orden y actualizar inventario
            for item in carrito_productos:
                product_id = item['product_id']
                quantity = int(item['quantity'])
                unit_price = float(item['unit_price'])
                subtotal_item = float(item['subtotal'])

                # Insertar detalle de orden
                db.execute_query(
                    CREATE_ORDER_DETAIL,
                    (order_id, product_id, quantity, unit_price, subtotal_item),
                    fetch=False
                )

                # Actualizar inventario (reservar cantidad y reducir disponible)
                db.execute_query(
                    UPDATE_INVENTORY_RESERVE,
                    (quantity, quantity, product_id, quantity),
                    fetch=False
                )

            logger.info(f"Orden {order_number} completada exitosamente")

            # Mensaje de confirmación
            mensaje = f"✅ **¡Pedido Confirmado!**\n\n"
            mensaje += f"📋 **Número de orden:** {order_number}\n"
            mensaje += f"👤 **Nombre:** {nombre_receptor}\n"
            mensaje += f"📞 **Teléfono:** {telefono}\n"
            mensaje += f"📍 **Dirección:** {direccion}\n\n"
            mensaje += f"**Resumen del pedido:**\n"
            for item in carrito_productos:
                mensaje += f"   • {int(item['quantity'])} {item['product_name']} - Q{float(item['subtotal']):.2f}\n"
            mensaje += f"\n💵 **Total:** Q{total:.2f}\n\n"
            mensaje += "Te contactaremos pronto para confirmar la entrega. ¡Gracias por tu compra! 🎉"

            dispatcher.utter_message(text=mensaje)

            # Limpiar slots del carrito y datos de envío
            return [
                SlotSet("carrito_productos", []),
                SlotSet("carrito_total", 0.0),
                SlotSet("carrito_cantidad_items", 0),
                SlotSet("nombre_receptor", None),
                SlotSet("telefono", None),
                SlotSet("direccion", None)
            ]

        except Exception as e:
            logger.error(f"Error al confirmar pedido: {str(e)}")
            dispatcher.utter_message(
                text=f"Lo siento, ocurrió un error al procesar tu pedido: {str(e)}\n\nPor favor, intenta de nuevo más tarde."
            )
            return []

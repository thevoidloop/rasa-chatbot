"""
Acciones relacionadas con el carrito de compras
"""
from typing import Any, Text, Dict, List
import json
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

from actions.database import db
from actions.database.queries import SEARCH_PRODUCT_BY_NAME, GET_LAST_CART_STATE
from actions.utils import normalize_product_name
from actions.cart.cart_utils import (
    calculate_unit_price,
    calculate_cart_totals,
    add_or_update_cart_item,
    format_cart_summary
)

logger = logging.getLogger(__name__)


class ActionRecuperarCarrito(Action):
    """Recupera el carrito de la última sesión del cliente"""

    def name(self) -> Text:
        return "action_recuperar_carrito"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        sender_id = tracker.sender_id
        logger.info(f"Intentando recuperar carrito para sender_id: {sender_id}")

        resultado = db.execute_query(GET_LAST_CART_STATE, (sender_id,), fetch=True)

        if resultado and resultado[0]['carrito_data']:
            try:
                carrito_anterior = json.loads(resultado[0]['carrito_data'])

                if carrito_anterior and len(carrito_anterior) > 0:
                    total_carrito, cantidad_items = calculate_cart_totals(carrito_anterior)

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

        # Buscar producto en BD con búsqueda flexible
        resultado = db.execute_query(
            SEARCH_PRODUCT_BY_NAME,
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

        # Calcular precio según cantidad
        precio_unitario, precio_tipo = calculate_unit_price(cantidad_solicitada, prod)
        subtotal_item = precio_unitario * cantidad_solicitada

        # Obtener carrito actual
        carrito = tracker.get_slot("carrito_productos") or []

        # Agregar o actualizar producto en el carrito
        carrito = add_or_update_cart_item(carrito, prod, cantidad_solicitada, precio_unitario, precio_tipo)

        # Calcular totales
        total_carrito, cantidad_items = calculate_cart_totals(carrito)

        # Mensaje de confirmación
        mensaje = f"✅ **{cantidad_solicitada} x {prod['name']}** agregado al carrito\n\n"
        mensaje += f"💰 Precio unitario: Q{precio_unitario:.2f}\n"
        mensaje += f"💵 Subtotal: Q{subtotal_item:.2f}\n\n"
        mensaje += format_cart_summary(carrito, total_carrito)
        mensaje += "\n\n¿Quieres seguir comprando o ver más productos? 🛍️"

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("carrito_productos", carrito),
            SlotSet("carrito_total", total_carrito),
            SlotSet("carrito_cantidad_items", cantidad_items)
        ]

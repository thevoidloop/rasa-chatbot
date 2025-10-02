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
from actions.database.queries import FUZZY_SEARCH_PRODUCT, SEARCH_PRODUCT_BY_NAME, GET_LAST_CART_STATE
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

                    mensaje = "Hey, te quedó esto pendiente de la última vez:\n\n"
                    for item in carrito_anterior:
                        mensaje += f"   • {item['quantity']} {item['product_name']} Q{float(item['subtotal']):.2f}\n"

                    mensaje += f"\n   💵 Total: Q{total_carrito:.2f}\n\n"
                    mensaje += "¿Quieres continuar o prefieres empezar de nuevo? 🛒"

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
            dispatcher.utter_message(text="¿Qué producto te gustaría agregar? 🤔")
            return []

        if not cantidad_solicitada:
            cantidad_solicitada = 1
        else:
            cantidad_solicitada = int(float(cantidad_solicitada))

        # Validación 1: String muy corto (menos de 3 caracteres)
        if len(producto.strip()) < 3:
            mensaje = "Mmm, no te entendí bien. ¿Me puedes decir el nombre del producto completo?\n"
            mensaje += "Por ejemplo: camisa, vestido, pantalón..."
            dispatcher.utter_message(text=mensaje)
            return []

        # Normalizar nombre de producto (manejar plurales y acentos)
        producto_normalizado = normalize_product_name(producto)

        # Estrategia de búsqueda progresiva:
        # 1. Intentar fuzzy matching (tolerante a typos)
        logger.info(f"Buscando producto con fuzzy matching: '{producto}'")
        resultado = db.execute_query(
            FUZZY_SEARCH_PRODUCT,
            (producto_normalizado, producto_normalizado),
            fetch=True
        )

        # 2. Si no encuentra con fuzzy, intentar LIKE tradicional
        if not resultado:
            logger.info(f"Fuzzy matching no encontró resultados, intentando LIKE")
            resultado = db.execute_query(
                SEARCH_PRODUCT_BY_NAME,
                (f"%{producto_normalizado}%", f"%{producto.lower()}%",
                 f"%{producto_normalizado}%", f"%{producto.lower()}%"),
                fetch=True
            )

        # 3. Si aún no encuentra, mostrar error
        if not resultado:
            mensaje = f"Lo siento, no entendí a qué te refieres con '{producto}' 🤔\n\n"
            mensaje += "Tengo estos productos disponibles:\n"
            mensaje += "• Camisa Básica\n• Pantalón Casual\n• Blusa Elegante\n• Vestido Verano\n• Jean Clásico\n\n"
            mensaje += "¿Quieres que te muestre el catálogo completo?"
            dispatcher.utter_message(text=mensaje)
            return []

        prod = resultado[0]

        # Advertencia si la similitud es baja (fuzzy matching)
        if 'match_score' in prod and prod['match_score'] < 0.5:
            logger.warning(f"Similitud baja ({prod['match_score']:.2f}) para '{producto}' → '{prod['name']}'")
            # No mostramos advertencia al usuario por ahora, solo logging

        # Verificar disponibilidad
        if cantidad_solicitada > prod['available_quantity']:
            mensaje = f"Uy, solo me quedan {prod['available_quantity']} unidades de {prod['name']} disponibles 😕\n\n"
            mensaje += f"¿Te parece si agregamos {prod['available_quantity']}?"
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
        mensaje = f"Perfecto, agregué {cantidad_solicitada} {prod['name']} a tu carrito ✅\n\n"
        mensaje += f"💰 Q{precio_unitario:.2f} c/u\n"
        mensaje += f"💵 Subtotal: Q{subtotal_item:.2f}\n\n"
        mensaje += format_cart_summary(carrito, total_carrito)
        mensaje += "\n\n¿Te gustaría algo más? 🛍️"

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("carrito_productos", carrito),
            SlotSet("carrito_total", total_carrito),
            SlotSet("carrito_cantidad_items", cantidad_items)
        ]

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
from actions.utils import normalize_product_name, normalize_quantity
from actions.cart.cart_utils import (
    calculate_unit_price,
    calculate_cart_totals,
    add_or_update_cart_item,
    format_cart_summary,
    recalculate_cart_prices
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

        # Obtener TODAS las entidades del mensaje (no solo los slots)
        entities = tracker.latest_message.get('entities', [])

        # Extraer productos y cantidades de las entidades
        productos_entidades = [e for e in entities if e['entity'] == 'producto']
        cantidades_entidades = [e for e in entities if e['entity'] == 'cantidad']

        # Si no hay productos en las entidades, intentar obtener del slot
        if not productos_entidades:
            producto = tracker.get_slot("producto_seleccionado")
            if not producto:
                dispatcher.utter_message(text="¿Qué producto te gustaría agregar? 🤔")
                return []
            productos_entidades = [{'value': producto}]

        # Emparejar productos con cantidades
        # Si hay menos cantidades que productos, asumir cantidad 1 para los faltantes
        productos_a_agregar = []
        for i, prod_entity in enumerate(productos_entidades):
            producto_nombre = prod_entity['value']
            if i < len(cantidades_entidades):
                cantidad_str = str(cantidades_entidades[i]['value'])
            else:
                cantidad_str = "1"

            productos_a_agregar.append({
                'nombre': producto_nombre,
                'cantidad_str': cantidad_str
            })

        logger.info(f"Procesando {len(productos_a_agregar)} productos: {productos_a_agregar}")

        # Obtener carrito actual
        carrito = tracker.get_slot("carrito_productos") or []
        productos_agregados = []

        # Procesar cada producto
        for item in productos_a_agregar:
            producto = item['nombre']
            cantidad_str = item['cantidad_str']

            # Normalizar cantidad
            cantidad_solicitada, cantidad_descripcion = normalize_quantity(cantidad_str, None)
            cantidad_solicitada = int(cantidad_solicitada)

            # Validación: String muy corto (menos de 3 caracteres)
            if len(producto.strip()) < 3:
                logger.warning(f"Producto '{producto}' demasiado corto, omitiendo")
                continue

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

            # 3. Si no encuentra, omitir este producto y continuar con el siguiente
            if not resultado:
                logger.warning(f"No se encontró el producto: '{producto}'")
                continue

            prod = resultado[0]

            # Si la cantidad original era un "fardo", recalcular con bundle_quantity del producto
            if "fardo" in cantidad_str.lower():
                bundle_quantity = prod.get('bundle_quantity', 12)  # Default 12 si no existe
                cantidad_solicitada, cantidad_descripcion = normalize_quantity(cantidad_str, bundle_quantity)
                cantidad_solicitada = int(cantidad_solicitada)
                logger.info(f"Cantidad recalculada con bundle_quantity={bundle_quantity}: {cantidad_descripcion}")

            # Advertencia si la similitud es baja (fuzzy matching)
            if 'match_score' in prod and prod['match_score'] < 0.5:
                logger.warning(f"Similitud baja ({prod['match_score']:.2f}) para '{producto}' → '{prod['name']}'")

            # Verificar disponibilidad
            if cantidad_solicitada > prod['available_quantity']:
                logger.warning(f"Stock insuficiente para {prod['name']}: {cantidad_solicitada} > {prod['available_quantity']}")
                continue

            # Calcular precio según cantidad (se recalculará después según total del carrito)
            precio_unitario, precio_tipo = calculate_unit_price(cantidad_solicitada, prod)

            # Agregar o actualizar producto en el carrito
            carrito = add_or_update_cart_item(carrito, prod, cantidad_solicitada, precio_unitario, precio_tipo)

            # Registrar producto agregado
            productos_agregados.append({
                'nombre': prod['name'],
                'cantidad': cantidad_solicitada,
                'cantidad_desc': cantidad_descripcion
            })

        # Si no se agregó ningún producto, mostrar error
        if not productos_agregados:
            mensaje = "Lo siento, no pude agregar ningún producto. ¿Podrías intentar de nuevo? 🤔"
            dispatcher.utter_message(text=mensaje)
            return []

        # IMPORTANTE: Recalcular precios basándose en la cantidad total del carrito
        carrito = recalculate_cart_prices(carrito)

        # Calcular totales después del recalculo
        total_carrito, cantidad_items = calculate_cart_totals(carrito)

        # Determinar el tier aplicado basándose en la cantidad total
        if cantidad_items >= 12:
            tier_name = "mayorista"
        elif cantidad_items >= 6:
            tier_name = "emprendedor"
        else:
            tier_name = "minorista"

        # Mensaje de confirmación con todos los productos agregados
        if len(productos_agregados) == 1:
            mensaje = f"Perfecto, agregué {productos_agregados[0]['cantidad_desc']} de {productos_agregados[0]['nombre']} a tu carrito ✅\n\n"
        else:
            mensaje = "Perfecto, agregué estos productos a tu carrito ✅\n\n"
            for prod_ag in productos_agregados:
                mensaje += f"   • {prod_ag['cantidad_desc']} de {prod_ag['nombre']}\n"
            mensaje += "\n"

        mensaje += f"🏷️ Precio aplicado: **{tier_name.capitalize()}** ({int(cantidad_items)} unidades en total)\n\n"
        mensaje += format_cart_summary(carrito, total_carrito)

        dispatcher.utter_message(text=mensaje)

        return [
            SlotSet("carrito_productos", carrito),
            SlotSet("carrito_total", total_carrito),
            SlotSet("carrito_cantidad_items", cantidad_items)
        ]

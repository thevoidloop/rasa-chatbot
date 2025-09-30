"""
Acciones relacionadas con el catálogo de productos
"""
from typing import Any, Text, Dict, List
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher

from actions.database import db
from actions.database.queries import GET_AVAILABLE_PRODUCTS

logger = logging.getLogger(__name__)


class ActionMostrarCatalogo(Action):
    """Muestra el catálogo completo de productos disponibles"""

    def name(self) -> Text:
        return "action_mostrar_catalogo"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        logger.info("Ejecutando action_mostrar_catalogo")

        productos = db.execute_query(GET_AVAILABLE_PRODUCTS, fetch=True)

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

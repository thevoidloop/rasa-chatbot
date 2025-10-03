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
            catalogo_mensaje = "Mira, esto es lo que tenemos ahora mismo:\n\n"

            for i, producto in enumerate(productos, 1):
                catalogo_mensaje += f"**{i}. {producto['name']}**\n"

                if producto['description']:
                    catalogo_mensaje += f"   {producto['description']}\n"

                catalogo_mensaje += f"   💰 Q{producto['individual_price']:.2f} (unidad)\n"

                # Mostrar precios de mayoreo y fardo si existen
                if producto['wholesale_price'] and producto['wholesale_quantity']:
                    catalogo_mensaje += f"   💰 Q{producto['wholesale_price']:.2f} (desde {producto['wholesale_quantity']} unidades)\n"

                if producto['bundle_price'] and producto['bundle_quantity']:
                    catalogo_mensaje += f"   💰 Q{producto['bundle_price']:.2f} (fardo de {producto['bundle_quantity']} unidades)\n"

                catalogo_mensaje += f"   📦 {producto['available_quantity']} unidades disponibles\n"
                catalogo_mensaje += "\n"

            catalogo_mensaje += "¿Te interesa algo de esto? 🛒"

        else:
            catalogo_mensaje = "Lo siento, ahora mismo no tengo productos disponibles 😔"

        dispatcher.utter_message(text=catalogo_mensaje)

        logger.info(f"Catálogo mostrado con {len(productos) if productos else 0} productos")

        return []

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import requests

class ActionMostrarCatalogo(Action):
    def name(self) -> Text:
        return "action_mostrar_catalogo"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Aquí conectarías con tu BD o API
        catalogo_mensaje = """
        📋 **CATÁLOGO DE PRODUCTOS**
        
        👕 Camisas - $25.000
        👖 Pantalones - $45.000  
        👗 Vestidos - $55.000
        👚 Blusas - $30.000
        
        ¿Qué producto te interesa?
        """
        
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
            dispatcher.utter_message(text="¿De qué producto quieres saber el precio?")
            return []
        
        # Simulación de consulta a BD
        precios = {
            "camisa": {"unidad": 25000, "media_docena": 140000, "docena": 270000},
            "pantalon": {"unidad": 45000, "media_docena": 250000, "docena": 480000},
            "vestido": {"unidad": 55000, "media_docena": 310000, "docena": 600000},
            "blusa": {"unidad": 30000, "media_docena": 170000, "docena": 330000}
        }
        
        producto_lower = producto.lower()
        if producto_lower in precios:
            precio_info = precios[producto_lower]
            mensaje = f"""
            💰 **Precios para {producto}:**
            
            • 1 unidad: ${precio_info['unidad']:,}
            • Media docena (6): ${precio_info['media_docena']:,}  
            • Docena (12): ${precio_info['docena']:,}
            
            ¿Cuántas unidades necesitas?
            """
            dispatcher.utter_message(text=mensaje)
        else:
            dispatcher.utter_message(text=f"No encontré información de precios para {producto}")
        
        return []

class ActionVerificarDisponibilidad(Action):
    def name(self) -> Text:
        return "action_verificar_disponibilidad"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        producto = tracker.get_slot("producto_seleccionado")
        
        # Simulación de consulta a inventario
        disponible = True  # En un caso real, consultarías tu BD
        
        if disponible:
            mensaje = f"✅ ¡Excelente! Tenemos {producto} disponible en stock."
        else:
            mensaje = f"❌ Lo siento, {producto} no está disponible actualmente."
        
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
            dispatcher.utter_message(text="Necesito saber qué producto y cuánta cantidad quieres.")
            return []
        
        # Aquí crearías el pedido en tu sistema
        mensaje = f"""
        🛒 **RESUMEN DE PEDIDO**
        
        Producto: {producto}
        Cantidad: {int(cantidad)} unidades
        
        ¿Confirmas este pedido? 
        
        Responde 'sí' para continuar o 'no' para cancelar.
        """
        
        dispatcher.utter_message(text=mensaje)
        return []
        
"""
Acción de validación para el formulario de información de envío
"""
from typing import Any, Text, Dict
import re
import logging

from rasa_sdk import FormValidationAction, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

logger = logging.getLogger(__name__)

# Debug: imprimir al cargar el módulo
print("=" * 80)
print("CARGANDO MÓDULO validation_actions.py - VERSION CON run() OVERRIDE")
print("=" * 80)


class ValidateShippingInfoForm(FormValidationAction):
    """Valida y extrae información del formulario de envío"""

    def name(self) -> Text:
        return "validate_shipping_info_form"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict
    ) -> list:
        """Validación personalizada con extracción multilínea"""
        from rasa_sdk.events import SlotSet

        print("=" * 80)
        print("MÉTODO RUN() EJECUTÁNDOSE EN ValidateShippingInfoForm")
        print("=" * 80)

        logger.info("=== Validando formulario de envío ===")
        text = tracker.latest_message.get("text", "")
        requested_slot = tracker.get_slot("requested_slot")
        logger.info(f"Slot solicitado: {requested_slot}, Texto: '{text}'")

        # Si es la primera vez que se pide el nombre, intentar extraer todos los datos
        if requested_slot == "nombre_receptor":
            # Detectar si el texto tiene múltiples líneas
            if '\n' in text:
                multiline_data = self.extract_multiline_data(text)
                logger.info(f"Datos multilínea detectados: {multiline_data}")

                if multiline_data:
                    # Retornar los 3 slots a la vez
                    return [
                        SlotSet("nombre_receptor", multiline_data['nombre_receptor']),
                        SlotSet("telefono", multiline_data['telefono']),
                        SlotSet("direccion", multiline_data['direccion']),
                        SlotSet("requested_slot", None)  # Completar el formulario
                    ]

            # Si no es multilínea, extraer solo el nombre (primera línea)
            nombre = text.split('\n')[0].strip() if text else ""
            if nombre and len(nombre) >= 3:
                return [SlotSet("nombre_receptor", nombre)]
            else:
                dispatcher.utter_message(text="Por favor proporciona un nombre válido.")
                return [SlotSet("nombre_receptor", None)]

        # Para teléfono, extraer 8 dígitos
        elif requested_slot == "telefono":
            phone = self.extract_phone_number(text)
            if phone and len(phone) == 8:
                return [SlotSet("telefono", phone)]
            else:
                dispatcher.utter_message(text="Por favor proporciona un número de teléfono válido (8 dígitos).")
                return [SlotSet("telefono", None)]

        # Para dirección, validar longitud mínima
        elif requested_slot == "direccion":
            if text and len(text.strip()) >= 10:
                return [SlotSet("direccion", text.strip())]
            else:
                dispatcher.utter_message(text="Por favor proporciona una dirección completa.")
                return [SlotSet("direccion", None)]

        # Default: usar el comportamiento por defecto
        return await super().run(dispatcher, tracker, domain)

    @staticmethod
    def extract_phone_number(text: str) -> str:
        """Extrae número de teléfono del texto (8 dígitos)"""
        # Eliminar espacios y guiones
        clean = re.sub(r'[\s\-]', '', text)
        # Buscar 8 dígitos consecutivos
        match = re.search(r'(\d{8})', clean)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def extract_multiline_data(text: str) -> Dict[str, str]:
        """Extrae datos cuando se envían en múltiples líneas"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        result = {}
        if len(lines) >= 3:
            # Primera línea: nombre
            result['nombre_receptor'] = lines[0]

            # Segunda línea: buscar teléfono (8 dígitos)
            phone = ValidateShippingInfoForm.extract_phone_number(lines[1])
            if phone:
                result['telefono'] = phone

            # Tercera línea en adelante: dirección
            result['direccion'] = ' '.join(lines[2:])

            # Solo retornar si se encontraron los 3 campos
            if 'telefono' in result and 'direccion' in result and result['direccion']:
                return result

        return {}

    async def validate_nombre_receptor(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Valida el nombre del receptor"""
        # Intentar extraer todos los datos si vienen en multilinea
        text = tracker.latest_message.get("text", "")
        logger.info(f"Validando nombre_receptor. Text: '{text}', slot_value: '{slot_value}'")

        # Detectar si el texto tiene múltiples líneas
        if '\n' in text or (slot_value and '\n' in str(slot_value)):
            multiline_data = self.extract_multiline_data(text)
            logger.info(f"Multiline data extracted: {multiline_data}")

            if multiline_data:
                # Si se encontraron los 3 campos, retornarlos todos
                logger.info(f"Retornando datos multilinea completos: {multiline_data}")
                return multiline_data

        # Si no es multilínea o no se pudieron extraer los 3 campos, validar solo el nombre
        # Tomar solo la primera línea si viene con saltos de línea
        nombre = str(slot_value).split('\n')[0].strip() if slot_value else ""

        if nombre and len(nombre) >= 3:
            logger.info(f"Validando solo nombre (primera línea): {nombre}")
            return {"nombre_receptor": nombre}
        else:
            dispatcher.utter_message(text="Por favor proporciona un nombre válido.")
            return {"nombre_receptor": None}

    async def validate_telefono(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Valida el teléfono"""
        if slot_value:
            phone = self.extract_phone_number(str(slot_value))
            if phone and len(phone) == 8:
                return {"telefono": phone}

        dispatcher.utter_message(text="Por favor proporciona un número de teléfono válido (8 dígitos).")
        return {"telefono": None}

    async def validate_direccion(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Valida la dirección"""
        if slot_value and len(str(slot_value).strip()) >= 10:
            return {"direccion": slot_value.strip()}
        else:
            dispatcher.utter_message(text="Por favor proporciona una dirección completa.")
            return {"direccion": None}

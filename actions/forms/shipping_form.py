"""
Formulario personalizado para recolectar información de envío
Permite que el usuario proporcione todos los datos en un solo mensaje
"""
from typing import Any, Text, Dict, List, Optional
import re
import logging

from rasa_sdk import Tracker, FormValidationAction
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

logger = logging.getLogger(__name__)


class ShippingInfoForm(FormValidationAction):
    """Validación del formulario de información de envío"""

    def name(self) -> Text:
        return "validate_shipping_info_form"

    @staticmethod
    def extract_phone_number(text: str) -> Optional[str]:
        """Extrae número de teléfono del texto (8 dígitos en Guatemala)"""
        # Buscar secuencias de 8 dígitos
        phone_patterns = [
            r'\b(\d{8})\b',  # 8 dígitos consecutivos
            r'\b(\d{4})-?(\d{4})\b',  # 4-4 dígitos con guión opcional
        ]

        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                # Unir los grupos capturados y eliminar guiones
                phone = ''.join(match.groups()).replace('-', '')
                if len(phone) == 8:
                    return phone
        return None

    @staticmethod
    def extract_from_multiline(text: str) -> Dict[str, Optional[str]]:
        """
        Extrae información cuando el usuario envía todo en un solo mensaje
        Formato esperado (líneas separadas):
        Nombre
        Teléfono
        Dirección
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        result = {
            'nombre_receptor': None,
            'telefono': None,
            'direccion': None
        }

        # Si hay exactamente 3 líneas, asumimos el orden: nombre, teléfono, dirección
        if len(lines) == 3:
            result['nombre_receptor'] = lines[0]
            # Intentar extraer teléfono de la segunda línea
            phone = ShippingInfoForm.extract_phone_number(lines[1])
            if phone:
                result['telefono'] = phone
                result['direccion'] = lines[2]
            return result

        # Si no hay 3 líneas, intentar extraer teléfono del texto completo
        phone = ShippingInfoForm.extract_phone_number(text)
        if phone:
            result['telefono'] = phone
            # Intentar inferir nombre y dirección
            # El nombre suele ser la primera parte (antes del teléfono)
            # La dirección es la parte después del teléfono
            parts = text.split(phone)
            if len(parts) == 2:
                before = parts[0].strip()
                after = parts[1].strip()

                # Eliminar saltos de línea del before y after
                before_lines = [l.strip() for l in before.split('\n') if l.strip()]
                after_lines = [l.strip() for l in after.split('\n') if l.strip()]

                if before_lines:
                    result['nombre_receptor'] = before_lines[0]
                if after_lines:
                    result['direccion'] = ' '.join(after_lines)

        return result

    async def required_slots(
        self,
        domain_slots: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> List[Text]:
        """Devuelve lista de slots requeridos"""
        return ["nombre_receptor", "telefono", "direccion"]

    async def extract_nombre_receptor(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Extrae el nombre del receptor"""
        # Si el slot ya está lleno, no hacer nada
        if tracker.get_slot("nombre_receptor"):
            return {}

        text = tracker.latest_message.get("text", "")

        # Intentar extraer de un mensaje multilinea
        extracted = self.extract_from_multiline(text)
        if extracted.get('nombre_receptor'):
            return {"nombre_receptor": extracted['nombre_receptor']}

        # Si no se pudo extraer y no es el primer slot que se solicita,
        # asumir que todo el texto es el nombre
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "nombre_receptor":
            return {"nombre_receptor": text.strip()}

        return {}

    async def extract_telefono(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Extrae el teléfono"""
        # Si el slot ya está lleno, no hacer nada
        if tracker.get_slot("telefono"):
            return {}

        text = tracker.latest_message.get("text", "")

        # Intentar extraer de un mensaje multilinea
        extracted = self.extract_from_multiline(text)
        if extracted.get('telefono'):
            return {"telefono": extracted['telefono']}

        # Intentar extraer teléfono del mensaje actual
        phone = self.extract_phone_number(text)
        if phone:
            return {"telefono": phone}

        return {}

    async def extract_direccion(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Extrae la dirección"""
        # Si el slot ya está lleno, no hacer nada
        if tracker.get_slot("direccion"):
            return {}

        text = tracker.latest_message.get("text", "")

        # Intentar extraer de un mensaje multilinea
        extracted = self.extract_from_multiline(text)
        if extracted.get('direccion'):
            return {"direccion": extracted['direccion']}

        # Si no se pudo extraer y no es el primer slot que se solicita,
        # asumir que todo el texto es la dirección
        requested_slot = tracker.get_slot("requested_slot")
        if requested_slot == "direccion":
            return {"direccion": text.strip()}

        return {}

    async def validate_nombre_receptor(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Valida el nombre del receptor"""
        if slot_value and len(slot_value.strip()) >= 3:
            return {"nombre_receptor": slot_value.strip()}
        else:
            dispatcher.utter_message(text="Por favor proporciona un nombre válido (mínimo 3 caracteres).")
            return {"nombre_receptor": None}

    async def validate_telefono(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        """Valida el número de teléfono"""
        if slot_value and len(slot_value) == 8 and slot_value.isdigit():
            return {"telefono": slot_value}
        else:
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
        if slot_value and len(slot_value.strip()) >= 10:
            return {"direccion": slot_value.strip()}
        else:
            dispatcher.utter_message(text="Por favor proporciona una dirección válida y completa.")
            return {"direccion": None}

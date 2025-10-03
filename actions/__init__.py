"""
Entry point para todas las acciones customizadas del chatbot RASA
Este archivo centraliza los imports de todos los modulos
"""
import logging

# Configuracion de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Importar todas las acciones
from actions.catalog import ActionMostrarCatalogo
from actions.cart import ActionAgregarAlCarrito, ActionRecuperarCarrito
from actions.orders import ActionConfirmarPedido

# Importar formularios
try:
    from actions.forms import ValidateShippingInfoForm
    __all__ = [
        'ActionMostrarCatalogo',
        'ActionAgregarAlCarrito',
        'ActionRecuperarCarrito',
        'ActionConfirmarPedido',
        'ValidateShippingInfoForm',
    ]
except ImportError as e:
    logger.warning(f"No se pudo importar ValidateShippingInfoForm: {e}")
    __all__ = [
        'ActionMostrarCatalogo',
        'ActionAgregarAlCarrito',
        'ActionRecuperarCarrito',
        'ActionConfirmarPedido',
    ]

"""
Punto de entrada principal para el action server de RASA
Este archivo debe existir para mantener compatibilidad con RASA,
pero ahora solo importa las acciones de los módulos organizados.
"""
# Importar todas las acciones desde los módulos organizados
from actions.catalog import ActionMostrarCatalogo
from actions.cart import ActionAgregarAlCarrito, ActionRecuperarCarrito

# RASA detecta automáticamente todas las clases que heredan de Action
# No es necesario exportar explícitamente las acciones

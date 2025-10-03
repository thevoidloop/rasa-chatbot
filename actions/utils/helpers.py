"""
Funciones helper compartidas entre diferentes módulos del chatbot
"""
import unicodedata
import re
from typing import Tuple, Optional


def normalize_product_name(name: str) -> str:
    """
    Normaliza nombres de productos eliminando plurales comunes en español
    y removiendo acentos para búsqueda flexible

    Args:
        name: Nombre del producto a normalizar

    Returns:
        str: Nombre normalizado sin acentos y en singular
    """
    name = name.lower().strip()

    # Remover acentos para búsqueda más flexible
    name_no_accents = ''.join(
        c for c in unicodedata.normalize('NFD', name)
        if unicodedata.category(c) != 'Mn'
    )

    # Plurales comunes en español
    # Reglas de pluralización en orden de prioridad
    plural_rules = [
        ('ces', 'z'),      # luces -> luz, peces -> pez
        ('nes', 'n'),      # pantalones -> pantalon
        ('ses', 's'),      # blusas -> blusa (pero esto ya está cubierto por 's')
        ('ies', 'y'),      # No común en español pero por si acaso
        ('as', 'a'),       # camisas -> camisa, blusas -> blusa
        ('os', 'o'),       # pantalones -> pantalon (ya cubierto), vestidos -> vestido
        ('es', ''),        # jeans -> jean (si termina en consonante + es)
        ('s', ''),         # remover 's' simple al final
    ]

    # Aplicar reglas de pluralización
    for plural_suffix, singular_suffix in plural_rules:
        if name_no_accents.endswith(plural_suffix):
            # Para evitar casos como "tres" -> "tre", verificar longitud mínima
            if len(name_no_accents) > len(plural_suffix) + 1:
                return name_no_accents[:-len(plural_suffix)] + singular_suffix

    return name_no_accents


def normalize_quantity(quantity_str: str, product_bundle_quantity: Optional[int] = None) -> Tuple[float, str]:
    """
    Normaliza expresiones de cantidad como 'media docena', 'docena', 'fardo' a números

    Args:
        quantity_str: Texto de cantidad extraído por NLU (ej: "media docena", "2 fardos", "una docena")
        product_bundle_quantity: Número de unidades en un fardo del producto específico (de la BD)

    Returns:
        Tuple[float, str]: (cantidad_numérica, descripción_legible)
        - cantidad_numérica: El número de unidades
        - descripción_legible: Descripción amigable (ej: "1 fardo (12 unidades)")

    Examples:
        normalize_quantity("media docena") -> (6.0, "media docena (6 unidades)")
        normalize_quantity("una docena") -> (12.0, "1 docena (12 unidades)")
        normalize_quantity("2 fardos", 24) -> (48.0, "2 fardos (48 unidades)")
        normalize_quantity("15") -> (15.0, "15 unidades")
    """
    quantity_str = quantity_str.lower().strip()

    # Diccionario de números en texto
    text_numbers = {
        'un': 1, 'una': 1, 'uno': 1,
        'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
        'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10,
        'media': 0.5, '½': 0.5, '1/2': 0.5
    }

    # Patrones de detección
    # Media docena
    if re.search(r'\b(media|½|1\/2)\s*(docena)?\b', quantity_str):
        return (6.0, "media docena (6 unidades)")

    # Docena(s) con número o texto
    docena_match = re.search(r'\b(\d+|un|una|dos|tres|cuatro|cinco)\s*docenas?\b', quantity_str)
    if docena_match:
        num_text = docena_match.group(1)
        multiplier = text_numbers.get(num_text, None)
        if multiplier is None:
            multiplier = int(num_text)
        quantity = multiplier * 12
        plural = "s" if multiplier > 1 else ""
        return (float(quantity), f"{int(multiplier)} docena{plural} ({int(quantity)} unidades)")

    # Fardo(s) con número o texto
    fardo_match = re.search(r'\b(\d+|un|una|dos|tres|cuatro|cinco)?\s*fardos?\b', quantity_str)
    if fardo_match:
        num_text = fardo_match.group(1) if fardo_match.group(1) else 'un'
        multiplier = text_numbers.get(num_text, None)
        if multiplier is None:
            multiplier = int(num_text) if num_text.isdigit() else 1

        if product_bundle_quantity:
            quantity = multiplier * product_bundle_quantity
            plural = "s" if multiplier > 1 else ""
            return (float(quantity), f"{int(multiplier)} fardo{plural} ({int(quantity)} unidades)")
        else:
            # Si no tenemos bundle_quantity, usar valor por defecto de 12
            quantity = multiplier * 12
            plural = "s" if multiplier > 1 else ""
            return (float(quantity), f"{int(multiplier)} fardo{plural} ({int(quantity)} unidades aprox.)")

    # Solo "media" sin docena explícita
    if quantity_str in ['media', '½', '1/2']:
        return (6.0, "media docena (6 unidades)")

    # Intentar convertir número directo
    try:
        # Eliminar texto adicional y extraer solo el número
        number_match = re.search(r'\b(\d+\.?\d*)\b', quantity_str)
        if number_match:
            num = float(number_match.group(1))
            plural = "es" if num != 1 else ""
            return (num, f"{int(num) if num == int(num) else num} unidad{plural}")
    except ValueError:
        pass

    # Por defecto, retornar 1 si no se puede parsear
    return (1.0, "1 unidad")

"""
Funciones helper compartidas entre diferentes módulos del chatbot
"""
import unicodedata


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

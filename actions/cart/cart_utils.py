"""
Utilidades para manejo del carrito de compras
Lógica de pricing tiers, validaciones y cálculos
"""
import logging

logger = logging.getLogger(__name__)


def calculate_unit_price(cantidad: int, producto: dict) -> tuple:
    """
    Calcula el precio unitario según la cantidad solicitada y los tiers de precios

    Pricing tiers:
    - individual_price: precio por unidad cuando cantidad < wholesale_quantity
    - wholesale_price: precio por unidad cuando cantidad >= wholesale_quantity
    - bundle_price: precio por unidad cuando cantidad >= bundle_quantity

    Args:
        cantidad: Cantidad de productos solicitada
        producto: Diccionario con información del producto (individual_price, wholesale_price,
                 bundle_price, bundle_quantity, wholesale_quantity)

    Returns:
        tuple: (precio_unitario, tipo_precio) donde tipo_precio puede ser 'individual',
               'wholesale' o 'bundle'
    """
    bundle_quantity = producto.get('bundle_quantity', 12)
    wholesale_quantity = producto.get('wholesale_quantity', 6)

    # Bundle: cantidad >= bundle_quantity (ej: 12+, 15+, 18+, etc según producto)
    if cantidad >= bundle_quantity and producto.get('bundle_price'):
        precio_unitario = float(producto['bundle_price'])
        precio_tipo = "bundle"
        logger.info(f"Precio bundle aplicado: Q{precio_unitario:.2f}/unidad (desde {bundle_quantity} unidades)")

    # Wholesale: cantidad >= wholesale_quantity pero < bundle_quantity
    elif cantidad >= wholesale_quantity and producto.get('wholesale_price'):
        precio_unitario = float(producto['wholesale_price'])
        precio_tipo = "wholesale"
        logger.info(f"Precio mayoreo aplicado: Q{precio_unitario:.2f}/unidad (desde {wholesale_quantity} unidades)")

    # Individual: cantidad < wholesale_quantity
    else:
        precio_unitario = float(producto['individual_price'])
        precio_tipo = "individual"
        logger.info(f"Precio individual aplicado: Q{precio_unitario:.2f}/unidad")

    return precio_unitario, precio_tipo


def calculate_cart_totals(carrito: list) -> tuple:
    """
    Calcula los totales del carrito

    Args:
        carrito: Lista de items en el carrito

    Returns:
        tuple: (total_carrito, cantidad_total_items)
    """
    total_carrito = sum(float(item['subtotal']) for item in carrito)
    cantidad_items = sum(int(item['quantity']) for item in carrito)

    return total_carrito, cantidad_items


def add_or_update_cart_item(carrito: list, producto: dict, cantidad: int,
                            precio_unitario: float, precio_tipo: str) -> list:
    """
    Agrega un producto al carrito o actualiza la cantidad si ya existe
    Guarda todos los precios del producto para poder recalcular después

    Args:
        carrito: Lista actual del carrito
        producto: Diccionario con información del producto
        cantidad: Cantidad a agregar
        precio_unitario: Precio unitario calculado
        precio_tipo: Tipo de precio aplicado

    Returns:
        list: Carrito actualizado
    """
    producto_existente = False

    # Buscar si el producto ya está en el carrito
    for item in carrito:
        if item['product_id'] == producto['id']:
            item['quantity'] += cantidad
            # No recalculamos aquí, se hará después con la cantidad total
            producto_existente = True
            logger.info(f"Producto existente actualizado: {producto['name']}, nueva cantidad: {item['quantity']}")
            break

    # Si no existe, agregar nuevo item con todos los precios
    if not producto_existente:
        carrito.append({
            'product_id': producto['id'],
            'product_name': producto['name'],
            'product_code': producto['code'],
            'quantity': cantidad,
            'unit_price': precio_unitario,  # Se actualizará después
            'subtotal': precio_unitario * cantidad,  # Se actualizará después
            'price_type': precio_tipo,  # Se actualizará después
            # Guardar todos los precios para recalcular
            'individual_price_value': float(producto['individual_price']),
            'wholesale_price_value': float(producto.get('wholesale_price', producto['individual_price'])),
            'bundle_price_value': float(producto.get('bundle_price', producto['individual_price']))
        })
        logger.info(f"Nuevo producto agregado al carrito: {producto['name']}, cantidad: {cantidad}")

    return carrito


def recalculate_cart_prices(carrito: list) -> list:
    """
    Recalcula los precios de todos los productos en el carrito basándose en la cantidad total.
    El tier de precios se aplica según el total de unidades en el carrito.

    Args:
        carrito: Lista de items en el carrito

    Returns:
        list: Carrito con precios recalculados
    """
    if not carrito:
        return carrito

    # Calcular cantidad total de items en el carrito
    cantidad_total = sum(int(item['quantity']) for item in carrito)

    # Determinar el tier de precios basado en la cantidad total
    if cantidad_total >= 12:
        price_field = 'bundle_price'
        price_type = 'mayorista'
    elif cantidad_total >= 6:
        price_field = 'wholesale_price'
        price_type = 'emprendedor'
    else:
        price_field = 'individual_price'
        price_type = 'minorista'

    logger.info(f"Recalculando precios del carrito. Cantidad total: {cantidad_total}, Tier: {price_type}")

    # Recalcular precios de cada item en el carrito
    for item in carrito:
        # El precio correcto ya está guardado en el item según el campo
        # Necesitamos obtener el producto de nuevo para tener todos los precios
        # Por ahora, asumimos que los precios están en el item

        # Determinar qué precio usar según el tier
        if price_type == 'mayorista' and 'bundle_price_value' in item:
            precio_unitario = float(item['bundle_price_value'])
        elif price_type == 'emprendedor' and 'wholesale_price_value' in item:
            precio_unitario = float(item['wholesale_price_value'])
        else:
            precio_unitario = float(item.get('individual_price_value', item['unit_price']))

        # Actualizar precio unitario y subtotal
        item['unit_price'] = precio_unitario
        item['price_type'] = price_type
        item['subtotal'] = precio_unitario * int(item['quantity'])

    return carrito


def format_cart_summary(carrito: list, total_carrito: float) -> str:
    """
    Formatea un resumen del carrito para mostrar al usuario

    Args:
        carrito: Lista de items en el carrito
        total_carrito: Total del carrito

    Returns:
        str: Mensaje formateado con el resumen del carrito
    """
    mensaje = "🛒 **Resumen del carrito:**\n"

    for item in carrito:
        mensaje += f"   • {item['quantity']} {item['product_name']} Q{float(item['subtotal']):.2f}\n"

    mensaje += f"\n   💵 **Total: Q{total_carrito:.2f}**"

    return mensaje

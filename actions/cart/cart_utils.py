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
            item['subtotal'] = float(item['unit_price']) * item['quantity']
            producto_existente = True
            logger.info(f"Producto existente actualizado: {producto['name']}, nueva cantidad: {item['quantity']}")
            break

    # Si no existe, agregar nuevo item
    if not producto_existente:
        subtotal_item = precio_unitario * cantidad
        carrito.append({
            'product_id': producto['id'],
            'product_name': producto['name'],
            'product_code': producto['code'],
            'quantity': cantidad,
            'unit_price': precio_unitario,
            'subtotal': subtotal_item,
            'price_type': precio_tipo
        })
        logger.info(f"Nuevo producto agregado al carrito: {producto['name']}, cantidad: {cantidad}")

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

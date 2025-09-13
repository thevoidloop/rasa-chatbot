-- init-db.sql - Script de inicialización para PostgreSQL
-- Base de datos para Chatbot de Ventas con RASA

-- =====================================
-- EXTENSIONES Y CONFIGURACIONES
-- =====================================

-- Habilitar extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Configurar zona horaria
SET timezone = 'America/Guatemala';

-- =====================================
-- TABLAS PRINCIPALES
-- =====================================

-- Tabla de clientes
CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    gender VARCHAR(10) CHECK (gender IN ('M', 'F', 'Otro')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true
);

-- Tabla de datos de envío
CREATE TABLE shipping_data (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    department VARCHAR(50) NOT NULL,
    municipality VARCHAR(50) NOT NULL,
    address_line1 VARCHAR(200) NOT NULL,
    address_line2 VARCHAR(200),
    address_references TEXT,
    delivery_phone VARCHAR(20),
    receiver_name VARCHAR(100),
    is_primary_address BOOLEAN DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true
);

-- Tabla de productos
CREATE TABLE products (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    individual_price DECIMAL(10,2) NOT NULL CHECK (individual_price >= 0),
    wholesale_price DECIMAL(10,2) CHECK (wholesale_price >= 0),
    bundle_price DECIMAL(10,2) CHECK (bundle_price >= 0),
    wholesale_quantity INTEGER DEFAULT 6 CHECK (wholesale_quantity > 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true
);

-- Tabla de inventario
CREATE TABLE inventory (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT UNIQUE NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    available_quantity INTEGER NOT NULL DEFAULT 0 CHECK (available_quantity >= 0),
    reserved_quantity INTEGER DEFAULT 0 CHECK (reserved_quantity >= 0),
    minimum_stock INTEGER DEFAULT 5 CHECK (minimum_stock >= 0),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de características de productos
CREATE TABLE product_characteristics (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    characteristic_name VARCHAR(50) NOT NULL,
    data_type VARCHAR(50) DEFAULT 'texto' CHECK (data_type IN ('texto', 'numero', 'booleano', 'fecha')),
    characteristic_value TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de pedidos
CREATE TABLE orders (
    id BIGSERIAL PRIMARY KEY,
    order_number VARCHAR(20) UNIQUE NOT NULL,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
    shipping_data_id BIGINT REFERENCES shipping_data(id) ON DELETE SET NULL,
    subtotal DECIMAL(10,2) NOT NULL CHECK (subtotal >= 0),
    shipping_cost DECIMAL(10,2) DEFAULT 0.00 CHECK (shipping_cost >= 0),
    total DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    status VARCHAR(20) DEFAULT 'pendiente' CHECK (status IN ('pendiente', 'confirmado', 'preparando', 'enviado', 'entregado', 'cancelado')),
    notes TEXT,
    order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(50) DEFAULT 'chatbot'
);

-- Tabla de detalles de pedidos
CREATE TABLE order_details (
    id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id BIGINT NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),
    line_subtotal DECIMAL(10,2) NOT NULL CHECK (line_subtotal >= 0),
    price_type VARCHAR(20) CHECK (price_type IN ('individual', 'wholesale', 'bundle')),
    product_notes TEXT
);

-- Tabla de conversaciones de RASA
CREATE TABLE rasa_conversations (
    id BIGSERIAL PRIMARY KEY,
    sender_id VARCHAR(255) NOT NULL,
    customer_id BIGINT REFERENCES customers(id) ON DELETE SET NULL,
    events TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT true
);

-- =====================================
-- TABLAS ADICIONALES PARA RASA
-- =====================================

-- Tabla para el tracker store de RASA (requerida por RASA)
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    sender_id VARCHAR(255) NOT NULL,
    type_name VARCHAR(255) NOT NULL,
    timestamp DOUBLE PRECISION,
    intent_name VARCHAR(255),
    action_name VARCHAR(255),
    data JSONB
);

-- Tabla para logging de conversaciones
CREATE TABLE conversaciones_chatbot (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    user_message TEXT,
    intent_detected VARCHAR(100),
    entities_detected JSONB,
    confidence_score DECIMAL(3,2),
    bot_response TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =====================================
-- ÍNDICES PARA OPTIMIZACIÓN
-- =====================================

-- Índices en customers
CREATE INDEX idx_customers_phone ON customers(phone);
CREATE INDEX idx_customers_active ON customers(active);

-- Índices en shipping_data
CREATE INDEX idx_shipping_data_customer_id ON shipping_data(customer_id);
CREATE INDEX idx_shipping_data_primary ON shipping_data(is_primary_address);

-- Índices en products
CREATE INDEX idx_products_code ON products(code);
CREATE INDEX idx_products_active ON products(active);
CREATE INDEX idx_products_name ON products(name);

-- Índices en inventory
CREATE INDEX idx_inventory_product_id ON inventory(product_id);
CREATE INDEX idx_inventory_available ON inventory(available_quantity);

-- Índices en product_characteristics
CREATE INDEX idx_characteristics_product_id ON product_characteristics(product_id);
CREATE INDEX idx_characteristics_name ON product_characteristics(characteristic_name);

-- Índices en orders
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_number ON orders(order_number);

-- Índices en order_details
CREATE INDEX idx_order_details_order_id ON order_details(order_id);
CREATE INDEX idx_order_details_product_id ON order_details(product_id);

-- Índices para RASA
CREATE INDEX idx_events_sender_id ON events(sender_id);
CREATE INDEX idx_events_timestamp ON events(timestamp);
CREATE INDEX idx_rasa_conversations_sender_id ON rasa_conversations(sender_id);
CREATE INDEX idx_rasa_conversations_customer_id ON rasa_conversations(customer_id);
CREATE INDEX idx_conversaciones_session_id ON conversaciones_chatbot(session_id);
CREATE INDEX idx_conversaciones_intent ON conversaciones_chatbot(intent_detected);

-- =====================================
-- TRIGGERS PARA UPDATED_AT
-- =====================================

-- Función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para actualizar updated_at automáticamente
CREATE TRIGGER update_customers_updated_at 
    BEFORE UPDATE ON customers 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at 
    BEFORE UPDATE ON products 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_updated_at 
    BEFORE UPDATE ON inventory 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_orders_updated_at 
    BEFORE UPDATE ON orders 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rasa_conversations_updated_at 
    BEFORE UPDATE ON rasa_conversations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================
-- FUNCIÓN PARA GENERAR NÚMERO DE PEDIDO
-- =====================================

CREATE OR REPLACE FUNCTION generate_order_number()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.order_number IS NULL OR NEW.order_number = '' THEN
        NEW.order_number = 'ORD-' || TO_CHAR(CURRENT_DATE, 'YYYYMMDD') || '-' || LPAD(NEW.id::TEXT, 6, '0');
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER trigger_generate_order_number
    BEFORE INSERT ON orders
    FOR EACH ROW EXECUTE FUNCTION generate_order_number();

-- =====================================
-- VISTA PARA REPORTE DE VENTAS
-- =====================================

CREATE OR REPLACE VIEW reporte_ventas AS
SELECT 
    p.name as producto,
    p.code as codigo_producto,
    SUM(od.quantity) as cantidad_total,
    COUNT(DISTINCT o.id) as veces_pedido,
    SUM(od.line_subtotal) as revenue_total,
    AVG(od.unit_price) as precio_promedio,
    MAX(o.order_date) as ultima_venta
FROM products p
LEFT JOIN order_details od ON p.id = od.product_id
LEFT JOIN orders o ON od.order_id = o.id AND o.status NOT IN ('cancelado')
WHERE p.active = true
GROUP BY p.id, p.name, p.code;

-- =====================================
-- DATOS DE EJEMPLO PARA TESTING
-- =====================================

-- Productos de ejemplo
INSERT INTO products (code, name, description, individual_price, wholesale_price, bundle_price, wholesale_quantity) VALUES
('CAM001', 'Camisa Básica', 'Camisa de algodón básica disponible en varios colores', 25.00, 22.00, 20.00, 6),
('PANT001', 'Pantalón Casual', 'Pantalón casual cómodo para uso diario', 45.00, 40.00, 35.00, 6),
('BLUS001', 'Blusa Elegante', 'Blusa elegante para ocasiones especiales', 35.00, 30.00, 28.00, 6),
('VEST001', 'Vestido Verano', 'Vestido ligero perfecto para el verano', 55.00, 50.00, 45.00, 6),
('JEAN001', 'Jean Clásico', 'Jean de mezclilla clásico', 65.00, 60.00, 55.00, 6);

-- Inventario inicial
INSERT INTO inventory (product_id, available_quantity, minimum_stock) VALUES
(1, 50, 10),
(2, 30, 8),
(3, 25, 5),
(4, 20, 5),
(5, 40, 10);

-- Características de productos
INSERT INTO product_characteristics (product_id, characteristic_name, data_type, characteristic_value) VALUES
(1, 'Tallas', 'texto', 'S, M, L, XL'),
(1, 'Colores', 'texto', 'Blanco, Negro, Azul, Rojo'),
(1, 'Material', 'texto', '100% Algodón'),
(2, 'Tallas', 'texto', '28, 30, 32, 34, 36, 38'),
(2, 'Colores', 'texto', 'Negro, Azul, Café'),
(2, 'Material', 'texto', 'Mezcla de algodón y poliéster'),
(3, 'Tallas', 'texto', 'S, M, L, XL'),
(3, 'Colores', 'texto', 'Blanco, Rosa, Azul claro'),
(4, 'Tallas', 'texto', 'S, M, L'),
(4, 'Colores', 'texto', 'Floreado, Liso'),
(5, 'Tallas', 'texto', '28, 30, 32, 34, 36'),
(5, 'Colores', 'texto', 'Azul clásico, Negro');

-- Cliente de ejemplo
INSERT INTO customers (name, phone, gender) VALUES
('Juan Pérez', '50123456789', 'M');

-- Dirección de ejemplo
INSERT INTO shipping_data (customer_id, department, municipality, address_line1, receiver_name, is_primary_address) VALUES
(1, 'Guatemala', 'Mixco', 'Zona 1, Calle Principal 123', 'Juan Pérez', true);

-- =====================================
-- PERMISOS Y CONFIGURACIONES FINALES
-- =====================================

-- Dar permisos al usuario de RASA
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO rasa_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO rasa_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO rasa_user;

-- Configurar búsqueda de esquema por defecto
ALTER USER rasa_user SET search_path = public;

-- =====================================
-- INFORMACIÓN FINAL
-- =====================================

-- Insertar información de inicialización
DO $$
BEGIN
    RAISE NOTICE '======================================';
    RAISE NOTICE 'Base de datos inicializada correctamente';
    RAISE NOTICE 'Tablas creadas: %', (SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public');
    RAISE NOTICE 'Productos de ejemplo insertados: %', (SELECT COUNT(*) FROM products);
    RAISE NOTICE '======================================';
END $$;
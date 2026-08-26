-- 1. Crear el esquema dedicado como pide el requerimiento
CREATE SCHEMA IF NOT EXISTS content;

-- Habilitar la extensión para generar UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Diseño y Creación de Tablas

-- Tabla de Usuarios (Tabla base / Padre)
CREATE TABLE content.usuario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    telefono VARCHAR(20),
    CONSTRAINT usuario_unique_email UNIQUE (email)
);

-- Tabla de Clientes (Hija de Usuario)
CREATE TABLE content.cliente (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL UNIQUE,
    FOREIGN KEY (usuario_id) REFERENCES content.usuario(id) ON DELETE CASCADE
);

-- Tabla de Roles de Empleado
CREATE TABLE content.rol_empleado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(50) NOT NULL UNIQUE, -- Ej: 'Mesero', 'Chef', 'Cajero'
    descripcion TEXT
);

-- Tabla de Empleados (Hija de Usuario)
CREATE TABLE content.empleado (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    usuario_id UUID NOT NULL UNIQUE,
    rol_id UUID NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES content.usuario(id) ON DELETE CASCADE,
    FOREIGN KEY (rol_id) REFERENCES content.rol_empleado(id)
);

-- Tabla de Mesas
CREATE TABLE content.mesa (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    numero INT NOT NULL UNIQUE,
    capacidad INT NOT NULL
);

-- Tabla de Categorías de Productos
CREATE TABLE content.categoria_producto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nombre VARCHAR(100) NOT NULL, -- Ej: 'Entradas', 'Platos Fuertes', 'Bebidas'
    descripcion TEXT
);

-- Tabla de Productos
CREATE TABLE content.producto (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    categoria_id UUID NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    ingredientes TEXT,
    precio DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (categoria_id) REFERENCES content.categoria_producto(id) ON DELETE CASCADE
);

-- Tabla de Recibo (Ventas/Pedidos)
CREATE TABLE content.recibo (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id UUID NOT NULL,
    mesero_id UUID, -- Puede ser NULL si es por app/delivery
    mesa_id UUID, -- Es NULLABLE. Si es NULL, es delivery/para llevar
    tipo_pedido VARCHAR(50) DEFAULT 'Local', -- 'Local', 'Delivery', 'Para llevar'
    total DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    metodo_pago VARCHAR(50), 
    creation_date DATE NOT NULL DEFAULT CURRENT_DATE, -- Columna clave para EXPLAIN ANALYZE
    FOREIGN KEY (cliente_id) REFERENCES content.cliente(id),
    FOREIGN KEY (mesero_id) REFERENCES content.empleado(id),
    FOREIGN KEY (mesa_id) REFERENCES content.mesa(id)
);

-- Tabla intermedia: Detalle del Recibo
CREATE TABLE content.recibo_detalle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    recibo_id UUID NOT NULL,
    producto_id UUID NOT NULL,
    cantidad INT NOT NULL DEFAULT 1,
    precio_unitario DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (recibo_id) REFERENCES content.recibo(id) ON DELETE CASCADE,
    FOREIGN KEY (producto_id) REFERENCES content.producto(id)
);

-- 3. Definir Índices
CREATE INDEX idx_usuario_email ON content.usuario(email);

-- Índice clave del ejercicio para probar EXPLAIN ANALYZE (Paso 2 del PDF)
-- CREATE INDEX database_name_creation_date_idx ON content.recibo(creation_date);
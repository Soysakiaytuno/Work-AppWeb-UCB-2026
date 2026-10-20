-- 1. Insertar Usuarios con Nombres Reales
INSERT INTO content.usuario (nombre, email, telefono) VALUES 
('Ana Martínez', 'ana.martinez@email.com', '555-0101'),
('Carlos López', 'carlos.lopez@email.com', '555-0102'),
('María García', 'maria.garcia@email.com', '555-0103'),
('Juan Pérez', 'juan.perez@email.com', '555-0104'),
('Lucía Fernández', 'lucia.f@email.com', '555-0105'),
('Jorge Ramírez', 'jorge.ramirez@email.com', '555-0106'),
('Elena Gómez', 'elena.gomez@email.com', '555-0107'),
('Diego Torres', 'diego.torres@email.com', '555-0108'),
('Sofía Ruiz', 'sofia.ruiz@email.com', '555-0109'),
('Miguel Sánchez', 'miguel.s@email.com', '555-0110'),
-- Empleados
('Roberto Chef', 'roberto.cocina@restaurante.com', '555-0201'),
('Carmen Mesera', 'carmen.salon@restaurante.com', '555-0202'),
('Luis Mesero', 'luis.salon@restaurante.com', '555-0203'),
('Diana Cajera', 'diana.caja@restaurante.com', '555-0204');

-- 2. Asignar los primeros 10 como Clientes
INSERT INTO content.cliente (usuario_id)
SELECT id FROM content.usuario LIMIT 10;

-- 3. Insertar Roles de Empleado reales
INSERT INTO content.rol_empleado (nombre, descripcion) VALUES 
('Chef Ejecutivo', 'Encargado principal de la cocina'),
('Mesero', 'Atención directa a las mesas'),
('Cajero', 'Responsable de cobros y facturación'),
('Recepcionista', 'Recibe y asigna mesas a los clientes');

-- 4. Asignar los roles a los empleados
INSERT INTO content.empleado (usuario_id, rol_id)
SELECT 
    (SELECT id FROM content.usuario WHERE email = 'roberto.cocina@restaurante.com'), 
    (SELECT id FROM content.rol_empleado WHERE nombre = 'Chef Ejecutivo')
UNION ALL
SELECT 
    (SELECT id FROM content.usuario WHERE email = 'carmen.salon@restaurante.com'), 
    (SELECT id FROM content.rol_empleado WHERE nombre = 'Mesero')
UNION ALL
SELECT 
    (SELECT id FROM content.usuario WHERE email = 'luis.salon@restaurante.com'), 
    (SELECT id FROM content.rol_empleado WHERE nombre = 'Mesero')
UNION ALL
SELECT 
    (SELECT id FROM content.usuario WHERE email = 'diana.caja@restaurante.com'), 
    (SELECT id FROM content.rol_empleado WHERE nombre = 'Cajero');

-- 5. Insertar Mesas (15 mesas en el local)
INSERT INTO content.mesa (numero, capacidad)
SELECT i, (random() * 4 + 2)::int 
FROM generate_series(1, 15) AS i;

-- 6. Insertar Categorías Reales
INSERT INTO content.categoria_producto (nombre, descripcion) VALUES 
('Entradas', 'Aperitivos para comenzar'), 
('Platos Fuertes', 'Platillos principales'), 
('Postres', 'Dulces y pasteles'), 
('Bebidas', 'Refrescos, jugos y licores');

-- 7. Insertar Productos Reales (Un menú realista de 10-15 items)
INSERT INTO content.producto (categoria_id, nombre, descripcion, ingredientes, precio) VALUES 
((SELECT id FROM content.categoria_producto WHERE nombre = 'Entradas'), 'Empanadas de Carne', 'Dos empanadas horneadas', 'Carne, cebolla, masa', 5.50),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Entradas'), 'Tequeños', 'Palitos de queso frito', 'Queso blanco, masa', 4.00),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Entradas'), 'Ceviche Clásico', 'Pescado fresco marinado en limón', 'Pescado, limón, cebolla morada, cilantro', 8.50),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Platos Fuertes'), 'Lomo Saltado', 'Clásico peruano', 'Carne de res, cebolla, tomate, papas', 15.00),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Platos Fuertes'), 'Hamburguesa Clásica', 'Con queso y papas', 'Carne, queso cheddar, pan, lechuga', 12.00),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Platos Fuertes'), 'Pizza Margarita', 'Pizza artesanal de 8 porciones', 'Masa madre, salsa de tomate, mozzarella', 14.50),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Platos Fuertes'), 'Pasta Alfredo con Pollo', 'Pasta cremosa', 'Fettuccine, crema, parmesano, pollo', 13.00),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Postres'), 'Tiramisú', 'Postre italiano', 'Café, mascarpone, cacao', 6.00),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Postres'), 'Cheesecake', 'Con frutos rojos', 'Queso crema, galleta, fresas', 6.50),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Bebidas'), 'Limonada Frappé', 'Refrescante y natural', 'Limón, hielo, azúcar', 3.00),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Bebidas'), 'Cerveza Artesanal', 'IPA local', 'Agua, malta, lúpulo', 4.50),
((SELECT id FROM content.categoria_producto WHERE nombre = 'Bebidas'), 'Coca-Cola', 'Lata 355ml', 'Bebida carbonatada', 2.00);

-- 8. Generar 10,000 recibos (Ventas Históricas) combinando los datos reales
-- NOTA: Mantener un volumen alto es obligatorio para que EXPLAIN ANALYZE evalúe el índice.
INSERT INTO content.recibo (cliente_id, mesero_id, mesa_id, tipo_pedido, total, metodo_pago, creation_date)
SELECT 
    (SELECT id FROM content.cliente ORDER BY random() LIMIT 1),
    (SELECT id FROM content.empleado WHERE rol_id = (SELECT id FROM content.rol_empleado WHERE nombre = 'Mesero' LIMIT 1) ORDER BY random() LIMIT 1),
    -- Si es Delivery (20% de probabilidad), la mesa es NULL
    CASE WHEN random() > 0.8 THEN NULL ELSE (SELECT id FROM content.mesa ORDER BY random() LIMIT 1) END,
    CASE WHEN random() > 0.8 THEN 'Delivery' ELSE 'Local' END,
    (random() * 80 + 15)::numeric(10,2),
    CASE WHEN random() > 0.4 THEN 'Tarjeta' ELSE 'Efectivo' END,
    -- Forzamos que existan unas 100 ventas en la fecha exacta de tu examen ('2020-01-01')
    CASE WHEN i <= 100 THEN '2020-01-01'::date ELSE current_date - (random() * 1800)::int END
FROM generate_series(1, 10000) AS i;

-- 9. (Opcional pero realista) Insertar detalles de recibo para que los recibos tengan productos
INSERT INTO content.recibo_detalle (recibo_id, producto_id, cantidad, precio_unitario)
SELECT 
    id,
    (SELECT id FROM content.producto ORDER BY random() LIMIT 1),
    (random() * 3 + 1)::int,
    10.00 -- Precio estático para simplificar la generación masiva
FROM content.recibo;
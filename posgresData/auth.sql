-- 1. Crear el nuevo esquema para autenticación
CREATE SCHEMA IF NOT EXISTS auth;

-- 2. Crear la tabla de usuarios en dicho esquema
CREATE TABLE IF NOT EXISTS auth.usuario (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL
);

-- (Opcional) Usuario de prueba inicial
INSERT INTO auth.usuario (username, password)
VALUES ('admin', 'admin123')
ON CONFLICT (username) DO NOTHING;

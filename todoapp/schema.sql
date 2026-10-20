-- DDL para la tabla de tareas (todos)
CREATE TABLE IF NOT EXISTS todos (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- (Opcional) Datos de prueba iniciales para ver algo al iniciar
INSERT INTO todos (title, description, completed) VALUES
('Aprender Docker y Flask', 'Seguir la guía paso a paso del proyecto', true),
('Probar la conexión con Postgres', 'Comprobar que los datos persisten en el contenedor', false);

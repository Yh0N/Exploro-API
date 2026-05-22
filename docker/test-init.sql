-- Script de inicialización para el contenedor de test
-- Se ejecuta automáticamente al crear el contenedor por primera vez.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Configuración de timezone Colombia
SET timezone = 'America/Bogota';

-- Script de inicialización de la base de datos
-- Se ejecuta automáticamente al crear el contenedor PostgreSQL por primera vez
-- Habilita la extensión PostGIS necesaria para operaciones geoespaciales

CREATE EXTENSION IF NOT EXISTS postgis;

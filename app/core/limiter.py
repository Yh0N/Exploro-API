"""
Instancia global del limitador de solicitudes (rate limiter).
Se define en un módulo separado para evitar importaciones circulares.
Los routers lo importan desde aquí, y main.py también lo registra en app.state.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter que usa la IP remota del cliente como clave de identificación
limiter = Limiter(key_func=get_remote_address)

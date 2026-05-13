import httpx
from typing import Optional, Tuple

async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convierte una dirección textual en coordenadas (latitud, longitud)
    usando el servicio Nominatim de OpenStreetMap.
    """
    # Limpieza básica sin quitar el # que es importante en Colombia
    address_clean = address.replace('_', '-').strip()
    
    # Construir query asegurando ciudad y país si no están
    query = address_clean
    if "pasto" not in address_clean.lower():
        query += ", Pasto"
    if "colombia" not in query.lower():
        query += ", Nariño, Colombia"
    
    print(f"[Geocoding] Buscando: {query}")
    
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 1
    }

    headers = {
        "User-Agent": "ExploroApp/1.0 (contacto@exploro.com)"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = float(data[0]["lat"])
                    lon = float(data[0]["lon"])
                    print(f"[Geocoding] Éxito: {lat}, {lon}")
                    return lat, lon
                else:
                    print(f"[Geocoding] No se encontraron resultados para: {query}")
            else:
                print(f"[Geocoding] Error de servicio: {response.status_code}")
    except Exception as e:
        print(f"[Geocoding] Error crítico: {e}")
        
    return None

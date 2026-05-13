import requests

url = "http://localhost:8000/places/nearby"
params = {
    "latitud": 1.2191180110331004,
    "longitud": -77.28148379942475,
    "radio_km": 1.4
}

response = requests.get(url, params=params)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

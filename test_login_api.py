
import requests
import json

def test_login():
    url = "http://localhost:8000/auth/login"
    payload = {
        "correo": "admin@gmail.com",
        "contraseña": "secret"
    }
    try:
        response = requests.post(url, json=payload, timeout=10.0)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error type: {type(e)}")
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()

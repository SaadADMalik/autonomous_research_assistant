import requests
import os

# Test if the dashboard can connect to the API
api_url = os.getenv('BACKEND_API_URL', 'http://localhost:8000')
print(f"Testing connection to: {api_url}")

try:
    response = requests.get(f'{api_url}/health', timeout=5)
    print(f"✅ Success! Status: {response.json()['status']}")
    print(f"   Status Code: {response.status_code}")
except requests.exceptions.ConnectionError as e:
    print(f"❌ Connection Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")

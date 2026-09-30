import requests

URL = "http://127.0.0.1:8000/api/device/status/"

data = {
    "device_id": "attendance-01"
}

response = requests.post(
    URL,
    json=data
)

print(response.status_code)
print(response.json())
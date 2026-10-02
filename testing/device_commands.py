import requests

URL = "http://127.0.0.1:8000/api/device/command/"

response = requests.get(
    URL,
    params={
        "device_id": "attendance-01"
    },
)

print(response.status_code)
print(response.json())
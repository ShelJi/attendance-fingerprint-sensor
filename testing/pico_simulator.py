import requests


URL = "http://127.0.0.1:8000/api/attendance/scan/"


def send_fingerprint(fingerprint_id):
    data = {
        "fingerprint_id": fingerprint_id,
        "device_id": "attendance-01",
    }

    response = requests.post(URL, json=data)

    print("Status:", response.status_code)
    print("Response:", response.text)


if __name__ == "__main__":
    fingerprint_id = input("Enter fingerprint ID: ")

    send_fingerprint(fingerprint_id)

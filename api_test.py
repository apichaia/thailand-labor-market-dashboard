
import os
import requests
import pandas as pd

print("กำลังเชื่อมต่อ Data API...")

API_URL = "https://opend.data.go.th/get-ckan/datastore_search"

API_KEY = os.getenv("THGOV_OPENDATA_TOKEN")

if not API_KEY:
    raise SystemExit(
        "ไม่พบ API Key กรุณาตั้งค่า "
        "THGOV_OPENDATA_TOKEN ใน PowerShell ก่อน"
    )

params = {
    "resource_id": "97312915-e522-4505-8814-2ed52b80503c",
    "limit": 5
}

# จุดสำคัญ: ส่ง API Key ใน HTTP Header
headers = {
    "api-key": API_KEY
}

try:
    response = requests.get(
        API_URL,
        params=params,
        headers=headers,
        timeout=30
    )

    print("HTTP Status:", response.status_code)
    response.raise_for_status()

    data = response.json()

    if not data.get("success", False):
        print("API แจ้งข้อผิดพลาด:", data)
    else:
        result = data["result"]
        df = pd.DataFrame(result.get("records", []))

        print("จำนวนรายการทั้งหมด:", result.get("total"))
        print("\nชื่อคอลัมน์:")
        print(df.columns.tolist())

        print("\nตัวอย่างข้อมูล:")
        print(df.head().to_string(index=False))

except requests.HTTPError as error:
    print("เรียก API ไม่สำเร็จ:", error)
    print("รายละเอียด:", response.text[:500])

except requests.RequestException as error:
    print("เชื่อมต่อไม่ได้:", error)

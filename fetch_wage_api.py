
import os
from pathlib import Path

import pandas as pd
import requests

API_URL = "https://opend.data.go.th/get-ckan/datastore_search"
RESOURCE_ID = "97312915-e522-4505-8814-2ed52b80503c"

API_KEY = (os.getenv("THGOV_OPENDATA_TOKEN") or "").strip()

if not API_KEY:
    raise SystemExit(
        "ไม่พบ API Key กรุณาตั้งค่าใน PowerShell ก่อน"
    )

headers = {"api-key": API_KEY}


def fetch_all_records():
    records = []
    offset = 0
    limit = 1000
    total = None

    while True:
        params = {
            "resource_id": RESOURCE_ID,
            "limit": limit,
            "offset": offset
        }

        response = requests.get(
            API_URL,
            params=params,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()

        payload = response.json()

        if not payload.get("success", False):
            raise RuntimeError(f"API error: {payload}")

        result = payload["result"]
        batch = result.get("records", [])
        total = result.get("total", 0)

        if not batch:
            break

        records.extend(batch)
        offset += len(batch)

        print(f"ดาวน์โหลดแล้ว {len(records):,} / {total:,} รายการ")

        if len(records) >= total:
            break

    df = pd.DataFrame(records)

    # ลบ BOM และช่องว่างจากชื่อคอลัมน์
    df.columns = (
        df.columns
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    return df


if __name__ == "__main__":
    df = fetch_all_records()

    output = Path("data/raw/average_wage_api.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(output, index=False, encoding="utf-8-sig")

    print("\nดาวน์โหลดสำเร็จ!")
    print("จำนวนแถว:", len(df))
    print("คอลัมน์:", df.columns.tolist())
    print("บันทึกไฟล์ที่:", output.resolve())

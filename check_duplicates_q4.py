
import pandas as pd

path = "data/raw/average_wage_api.csv"

df = pd.read_csv(
    path,
    encoding="utf-8-sig",
    low_memory=False
)

# ทำความสะอาดชื่อคอลัมน์
df.columns = (
    df.columns.astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
)

# ทำความสะอาดข้อความ
for col in df.select_dtypes(include=["object", "string"]).columns:
    df[col] = df[col].astype("string").str.strip()

# เลือกข้อมูลไตรมาส 4 ปี 2567
q4 = df[
    df["quarter"].str.contains("4/2567", na=False, regex=False)
].copy()

# ตรวจแถวภาพรวมที่มีปัญหา
overall = q4[
    q4["region"].eq("Total")
    & q4["area"].eq("รวม")
    & q4["sex"].eq("รวม")
    & q4["age_group"].eq("Total")
]

print("=" * 60)
print("1. แถวภาพรวมที่พบ")
print("=" * 60)

print(
    overall[
        ["_id", "year", "quarter", "region", "area",
         "sex", "age_group", "value", "unit", "source"]
    ].to_string(index=False)
)

# ตรวจคีย์ซ้ำทั่วทั้งข้อมูลไตรมาส 4
key_cols = [
    "year", "quarter", "region",
    "area", "sex", "age_group"
]

duplicates = q4[
    q4.duplicated(subset=key_cols, keep=False)
].sort_values(key_cols)

print("\n" + "=" * 60)
print("2. รายการทั้งหมดที่มีคีย์ซ้ำ")
print("=" * 60)

if duplicates.empty:
    print("ไม่พบคีย์ซ้ำ")
else:
    print(
        duplicates[
            ["_id", "year", "quarter", "region", "area",
             "sex", "age_group", "value", "unit", "source"]
        ].to_string(index=False)
    )

# นับจำนวนซ้ำของแต่ละชุดหมวดหมู่
counts = (
    q4.groupby(key_cols, dropna=False)
    .size()
    .reset_index(name="row_count")
)

print("\n" + "=" * 60)
print("3. สรุปหมวดหมู่ที่มีมากกว่า 1 แถว")
print("=" * 60)

print(
    counts[counts["row_count"] > 1]
    .to_string(index=False)
)


import pandas as pd

path = "data/raw/average_wage_api.csv"

df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

# ทำความสะอาดชื่อคอลัมน์และช่องว่าง
df.columns = (
    df.columns.astype(str)
    .str.replace("\ufeff", "", regex=False)
    .str.strip()
)

for col in df.select_dtypes(include=["object", "string"]).columns:
    df[col] = df[col].astype("string").str.strip()

# เลือกไตรมาส 4 ปี 2567
q4 = df[
    df["quarter"].str.contains("4/2567", regex=False, na=False)
].copy()

print("=== หมวดหมู่เพศ ===")
print(q4["sex"].value_counts(dropna=False).to_string())

print("\n=== หมวดหมู่กลุ่มอายุ ===")
print(q4["age_group"].value_counts(dropna=False).to_string())

print("\n=== ตัวอย่างข้อมูลที่ region = Total ===")
cols = [
    "year", "quarter", "region", "area",
    "sex", "age_group", "value", "unit"
]

print(
    q4.loc[q4["region"].eq("Total"), cols]
    .head(15)
    .to_string(index=False)
)

print("\n=== ตรวจสอบแถวภาพรวมที่ใช้คำว่า รวม หรือ Total ===")

total_labels = {"รวม", "Total"}

overall = q4[
    q4["region"].isin({"Total", "ทั่วประเทศ", "ทั่วราชอาณาจักร"})
    & q4["area"].isin(total_labels)
    & q4["sex"].isin(total_labels)
    & q4["age_group"].isin(total_labels)
]

print(overall[cols].to_string(index=False))
print("\nจำนวนแถวภาพรวมที่พบ:", len(overall))

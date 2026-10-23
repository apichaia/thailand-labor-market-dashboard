
from pathlib import Path
import re
import pandas as pd

RAW_DIR = Path("data/raw")

FILES = {
    "employment": RAW_DIR / "employment_rate_api.csv",
    "wage": RAW_DIR / "average_wage_api.csv",
}

NATIONAL_REGIONS = {
    "ทั่วประเทศ",
    "ทั่วราชอาณาจักร",
}


def load_data(path):
    if not path.exists():
        print(f"\nไม่พบไฟล์: {path}")
        return None

    df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

    # ทำความสะอาดชื่อคอลัมน์และช่องว่าง
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()

    return df


def make_quarter_key(value):
    match = re.search(r"([1-4])", str(value))
    return f"Q{match.group(1)}" if match else str(value)


def inspect_dataset(name, df):
    print("\n" + "=" * 65)
    print(f"ชุดข้อมูล: {name}")
    print("จำนวนแถว:", len(df))
    print("คอลัมน์:", df.columns.tolist())

    required = {"year", "quarter", "region", "area", "value"}

    missing = required - set(df.columns)
    if missing:
        print("ขาดคอลัมน์ที่ต้องตรวจสอบ:", missing)
        return None

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["quarter_key"] = df["quarter"].apply(make_quarter_key)

    print("\nปีที่มีทั้งหมด:")
    print(sorted(df["year"].dropna().astype(int).unique()))

    print("\nรูปแบบไตรมาส:")
    print(df["quarter"].value_counts().to_string())

    print("\nรูปแบบภูมิภาค:")
    print(df["region"].value_counts().head(20).to_string())

    # เลือกข้อมูลระดับประเทศและพื้นที่รวมก่อน
    mask = (
        df["region"].isin(NATIONAL_REGIONS)
        & df["area"].eq("รวม")
    )

    if name == "employment":
        if "level_of_edu" not in df.columns:
            print("ไม่พบคอลัมน์ level_of_edu")
            return None

        mask &= df["level_of_edu"].eq("รวม")

    elif name == "wage":
        for col in ["sex", "age_group"]:
            if col not in df.columns:
                print(f"ไม่พบคอลัมน์ {col}")
                return None
            mask &= df[col].eq("รวม")

    selected = df.loc[mask].copy()

    print("\nจำนวนแถวหลังเลือกข้อมูลภาพรวม:", len(selected))

    if selected.empty:
        print("ยังไม่พบแถวภาพรวม ต้องตรวจค่าหมวดหมู่เพิ่มเติม")
        return selected

    print("\nตัวอย่างแถวที่เลือก:")
    print(selected.head(10).to_string(index=False))

    print("\nจำนวนแถวต่อปีและไตรมาส:")
    counts = (
        selected.groupby(["year", "quarter_key"])
        .size()
        .rename("rows")
        .reset_index()
    )
    print(counts.to_string(index=False))

    # ตรวจว่าปี/ไตรมาสเดียวกันมีหลายแถวหรือไม่
    duplicated = selected.duplicated(
        subset=["year", "quarter_key"],
        keep=False
    )

    if duplicated.any():
        print("\nคำเตือน: พบหลายแถวในปี/ไตรมาสเดียวกัน")
        print(
            selected.loc[duplicated]
            .sort_values(["year", "quarter_key", "region"])
            .to_string(index=False)
        )
    else:
        print("\nไม่พบข้อมูลซ้ำในระดับปี/ไตรมาส")

    return selected


employment = load_data(FILES["employment"])
wage = load_data(FILES["wage"])

if employment is not None and wage is not None:
    e = inspect_dataset("employment", employment)
    w = inspect_dataset("wage", wage)

    if e is not None and w is not None and not e.empty and not w.empty:
        e_periods = set(zip(
            e["year"].astype(int),
            e["quarter_key"]
        ))
        w_periods = set(zip(
            w["year"].astype(int),
            w["quarter_key"]
        ))

        common_periods = sorted(e_periods & w_periods)

        print("\n" + "=" * 65)
        print("ปี/ไตรมาสที่ทั้งสองชุดมีร่วมกัน:", len(common_periods))
        print(common_periods)
else:
    print(
        "\nกรุณาตรวจสอบว่าไฟล์ API ทั้งสองอยู่ใน data/raw "
        "และชื่อไฟล์ถูกต้อง"
    )

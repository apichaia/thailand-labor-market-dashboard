import re
import sys
from pathlib import Path
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "data" / "raw"
OUT_DIR = BASE_DIR / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def clean_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()
    return df


def clean_quarter(val):
    match = re.search(r"([1-4])", str(val))
    return f"Q{match.group(1)}" if match else pd.NA


def clean_region(val):
    s = str(val).strip()
    if any(k in s for k in ["ทั่วราชอาณาจักร", "ทั่วประเทศ", "Total"]):
        return "ทั่วประเทศ"
    if "กรุงเทพ" in s:
        return "กรุงเทพมหานคร"
    if any(k in s for k in ["ตะวันออกเฉียงเหนือ", "อีสาน"]):
        return "ภาคตะวันออกเฉียงเหนือ"
    if any(k in s for k in ["ภาคกลาง", "กลาง", "ตะวันออก"]):
        return "ภาคกลาง"
    if "เหนือ" in s and "ตะวันออก" not in s:
        return "ภาคเหนือ"
    if "ใต้" in s:
        return "ภาคใต้"
    return s


def clean_area(val):
    s = str(val).strip()
    if "นอกเขต" in s:
        return "นอกเขตเทศบาล"
    if "ในเขต" in s or "เขตเทศบาล" in s:
        return "ในเขตเทศบาล"
    return "รวม"


def clean_sex(val):
    s = str(val).strip()
    if "ชาย" in s and "หญิง" not in s:
        return "ชาย"
    if "หญิง" in s:
        return "หญิง"
    return "รวม"


def clean_age(val):
    s = str(val).strip()
    if "15-19" in s:
        return "15-19 ปี"
    if "20-24" in s:
        return "20-24 ปี"
    if "25-29" in s:
        return "25-29 ปี"
    if "30-34" in s:
        return "30-34 ปี"
    if "35-39" in s:
        return "35-39 ปี"
    if "40-49" in s:
        return "40-49 ปี"
    if "50-59" in s:
        return "50-59 ปี"
    if "60" in s:
        return "60 ปีขึ้นไป"
    return "รวม"


def clean_edu(val):
    s = re.sub(r"^\d+\.\s*", "", str(val)).strip()
    if s in ["สายวิชาการ", "มัธยมศึกษาตอนปลาย สายวิชาการ"]:
        return "มัธยมศึกษาตอนปลาย สายวิชาการศึกษา"
    if any(k in s for k in ["อื่นๆ", "อื่น ๆ", "ไม่ทราบ"]):
        return "อื่นๆ / ไม่ทราบ"
    if s in ["Total", ""]:
        return "รวม"
    return s


def run_pipeline():
    print("=" * 60)
    print("เริ่มการเตรียมข้อมูล Thailand Labor Market Dashboard")
    print("=" * 60)

    # 1. โหลดข้อมูลอัตราการมีงานทำและค่าจ้าง
    emp_edu_raw = clean_cols(pd.read_csv(RAW_DIR / "employment_rate_api.csv", encoding="utf-8-sig", low_memory=False))
    wage_age_raw = clean_cols(pd.read_csv(RAW_DIR / "average_wage_api.csv", encoding="utf-8-sig", low_memory=False))
    
    emp_age_file = RAW_DIR / "employment_by_age.csv"
    wage_edu_file = RAW_DIR / "wage_by_education.csv"
    wage_ind_file = RAW_DIR / "wage_by_industry.csv"

    # โหลดไฟล์เสริม
    emp_age_raw = clean_cols(pd.read_csv(emp_age_file, encoding="utf-8-sig", low_memory=False)) if emp_age_file.exists() else None
    wage_edu_raw = clean_cols(pd.read_csv(wage_edu_file, encoding="utf-8-sig", low_memory=False)) if wage_edu_file.exists() else None
    wage_ind_raw = clean_cols(pd.read_csv(wage_ind_file, encoding="utf-8-sig", low_memory=False)) if wage_ind_file.exists() else None

    # แปลงคอลัมน์มาตรฐาน
    for df in [emp_edu_raw, wage_age_raw, emp_age_raw, wage_edu_raw]:
        if df is not None:
            df["year"] = pd.to_numeric(df["year"], errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df["quarter_key"] = df["quarter"].apply(clean_quarter)
            df["region_clean"] = df["region"].apply(clean_region)
            df["area_clean"] = df["area"].apply(clean_area)
            if "sex" in df.columns:
                df["sex_clean"] = df["sex"].apply(clean_sex)
            if "age_group" in df.columns:
                df["age_clean"] = df["age_group"].apply(clean_age)
            if "level_of_edu" in df.columns:
                df["edu_clean"] = df["level_of_edu"].apply(clean_edu)

    # -------------------------------------------------------------------------
    # ตารางที่ 1: ภาพรวมประเทศและภูมิภาค (labor_market_overview.csv)
    # -------------------------------------------------------------------------
    print("ประมวลผลตารางภาพรวม (Overview)...")
    
    e_ov = emp_edu_raw[emp_edu_raw["edu_clean"] == "รวม"].copy()
    e_ov = e_ov.groupby(["year", "quarter_key", "region_clean", "area_clean"], as_index=False)["value"].mean()
    e_ov.rename(columns={"value": "employment_rate"}, inplace=True)

    w_ov = wage_age_raw[(wage_age_raw["sex_clean"] == "รวม") & (wage_age_raw["age_clean"] == "รวม")].copy()
    w_ov = w_ov.groupby(["year", "quarter_key", "region_clean", "area_clean"], as_index=False)["value"].mean()
    w_ov.rename(columns={"value": "avg_wage"}, inplace=True)

    overview = pd.merge(e_ov, w_ov, on=["year", "quarter_key", "region_clean", "area_clean"], how="inner")
    overview["quarter_num"] = overview["quarter_key"].str.replace("Q", "").astype(int)
    overview["period"] = overview.apply(lambda r: f"{int(r['year'])} ไตรมาส {r['quarter_num']}", axis=1)
    overview.sort_values(["year", "quarter_num", "region_clean", "area_clean"], inplace=True)
    overview.to_csv(OUT_DIR / "labor_market_overview.csv", index=False, encoding="utf-8-sig")

    # -------------------------------------------------------------------------
    # ตารางที่ 2: จำแนกตามระดับการศึกษา (labor_market_education.csv)
    # -------------------------------------------------------------------------
    edu_merged = pd.DataFrame()
    if wage_edu_raw is not None:
        print("ประมวลผลตารางระดับการศึกษา (Education)...")
        e_ed = emp_edu_raw.groupby(["year", "quarter_key", "region_clean", "area_clean", "edu_clean"], as_index=False)["value"].mean()
        e_ed.rename(columns={"value": "employment_rate"}, inplace=True)

        w_ed = wage_edu_raw.groupby(["year", "quarter_key", "region_clean", "area_clean", "edu_clean", "sex_clean"], as_index=False)["value"].mean()
        w_ed.rename(columns={"value": "avg_wage"}, inplace=True)

        edu_merged = pd.merge(e_ed, w_ed, on=["year", "quarter_key", "region_clean", "area_clean", "edu_clean"], how="inner")
        edu_merged.to_csv(OUT_DIR / "labor_market_education.csv", index=False, encoding="utf-8-sig")

    # -------------------------------------------------------------------------
    # ตารางที่ 3: จำแนกตามกลุ่มอายุและเพศ (labor_market_age.csv)
    # -------------------------------------------------------------------------
    age_merged = pd.DataFrame()
    if emp_age_raw is not None:
        print("ประมวลผลตารางกลุ่มอายุและเพศ (Age & Sex)...")
        e_ag = emp_age_raw.groupby(["year", "quarter_key", "region_clean", "area_clean", "sex_clean", "age_clean"], as_index=False)["value"].mean()
        e_ag.rename(columns={"value": "employment_rate"}, inplace=True)

        w_ag = wage_age_raw.groupby(["year", "quarter_key", "region_clean", "area_clean", "sex_clean", "age_clean"], as_index=False)["value"].mean()
        w_ag.rename(columns={"value": "avg_wage"}, inplace=True)

        age_merged = pd.merge(e_ag, w_ag, on=["year", "quarter_key", "region_clean", "area_clean", "sex_clean", "age_clean"], how="inner")
        age_merged.to_csv(OUT_DIR / "labor_market_age.csv", index=False, encoding="utf-8-sig")

    # -------------------------------------------------------------------------
    # ตารางที่ 4: จำแนกตามอุตสาหกรรม (labor_market_industry.csv)
    # -------------------------------------------------------------------------
    ind_clean = pd.DataFrame()
    if wage_ind_raw is not None:
        print("ประมวลผลตารางประเภทอุตสาหกรรม (Industry)...")
        w_ind = wage_ind_raw.copy()
        w_ind.columns = [c.lower() for c in w_ind.columns]
        w_ind["year"] = pd.to_numeric(w_ind["year"], errors="coerce")
        w_ind["value"] = pd.to_numeric(w_ind["value"], errors="coerce")
        w_ind["quarter_key"] = w_ind["quarter"].apply(clean_quarter)
        w_ind["region_clean"] = w_ind["region"].apply(clean_region)
        w_ind["industry"] = w_ind["industry"].astype(str).str.strip()
        
        ind_clean = w_ind.dropna(subset=["year", "quarter_key", "value"]).copy()
        ind_clean.rename(columns={"value": "avg_wage"}, inplace=True)
        ind_clean.to_csv(OUT_DIR / "labor_market_industry.csv", index=False, encoding="utf-8-sig")

    # -------------------------------------------------------------------------
    # รวมทุกมิติลงใน labor_market_merged.csv เพื่อให้ app.py อ่านไฟล์เดียวได้ครบทุกมิติ
    # -------------------------------------------------------------------------
    print("ประมวลผลไฟล์รวมหลัก labor_market_merged.csv...")
    cols = ["year", "quarter_key", "region", "area", "sex", "age_group", "education", "industry", "employment_rate", "avg_wage"]

    # 1. Overview parts
    ov_part = overview.rename(columns={"region_clean": "region", "area_clean": "area"}).copy()
    ov_part["sex"] = "รวม"
    ov_part["age_group"] = "รวม"
    ov_part["education"] = "รวม"
    ov_part["industry"] = "รวม"
    parts = [ov_part[cols]]

    # 2. Education parts
    if not edu_merged.empty:
        ed_part = edu_merged.rename(columns={"region_clean": "region", "area_clean": "area", "edu_clean": "education", "sex_clean": "sex"}).copy()
        if "sex" not in ed_part.columns:
            ed_part["sex"] = "รวม"
        ed_part["age_group"] = "รวม"
        ed_part["industry"] = "รวม"
        parts.append(ed_part[cols])

    # 3. Age & Sex parts
    if not age_merged.empty:
        ag_part = age_merged.rename(columns={"region_clean": "region", "area_clean": "area", "sex_clean": "sex", "age_clean": "age_group"}).copy()
        ag_part["education"] = "รวม"
        ag_part["industry"] = "รวม"
        parts.append(ag_part[cols])

    # 4. Industry parts
    if not ind_clean.empty:
        in_part = ind_clean.rename(columns={"region_clean": "region"}).copy()
        in_part["area"] = "รวม"
        in_part["sex"] = "รวม"
        in_part["age_group"] = "รวม"
        in_part["education"] = "รวม"
        in_part["employment_rate"] = pd.NA
        parts.append(in_part[cols])

    unified = pd.concat(parts, ignore_index=True).drop_duplicates()
    unified.to_csv(OUT_DIR / "labor_market_merged.csv", index=False, encoding="utf-8-sig")
    print(f"-> บันทึก labor_market_merged.csv รวมทุกมิติ ({len(unified)} แถว) สำเร็จ!")

    print("=" * 60)
    print("เตรียมข้อมูลทั้งหมดเสร็จสมบูรณ์ พร้อมสำหรับการรัน Dashboard")
    print("=" * 60)


if __name__ == "__main__":
    run_pipeline()

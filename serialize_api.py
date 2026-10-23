import json
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "processed" / "labor_market_merged.csv"
OUT_HTML = BASE_DIR / "dashboard.html"

# Load real API dataset
df = pd.read_csv(DATA_FILE)

# 1. Clean and drop missing targets for calculations
valid_df = df.dropna(subset=['employment_rate', 'avg_wage']).copy()

# 2. National timeline series (Overall benchmark)
ov = valid_df[
    (valid_df['region'] == 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม') & 
    (valid_df['sex'] == 'รวม') & 
    (valid_df['age_group'] == 'รวม') & 
    (valid_df['education'] == 'รวม') &
    (valid_df['industry'] == 'รวม')
].sort_values(['year', 'quarter_key'])

if ov.empty:
    # If industry 'รวม' doesn't exist, aggregate
    ov = valid_df[
        (valid_df['region'] == 'ทั่วประเทศ') & 
        (valid_df['area'] == 'รวม') & 
        (valid_df['sex'] == 'รวม') & 
        (valid_df['age_group'] == 'รวม') & 
        (valid_df['education'] == 'รวม')
    ].groupby(['year', 'quarter_key'])[['employment_rate', 'avg_wage']].mean().reset_index().sort_values(['year', 'quarter_key'])

timeline = ov[['year', 'quarter_key', 'employment_rate', 'avg_wage']].round(2).to_dict(orient='records')

# National averages
nat_emp_mean = round(float(ov['employment_rate'].mean()), 2)
nat_wage_mean = round(float(ov['avg_wage'].mean()), 2)

# 3. Regional breakdown
reg = valid_df[
    (valid_df['region'] != 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม') & 
    (valid_df['sex'] == 'รวม') & 
    (valid_df['age_group'] == 'รวม') & 
    (valid_df['education'] == 'รวม')
]
reg_data = reg.groupby('region')[['employment_rate', 'avg_wage']].mean().round(2).reset_index().sort_values('employment_rate', ascending=False).to_dict(orient='records')

# 4. Education breakdown (for Butterfly Chart)
ed = valid_df[
    (valid_df['education'] != 'รวม') & 
    (valid_df['region'] == 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม')
]
ed_order = [
    "ไม่มีการศึกษา", "ต่ำกว่าประถมศึกษา", "ประถมศึกษา", "มัธยมศึกษาตอนต้น",
    "มัธยมศึกษาตอนปลาย สายสามัญ", "มัธยมศึกษาตอนปลาย สายอาชีวศึกษา", "มัธยมศึกษาตอนปลาย สายวิชาการศึกษา",
    "อุดมศึกษา สายวิชาชีพ", "อุดมศึกษา สายวิชาการ", "อุดมศึกษา สายวิชาการศึกษา"
]
ed_grouped = ed.groupby('education')[['employment_rate', 'avg_wage']].mean().round(2).reset_index()
ed_grouped['order'] = ed_grouped['education'].apply(lambda x: ed_order.index(x) if x in ed_order else 99)
ed_data = ed_grouped.sort_values('order').drop(columns=['order']).to_dict(orient='records')

# 5. Gender by Age breakdown (for Grouped Bar)
ag = valid_df[
    (valid_df['sex'].isin(['ชาย', 'หญิง'])) & 
    (valid_df['age_group'] != 'รวม') & 
    (valid_df['region'] == 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม')
]
age_order = ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"]
ag_pivot = ag.groupby(['age_group', 'sex'])['avg_wage'].mean().unstack().round(2).reindex(age_order).dropna().reset_index()
ag_data = ag_pivot.to_dict(orient='records')

# 6. Pre-computed Cohorts for Graph 8
cohorts = {}
# Cohort 1: Higher Education (Academic)
c_uni = valid_df[(valid_df['education'] == 'อุดมศึกษา สายวิชาการ') & (valid_df['region'] == 'ทั่วประเทศ')].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index()
cohorts['อุดมศึกษา สายวิชาการ'] = c_uni.to_dict(orient='records')

# Cohort 2: Primary Education
c_pri = valid_df[(valid_df['education'] == 'ประถมศึกษา') & (valid_df['region'] == 'ทั่วประเทศ')].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index()
cohorts['ประถมศึกษา'] = c_pri.to_dict(orient='records')

# Cohort 3: Lower Secondary
c_sec = valid_df[(valid_df['education'] == 'มัธยมศึกษาตอนต้น') & (valid_df['region'] == 'ทั่วประเทศ')].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index()
cohorts['มัธยมศึกษาตอนต้น'] = c_sec.to_dict(orient='records')

# Cohort 4: Vocational High School
c_voc = valid_df[(valid_df['education'] == 'มัธยมศึกษาตอนปลาย สายอาชีวศึกษา') & (valid_df['region'] == 'ทั่วประเทศ')].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index()
cohorts['มัธยมปลาย สายอาชีวศึกษา'] = c_voc.to_dict(orient='records')

# Cohort 5: Northeast (Isan)
c_ne = valid_df[valid_df['region'] == 'ภาคตะวันออกเฉียงเหนือ'].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index()
cohorts['ภาคตะวันออกเฉียงเหนือ'] = c_ne.to_dict(orient='records')

# Cohort 6: Bangkok
c_bkk = valid_df[valid_df['region'] == 'กรุงเทพมหานคร'].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index()
cohorts['กรุงเทพมหานคร'] = c_bkk.to_dict(orient='records')

# 7. Unique vocabulary for the compact dynamic filter dataset
cols_to_index = ['year', 'quarter_key', 'region', 'area', 'sex', 'age_group', 'education', 'industry']
vocab = {}
inv_vocab = {}

for c in cols_to_index:
    vals = [str(x) for x in valid_df[c].dropna().unique()]
    # Put 'รวม' or 'ทั่วประเทศ' or 'ALL' at position 0 if present
    if 'ทั่วประเทศ' in vals:
        vals.remove('ทั่วประเทศ')
        vals.insert(0, 'ทั่วประเทศ')
    elif 'รวม' in vals:
        vals.remove('รวม')
        vals.insert(0, 'รวม')
    vocab[c] = {v: i for i, v in enumerate(vals)}
    inv_vocab[c] = vals

# Build dictionary-encoded rows
encoded_rows = []
for r in valid_df[['year', 'quarter_key', 'region', 'area', 'sex', 'age_group', 'education', 'industry', 'employment_rate', 'avg_wage']].itertuples(index=False):
    encoded_rows.append([
        vocab['year'][str(r[0])],
        vocab['quarter_key'][str(r[1])],
        vocab['region'][str(r[2])],
        vocab['area'][str(r[3])],
        vocab['sex'][str(r[4])],
        vocab['age_group'][str(r[5])],
        vocab['education'][str(r[6])],
        vocab['industry'][str(r[7])],
        round(float(r[8]), 2),
        round(float(r[9]), 1)
    ])

# 8. Industry list sorted by average wage
ind_agg = valid_df[valid_df['industry'] != 'รวม'].groupby('industry')['avg_wage'].mean().round(2).reset_index().sort_values('avg_wage', ascending=False)
industries_data = ind_agg.to_dict(orient='records')

api_json_str = json.dumps({
    "timeline": timeline,
    "national_benchmark": {"employment_rate": nat_emp_mean, "avg_wage": nat_wage_mean},
    "regions": reg_data,
    "education": ed_data,
    "age_gender": ag_data,
    "cohorts": cohorts,
    "industries": industries_data,
    "vocab": inv_vocab,
    "rows": encoded_rows
}, ensure_ascii=False)

print(f"Serialized API bundle: {len(timeline)} quarters, {len(reg_data)} regions, {len(encoded_rows)} data points.")

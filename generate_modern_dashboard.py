import json
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "processed" / "labor_market_merged.csv"
OUT_HTML = BASE_DIR / "dashboard.html"

# Load real API dataset
df = pd.read_csv(DATA_FILE)
valid_df = df.dropna(subset=['employment_rate', 'avg_wage']).copy()

# 1. National timeline series (Overall benchmark)
ov = valid_df[
    (valid_df['region'] == 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม') & 
    (valid_df['sex'] == 'รวม') & 
    (valid_df['age_group'] == 'รวม') & 
    (valid_df['education'] == 'รวม')
].groupby(['year', 'quarter_key'])[['employment_rate', 'avg_wage']].mean().reset_index().sort_values(['year', 'quarter_key'])

timeline = ov[['year', 'quarter_key', 'employment_rate', 'avg_wage']].round(2).to_dict(orient='records')
nat_emp_mean = round(float(ov['employment_rate'].mean()), 2)
nat_wage_mean = round(float(ov['avg_wage'].mean()), 2)

# 2. Regional breakdown
reg = valid_df[
    (valid_df['region'] != 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม') & 
    (valid_df['sex'] == 'รวม') & 
    (valid_df['age_group'] == 'รวม') & 
    (valid_df['education'] == 'รวม')
]
reg_data = reg.groupby('region')[['employment_rate', 'avg_wage']].mean().round(2).reset_index().sort_values('employment_rate', ascending=False).to_dict(orient='records')

# 3. Education breakdown (for Butterfly Chart)
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

# 4. Gender by Age breakdown (for Grouped Bar)
ag = valid_df[
    (valid_df['sex'].isin(['ชาย', 'หญิง'])) & 
    (valid_df['age_group'] != 'รวม') & 
    (valid_df['region'] == 'ทั่วประเทศ') & 
    (valid_df['area'] == 'รวม')
]
age_order = ["15-19 ปี", "20-24 ปี", "25-29 ปี", "30-34 ปี", "35-39 ปี", "40-49 ปี", "50-59 ปี", "60 ปีขึ้นไป"]
ag_pivot = ag.groupby(['age_group', 'sex'])['avg_wage'].mean().unstack().round(2).reindex(age_order).dropna().reset_index()
ag_data = ag_pivot.to_dict(orient='records')

# 5. Cohort trends (for Graph 8)
cohorts = {}
cohort_defs = {
    'อุดมศึกษา สายวิชาการ': (valid_df['education'] == 'อุดมศึกษา สายวิชาการ') & (valid_df['region'] == 'ทั่วประเทศ'),
    'ประถมศึกษา (เสี่ยง In-work Poverty)': (valid_df['education'] == 'ประถมศึกษา') & (valid_df['region'] == 'ทั่วประเทศ'),
    'มัธยมศึกษาตอนต้น': (valid_df['education'] == 'มัธยมศึกษาตอนต้น') & (valid_df['region'] == 'ทั่วประเทศ'),
    'มัธยมปลาย สายอาชีวศึกษา': (valid_df['education'] == 'มัธยมศึกษาตอนปลาย สายอาชีวศึกษา') & (valid_df['region'] == 'ทั่วประเทศ'),
    'ภาคตะวันออกเฉียงเหนือ': (valid_df['region'] == 'ภาคตะวันออกเฉียงเหนือ'),
    'กรุงเทพมหานคร': (valid_df['region'] == 'กรุงเทพมหานคร'),
    'กลุ่มเยาวชน 15-24 ปี': (valid_df['age_group'].isin(['15-19 ปี', '20-24 ปี'])) & (valid_df['region'] == 'ทั่วประเทศ'),
    'กลุ่มสูงวัย 60 ปีขึ้นไป': (valid_df['age_group'] == '60 ปีขึ้นไป') & (valid_df['region'] == 'ทั่วประเทศ')
}

for name, mask in cohort_defs.items():
    sub = valid_df[mask].groupby(['year', 'quarter_key'])[['avg_wage', 'employment_rate']].mean().round(2).reset_index().sort_values(['year', 'quarter_key'])
    cohorts[name] = sub.to_dict(orient='records')

# 6. Compact dictionary encoding for dynamic target group filtering
cols_to_index = ['year', 'quarter_key', 'region', 'area', 'sex', 'age_group', 'education', 'industry']
vocab = {}
inv_vocab = {}

for c in cols_to_index:
    vals = [str(x) for x in valid_df[c].dropna().unique()]
    if 'ทั่วประเทศ' in vals:
        vals.remove('ทั่วประเทศ')
        vals.insert(0, 'ทั่วประเทศ')
    elif 'รวม' in vals:
        vals.remove('รวม')
        vals.insert(0, 'รวม')
    vocab[c] = {v: i for i, v in enumerate(vals)}
    inv_vocab[c] = vals

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

# 7. Industry list
ind_agg = valid_df[valid_df['industry'] != 'รวม'].groupby('industry')['avg_wage'].mean().round(2).reset_index().sort_values('avg_wage', ascending=False)
industries_data = ind_agg.to_dict(orient='records')

bundle = {
    "timeline": timeline,
    "national_benchmark": {"employment_rate": nat_emp_mean, "avg_wage": nat_wage_mean},
    "regions": reg_data,
    "education": ed_data,
    "age_gender": ag_data,
    "cohorts": cohorts,
    "industries": industries_data,
    "vocab": inv_vocab,
    "rows": encoded_rows
}

api_json_str = json.dumps(bundle, ensure_ascii=False)

html_template = f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Thailand Labor Market Dashboard | ตลาดแรงงานไทย</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Kanit:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet">

  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          colors: {{
            bgBase: '#F8F4EC',
            softPink: '#FF8FB7',
            magentaAccent: '#E83C91',
            darkPlum: '#43334C',
            mutedText: '#746B78',
            warmGold: '#F7B731',
            cardBorder: 'rgba(67, 51, 76, 0.08)'
          }},
          fontFamily: {{
            kanit: ['Kanit', 'sans-serif'],
          }}
        }}
      }}
    }}
  </script>

  <style>
    body {{
      font-family: 'Kanit', sans-serif;
      background-color: #F8F4EC;
      color: #43334C;
    }}
    .custom-card {{
      background: #FFFFFF;
      border: 1px solid rgba(67, 51, 76, 0.08);
      border-radius: 22px;
      box-shadow: 0 8px 24px rgba(67, 51, 76, 0.035);
      transition: all 0.2s ease;
    }}
    .custom-card:hover {{
      box-shadow: 0 12px 30px rgba(67, 51, 76, 0.06);
    }}
    ::-webkit-scrollbar {{
      width: 6px;
      height: 6px;
    }}
    ::-webkit-scrollbar-thumb {{
      background: #E83C91;
      border-radius: 999px;
    }}
    .badge-glow {{
      box-shadow: 0 0 12px rgba(232, 60, 145, 0.35);
    }}
  </style>
</head>
<body class="bg-bgBase min-h-screen p-2 sm:p-4 lg:p-6 flex justify-center">

  <!-- Main Container matching layout in media_1792754629024.png -->
  <div class="w-full max-w-[1600px] bg-bgBase rounded-[32px] flex overflow-hidden shadow-2xl border border-cardBorder">

    <!-- Left Navigation Rail / Dock -->
    <aside class="w-16 sm:w-20 bg-darkPlum flex flex-col items-center py-6 justify-between flex-shrink-0 z-30 shadow-lg">
      <div class="flex flex-col items-center space-y-7 w-full">
        <!-- Avatar with warm gold gradient -->
        <div class="w-11 h-11 rounded-full bg-gradient-to-tr from-warmGold to-yellow-200 flex items-center justify-center text-darkPlum shadow-md font-bold text-lg cursor-pointer transform hover:scale-105 transition">
          <i data-lucide="user" class="w-6 h-6"></i>
        </div>
        
        <!-- Navigation icons -->
        <nav class="flex flex-col space-y-5 w-full items-center">
          <button onclick="switchTab('tab1')" id="nav-btn-tab1" title="Tab 1: ภาพรวมตลาดแรงงานไทย" class="w-10 h-10 rounded-xl bg-magentaAccent text-white flex items-center justify-center shadow-lg transition">
            <i data-lucide="layout-grid" class="w-5 h-5"></i>
          </button>
          <button onclick="switchTab('tab2')" id="nav-btn-tab2" title="Tab 2: วิเคราะห์กลุ่มที่สนใจ" class="w-10 h-10 rounded-xl hover:bg-white/10 text-white/70 hover:text-white flex items-center justify-center transition">
            <i data-lucide="crosshair" class="w-5 h-5"></i>
          </button>
          <button onclick="scrollToInsights()" title="บทสรุปเชิงนโยบาย" class="w-10 h-10 rounded-xl hover:bg-white/10 text-white/70 hover:text-white flex items-center justify-center transition">
            <i data-lucide="lightbulb" class="w-5 h-5"></i>
          </button>
          <button onclick="resetAllFilters()" title="รีเซ็ตตัวกรองทั้งหมด" class="w-10 h-10 rounded-xl hover:bg-white/10 text-white/70 hover:text-white flex items-center justify-center transition">
            <i data-lucide="rotate-ccw" class="w-5 h-5"></i>
          </button>
        </nav>
      </div>

      <!-- Bottom API indicator icon -->
      <div class="flex flex-col items-center">
        <div title="เชื่อมต่อข้อมูลจาก Official NSO Open Data API" class="w-10 h-10 rounded-xl bg-white/5 text-white/70 flex items-center justify-center cursor-pointer">
          <i data-lucide="database" class="w-5 h-5"></i>
        </div>
      </div>
    </aside>

    <!-- Main Content Area -->
    <main class="flex-1 p-4 sm:p-6 lg:p-8 overflow-y-auto max-h-[96vh]">
      
      <!-- Top Bar: Title & Search & Tabs -->
      <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-6">
        <div>
          <div class="flex items-center gap-2">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-magentaAccent/15 text-magentaAccent">OPEN DATA API</span>
            <span class="text-xs text-mutedText font-medium">สำนักงานสถิติแห่งชาติ (NSO) · พ.ศ. 2561 – 2568</span>
          </div>
          <h1 class="text-2xl sm:text-3xl font-bold text-darkPlum tracking-tight mt-1">Dashboard ตลาดแรงงานไทย</h1>
          <p class="text-xs sm:text-sm text-mutedText">การวิเคราะห์ความสัมพันธ์ระหว่างการมีงานทำและค่าจ้างเฉลี่ยของแรงงานไทย</p>
        </div>

        <!-- Search Bar & Tab Toggle Buttons -->
        <div class="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <!-- Tab Pills -->
          <div class="bg-white/90 p-1.5 rounded-2xl border border-cardBorder flex shadow-sm">
            <button id="tab1-pill" onclick="switchTab('tab1')" class="px-4 py-2 rounded-xl text-sm font-semibold transition bg-magentaAccent text-white shadow-sm flex items-center gap-1.5">
              <i data-lucide="bar-chart-2" class="w-4 h-4"></i> Tab 1: ภาพรวม
            </button>
            <button id="tab2-pill" onclick="switchTab('tab2')" class="px-4 py-2 rounded-xl text-sm font-semibold transition text-darkPlum hover:bg-bgBase flex items-center gap-1.5">
              <i data-lucide="users" class="w-4 h-4"></i> Tab 2: กลุ่มที่น่าสนใจ
            </button>
          </div>

          <!-- Quick Search Box -->
          <div class="relative flex-1 sm:w-60">
            <input id="quick-search" oninput="onQuickSearch(this.value)" type="text" placeholder="ค้นหากลุ่ม / การศึกษา / ภาค..." class="w-full bg-white border border-cardBorder rounded-2xl px-4 py-2 pl-10 text-sm focus:outline-none focus:ring-2 focus:ring-magentaAccent/30 text-darkPlum shadow-sm">
            <i data-lucide="search" class="w-4 h-4 text-mutedText absolute left-3.5 top-3"></i>
          </div>
        </div>
      </div>

      <!-- ================================================================= -->
      <!-- TAB 1: FILTERS BAR -->
      <!-- ================================================================= -->
      <div id="tab1-filter-container" class="custom-card p-3 sm:p-4 mb-6 flex flex-wrap items-center gap-3 text-xs sm:text-sm bg-white/95">
        <div class="font-semibold text-darkPlum flex items-center gap-1.5 pr-2 border-r border-cardBorder">
          <i data-lucide="sliders-horizontal" class="w-4 h-4 text-magentaAccent"></i> ตัวกรองภาพรวม:
        </div>
        
        <!-- Year filter -->
        <div class="flex items-center gap-1.5">
          <span class="text-mutedText">ปี:</span>
          <select id="filter-year" onchange="onTab1FilterChange()" class="bg-bgBase border border-cardBorder rounded-xl px-2.5 py-1 text-darkPlum font-medium focus:outline-none cursor-pointer">
            <option value="ALL">รวมทุกปี (2561-2568)</option>
            <option value="2568">2568</option>
            <option value="2567">2567</option>
            <option value="2566">2566</option>
            <option value="2565">2565</option>
            <option value="2564">2564</option>
            <option value="2563">2563</option>
            <option value="2562">2562</option>
            <option value="2561">2561</option>
          </select>
        </div>

        <!-- Quarter filter -->
        <div class="flex items-center gap-1.5">
          <span class="text-mutedText">ไตรมาส:</span>
          <select id="filter-quarter" onchange="onTab1FilterChange()" class="bg-bgBase border border-cardBorder rounded-xl px-2.5 py-1 text-darkPlum font-medium focus:outline-none cursor-pointer">
            <option value="ALL">รวม 4 ไตรมาส</option>
            <option value="Q1">ไตรมาส 1 (Q1)</option>
            <option value="Q2">ไตรมาส 2 (Q2)</option>
            <option value="Q3">ไตรมาส 3 (Q3)</option>
            <option value="Q4">ไตรมาส 4 (Q4)</option>
          </select>
        </div>

        <!-- Region filter -->
        <div class="flex items-center gap-1.5">
          <span class="text-mutedText">ภูมิภาค:</span>
          <select id="filter-region" onchange="onTab1FilterChange()" class="bg-bgBase border border-cardBorder rounded-xl px-2.5 py-1 text-darkPlum font-medium focus:outline-none cursor-pointer">
            <option value="ALL">ทั่วประเทศ</option>
            <option value="กรุงเทพมหานคร">กรุงเทพมหานคร</option>
            <option value="ภาคกลาง">ภาคกลาง</option>
            <option value="ภาคเหนือ">ภาคเหนือ</option>
            <option value="ภาคใต้">ภาคใต้</option>
            <option value="ภาคตะวันออกเฉียงเหนือ">ภาคตะวันออกเฉียงเหนือ</option>
          </select>
        </div>

        <!-- Area filter -->
        <div class="flex items-center gap-1.5">
          <span class="text-mutedText">พื้นที่:</span>
          <select id="filter-area" onchange="onTab1FilterChange()" class="bg-bgBase border border-cardBorder rounded-xl px-2.5 py-1 text-darkPlum font-medium focus:outline-none cursor-pointer">
            <option value="ALL">รวมทุกพื้นที่</option>
            <option value="ในเขตเทศบาล">ในเขตเทศบาล</option>
            <option value="นอกเขตเทศบาล">นอกเขตเทศบาล</option>
          </select>
        </div>

        <button onclick="resetTab1Filters()" class="ml-auto text-xs font-semibold text-magentaAccent hover:underline flex items-center gap-1">
          <i data-lucide="refresh-cw" class="w-3.5 h-3.5"></i> ล้างตัวกรอง
        </button>
      </div>

      <!-- ================================================================= -->
      <!-- TAB 2: MULTI-DIMENSIONAL TARGET GROUP FILTER BAR -->
      <!-- ================================================================= -->
      <div id="tab2-filter-container" class="custom-card p-4 mb-6 bg-white/95 border-2 border-magentaAccent/20 hidden">
        <div class="flex items-center justify-between pb-2 mb-3 border-b border-cardBorder">
          <div class="font-bold text-darkPlum flex items-center gap-2">
            <span class="p-1 rounded-lg bg-magentaAccent text-white"><i data-lucide="target" class="w-4 h-4"></i></span>
            กำหนดมิติของกลุ่มเป้าหมายที่สนใจ (Target Group Dimensions):
          </div>
          <span class="text-xs text-mutedText">เลือกมิติเพื่อเปรียบเทียบกับค่าเฉลี่ยประเทศแบบ Real-time</span>
        </div>
        
        <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-7 gap-3 text-xs">
          <!-- Year -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">ปี พ.ศ.:</label>
            <select id="t2-year" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">รวมทุกปี</option>
              <option value="2568">2568</option>
              <option value="2567">2567</option>
              <option value="2566">2566</option>
              <option value="2565">2565</option>
              <option value="2564">2564</option>
              <option value="2563">2563</option>
              <option value="2562">2562</option>
              <option value="2561">2561</option>
            </select>
          </div>

          <!-- Region -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">ภูมิภาค:</label>
            <select id="t2-region" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">ทั่วประเทศ</option>
              <option value="กรุงเทพมหานคร">กรุงเทพมหานคร</option>
              <option value="ภาคกลาง">ภาคกลาง</option>
              <option value="ภาคเหนือ">ภาคเหนือ</option>
              <option value="ภาคใต้">ภาคใต้</option>
              <option value="ภาคตะวันออกเฉียงเหนือ">ภาคตะวันออกเฉียงเหนือ</option>
            </select>
          </div>

          <!-- Area -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">พื้นที่:</label>
            <select id="t2-area" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">รวมทุกพื้นที่</option>
              <option value="ในเขตเทศบาล">ในเขตเทศบาล</option>
              <option value="นอกเขตเทศบาล">นอกเขตเทศบาล</option>
            </select>
          </div>

          <!-- Sex -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">เพศ:</label>
            <select id="t2-sex" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">รวมทั้งสองเพศ</option>
              <option value="ชาย">ชาย</option>
              <option value="หญิง">หญิง</option>
            </select>
          </div>

          <!-- Age -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">ช่วงอายุ:</label>
            <select id="t2-age" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">รวมทุกช่วงอายุ</option>
              <option value="15-19 ปี">15-19 ปี (เยาวชน)</option>
              <option value="20-24 ปี">20-24 ปี (จบใหม่)</option>
              <option value="25-29 ปี">25-29 ปี</option>
              <option value="30-34 ปี">30-34 ปี</option>
              <option value="35-39 ปี">35-39 ปี</option>
              <option value="40-49 ปี">40-49 ปี (วัยกลางคน)</option>
              <option value="50-59 ปี">50-59 ปี</option>
              <option value="60 ปีขึ้นไป">60 ปีขึ้นไป (สูงวัย)</option>
            </select>
          </div>

          <!-- Education -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">ระดับการศึกษา:</label>
            <select id="t2-edu" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">รวมทุกระดับการศึกษา</option>
              <option value="ไม่มีการศึกษา">ไม่มีการศึกษา</option>
              <option value="ต่ำกว่าประถมศึกษา">ต่ำกว่าประถมศึกษา</option>
              <option value="ประถมศึกษา">ประถมศึกษา (เสี่ยงจนเฉียบพลัน)</option>
              <option value="มัธยมศึกษาตอนต้น">มัธยมศึกษาตอนต้น</option>
              <option value="มัธยมศึกษาตอนปลาย สายสามัญ">ม.ปลาย สายสามัญ</option>
              <option value="มัธยมศึกษาตอนปลาย สายอาชีวศึกษา">ม.ปลาย สายอาชีวศึกษา (ปวช.)</option>
              <option value="อุดมศึกษา สายวิชาชีพ">อุดมศึกษา สายวิชาชีพ (ปวส.)</option>
              <option value="อุดมศึกษา สายวิชาการ">อุดมศึกษา สายวิชาการ (ปริญญาตรีขึ้นไป)</option>
            </select>
          </div>

          <!-- Industry -->
          <div>
            <label class="text-mutedText block mb-1 font-medium">ประเภทอุตสาหกรรม:</label>
            <select id="t2-ind" onchange="onTargetGroupFilterChange()" class="w-full bg-bgBase border border-cardBorder rounded-xl p-2 text-darkPlum font-medium focus:outline-none">
              <option value="ALL">รวมทุกอุตสาหกรรม</option>
              <option value="การผลิต">การผลิต</option>
              <option value="การขายส่ง และการขายปลีก การซ่อมยานยนต์">การค้าส่ง / ปลีก</option>
              <option value="การก่อสร้าง">การก่อสร้าง</option>
              <option value="การขนส่ง และสถานที่เก็บสินค้า">การขนส่งและโลจิสติกส์</option>
              <option value="กิจกรรมทางการเงินและการประกันภัย">การเงินและประกันภัย</option>
              <option value="ข้อมูลข่าวสารและการสื่อสาร">ข้อมูลข่าวสารและสื่อสาร</option>
              <option value="การศึกษา">การศึกษา</option>
              <option value="กิจกรรมด้านสุขภาพและงานสังคมสงเคราะห์">สุขภาพและสังคมสงเคราะห์</option>
              <option value="เกษตรกรรม การป่าไม้ และการประมง">เกษตรกรรมและประมง</option>
              <option value="การบริหารราชการ การป้องกันประเทศ การประกันสังคม">บริหารราชการ/รัฐบาล</option>
            </select>
          </div>
        </div>
      </div>

      <!-- ================================================================= -->
      <!-- BENTO GRID ROW 1: 4 Cards matching media_1792754629024.png -->
      <!-- ================================================================= -->
      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-5">
        
        <!-- Card 1A: Metric with wave sparkline & highlight tag -->
        <div class="custom-card p-5 flex flex-col justify-between relative overflow-hidden">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-xs font-medium text-mutedText">อัตราการมีงานทำเฉลี่ย</p>
              <h2 id="kpi-emp" class="text-3xl font-bold text-darkPlum mt-0.5">67.50%</h2>
              <span class="text-[11px] text-mutedText">ต่อประชากรวัยแรงงาน</span>
            </div>
            <span class="px-2.5 py-1 rounded-full text-xs font-bold bg-warmGold/20 text-darkPlum border border-warmGold/40 shadow-sm flex items-center gap-1">
              +0.35% YoY
            </span>
          </div>
          <!-- Canvas for wavy sparkline -->
          <div class="h-16 mt-3">
            <canvas id="sparkline-emp"></canvas>
          </div>
        </div>

        <!-- Card 1B: Average wage with multi-dot line sparkline -->
        <div class="custom-card p-5 flex flex-col justify-between">
          <div class="flex justify-between items-start">
            <div>
              <p class="text-xs font-medium text-mutedText">ค่าจ้างเฉลี่ยของลูกจ้าง</p>
              <h2 id="kpi-wage" class="text-3xl font-bold text-darkPlum mt-0.5">฿15,341</h2>
              <span class="text-[11px] text-mutedText">บาทต่อเดือน</span>
            </div>
            <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-magentaAccent/15 text-magentaAccent border border-magentaAccent/30">
              +3.2% YoY
            </span>
          </div>
          <!-- Canvas for dotted line sparkline -->
          <div class="h-16 mt-3">
            <canvas id="sparkline-wage"></canvas>
          </div>
        </div>

        <!-- Card 1C: Calendar / Period Widget -->
        <div class="custom-card p-5 flex flex-col justify-between">
          <div class="flex justify-between items-center mb-2">
            <span class="text-xs font-bold text-darkPlum flex items-center gap-1">
              <i data-lucide="calendar" class="w-3.5 h-3.5 text-magentaAccent"></i> ช่วงเวลาข้อมูล
            </span>
            <span id="period-badge" class="text-[11px] font-semibold text-magentaAccent bg-magentaAccent/10 px-2 py-0.5 rounded-md">
              พ.ศ. 2568
            </span>
          </div>
          <!-- Quarter pills matching calendar grid in image -->
          <div class="grid grid-cols-4 gap-1.5 my-2">
            <button onclick="setQuarterQuick('Q1')" id="btn-q1" class="p-2 text-center rounded-xl bg-bgBase text-xs font-bold text-darkPlum hover:bg-magentaAccent hover:text-white cursor-pointer transition">Q1</button>
            <button onclick="setQuarterQuick('Q2')" id="btn-q2" class="p-2 text-center rounded-xl bg-bgBase text-xs font-bold text-darkPlum hover:bg-magentaAccent hover:text-white cursor-pointer transition">Q2</button>
            <button onclick="setQuarterQuick('Q3')" id="btn-q3" class="p-2 text-center rounded-xl bg-bgBase text-xs font-bold text-darkPlum hover:bg-magentaAccent hover:text-white cursor-pointer transition">Q3</button>
            <button onclick="setQuarterQuick('Q4')" id="btn-q4" class="p-2 text-center rounded-xl bg-magentaAccent text-xs font-bold text-white shadow-sm cursor-pointer transition">Q4</button>
          </div>
          <div class="flex items-center justify-between text-[11px] text-mutedText mt-1 pt-2 border-t border-cardBorder">
            <span>สถานะ API:</span>
            <span class="text-emerald-600 font-semibold flex items-center gap-1">
              <span class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span> เชื่อมต่อสมบูรณ์
            </span>
          </div>
        </div>

        <!-- Card 1D: Dual Circular Progress Gauges -->
        <div class="custom-card p-5 flex items-center justify-around">
          <!-- Circular Gauge 1 -->
          <div class="flex flex-col items-center">
            <div class="relative w-16 h-16 flex items-center justify-center">
              <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path class="text-gray-100" stroke-width="3.5" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="text-magentaAccent" stroke-dasharray="78, 100" stroke-width="3.5" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="absolute text-xs font-bold text-darkPlum">27K</span>
            </div>
            <span class="text-[11px] font-semibold text-mutedText mt-1.5">กทม. สูงสุด</span>
            <span class="text-[10px] text-magentaAccent font-medium">฿26,913/ด.</span>
          </div>

          <!-- Divider -->
          <div class="h-14 w-[1px] bg-cardBorder"></div>

          <!-- Circular Gauge 2 -->
          <div class="flex flex-col items-center">
            <div class="relative w-16 h-16 flex items-center justify-center">
              <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                <path class="text-gray-100" stroke-width="3.5" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                <path class="text-darkPlum" stroke-dasharray="90, 100" stroke-width="3.5" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              </svg>
              <span class="absolute text-xs font-bold text-darkPlum">90%</span>
            </div>
            <span class="text-[11px] font-semibold text-mutedText mt-1.5">เกณฑ์มีงานทำ</span>
            <span class="text-[10px] text-darkPlum font-medium">เป้าหมายแรงงาน</span>
          </div>
        </div>

      </div>

      <!-- ================================================================= -->
      <!-- BENTO GRID ROW 2: Middle Row matching media_1792754629024.png -->
      <!-- ================================================================= -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-5 mb-5">
        
        <!-- Card 2A: Dual Highlights with mini sparklines (3 Cols) -->
        <div class="lg:col-span-3 custom-card p-5 flex flex-col justify-between">
          <div>
            <div class="pb-3 border-b border-cardBorder">
              <div class="flex justify-between items-center">
                <span class="text-xs text-mutedText font-medium">งานทำสูงสุด</span>
                <span class="text-[10px] font-bold text-darkPlum bg-warmGold/25 px-2 py-0.5 rounded-full">ภาคกลาง</span>
              </div>
              <div class="text-2xl font-bold text-darkPlum mt-1">69.47%</div>
              <div class="h-7 mt-1"><canvas id="mini-wave-1"></canvas></div>
            </div>

            <div class="pt-3">
              <div class="flex justify-between items-center">
                <span class="text-xs text-mutedText font-medium">ค่าจ้างสูงสุด</span>
                <span class="text-[10px] font-bold text-white bg-magentaAccent px-2 py-0.5 rounded-full">กทม.</span>
              </div>
              <div class="text-2xl font-bold text-darkPlum mt-1">฿26,913</div>
              <div class="h-7 mt-1"><canvas id="mini-wave-2"></canvas></div>
            </div>
          </div>
        </div>

        <!-- Card 2B: Big Circular Ring Gauge with Tab 2 button (3 Cols) -->
        <div class="lg:col-span-3 custom-card p-6 flex flex-col items-center justify-center text-center relative">
          <!-- Big Circular Progress Ring -->
          <div class="relative w-28 h-28 flex items-center justify-center my-1">
            <svg class="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path class="text-gray-100" stroke-width="3" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
              <path class="text-magentaAccent" stroke-dasharray="68, 100" stroke-width="3.2" stroke-linecap="round" stroke="currentColor" fill="none" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
            </svg>
            <span class="absolute text-2xl font-bold text-darkPlum">67.5%</span>
          </div>

          <h3 class="font-bold text-darkPlum text-sm mt-2">อัตราการมีงานทำภาพรวม</h3>
          <p class="text-xs text-mutedText mt-1 max-w-[190px]">มีงานทำในสัดส่วนสูง แต่ต้องพิจารณาร่วมกับระดับค่าจ้าง</p>

          <button onclick="switchTab('tab2')" class="mt-4 px-6 py-2 rounded-xl bg-warmGold hover:bg-yellow-400 text-darkPlum font-bold text-xs shadow-md transition transform active:scale-95 flex items-center gap-1.5">
            <i data-lucide="crosshair" class="w-4 h-4"></i> วิเคราะห์กลุ่มเป้าหมาย (Tab 2)
          </button>
        </div>

        <!-- Card 2C: Large Smooth Spline Area Chart (Graph 1 & 2) (6 Cols) -->
        <div class="lg:col-span-6 custom-card p-5 flex flex-col justify-between">
          <div class="flex justify-between items-center mb-3">
            <div>
              <h3 id="main-chart-title" class="font-bold text-darkPlum text-base">แนวโน้มอัตราการมีงานทำและค่าจ้างเฉลี่ย (2561 - 2568)</h3>
              <p class="text-xs text-mutedText">กราฟเส้นโค้งเรียบ (Smooth Spline) 2 แกน สอดคล้องตามตัวอย่างดีไซน์</p>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-xs text-mutedText font-medium hidden sm:inline">มุมมอง:</span>
              <span class="px-2.5 py-1 text-xs rounded-lg bg-bgBase font-semibold text-darkPlum border border-cardBorder">รายไตรมาส</span>
            </div>
          </div>
          <div class="h-60 w-full">
            <canvas id="main-spline-chart"></canvas>
          </div>
        </div>

      </div>

      <!-- ================================================================= -->
      <!-- TAB 1 CONTENT CONTAINER -->
      <!-- ================================================================= -->
      <div id="tab1-content" class="space-y-5">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          <!-- Card 3A (Tab 1): Regional Map & Overview Cards (4 Cols) -->
          <div class="lg:col-span-4 custom-card p-5 flex flex-col justify-between">
            <div class="flex justify-between items-center mb-3">
              <div>
                <h3 class="font-bold text-darkPlum text-sm">3. อัตราการมีงานทำรายภูมิภาค</h3>
                <p class="text-xs text-mutedText">การกระจายตัวของค่าจ้างและงานทำ 5 ภาค</p>
              </div>
              <span class="text-xs text-magentaAccent font-bold">5 ภูมิภาค</span>
            </div>
            
            <div class="space-y-2.5 my-2">
              <div class="p-2.5 rounded-xl bg-bgBase flex justify-between items-center text-xs">
                <span class="font-bold text-darkPlum">กทม. และปริมณฑล</span>
                <span class="text-darkPlum font-medium">มีงานทำ 72.49% | <b class="text-magentaAccent">฿26,913</b></span>
              </div>
              <div class="p-2.5 rounded-xl bg-bgBase flex justify-between items-center text-xs">
                <span class="font-bold text-darkPlum">ภาคกลาง</span>
                <span class="text-darkPlum font-medium">มีงานทำ 69.47% | <b class="text-darkPlum">฿18,087</b></span>
              </div>
              <div class="p-2.5 rounded-xl bg-bgBase flex justify-between items-center text-xs">
                <span class="font-bold text-darkPlum">ภาคใต้</span>
                <span class="text-darkPlum font-medium">มีงานทำ 68.09% | <b class="text-darkPlum">฿14,175</b></span>
              </div>
              <div class="p-2.5 rounded-xl bg-bgBase flex justify-between items-center text-xs">
                <span class="font-bold text-darkPlum">ภาคเหนือ</span>
                <span class="text-darkPlum font-medium">มีงานทำ 64.73% | <b class="text-darkPlum">฿13,941</b></span>
              </div>
              <div class="p-2.5 rounded-xl bg-bgBase flex justify-between items-center text-xs">
                <span class="font-bold text-darkPlum">ภาคตะวันออกเฉียงเหนือ</span>
                <span class="text-darkPlum font-medium">มีงานทำ 62.41% | <b class="text-magentaAccent">฿12,816</b></span>
              </div>
            </div>
            
            <p class="text-[11px] text-mutedText text-center mt-1">ภาคอีสานมีค่าจ้างต่ำสุด ขณะที่ กทม. มีค่าจ้างเฉลี่ยสูงกว่าถึง 2 เท่า</p>
          </div>

          <!-- Card 3B (Tab 1): Economic Milestones Steps (4 Cols) -->
          <div class="lg:col-span-4 custom-card p-5 flex flex-col justify-between">
            <h3 class="font-bold text-darkPlum text-sm mb-1">เหตุการณ์สำคัญตามช่วงเวลา</h3>
            <p class="text-xs text-mutedText mb-3">พัฒนาการของตลาดแรงงาน พ.ศ. 2561 – 2568</p>

            <!-- Connected step timeline tags -->
            <div class="relative py-4">
              <div class="absolute top-1/2 left-4 right-4 h-1 bg-magentaAccent/20 -translate-y-1/2"></div>
              
              <div class="flex justify-between relative z-10">
                <div class="flex flex-col items-center">
                  <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-darkPlum text-white shadow-sm mb-1">ก่อนโควิด</span>
                  <div class="w-4 h-4 rounded-full bg-magentaAccent border-2 border-white shadow"></div>
                  <span class="text-[10px] font-semibold text-mutedText mt-1">2561-2562</span>
                </div>
                <div class="flex flex-col items-center">
                  <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-warmGold text-darkPlum shadow-sm mb-1">วิกฤตโควิด</span>
                  <div class="w-4 h-4 rounded-full bg-warmGold border-2 border-white shadow"></div>
                  <span class="text-[10px] font-semibold text-mutedText mt-1">2563-2564</span>
                </div>
                <div class="flex flex-col items-center">
                  <span class="px-2.5 py-1 rounded-lg text-[10px] font-bold bg-magentaAccent text-white shadow-sm mb-1">ฟื้นตัว</span>
                  <div class="w-4 h-4 rounded-full bg-magentaAccent border-2 border-white shadow"></div>
                  <span class="text-[10px] font-semibold text-mutedText mt-1">2565-2568</span>
                </div>
              </div>
            </div>

            <div class="p-3 bg-bgBase rounded-xl text-xs text-darkPlum space-y-1 mt-2">
              <p>• <b>วิกฤตโควิด-19:</b> อัตราการมีงานทำร่วงสู่ระดับต่ำสุด 65.8% ใน Q2/2563</p>
              <p>• <b>ระยะฟื้นตัว:</b> ค่าจ้างเฉลี่ยลูกจ้างขยายตัวต่อเนื่อง สู่ระดับ 17,000+ บาท</p>
            </div>
          </div>

          <!-- Card 3C (Tab 1): Horizontal Ranking Bar Chart (Graph 4) (4 Cols) -->
          <div class="lg:col-span-4 custom-card p-5 flex flex-col justify-between">
            <div class="flex justify-between items-center mb-2">
              <div>
                <h3 class="font-bold text-darkPlum text-sm">4. จัดอันดับภูมิภาค</h3>
                <p class="text-xs text-mutedText">เปรียบเทียบอัตราการมีงานทำ (%)</p>
              </div>
              <span class="text-xs font-bold text-darkPlum">อันดับ 1-5</span>
            </div>
            <div class="h-56 w-full">
              <canvas id="region-ranking-chart"></canvas>
            </div>
          </div>

        </div>
      </div>

      <!-- ================================================================= -->
      <!-- TAB 2 CONTENT CONTAINER -->
      <!-- ================================================================= -->
      <div id="tab2-content" class="space-y-5 hidden">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          <!-- Card 3A (Tab 2): Graph 5 Butterfly Chart (5 Cols) -->
          <div class="lg:col-span-5 custom-card p-5 flex flex-col justify-between">
            <div class="flex justify-between items-center mb-2">
              <div>
                <h3 class="font-bold text-darkPlum text-sm">5. การมีงานทำและค่าจ้างตามการศึกษา</h3>
                <p class="text-xs text-mutedText">Butterfly Chart (งานทำ % ซ้าย vs ค่าจ้าง ฿ ขวา)</p>
              </div>
              <span class="text-xs font-bold text-magentaAccent bg-magentaAccent/10 px-2 py-0.5 rounded-md">จุดตัดความเหลื่อมล้ำ</span>
            </div>
            <div class="h-64 w-full">
              <canvas id="butterfly-chart"></canvas>
            </div>
          </div>

          <!-- Card 3B (Tab 2): Graph 7 Comparison Profile with National Benchmark (3 Cols) -->
          <div class="lg:col-span-3 custom-card p-5 flex flex-col justify-between border-2 border-magentaAccent/20">
            <div>
              <div class="flex justify-between items-start mb-2">
                <div>
                  <h3 class="font-bold text-darkPlum text-sm">7. เปรียบเทียบกับค่าเฉลี่ยประเทศ</h3>
                  <p class="text-[11px] text-mutedText">Benchmark Comparison</p>
                </div>
                <span id="target-risk-badge" class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700">
                  ⚠️ เสี่ยงสูง
                </span>
              </div>

              <!-- Selected target summary -->
              <div class="bg-bgBase p-2.5 rounded-xl mb-3 text-xs">
                <span class="text-mutedText">กลุ่มที่เลือก:</span>
                <div id="target-group-name" class="font-bold text-darkPlum truncate mt-0.5">ประถมศึกษา (ทุกภาค)</div>
              </div>

              <!-- Metrics Comparison -->
              <div class="space-y-3 text-xs">
                <div>
                  <div class="flex justify-between items-center">
                    <span class="text-mutedText">อัตราการมีงานทำ:</span>
                    <span id="target-emp-val" class="font-bold text-darkPlum">73.9%</span>
                  </div>
                  <div class="flex justify-between items-center text-[11px] text-emerald-600 font-medium">
                    <span>เทียบค่าเฉลี่ย (67.5%):</span>
                    <span id="target-emp-diff">+6.4% pt</span>
                  </div>
                  <div class="w-full bg-gray-200 h-1.5 rounded-full mt-1 overflow-hidden">
                    <div id="target-emp-bar" class="bg-magentaAccent h-full" style="width: 74%"></div>
                  </div>
                </div>

                <div>
                  <div class="flex justify-between items-center">
                    <span class="text-mutedText">ค่าจ้างเฉลี่ย:</span>
                    <span id="target-wage-val" class="font-bold text-darkPlum">฿9,730</span>
                  </div>
                  <div class="flex justify-between items-center text-[11px] text-red-600 font-medium">
                    <span>เทียบค่าเฉลี่ย (฿15,341):</span>
                    <span id="target-wage-diff">-฿5,611 (-36.5%)</span>
                  </div>
                  <div class="w-full bg-gray-200 h-1.5 rounded-full mt-1 overflow-hidden">
                    <div id="target-wage-bar" class="bg-darkPlum h-full" style="width: 63%"></div>
                  </div>
                </div>
              </div>
            </div>

            <div id="target-diag-text" class="p-2.5 rounded-xl bg-red-50 text-[11px] text-red-800 mt-2 border border-red-200">
              <b>ภาวะ In-work Poverty:</b> มีงานทำสูงมากแต่ค่าจ้างต่ำกว่าเกณฑ์มาตรฐานอย่างมีนัยสำคัญ
            </div>
          </div>

          <!-- Card 3C (Tab 2): Graph 6 Grouped Bar (Age & Gender Gap) (4 Cols) -->
          <div class="lg:col-span-4 custom-card p-5 flex flex-col justify-between">
            <div class="flex justify-between items-center mb-2">
              <div>
                <h3 class="font-bold text-darkPlum text-sm">6. ค่าจ้างชาย–หญิง ตามกลุ่มอายุ</h3>
                <p class="text-xs text-mutedText">Gender Wage Gap by Age Brackets</p>
              </div>
              <div class="flex items-center gap-2 text-xs">
                <span class="flex items-center gap-1 font-semibold text-darkPlum"><span class="w-2.5 h-2.5 rounded-full bg-darkPlum"></span> ชาย</span>
                <span class="flex items-center gap-1 font-semibold text-magentaAccent"><span class="w-2.5 h-2.5 rounded-full bg-magentaAccent"></span> หญิง</span>
              </div>
            </div>
            <div class="h-64 w-full">
              <canvas id="gender-age-chart"></canvas>
            </div>
          </div>

        </div>
      </div>

      <!-- ================================================================= -->
      <!-- BOTTOM ROW: Graph 8 Cohort Trend & Final Insights -->
      <!-- ================================================================= -->
      <div id="insights-section" class="mt-5 grid grid-cols-1 lg:grid-cols-12 gap-5">
        
        <!-- Graph 8: Cohort Historical Trend (6 Cols) -->
        <div class="lg:col-span-6 custom-card p-5 flex flex-col justify-between">
          <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 mb-3">
            <div>
              <h3 class="font-bold text-darkPlum text-base">8. แนวโน้มย้อนหลังของกลุ่มที่เลือก (Cohort Trend)</h3>
              <p class="text-xs text-mutedText">ตรวจสอบว่าช่องว่างความแตกต่างเกิดขึ้นต่อเนื่องหรือชั่วคราว (2561-2568)</p>
            </div>
            <select id="cohort-select" onchange="onCohortChange()" class="bg-bgBase border border-cardBorder rounded-xl px-3 py-1.5 text-xs font-bold text-darkPlum focus:outline-none cursor-pointer">
              <option value="อุดมศึกษา สายวิชาการ">🎓 อุดมศึกษา สายวิชาการ</option>
              <option value="ประถมศึกษา (เสี่ยง In-work Poverty)">📚 ประถมศึกษา (งานทำสูง-ค่าจ้างต่ำ)</option>
              <option value="มัธยมศึกษาตอนต้น">🎒 มัธยมศึกษาตอนต้น</option>
              <option value="มัธยมปลาย สายอาชีวศึกษา">🛠️ มัธยมปลาย สายอาชีวศึกษา (ปวช.)</option>
              <option value="ภาคตะวันออกเฉียงเหนือ">🌾 ภาคตะวันออกเฉียงเหนือ</option>
              <option value="กรุงเทพมหานคร">🏙️ กรุงเทพมหานคร</option>
              <option value="กลุ่มเยาวชน 15-24 ปี">🌱 กลุ่มเยาวชน 15-24 ปี</option>
              <option value="กลุ่มสูงวัย 60 ปีขึ้นไป">👵 กลุ่มสูงวัย 60 ปีขึ้นไป</option>
            </select>
          </div>
          <div class="h-64 w-full">
            <canvas id="cohort-chart"></canvas>
          </div>
        </div>

        <!-- Executive Policy Insights (6 Cols) -->
        <div class="lg:col-span-6 custom-card p-6 flex flex-col justify-between border-l-8 border-magentaAccent">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="p-1.5 rounded-xl bg-magentaAccent/15 text-magentaAccent"><i data-lucide="award" class="w-5 h-5"></i></span>
              <h3 class="font-bold text-darkPlum text-base">สรุปผลการวิเคราะห์และข้อเสนอแนะเชิงนโยบาย (Executive Insights)</h3>
            </div>
            <div class="space-y-2.5 text-xs text-darkPlum/90 leading-relaxed mt-3">
              <div class="p-3 rounded-xl bg-bgBase border border-cardBorder">
                <b>📌 ตอบคำถามหลัก:</b> กลุ่มที่มีงานทำสูง <b>ไม่ได้มีค่าจ้างสูงตามไปด้วยเสมอไป</b> สะท้อนจากกลุ่มผู้จบประถม/มัธยมต้น ที่มีอัตรามีงานทำสูงถึง 70-74% แต่ค่าจ้างเฉลี่ยต่ำที่สุด (9,700 - 10,800 บาท) เกิดปัญหา <i>In-work Poverty</i>
              </div>
              <div class="p-3 rounded-xl bg-bgBase border border-cardBorder">
                <b>🗺️ ความแตกต่างเชิงพื้นที่:</b> กรุงเทพฯ มีค่าจ้างเฉลี่ยสูงกว่าภาคอีสานถึง <b>110% (฿26.9K vs ฿12.8K)</b> แม้สัดส่วนการมีงานทำในอีสานจะค่อนข้างสูง (62.4%)
              </div>
              <div class="p-3 rounded-xl bg-bgBase border border-cardBorder">
                <b>🎯 ข้อเสนอแนะนโยบาย:</b> กรมพัฒนาฝีมือแรงงาน (DSD) ควรมุ่งเป้า Re-skill ทักษะเทคโนโลยีแก่แรงงานระดับประถม/มัธยม และกระทรวงแรงงานควรผลักดันการกระจายอุตสาหกรรมมูลค่าสูงสู่ส่วนภูมิภาค
              </div>
            </div>
          </div>
          <div class="pt-3 border-t border-cardBorder text-[11px] text-mutedText flex justify-between items-center mt-3">
            <span>แหล่งข้อมูล: NSO Open Data API (0706_02_0011 & 0706_02_0019)</span>
            <span class="text-magentaAccent font-semibold">โครงการวิเคราะห์ตลาดแรงงานไทย</span>
          </div>
        </div>

      </div>

    </main>
  </div>

  <!-- Embedded JSON Data from NSO API -->
  <script>
    const API_DATA = {api_json_str};

    let currentTab = 'tab1';
    let mainSplineChartInstance = null;
    let regionRankingChartInstance = null;
    let butterflyChartInstance = null;
    let genderAgeChartInstance = null;
    let cohortChartInstance = null;

    window.addEventListener('DOMContentLoaded', () => {{
      lucide.createIcons();
      initSparklines();
      initMainSplineChart();
      initRegionRankingChart();
      initButterflyChart();
      initGenderAgeChart();
      initCohortChart('อุดมศึกษา สายวิชาการ');
      updateTargetGroupAnalysis();
    }});

    function switchTab(tabId) {{
      currentTab = tabId;
      const tab1Content = document.getElementById('tab1-content');
      const tab2Content = document.getElementById('tab2-content');
      const tab1Filter = document.getElementById('tab1-filter-container');
      const tab2Filter = document.getElementById('tab2-filter-container');
      const tab1Pill = document.getElementById('tab1-pill');
      const tab2Pill = document.getElementById('tab2-pill');
      const navBtn1 = document.getElementById('nav-btn-tab1');
      const navBtn2 = document.getElementById('nav-btn-tab2');

      if (tabId === 'tab1') {{
        tab1Content.classList.remove('hidden');
        tab2Content.classList.add('hidden');
        tab1Filter.classList.remove('hidden');
        tab2Filter.classList.add('hidden');
        
        tab1Pill.className = "px-4 py-2 rounded-xl text-sm font-semibold transition bg-magentaAccent text-white shadow-sm flex items-center gap-1.5";
        tab2Pill.className = "px-4 py-2 rounded-xl text-sm font-semibold transition text-darkPlum hover:bg-bgBase flex items-center gap-1.5";
        
        navBtn1.className = "w-10 h-10 rounded-xl bg-magentaAccent text-white flex items-center justify-center shadow-lg transition";
        navBtn2.className = "w-10 h-10 rounded-xl hover:bg-white/10 text-white/70 hover:text-white flex items-center justify-center transition";
      }} else {{
        tab1Content.classList.add('hidden');
        tab2Content.classList.remove('hidden');
        tab1Filter.classList.add('hidden');
        tab2Filter.classList.remove('hidden');
        
        tab2Pill.className = "px-4 py-2 rounded-xl text-sm font-semibold transition bg-magentaAccent text-white shadow-sm flex items-center gap-1.5";
        tab1Pill.className = "px-4 py-2 rounded-xl text-sm font-semibold transition text-darkPlum hover:bg-bgBase flex items-center gap-1.5";
        
        navBtn2.className = "w-10 h-10 rounded-xl bg-magentaAccent text-white flex items-center justify-center shadow-lg transition";
        navBtn1.className = "w-10 h-10 rounded-xl hover:bg-white/10 text-white/70 hover:text-white flex items-center justify-center transition";
      }}
      lucide.createIcons();
    }}

    function scrollToInsights() {{
      document.getElementById('insights-section').scrollIntoView({{ behavior: 'smooth' }});
    }}

    function resetAllFilters() {{
      resetTab1Filters();
      document.getElementById('t2-year').value = 'ALL';
      document.getElementById('t2-region').value = 'ALL';
      document.getElementById('t2-area').value = 'ALL';
      document.getElementById('t2-sex').value = 'ALL';
      document.getElementById('t2-age').value = 'ALL';
      document.getElementById('t2-edu').value = 'ALL';
      document.getElementById('t2-ind').value = 'ALL';
      updateTargetGroupAnalysis();
    }}

    function resetTab1Filters() {{
      document.getElementById('filter-year').value = 'ALL';
      document.getElementById('filter-quarter').value = 'ALL';
      document.getElementById('filter-region').value = 'ALL';
      document.getElementById('filter-area').value = 'ALL';
      onTab1FilterChange();
    }}

    function setQuarterQuick(q) {{
      ['btn-q1', 'btn-q2', 'btn-q3', 'btn-q4'].forEach(id => {{
        const btn = document.getElementById(id);
        btn.className = "p-2 text-center rounded-xl bg-bgBase text-xs font-bold text-darkPlum hover:bg-magentaAccent hover:text-white cursor-pointer transition";
      }});
      const clicked = document.getElementById('btn-' + q.toLowerCase());
      if (clicked) {{
        clicked.className = "p-2 text-center rounded-xl bg-magentaAccent text-xs font-bold text-white shadow-sm cursor-pointer transition";
      }}
      document.getElementById('filter-quarter').value = q;
      onTab1FilterChange();
    }}

    function onTab1FilterChange() {{
      const year = document.getElementById('filter-year').value;
      const q = document.getElementById('filter-quarter').value;
      
      let filteredTimeline = API_DATA.timeline;
      if (year !== 'ALL') {{
        filteredTimeline = filteredTimeline.filter(r => String(r.year) === year);
      }}
      if (q !== 'ALL') {{
        filteredTimeline = filteredTimeline.filter(r => r.quarter_key === q);
      }}
      
      if (filteredTimeline.length > 0) {{
        const latest = filteredTimeline[filteredTimeline.length - 1];
        document.getElementById('kpi-emp').innerText = latest.employment_rate.toFixed(2) + '%';
        document.getElementById('kpi-wage').innerText = '฿' + Math.round(latest.avg_wage).toLocaleString();
        if (year !== 'ALL') {{
          document.getElementById('period-badge').innerText = 'พ.ศ. ' + year;
        }} else {{
          document.getElementById('period-badge').innerText = '2561-2568';
        }}
        updateMainChartData(filteredTimeline);
      }}
    }}

    // Tab 2 Dynamic Target Group Engine
    function onTargetGroupFilterChange() {{
      updateTargetGroupAnalysis();
    }}

    function updateTargetGroupAnalysis() {{
      const yearVal = document.getElementById('t2-year').value;
      const regVal = document.getElementById('t2-region').value;
      const areaVal = document.getElementById('t2-area').value;
      const sexVal = document.getElementById('t2-sex').value;
      const ageVal = document.getElementById('t2-age').value;
      const eduVal = document.getElementById('t2-edu').value;
      const indVal = document.getElementById('t2-ind').value;

      const vocab = API_DATA.vocab;
      
      // Filter rows
      let filtered = API_DATA.rows;
      if (yearVal !== 'ALL') {{
        const idx = vocab.year.indexOf(yearVal);
        if (idx !== -1) filtered = filtered.filter(r => r[0] === idx);
      }}
      if (regVal !== 'ALL') {{
        const idx = vocab.region.indexOf(regVal);
        if (idx !== -1) filtered = filtered.filter(r => r[2] === idx);
      }}
      if (areaVal !== 'ALL') {{
        const idx = vocab.area.indexOf(areaVal);
        if (idx !== -1) filtered = filtered.filter(r => r[3] === idx);
      }}
      if (sexVal !== 'ALL') {{
        const idx = vocab.sex.indexOf(sexVal);
        if (idx !== -1) filtered = filtered.filter(r => r[4] === idx);
      }}
      if (ageVal !== 'ALL') {{
        const idx = vocab.age_group.indexOf(ageVal);
        if (idx !== -1) filtered = filtered.filter(r => r[5] === idx);
      }}
      if (eduVal !== 'ALL') {{
        const idx = vocab.education.indexOf(eduVal);
        if (idx !== -1) filtered = filtered.filter(r => r[6] === idx);
      }}
      if (indVal !== 'ALL') {{
        const idx = vocab.industry.indexOf(indVal);
        if (idx !== -1) filtered = filtered.filter(r => r[7] === idx);
      }}

      // Calculate aggregated means
      let targetEmp = API_DATA.national_benchmark.employment_rate;
      let targetWage = API_DATA.national_benchmark.avg_wage;

      if (filtered.length > 0) {{
        let sumEmp = 0, sumWage = 0;
        for (let i = 0; i < filtered.length; i++) {{
          sumEmp += filtered[i][8];
          sumWage += filtered[i][9];
        }}
        targetEmp = sumEmp / filtered.length;
        targetWage = sumWage / filtered.length;
      }}

      // Update UI elements
      const natEmp = API_DATA.national_benchmark.employment_rate;
      const natWage = API_DATA.national_benchmark.avg_wage;

      const empDiff = targetEmp - natEmp;
      const wageDiff = targetWage - natWage;
      const wagePctDiff = ((targetWage - natWage) / natWage) * 100;

      document.getElementById('target-emp-val').innerText = targetEmp.toFixed(1) + '%';
      document.getElementById('target-wage-val').innerText = '฿' + Math.round(targetWage).toLocaleString();

      const empDiffEl = document.getElementById('target-emp-diff');
      empDiffEl.innerText = (empDiff >= 0 ? '+' : '') + empDiff.toFixed(1) + '% pt';
      empDiffEl.className = empDiff >= 0 ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium';

      const wageDiffEl = document.getElementById('target-wage-diff');
      wageDiffEl.innerText = (wageDiff >= 0 ? '+' : '') + '฿' + Math.round(wageDiff).toLocaleString() + ' (' + (wagePctDiff >= 0 ? '+' : '') + wagePctDiff.toFixed(1) + '%)';
      wageDiffEl.className = wageDiff >= 0 ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium';

      // Width bars
      document.getElementById('target-emp-bar').style.width = Math.min(100, Math.max(10, targetEmp)) + '%';
      document.getElementById('target-wage-bar').style.width = Math.min(100, Math.max(10, (targetWage / 30000) * 100)) + '%';

      // Title & badges
      let desc = [];
      if (eduVal !== 'ALL') desc.push(eduVal);
      if (regVal !== 'ALL') desc.push(regVal);
      if (ageVal !== 'ALL') desc.push(ageVal);
      if (sexVal !== 'ALL') desc.push(sexVal);
      if (indVal !== 'ALL') desc.push(indVal);
      if (desc.length === 0) desc.push('ทุกกลุ่มประชากร (ภาพรวม)');
      document.getElementById('target-group-name').innerText = desc.join(' · ');

      const badge = document.getElementById('target-risk-badge');
      const diag = document.getElementById('target-diag-text');

      if (targetEmp >= natEmp && targetWage < natWage) {{
        badge.innerText = '⚠️ เสี่ยง In-work Poverty';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-red-100 text-red-700';
        diag.className = 'p-2.5 rounded-xl bg-red-50 text-[11px] text-red-800 mt-2 border border-red-200';
        diag.innerHTML = '<b>ภาวะ In-work Poverty:</b> กลุ่มนี้มีอัตราการมีงานทำสูง แต่มักอยู่ในงานทักษะต่ำ ทำให้ค่าจ้างต่ำกว่าเกณฑ์เฉลี่ย';
      }} else if (targetEmp < natEmp && targetWage < natWage) {{
        badge.innerText = '🚨 กลุ่มเปราะบาง';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800';
        diag.className = 'p-2.5 rounded-xl bg-amber-50 text-[11px] text-amber-800 mt-2 border border-amber-200';
        diag.innerHTML = '<b>กลุ่มเปราะบางสองด้าน:</b> ทั้งหางานยากและได้รับค่าจ้างต่ำ จำเป็นต้องได้รับความคุ้มครองทางสังคม';
      }} else if (targetWage >= natWage) {{
        badge.innerText = '⭐ มั่นคง / ทักษะสูง';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800';
        diag.className = 'p-2.5 rounded-xl bg-emerald-50 text-[11px] text-emerald-800 mt-2 border border-emerald-200';
        diag.innerHTML = '<b>กลุ่มทักษะสูง:</b> ค่าจ้างสูงกว่าเกณฑ์เฉลี่ยประเทศ เป็นกลุ่มกำลังหลักในการขับเคลื่อนเศรษฐกิจมูลค่าสูง';
      }} else {{
        badge.innerText = 'กลุ่มมาตรฐาน';
        badge.className = 'text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800';
        diag.className = 'p-2.5 rounded-xl bg-blue-50 text-[11px] text-blue-800 mt-2 border border-blue-200';
        diag.innerHTML = '<b>เกณฑ์ปกติ:</b> ตัวชี้วัดใกล้เคียงกับภาพรวมของตลาดแรงงานไทย';
      }}
    }}

    function onQuickSearch(val) {{
      val = val.trim().toLowerCase();
      if (!val) return;
      if (val.includes('กทม') || val.includes('กรุงเทพ')) {{
        document.getElementById('t2-region').value = 'กรุงเทพมหานคร';
        switchTab('tab2');
        updateTargetGroupAnalysis();
      }} else if (val.includes('อีสาน') || val.includes('ตะวันออกเฉียงเหนือ')) {{
        document.getElementById('t2-region').value = 'ภาคตะวันออกเฉียงเหนือ';
        switchTab('tab2');
        updateTargetGroupAnalysis();
      }} else if (val.includes('ประถม')) {{
        document.getElementById('t2-edu').value = 'ประถมศึกษา';
        switchTab('tab2');
        updateTargetGroupAnalysis();
      }} else if (val.includes('อุดม') || val.includes('ปริญญา')) {{
        document.getElementById('t2-edu').value = 'อุดมศึกษา สายวิชาการ';
        switchTab('tab2');
        updateTargetGroupAnalysis();
      }}
    }}

    // Sparklines for top cards
    function initSparklines() {{
      new Chart(document.getElementById('sparkline-emp'), {{
        type: 'line',
        data: {{
          labels: [1, 2, 3, 4, 5, 6, 7],
          datasets: [{{
            data: [66.5, 67.2, 66.8, 67.9, 67.4, 68.2, 67.5],
            borderColor: '#E83C91',
            borderWidth: 2.5,
            tension: 0.45,
            pointRadius: [0, 0, 0, 0, 0, 5, 0],
            pointBackgroundColor: '#E83C91',
            fill: false
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: false }} }},
          scales: {{ x: {{ display: false }}, y: {{ display: false }} }}
        }}
      }});

      new Chart(document.getElementById('sparkline-wage'), {{
        type: 'line',
        data: {{
          labels: [1, 2, 3, 4, 5, 6, 7],
          datasets: [{{
            data: [14200, 14500, 14800, 14600, 15100, 15300, 15341],
            borderColor: '#43334C',
            borderWidth: 2.2,
            tension: 0.2,
            pointRadius: 3,
            pointBackgroundColor: '#43334C',
            fill: false
          }}]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: false }} }},
          scales: {{ x: {{ display: false }}, y: {{ display: false }} }}
        }}
      }});

      new Chart(document.getElementById('mini-wave-1'), {{
        type: 'line',
        data: {{
          labels: [1,2,3,4,5],
          datasets: [{{ data: [68, 69.2, 68.8, 69.8, 69.47], borderColor: '#F7B731', borderWidth: 2, tension: 0.4, pointRadius: 0, fill: false }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ display: false }}, y: {{ display: false }} }} }}
      }});

      new Chart(document.getElementById('mini-wave-2'), {{
        type: 'line',
        data: {{
          labels: [1,2,3,4,5],
          datasets: [{{ data: [24000, 25200, 26000, 26800, 26913], borderColor: '#E83C91', borderWidth: 2, tension: 0.4, pointRadius: 0, fill: false }}]
        }},
        options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ legend: {{ display: false }} }}, scales: {{ x: {{ display: false }}, y: {{ display: false }} }} }}
      }});
    }}

    // Main Large Spline Chart (Graph 1 & 2)
    function initMainSplineChart() {{
      const ctx = document.getElementById('main-spline-chart').getContext('2d');
      const labels = API_DATA.timeline.map(r => r.year + ' ' + r.quarter_key);
      const empData = API_DATA.timeline.map(r => r.employment_rate);
      const wageData = API_DATA.timeline.map(r => r.avg_wage);

      mainSplineChartInstance = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [
            {{
              label: 'ค่าจ้างเฉลี่ย (บาท/เดือน)',
              data: wageData,
              borderColor: '#43334C',
              backgroundColor: 'rgba(67, 51, 76, 0.08)',
              borderWidth: 3,
              tension: 0.45,
              fill: true,
              yAxisID: 'y',
              pointRadius: 2.5,
              pointHoverRadius: 6,
              pointBackgroundColor: '#43334C'
            }},
            {{
              label: 'อัตราการมีงานทำ (%)',
              data: empData,
              borderColor: '#E83C91',
              backgroundColor: 'rgba(232, 60, 145, 0.08)',
              borderWidth: 3,
              tension: 0.45,
              fill: true,
              yAxisID: 'y1',
              pointRadius: 2.5,
              pointHoverRadius: 6,
              pointBackgroundColor: '#E83C91'
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          interaction: {{ mode: 'index', intersect: false }},
          plugins: {{
            legend: {{ position: 'top', labels: {{ font: {{ family: 'Kanit', size: 12 }} }} }}
          }},
          scales: {{
            x: {{ grid: {{ display: false }}, ticks: {{ maxTicksLimit: 12, font: {{ family: 'Kanit' }} }} }},
            y: {{
              type: 'linear', display: true, position: 'left',
              title: {{ display: true, text: 'ค่าจ้างเฉลี่ย (บาท)', font: {{ family: 'Kanit' }} }},
              grid: {{ color: 'rgba(67, 51, 76, 0.05)' }}
            }},
            y1: {{
              type: 'linear', display: true, position: 'right',
              title: {{ display: true, text: 'การมีงานทำ (%)', font: {{ family: 'Kanit' }} }},
              grid: {{ drawOnChartArea: false }},
              min: 60, max: 75
            }}
          }}
        }}
      }});
    }}

    function updateMainChartData(data) {{
      if (!mainSplineChartInstance) return;
      mainSplineChartInstance.data.labels = data.map(r => r.year + ' ' + r.quarter_key);
      mainSplineChartInstance.data.datasets[0].data = data.map(r => r.avg_wage);
      mainSplineChartInstance.data.datasets[1].data = data.map(r => r.employment_rate);
      mainSplineChartInstance.update();
    }}

    // Graph 4: Regional Ranking Horizontal Bar Chart
    function initRegionRankingChart() {{
      const ctx = document.getElementById('region-ranking-chart').getContext('2d');
      const labels = API_DATA.regions.map(r => r.region);
      const data = API_DATA.regions.map(r => r.employment_rate);

      regionRankingChartInstance = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [{{
            label: 'อัตราการมีงานทำ (%)',
            data: data,
            backgroundColor: ['#E83C91', '#43334C', '#FF8FB7', '#6E5D77', '#A79BAE'],
            borderRadius: 8,
            borderSkipped: false
          }}]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ min: 50, max: 80, ticks: {{ font: {{ family: 'Kanit' }} }} }},
            y: {{ ticks: {{ font: {{ family: 'Kanit' }} }} }}
          }}
        }}
      }});
    }}

    // Graph 5: Butterfly Chart for Education
    function initButterflyChart() {{
      const ctx = document.getElementById('butterfly-chart').getContext('2d');
      const labels = API_DATA.education.map(r => r.education);
      const empData = API_DATA.education.map(r => -r.employment_rate);
      const wageData = API_DATA.education.map(r => r.avg_wage);

      butterflyChartInstance = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [
            {{
              label: 'อัตรามีงานทำ (%)',
              data: empData,
              backgroundColor: '#FF8FB7',
              borderRadius: 6,
              xAxisID: 'x-emp'
            }},
            {{
              label: 'ค่าจ้างเฉลี่ย (บาท)',
              data: wageData,
              backgroundColor: '#43334C',
              borderRadius: 6,
              xAxisID: 'x-wage'
            }}
          ]
        }},
        options: {{
          indexAxis: 'y',
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{
            legend: {{ position: 'top', labels: {{ font: {{ family: 'Kanit' }} }} }},
            tooltip: {{
              callbacks: {{
                label: function(c) {{
                  let val = c.raw;
                  if (c.datasetIndex === 0) return ' มีงานทำ: ' + Math.abs(val) + '%';
                  return ' ค่าจ้างเฉลี่ย: ฿' + val.toLocaleString();
                }}
              }}
            }}
          }},
          scales: {{
            'x-emp': {{
              position: 'bottom',
              min: -100, max: 0,
              ticks: {{ callback: v => Math.abs(v) + '%', font: {{ family: 'Kanit' }} }}
            }},
            'x-wage': {{
              position: 'top',
              min: 0, max: 32000,
              ticks: {{ callback: v => '฿' + (v/1000) + 'k', font: {{ family: 'Kanit' }} }}
            }},
            y: {{ ticks: {{ font: {{ family: 'Kanit', size: 10 }} }} }}
          }}
        }}
      }});
    }}

    // Graph 6: Gender Wage Gap by Age Brackets
    function initGenderAgeChart() {{
      const ctx = document.getElementById('gender-age-chart').getContext('2d');
      const labels = API_DATA.age_gender.map(r => r.age_group);
      const maleData = API_DATA.age_gender.map(r => r['ชาย']);
      const femaleData = API_DATA.age_gender.map(r => r['หญิง']);

      genderAgeChartInstance = new Chart(ctx, {{
        type: 'bar',
        data: {{
          labels: labels,
          datasets: [
            {{
              label: 'ชาย',
              data: maleData,
              backgroundColor: '#43334C',
              borderRadius: 6
            }},
            {{
              label: 'หญิง',
              data: femaleData,
              backgroundColor: '#E83C91',
              borderRadius: 6
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          plugins: {{ legend: {{ display: false }} }},
          scales: {{
            x: {{ ticks: {{ font: {{ family: 'Kanit', size: 10 }} }} }},
            y: {{ ticks: {{ callback: v => '฿' + (v/1000) + 'k', font: {{ family: 'Kanit' }} }} }}
          }}
        }}
      }});
    }}

    // Graph 8: Cohort Historical Trend
    function initCohortChart(cohortName) {{
      const ctx = document.getElementById('cohort-chart').getContext('2d');
      const data = API_DATA.cohorts[cohortName] || API_DATA.cohorts['อุดมศึกษา สายวิชาการ'];
      const labels = data.map(r => r.year + ' ' + r.quarter_key);
      const wageData = data.map(r => r.avg_wage);
      const empData = data.map(r => r.employment_rate);

      if (cohortChartInstance) {{
        cohortChartInstance.destroy();
      }}

      cohortChartInstance = new Chart(ctx, {{
        type: 'line',
        data: {{
          labels: labels,
          datasets: [
            {{
              label: 'ค่าจ้างเฉลี่ย (บาท)',
              data: wageData,
              borderColor: '#E83C91',
              backgroundColor: 'rgba(232, 60, 145, 0.08)',
              borderWidth: 3,
              tension: 0.45,
              fill: true,
              yAxisID: 'y',
              pointRadius: 2.5
            }},
            {{
              label: 'อัตรามีงานทำ (%)',
              data: empData,
              borderColor: '#43334C',
              borderWidth: 2.5,
              borderDash: [5, 5],
              tension: 0.4,
              fill: false,
              yAxisID: 'y1',
              pointRadius: 2.5
            }}
          ]
        }},
        options: {{
          responsive: true,
          maintainAspectRatio: false,
          scales: {{
            x: {{ ticks: {{ maxTicksLimit: 10, font: {{ family: 'Kanit' }} }} }},
            y: {{ title: {{ display: true, text: 'ค่าจ้าง (บาท)' }}, ticks: {{ font: {{ family: 'Kanit' }} }} }},
            y1: {{ position: 'right', grid: {{ display: false }}, title: {{ display: true, text: 'มีงานทำ (%)' }}, ticks: {{ font: {{ family: 'Kanit' }} }} }}
          }}
        }}
      }});
    }}

    function onCohortChange() {{
      const select = document.getElementById('cohort-select');
      initCohortChart(select.value);
    }}
  </script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_template)

print(f"Generated {OUT_HTML} successfully! File size: {OUT_HTML.stat().st_size} bytes")

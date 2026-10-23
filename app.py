from pathlib import Path
import re
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# THAILAND LABOR MARKET DASHBOARD
# อ่านไฟล์ข้อมูลเดิมเท่านั้น ไม่สร้างชุดข้อมูลใหม่
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "processed" / "labor_market_merged.csv"
GEOJSON_FILE = BASE_DIR / "data" / "processed" / "thailand_regions.geojson"

# Theme ตาม PDF
BG = "#F8F4EC"
PINK = "#FF8FB7"
MAGENTA = "#E83C91"
PURPLE = "#43334C"
MUTED = "#746B78"

st.set_page_config(
    page_title="Thailand Labor Market Dashboard",
    page_icon="📊",
    layout="wide"
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"],
[data-testid="stAppViewContainer"] {{
    font-family: 'Kanit', sans-serif;
}}

.stApp {{
    background: {BG};
}}

[data-testid="stSidebar"] {{
    background: {PURPLE};
}}

[data-testid="stSidebar"] * {{
    color: #FFF9FC;
}}

[data-testid="stSidebar"] [data-baseweb="select"] * {{
    color: {PURPLE};
}}

.block-container {{
    padding-top: 1.4rem;
    max-width: 1500px;
}}

h1, h2, h3 {{
    color: {PURPLE};
}}

[data-testid="stMetric"] {{
    background: #FFFFFF;
    border: 1px solid #F0DDE6;
    padding: 16px;
    border-radius: 16px;
}}

[data-testid="stPlotlyChart"] {{
    background: #FFFFFF;
    border: 1px solid #F0DDE6;
    border-radius: 16px;
    padding: 8px;
}}

.hero {{
    background: linear-gradient(115deg, {PURPLE}, {MAGENTA});
    padding: 26px 30px;
    border-radius: 22px;
    color: white;
    margin-bottom: 18px;
}}

.hero h1 {{
    color: white;
    font-size: 2.1rem;
    margin: 0;
}}

.hero p {{
    color: #FFF5FA;
    margin-top: 6px;
}}

</style>
""", unsafe_allow_html=True)


# ============================================================
# 1. COLUMN MAPPING
# รองรับชื่อคอลัมน์ที่พบบ่อยทั้งภาษาอังกฤษและภาษาไทย
# ============================================================

ALIASES = {
    "year": [
        "year", "year_be", "ปี", "ปีพ.ศ.", "พ.ศ.", "ปีที่"
    ],
    "quarter": [
        "quarter_key", "quarter", "ไตรมาส",
        "ไตรมาสที่", "quarter_name", "qtr"
    ],
    "employment": [
        "employment_rate", "employment_rate_pct",
        "employment", "emp_rate",
        "อัตราการมีงานทำ", "อัตราการมีงานทำร้อยละ"
    ],
    "wage": [
        "avg_wage", "avg_wage_baht_month",
        "average_wage", "wage",
        "ค่าจ้างเฉลี่ย", "ค่าจ้างเฉลี่ยบาทต่อเดือน"
    ],
    "region": [
        "region", "region_name", "ภูมิภาค", "ภาค"
    ],
    "area": [
        "area", "area_type", "urban_rural",
        "พื้นที่", "ประเภทพื้นที่"
    ],
    "sex": [
        "sex", "gender", "เพศ"
    ],
    "age_group": [
        "age_group", "age_band", "age",
        "กลุ่มอายุ", "อายุ"
    ],
    "education": [
        "education", "education_level", "edu_level",
        "ระดับการศึกษา", "วุฒิการศึกษา"
    ],
    "industry": [
        "industry", "industry_name", "industry_group",
        "ประเภทอุตสาหกรรม", "หมวดอุตสาหกรรม"
    ]
}

DIMENSIONS = [
    "region",
    "area",
    "sex",
    "age_group",
    "education",
    "industry"
]

DIM_LABELS = {
    "region": "ภูมิภาค",
    "area": "พื้นที่",
    "sex": "เพศ",
    "age_group": "กลุ่มอายุ",
    "education": "ระดับการศึกษา",
    "industry": "ประเภทอุตสาหกรรม"
}


def norm_key(value):
    """ปรับชื่อคอลัมน์เพื่อช่วยจับคู่ชื่อไทย/อังกฤษ"""
    return re.sub(r"[^a-z0-9ก-๙]", "", str(value).lower())


def find_column(columns, aliases):
    normalized = {norm_key(c): c for c in columns}

    # ค้นหาชื่อที่ตรงกันก่อน
    for alias in aliases:
        key = norm_key(alias)

        if key in normalized:
            return normalized[key]

    # รองรับชื่อที่มี prefix/suffix
    for alias in aliases:
        key = norm_key(alias)

        matches = [
            c for c in columns
            if key and key in norm_key(c)
        ]

        if len(matches) == 1:
            return matches[0]

    return None


def quarter_number(value):
    """อ่านค่าไตรมาส เช่น Q1, ไตรมาส 1 หรือ 2561-Q1"""
    text = str(value).strip().upper()

    match = re.search(
        r"(?:Q|ไตรมาส\s*)([1-4])",
        text,
        re.I
    )

    if match:
        return int(match.group(1))

    if re.fullmatch(r"\s*[1-4]\s*", text):
        return int(text)

    matches = re.findall(r"[1-4]", text)

    return int(matches[-1]) if matches else 0


def is_total(value):
    """ตรวจว่าค่าเป็นกลุ่มรวม ไม่ใช่กลุ่มย่อย"""
    s = str(value).strip().lower()

    return s in {
        "รวม", "ทั้งหมด", "ทุกกลุ่ม",
        "all", "total", "overall",
        "ทั้งประเทศ", "ทั่วประเทศ"
    }


def clean_category(series):
    return (
        series.astype("string")
        .str.strip()
        .replace({
            "": pd.NA,
            "nan": pd.NA,
            "None": pd.NA
        })
    )


# ============================================================
# 2. LOAD EXISTING DATA
# ============================================================

def load_data(path):
    raw = pd.read_csv(
        path,
        encoding="utf-8-sig",
        low_memory=False
    )

    raw.columns = [
        str(c).replace("\ufeff", "").strip()
        for c in raw.columns
    ]

    found = {
        key: find_column(raw.columns, aliases)
        for key, aliases in ALIASES.items()
    }

    required = [
        ("year", "ปี"),
        ("employment", "อัตราการมีงานทำ"),
        ("wage", "ค่าจ้างเฉลี่ย")
    ]

    missing = [
        label
        for key, label in required
        if found[key] is None
    ]

    if missing:
        raise ValueError(
            "ไม่พบคอลัมน์สำคัญ: "
            + ", ".join(missing)
            + "\nกรุณาตรวจชื่อคอลัมน์ใน CSV"
            + "\nคอลัมน์ที่พบ: "
            + ", ".join(map(str, raw.columns))
        )

    df = pd.DataFrame(index=raw.index)

    # ปี ค.ศ. จะเปลี่ยนเป็นปี พ.ศ.
    df["year_raw"] = pd.to_numeric(
        raw[found["year"]],
        errors="coerce"
    )

    df["year_be"] = df["year_raw"].apply(
        lambda y: y + 543
        if pd.notna(y) and y < 2400
        else y
    )

    df["year_be"] = pd.to_numeric(
        df["year_be"],
        errors="coerce"
    )

    df["employment"] = pd.to_numeric(
        raw[found["employment"]],
        errors="coerce"
    )

    df["wage"] = pd.to_numeric(
        raw[found["wage"]],
        errors="coerce"
    )

    q_col = found["quarter"]

    if q_col:
        df["quarter_num"] = raw[q_col].apply(quarter_number)
    else:
        df["quarter_num"] = 0

    has_quarter = bool(
        q_col and (df["quarter_num"] > 0).any()
    )

    if has_quarter:
        df["period_order"] = (
            df["year_be"] * 10 + df["quarter_num"]
        )

        df["period_label"] = df.apply(
            lambda r: (
                f"พ.ศ. {int(r['year_be'])} · "
                f"Q{int(r['quarter_num'])}"
            )
            if pd.notna(r["year_be"])
            and r["quarter_num"] > 0
            else "ไม่ระบุช่วงเวลา",
            axis=1
        )

    else:
        df["period_order"] = df["year_be"] * 10

        df["period_label"] = df["year_be"].apply(
            lambda y: (
                f"พ.ศ. {int(y)}"
                if pd.notna(y)
                else "ไม่ระบุปี"
            )
        )

    # มิติประชากร
    for dim in DIMENSIONS:
        col = found[dim]

        if col:
            df[dim] = clean_category(
                raw[col]
            ).fillna("ไม่ระบุ")
        else:
            # หากไฟล์ไม่มีมิตินี้ ให้แสดงว่าไม่มีการจำแนกกลุ่ม
            df[dim] = "รวม"

    df = df.dropna(subset=["year_be"])

    df = df[
        df["employment"].notna()
        | df["wage"].notna()
    ].copy()

    df["year_be"] = df["year_be"].astype(int)

    df["quarter_num"] = (
        pd.to_numeric(
            df["quarter_num"],
            errors="coerce"
        )
        .fillna(0)
        .astype(int)
    )

    return (
        df.sort_values("period_order").reset_index(drop=True),
        has_quarter,
        found,
        list(raw.columns)
    )


def filter_values(series):
    values = (
        series.dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    return sorted(
        values,
        key=lambda x: (not is_total(x), x)
    )


def aggregate_period(frame):
    """สรุปค่าเฉลี่ยแยกตามช่วงเวลาในมุมมองที่เลือก"""

    if frame.empty:
        return pd.DataFrame(
            columns=[
                "period_order", "period_label",
                "employment", "wage"
            ]
        )

    result = (
        frame.groupby(
            ["period_order", "period_label"],
            as_index=False
        )
        .agg(
            employment=("employment", "mean"),
            wage=("wage", "mean")
        )
        .sort_values("period_order")
    )

    return result


def chart_style(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=35, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Kanit, sans-serif",
            color=PURPLE,
            size=12
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            title_text=""
        ),
        hoverlabel=dict(
            font_family="Kanit",
            bgcolor=PURPLE,
            font_color="white"
        )
    )

    fig.update_xaxes(
        showgrid=False,
        linecolor="#E8DDE3"
    )

    fig.update_yaxes(
        gridcolor="#F0E5EB",
        zeroline=False
    )

    return fig


# ============================================================
# 3. REGION MAP HELPERS
# รองรับ GeoJSON หากมีไฟล์ขอบเขตภูมิภาคอยู่แล้ว
# ============================================================

def region_label(value):
    s = str(value).strip()
    compact = norm_key(s)

    if "กรุงเทพ" in s or compact in {
        "bkk", "bangkok", "กรุงเทพมหานคร"
    }:
        return "กทม."

    if (
        "ตะวันออกเฉียงเหนือ" in s
        or "อีสาน" in s
        or compact in {
            "northeast", "northeastern",
            "northeastregion", "isan"
        }
    ):
        return "ภาคตะวันออกเฉียงเหนือ"

    if "เหนือ" in s or compact in {
        "north", "northern",
        "northregion", "northernregion"
    }:
        return "ภาคเหนือ"

    if "ใต้" in s or compact in {
        "south", "southern",
        "southregion", "southernregion"
    }:
        return "ภาคใต้"

    if "กลาง" in s or compact in {
        "central", "centralregion"
    }:
        return "ภาคกลาง"

    return s


def make_region_map(region_summary):
    """
    หากมี GeoJSON ของภูมิภาคและชื่อพื้นที่ตรงกัน
    จะใช้ Choropleth จริง
    หากไม่มี จะแสดงจุดตามตำแหน่งภูมิภาคแทน
    """

    if GEOJSON_FILE.exists():
        try:
            geojson = json.loads(
                GEOJSON_FILE.read_text(encoding="utf-8")
            )

            features = geojson.get("features", [])

            prop_keys = (
                set().union(
                    *(
                        feature.get("properties", {}).keys()
                        for feature in features
                    )
                )
                if features else set()
            )

            target_labels = {
                norm_key(region_label(v))
                for v in region_summary["region_plot"]
            }

            for prop_key in prop_keys:
                lookup = {}

                for feature in features:
                    raw_value = feature.get(
                        "properties", {}
                    ).get(prop_key)

                    if raw_value is not None:
                        lookup[
                            norm_key(region_label(raw_value))
                        ] = raw_value

                matched = target_labels.intersection(
                    lookup.keys()
                )

                # ต้องจับคู่ได้อย่างน้อย 2 ภูมิภาค
                if len(matched) >= 2:
                    map_df = region_summary.copy()

                    map_df["geo_location"] = (
                        map_df["region_plot"].map(
                            lambda v: lookup.get(
                                norm_key(region_label(v))
                            )
                        )
                    )

                    map_df = map_df.dropna(
                        subset=["geo_location"]
                    )

                    fig = px.choropleth(
                        map_df,
                        geojson=geojson,
                        locations="geo_location",
                        featureidkey=f"properties.{prop_key}",
                        color="employment",
                        hover_name="region_plot",
                        hover_data={
                            "employment": ":.2f",
                            "wage": ":,.0f",
                            "geo_location": False
                        },
                        color_continuous_scale=[
                            PINK, MAGENTA, PURPLE
                        ],
                        labels={
                            "employment": "อัตราการมีงานทำ (%)",
                            "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"
                        }
                    )

                    fig.update_geos(
                        fitbounds="locations",
                        visible=False,
                        showcountries=True,
                        countrycolor="#C8B9C2",
                        bgcolor="rgba(0,0,0,0)"
                    )

                    fig.update_layout(
                        height=380,
                        margin=dict(l=0, r=0, t=10, b=0),
                        paper_bgcolor="rgba(0,0,0,0)",
                        font=dict(family="Kanit")
                    )

                    return fig, True

        except Exception:
            # ถ้าอ่าน GeoJSON หรือจับคู่ชื่อไม่ได้ จะใช้แผนที่จุดแทน
            pass

    coords = {
        "กทม.": (13.7563, 100.5018),
        "ภาคกลาง": (14.8, 100.6),
        "ภาคเหนือ": (18.8, 99.0),
        "ภาคใต้": (8.4, 99.7),
        "ภาคตะวันออกเฉียงเหนือ": (16.2, 103.0)
    }

    map_df = region_summary.copy()

    map_df["lat"] = map_df["region_plot"].map(
        lambda x: coords.get(x, (15, 101))[0]
    )

    map_df["lon"] = map_df["region_plot"].map(
        lambda x: coords.get(x, (15, 101))[1]
    )

    fig = px.scatter_geo(
        map_df,
        lat="lat",
        lon="lon",
        color="employment",
        size="employment",
        hover_name="region_plot",
        hover_data={
            "employment": ":.2f",
            "wage": ":,.0f",
            "lat": False,
            "lon": False
        },
        color_continuous_scale=[
            PINK, MAGENTA, PURPLE
        ],
        size_max=38,
        labels={
            "employment": "อัตราการมีงานทำ (%)",
            "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"
        }
    )

    fig.update_geos(
        scope="asia",
        fitbounds="locations",
        visible=False,
        showcountries=True,
        countrycolor="#C8B9C2",
        showland=True,
        landcolor="#EEE5E8",
        bgcolor="rgba(0,0,0,0)"
    )

    fig.update_layout(
        height=380,
        margin=dict(l=0, r=0, t=10, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Kanit")
    )

    return fig, False


def gender_label(value):
    s = str(value).strip().lower()

    if s in {"m", "male", "ชาย"}:
        return "ชาย"

    if s in {"f", "female", "หญิง"}:
        return "หญิง"

    if is_total(value):
        return "รวม"

    return str(value)


# ============================================================
# 4. LOAD DATA
# ============================================================

if not DATA_FILE.exists():
    st.error(
        f"ไม่พบไฟล์ข้อมูลเดิม: `{DATA_FILE}`\n\n"
        "โปรดวาง labor_market_merged.csv ไว้ใน "
        "`data/processed/` ภายในโฟลเดอร์โปรเจกต์"
    )
    st.stop()

try:
    data, HAS_QUARTER, FOUND_COLS, SOURCE_COLUMNS = load_data(
        DATA_FILE
    )
except Exception as exc:
    st.error(f"โหลดข้อมูลไม่สำเร็จ: {exc}")
    st.stop()

if data.empty:
    st.warning("ไฟล์ CSV ไม่มีข้อมูลที่ใช้วิเคราะห์ได้")
    st.stop()


# ============================================================
# 5. PAGE HEADER
# ============================================================

st.markdown("""
<div class="hero">
    <div style="font-size:.8rem;letter-spacing:.12em;color:#FFE0EF;">
        THAILAND · LABOR MARKET INSIGHTS
    </div>
    <h1>ตลาดแรงงานไทย</h1>
    <p>
        การมีงานทำ × ค่าจ้างเฉลี่ย · ภาพรวม แนวโน้ม
        และความแตกต่างระหว่างกลุ่มประชากร
    </p>
</div>
""", unsafe_allow_html=True)


# ============================================================
# 6. GLOBAL FILTERS
# ============================================================

with st.sidebar:
    st.markdown("### 🎨 โหมดการแสดงผล (Display)")
    view_mode = st.radio(
        "เลือกมุมมอง Dashboard:",
        options=[
            "✨ Ultra-Modern Bento Grid (ตามภาพต้นแบบ)",
            "📊 Native Streamlit (Plotly Interactive)"
        ],
        index=0
    )
    st.markdown("---")

if view_mode == "✨ Ultra-Modern Bento Grid (ตามภาพต้นแบบ)":
    html_path = BASE_DIR / "dashboard.html"
    if not html_path.exists():
        import subprocess
        subprocess.run(["python", str(BASE_DIR / "generate_modern_dashboard.py")])
    
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    st.markdown("""
        <style>
        .block-container {
            padding: 0.5rem 0.5rem 1rem 0.5rem !important;
            max-width: 100% !important;
        }
        header[data-testid="stHeader"] {
            background: transparent !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    st.components.v1.html(html_content, height=1450, scrolling=True)
    st.stop()

with st.sidebar:
    st.markdown("## ตัวกรองข้อมูล")
    st.caption("เลือกช่วงเวลาหรือกลุ่มประชากรที่ต้องการดู")

    years = sorted(
        data["year_be"].dropna().astype(int).unique().tolist()
    )

    if len(years) > 1:
        min_y, max_y = years[0], years[-1]

        default_min = max(min_y, 2561)
        default_max = min(max_y, 2568)

        if default_min > default_max:
            default_min, default_max = min_y, max_y

        year_range = st.slider(
            "ช่วงปี พ.ศ.",
            min_value=min_y,
            max_value=max_y,
            value=(default_min, default_max),
            step=1
        )

    else:
        year_range = (years[0], years[0])
        st.caption(f"ปีที่มีข้อมูล: พ.ศ. {years[0]}")

    if HAS_QUARTER:
        q_options = [
            q for q in [1, 2, 3, 4]
            if q in data["quarter_num"].unique()
        ]

        chosen_q = st.multiselect(
            "ไตรมาส",
            q_options,
            default=q_options,
            format_func=lambda q: f"Q{q}"
        )

    else:
        chosen_q = []
        st.caption("ไฟล์นี้เป็นข้อมูลรายปี")

    selected = {}

    for dim in DIMENSIONS:
        vals = filter_values(data[dim])

        selected[dim] = st.selectbox(
            DIM_LABELS[dim],
            ["ทั้งหมด"] + vals,
            index=0,
            key=f"filter_{dim}"
        )

    st.markdown("---")
    st.markdown("**แหล่งข้อมูลต้นทาง**")
    st.markdown(
        "[อัตราการมีงานทำ - data.go.th]"
        "(https://data.go.th/dataset/0706_02_0011)"
    )
    st.markdown(
        "[ค่าจ้างเฉลี่ยของลูกจ้าง - data.go.th]"
        "(https://data.go.th/dataset/0706_02_0019)"
    )


filtered = data[
    data["year_be"].between(
        year_range[0], year_range[1]
    )
].copy()

if HAS_QUARTER:
    filtered = filtered[
        filtered["quarter_num"].isin(chosen_q)
    ].copy()

for dim, value in selected.items():
    if value != "ทั้งหมด":
        filtered = filtered[
            filtered[dim].astype(str) == value
        ]

if filtered.empty:
    st.warning(
        "ไม่พบข้อมูลที่ตรงกับตัวกรอง "
        "กรุณาเปลี่ยนช่วงเวลาหรือเลือก 'ทั้งหมด' ในบางตัวกรอง"
    )
    st.stop()

st.caption(
    "หมายเหตุ: เมื่อเลือก 'ทั้งหมด' ในมิติที่มีหลายกลุ่ม "
    "ตัวเลขสรุปเป็นค่าเฉลี่ยของแถวที่ผ่านตัวกรอง "
    "ไม่ใช่ค่าเฉลี่ยถ่วงน้ำหนัก หากไม่มีจำนวนแรงงานสำหรับถ่วงน้ำหนัก"
)

tab1, tab2 = st.tabs([
    "📈 1. ภาพรวมตลาดแรงงานไทย",
    "🔎 2. วิเคราะห์ความแตกต่างและกลุ่มที่ควรสนใจ"
])


# ============================================================
# TAB 1: OVERVIEW
# ============================================================

with tab1:
    st.subheader("ภาพรวมตลาดแรงงาน")

    trend = aggregate_period(filtered)

    latest = trend.iloc[-1]
    previous = trend.iloc[-2] if len(trend) > 1 else None

    k1, k2, k3, k4 = st.columns(4)

    emp_delta = (
        f"{latest['employment'] - previous['employment']:+.2f} จุดเปอร์เซ็นต์"
        if previous is not None
        and pd.notna(latest["employment"])
        and pd.notna(previous["employment"])
        else None
    )

    wage_delta = (
        f"{latest['wage'] - previous['wage']:+,.0f} บาท/เดือน"
        if previous is not None
        and pd.notna(latest["wage"])
        and pd.notna(previous["wage"])
        else None
    )

    k1.metric(
        "อัตราการมีงานทำ",
        f"{latest['employment']:.2f}%"
        if pd.notna(latest["employment"]) else "ไม่มีข้อมูล",
        delta=emp_delta
    )

    k2.metric(
        "ค่าจ้างเฉลี่ย",
        f"฿{latest['wage']:,.0f}"
        if pd.notna(latest["wage"]) else "ไม่มีข้อมูล",
        delta=wage_delta
    )

    k3.metric("ช่วงเวลาที่แสดง", f"{len(trend):,} ช่วง")
    k4.metric("ข้อมูลล่าสุด", str(latest["period_label"]))

    c1, c2 = st.columns(2, gap="large")

    # 01 Employment trend
    with c1:
        st.markdown("**01 · แนวโน้มอัตราการมีงานทำ**")

        emp_data = trend.dropna(subset=["employment"])

        if not emp_data.empty:
            fig = px.line(
                emp_data,
                x="period_label",
                y="employment",
                markers=True,
                labels={
                    "period_label": "ช่วงเวลา",
                    "employment": "อัตราการมีงานทำ (%)"
                }
            )

            fig.update_traces(
                line=dict(color=MAGENTA, width=3),
                marker=dict(size=7),
                hovertemplate=(
                    "%{x}<br>"
                    "อัตราการมีงานทำ: %{y:.2f}%<extra></extra>"
                )
            )

            fig.update_xaxes(tickangle=-35)

            st.plotly_chart(
                chart_style(fig),
                use_container_width=True,
                config={"displayModeBar": False}
            )

        else:
            st.info("ไม่มีข้อมูลอัตราการมีงานทำในช่วงที่เลือก")

    # 02 Average wage trend
    with c2:
        st.markdown("**02 · แนวโน้มค่าจ้างเฉลี่ย**")

        wage_data = trend.dropna(subset=["wage"])

        if not wage_data.empty:
            fig = px.line(
                wage_data,
                x="period_label",
                y="wage",
                markers=True,
                labels={
                    "period_label": "ช่วงเวลา",
                    "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"
                }
            )

            fig.update_traces(
                line=dict(color=PURPLE, width=3),
                marker=dict(size=7),
                hovertemplate=(
                    "%{x}<br>"
                    "ค่าจ้างเฉลี่ย: ฿%{y:,.0f}<extra></extra>"
                )
            )

            fig.update_xaxes(tickangle=-35)
            fig.update_yaxes(tickprefix="฿")

            st.plotly_chart(
                chart_style(fig),
                use_container_width=True,
                config={"displayModeBar": False}
            )

        else:
            st.info("ไม่มีข้อมูลค่าจ้างในช่วงที่เลือก")

    # 03 & 04 Region comparison
    st.markdown("### 03 · เปรียบเทียบอัตราการมีงานทำรายภูมิภาค")

    region_data = filtered.copy()

    region_data["region_plot"] = (
        region_data["region"].map(region_label)
    )

    region_data = region_data[
        ~region_data["region"].map(is_total)
    ]

    region_summary = (
        region_data.groupby("region_plot", as_index=False)
        .agg(
            employment=("employment", "mean"),
            wage=("wage", "mean")
        )
        .dropna(subset=["employment"])
    )

    map_col, rank_col = st.columns([1.25, 1], gap="large")

    with map_col:
        st.markdown("**แผนที่ค่าตัวชี้วัดรายภูมิภาค**")

        if not region_summary.empty:
            fig, is_choropleth = make_region_map(region_summary)

            st.plotly_chart(
                fig,
                use_container_width=True,
                config={"displayModeBar": False}
            )

            if is_choropleth:
                st.caption(
                    "ใช้ GeoJSON ที่พบใน "
                    "data/processed/thailand_regions.geojson "
                    "เพื่อระบายสีขอบเขตภูมิภาค"
                )
            else:
                st.caption(
                    "แสดงจุดสีตามค่าของภูมิภาค หากต้องการ "
                    "Choropleth ที่ระบายขอบเขตจริง "
                    "ให้นำ GeoJSON ของภูมิภาคมาไว้ที่ "
                    "data/processed/thailand_regions.geojson"
                )

        else:
            st.info(
                "ไม่พบข้อมูลภูมิภาคที่แยกกลุ่มได้ "
                "กรุณาตั้งตัวกรองภูมิภาคเป็น 'ทั้งหมด' "
                "และตรวจสอบคอลัมน์ใน CSV"
            )

    with rank_col:
        st.markdown(
            "**04 · จัดอันดับภูมิภาคตามอัตราการมีงานทำ**"
        )

        if not region_summary.empty:
            rank = region_summary.sort_values(
                "employment",
                ascending=True
            )

            fig = px.bar(
                rank,
                x="employment",
                y="region_plot",
                orientation="h",
                text=rank["employment"].map(
                    lambda x: f"{x:.2f}%"
                ),
                labels={
                    "employment": "อัตราการมีงานทำ (%)",
                    "region_plot": "ภูมิภาค"
                }
            )

            fig.update_traces(
                marker_color=MAGENTA,
                textposition="outside",
                cliponaxis=False
            )

            fig.update_layout(
                height=380,
                xaxis_range=[
                    0,
                    max(float(rank["employment"].max()) * 1.18, 1)
                ]
            )

            st.plotly_chart(
                chart_style(fig, 380),
                use_container_width=True,
                config={"displayModeBar": False}
            )

        else:
            st.info("ไม่มีข้อมูลเพียงพอสำหรับจัดอันดับ")

    # Data table and CSV export (ดาวน์โหลดเฉพาะมุมมอง ไม่บันทึกชุดข้อมูลใหม่)
    with st.expander("📋 ดูข้อมูลหลังใช้ตัวกรอง / ดาวน์โหลด CSV"):

        display_cols = (
            ["year_be", "quarter_num", "period_label"]
            + DIMENSIONS
            + ["employment", "wage"]
        )

        display = filtered[display_cols].rename(
            columns={
                "year_be": "ปี พ.ศ.",
                "quarter_num": "ไตรมาส",
                "period_label": "ช่วงเวลา",
                "region": "ภูมิภาค",
                "area": "พื้นที่",
                "sex": "เพศ",
                "age_group": "กลุ่มอายุ",
                "education": "ระดับการศึกษา",
                "industry": "ประเภทอุตสาหกรรม",
                "employment": "อัตราการมีงานทำ (%)",
                "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"
            }
        )

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True
        )

        st.download_button(
            "⬇ ดาวน์โหลดมุมมองนี้เป็น CSV",
            display.to_csv(index=False).encode("utf-8-sig"),
            file_name="labor_market_view.csv",
            mime="text/csv"
        )


# ============================================================
# TAB 2: DIFFERENCES AND TARGET GROUPS
# ============================================================

with tab2:
    st.subheader(
        "วิเคราะห์ความแตกต่างและกลุ่มที่ควรสนใจ"
    )

    st.caption(
        "ใช้การวิเคราะห์เชิงสำรวจเพื่อเลือกประเด็นศึกษาต่อ "
        "ไม่ใช่หลักฐานยืนยันเหตุและผล"
    )

    # --------------------------------------------------------
    # 05 Butterfly chart by education
    # --------------------------------------------------------

    st.markdown(
        "### 05 · การมีงานทำและค่าจ้างตามระดับการศึกษา"
    )

    edu_data = filtered[
        ~filtered["education"].map(is_total)
    ].copy()

    edu_summary = (
        edu_data.groupby("education", as_index=False)
        .agg(
            employment=("employment", "mean"),
            wage=("wage", "mean")
        )
        .dropna(subset=["employment", "wage"])
    )

    if not edu_summary.empty:
        edu_summary = edu_summary.sort_values(
            "employment",
            ascending=True
        )

        fig = go.Figure()

        # ฝั่งซ้าย: อัตราการมีงานทำ
        fig.add_trace(
            go.Bar(
                name="อัตราการมีงานทำ",
                y=edu_summary["education"],
                x=-edu_summary["employment"],
                orientation="h",
                marker_color=MAGENTA,
                customdata=edu_summary[["employment", "wage"]],
                xaxis="x",
                hovertemplate=(
                    "%{y}<br>"
                    "อัตราการมีงานทำ: "
                    "%{customdata[0]:.2f}%<extra></extra>"
                )
            )
        )

        # ฝั่งขวา: ค่าจ้าง
        fig.add_trace(
            go.Bar(
                name="ค่าจ้างเฉลี่ย",
                y=edu_summary["education"],
                x=edu_summary["wage"],
                orientation="h",
                marker_color=PURPLE,
                customdata=edu_summary[["employment", "wage"]],
                xaxis="x2",
                hovertemplate=(
                    "%{y}<br>"
                    "ค่าจ้างเฉลี่ย: "
                    "฿%{customdata[1]:,.0f}/เดือน<extra></extra>"
                )
            )
        )

        fig.update_layout(
            barmode="overlay",
            height=max(360, 44 * len(edu_summary)),
            margin=dict(l=10, r=10, t=35, b=15),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Kanit", color=PURPLE),
            legend=dict(
                orientation="h",
                y=1.08,
                x=0
            ),
            xaxis=dict(
                domain=[0, 0.46],
                range=[-100, 0],
                title="อัตราการมีงานทำ (%)",
                tickvals=[-100, -75, -50, -25, 0],
                ticktext=["100", "75", "50", "25", "0"],
                showgrid=False
            ),
            xaxis2=dict(
                domain=[0.56, 1],
                range=[
                    0,
                    max(float(edu_summary["wage"].max()) * 1.12, 1)
                ],
                title="ค่าจ้างเฉลี่ย (บาท/เดือน)",
                tickprefix="฿",
                anchor="y",
                showgrid=False
            ),
            yaxis=dict(
                title="",
                gridcolor="#F0E5EB"
            )
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            config={"displayModeBar": False}
        )

    else:
        st.info(
            "ยังสร้างกราฟระดับการศึกษาไม่ได้ "
            "ตรวจว่ามีคอลัมน์การศึกษาและเลือกตัวกรองเป็น 'ทั้งหมด'"
        )

    # --------------------------------------------------------
    # 06 Average wages by gender and age
    # --------------------------------------------------------

    st.markdown(
        "### 06 · เปรียบเทียบค่าจ้างชาย–หญิงตามกลุ่มอายุ"
    )

    gender_data = filtered.copy()

    gender_data["gender_plot"] = (
        gender_data["sex"].map(gender_label)
    )

    gender_data = gender_data[
        gender_data["gender_plot"].isin(["ชาย", "หญิง"])
        & ~gender_data["age_group"].map(is_total)
    ]

    gender_summary = (
        gender_data.groupby(
            ["age_group", "gender_plot"],
            as_index=False
        )
        .agg(wage=("wage", "mean"))
        .dropna(subset=["wage"])
    )

    if not gender_summary.empty:
        known_age_order = [
            "15-19 ปี", "15-19ปี",
            "20-24 ปี", "20-24ปี",
            "25-29 ปี", "25-29ปี",
            "30-34 ปี", "30-34ปี",
            "35-39 ปี", "35-39ปี",
            "40-49 ปี", "40-49ปี",
            "50-59 ปี", "50-59ปี",
            "60 ปีขึ้นไป", "60ปีขึ้นไป"
        ]

        present_ages = (
            gender_summary["age_group"]
            .astype(str)
            .unique()
            .tolist()
        )

        age_order = (
            [x for x in known_age_order if x in present_ages]
            + [x for x in present_ages if x not in known_age_order]
        )

        fig = px.bar(
            gender_summary,
            x="age_group",
            y="wage",
            color="gender_plot",
            barmode="group",
            category_orders={
                "age_group": age_order,
                "gender_plot": ["ชาย", "หญิง"]
            },
            color_discrete_map={
                "ชาย": MAGENTA,
                "หญิง": PURPLE
            },
            labels={
                "age_group": "กลุ่มอายุ",
                "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)",
                "gender_plot": "เพศ"
            },
            text_auto=".0f"
        )

        fig.update_yaxes(tickprefix="฿")
        fig.update_xaxes(tickangle=-25)

        st.plotly_chart(
            chart_style(fig, 390),
            use_container_width=True,
            config={"displayModeBar": False}
        )

        gap = (
            gender_summary.pivot(
                index="age_group",
                columns="gender_plot",
                values="wage"
            )
            .dropna()
        )

        if not gap.empty and {"ชาย", "หญิง"}.issubset(gap.columns):
            gap["ส่วนต่าง"] = (gap["ชาย"] - gap["หญิง"]).abs()

            biggest = gap["ส่วนต่าง"].idxmax()

            st.info(
                f"ช่วงอายุที่พบส่วนต่างค่าจ้างเฉลี่ยระหว่างชายและหญิงมากที่สุด: "
                f"{biggest} "
                f"(ส่วนต่างประมาณ "
                f"฿{gap.loc[biggest, 'ส่วนต่าง']:,.0f}/เดือน)"
            )

    else:
        st.info(
            "ไม่มีข้อมูลชายและหญิงให้เปรียบเทียบ "
            "กรุณาตั้งตัวกรองเพศเป็น 'ทั้งหมด' "
            "และตรวจสอบค่าหมวดเพศใน CSV"
        )

    # --------------------------------------------------------
    # 07 Comparison profiles / cards
    # --------------------------------------------------------

    st.markdown(
        "### 07 · ค้นหากลุ่มที่มีอัตราการมีงานทำสูง แต่ค่าจ้างต่ำ"
    )

    profile_dim = st.selectbox(
        "ใช้มิติใดในการเปรียบเทียบกลุ่มประชากร",
        DIMENSIONS,
        format_func=lambda x: DIM_LABELS[x],
        key="profile_dim"
    )

    profile_data = filtered[
        ~filtered[profile_dim].map(is_total)
    ].copy()

    profile = (
        profile_data.groupby(profile_dim, as_index=False)
        .agg(
            employment=("employment", "mean"),
            wage=("wage", "mean")
        )
        .dropna(subset=["employment", "wage"])
    )

    if not profile.empty:
        emp_med = profile["employment"].median()
        wage_med = profile["wage"].median()

        candidates = profile[
            (profile["employment"] >= emp_med)
            & (profile["wage"] <= wage_med)
        ].copy()

        candidates = candidates.sort_values(
            ["employment", "wage"],
            ascending=[False, True]
        )

        if not candidates.empty:
            chosen_group = candidates.iloc[0]
        else:
            chosen_group = profile.sort_values(
                ["employment", "wage"],
                ascending=[False, True]
            ).iloc[0]

        highest_emp = profile.loc[
            profile["employment"].idxmax()
        ]

        lowest_wage = profile.loc[
            profile["wage"].idxmin()
        ]

        a, b, c = st.columns(3)

        a.metric(
            "อัตราการมีงานทำสูงสุด",
            f"{highest_emp['employment']:.2f}%",
            str(highest_emp[profile_dim])
        )

        b.metric(
            "ค่าจ้างเฉลี่ยต่ำสุด",
            f"฿{lowest_wage['wage']:,.0f}",
            str(lowest_wage[profile_dim])
        )

        c.metric(
            "กลุ่มที่ควรพิจารณาต่อ",
            str(chosen_group[profile_dim]),
            f"งานทำ {chosen_group['employment']:.2f}% "
            f"· ฿{chosen_group['wage']:,.0f}/เดือน"
        )

        fig = px.scatter(
            profile,
            x="employment",
            y="wage",
            text=profile[profile_dim],
            labels={
                "employment": "อัตราการมีงานทำ (%)",
                "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"
            }
        )

        fig.update_traces(
            marker=dict(
                size=13,
                color=MAGENTA,
                line=dict(color="white", width=1)
            ),
            textposition="top center",
            hovertemplate=(
                "กลุ่ม: %{text}<br>"
                "อัตราการมีงานทำ: %{x:.2f}%<br>"
                "ค่าจ้าง: ฿%{y:,.0f}<extra></extra>"
            )
        )

        st.plotly_chart(
            chart_style(fig, 430),
            use_container_width=True,
            config={"displayModeBar": False}
        )

        st.caption(
            "เกณฑ์งานทำสูงแต่ค่าจ้างต่ำใช้ค่ามัธยฐานของกลุ่ม "
            "ในมุมมองที่เลือกเพื่อคัดกรองเบื้องต้น "
            "ไม่ใช่เกณฑ์นโยบายตายตัว"
        )

    else:
        st.info(
            "ไม่พบกลุ่มที่มีข้อมูลอัตราการมีงานทำและค่าจ้างพร้อมกัน"
        )

    # --------------------------------------------------------
    # 08 Historical trend for selected group
    # --------------------------------------------------------

    st.markdown("### 08 · แนวโน้มย้อนหลังของกลุ่มที่เลือก")

    trend_dim = st.selectbox(
        "มิติของกลุ่ม",
        DIMENSIONS,
        format_func=lambda x: DIM_LABELS[x],
        key="trend_dim"
    )

    trend_options = [
        v for v in filter_values(filtered[trend_dim])
        if not is_total(v)
    ]

    if trend_options:
        trend_value = st.selectbox(
            "เลือกกลุ่ม",
            trend_options,
            key="trend_value"
        )

        focus = filtered[
            filtered[trend_dim].astype(str) == trend_value
        ]

        focus_trend = aggregate_period(focus)

        if not focus_trend.empty:
            t1, t2 = st.columns(2)

            with t1:
                emp_focus = focus_trend.dropna(
                    subset=["employment"]
                )

                fig = px.line(
                    emp_focus,
                    x="period_label",
                    y="employment",
                    markers=True,
                    labels={
                        "period_label": "ช่วงเวลา",
                        "employment": "อัตราการมีงานทำ (%)"
                    }
                )

                fig.update_traces(
                    line=dict(color=MAGENTA, width=3)
                )
                fig.update_xaxes(tickangle=-35)

                st.plotly_chart(
                    chart_style(fig),
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

            with t2:
                wage_focus = focus_trend.dropna(
                    subset=["wage"]
                )

                fig = px.line(
                    wage_focus,
                    x="period_label",
                    y="wage",
                    markers=True,
                    labels={
                        "period_label": "ช่วงเวลา",
                        "wage": "ค่าจ้างเฉลี่ย (บาท/เดือน)"
                    }
                )

                fig.update_traces(
                    line=dict(color=PURPLE, width=3)
                )
                fig.update_xaxes(tickangle=-35)
                fig.update_yaxes(tickprefix="฿")

                st.plotly_chart(
                    chart_style(fig),
                    use_container_width=True,
                    config={"displayModeBar": False}
                )

        else:
            st.info("กลุ่มนี้ไม่มีข้อมูลแนวโน้มในช่วงเวลาที่เลือก")

    else:
        st.info(
            "ไม่มีหมวดกลุ่มย่อยให้เลือก "
            "กรุณาตั้งตัวกรองที่เกี่ยวข้องเป็น 'ทั้งหมด'"
        )


# ============================================================
# 9. DATA NOTES
# ============================================================

with st.expander("📌 นิยามและข้อจำกัดของข้อมูล"):
    st.markdown("""
- แหล่งข้อมูลต้นทางที่ระบุในโครงงานคือสำนักงานสถิติแห่งชาติ (NSO) ผ่าน data.go.th
- อัตราการมีงานทำและค่าจ้างเฉลี่ยอาจครอบคลุมประชากรคนละกลุ่ม โดยค่าจ้างเฉลี่ยเป็นข้อมูลของลูกจ้าง
- Dashboard ใช้เฉพาะแถวที่อยู่ใน CSV เดิมและตรงกับตัวกรอง ไม่ได้เติมค่าข้อมูลที่ไม่มีอยู่
- หากข้อมูลมีหลายแถวจากการจำแนกกลุ่ม ภาพรวมในโค้ดนี้ใช้ค่าเฉลี่ยอย่างง่าย ไม่ใช่ค่าเฉลี่ยถ่วงน้ำหนัก
- ผลที่เห็นเป็นแนวทางช่วยเลือกประเด็นศึกษาเพิ่มเติม ไม่ใช่ข้อพิสูจน์เหตุและผล
- หากไม่มี GeoJSON ของภูมิภาค แผนที่จะแสดงจุดตำแหน่งภูมิภาคแทนการระบายขอบเขตพื้นที่จริง
""")

st.markdown(
    f"""
    <div style="
        margin-top:24px;
        padding-top:12px;
        border-top:1px solid #E8DDE3;
        color:{MUTED};
        font-size:.8rem;">
        THAILAND LABOR MARKET DASHBOARD · Data Visualization Project
        · NSO / data.go.th
    </div>
    """,
    unsafe_allow_html=True
)
"""Central configuration: paths, thresholds and the registry of data sources.

Every source URL can be overridden without touching code, either with an
environment variable ``TUI_URL_<KEY>`` (KEY in upper case) or with a ``.env``
file in the project root (see ``.env.example``).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROCESSED = BASE_DIR / "data" / "processed"
LOG_DIR = BASE_DIR / "logs"
MANIFEST_PATH = DATA_RAW / "manifest.json"


def _load_dotenv(path: Path) -> None:
    """Tiny .env loader (KEY=VALUE lines). Existing environment wins."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(BASE_DIR / ".env")

# NSO's WAF rejects the default python-requests agent (HTTP 418). We identify
# ourselves honestly instead of impersonating a browser.
USER_AGENT = os.environ.get(
    "TUI_USER_AGENT",
    "ThailandUnemploymentDashboard/1.0 (research; public open data)",
)
HTTP_TIMEOUT = (10, 90)  # connect, read (seconds)
HTTP_RETRIES = 2

CKAN_BASE = os.environ.get("TUI_CKAN_BASE", "https://data.go.th/api/3/action")

# A cached download older than this is labelled "stale" in the UI.
STALE_AFTER_DAYS = int(os.environ.get("TUI_STALE_AFTER_DAYS", "7"))

# Reconciliation tolerance between independently published tables (relative).
RECONCILE_TOL = 0.01
# Published unemployment rates are rounded; allow this absolute gap (pp) when
# comparing a computed rate to a published one (one-decimal rounding = 0.05).
RATE_TOL_PP = 0.06

# Employment rate / average wage checks (data_processing/labour_market.py)
EMP_AGREE_TOL_PP = 0.05   # national employment rate published by 3 tables must agree within 0.05 percentage points
WAGE_AGREE_TOL = 0.01     # national average wage published by 3 tables must agree within 1 %
WAGE_JUMP_TOL = 0.10      # ... and may not jump more than 10 % from the median of its 5-quarter neighbourhood
JOINT_START_BE, JOINT_END_BE = 2561, 2568   # default window for the employment/wage page

BE_OFFSET = 543  # Buddhist Era -> Common Era
MIN_BE, MAX_BE = 2500, 2700


@dataclass(frozen=True)
class SourceSpec:
    key: str
    title: str
    org: str
    kind: str  # nso_csv | xlsx | sso_csv | bot_html
    url: str
    landing_url: str
    unit: str = ""
    frequency: str = ""
    role: str = ""
    required: bool = False
    encoding: str = "utf-8-sig"
    ckan_package: str | None = None
    resolve_via_ckan: str | None = None  # resource format to look up at refresh time
    notes: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def effective_url(self) -> str:
        return os.environ.get(f"TUI_URL_{self.key.upper()}", self.url)

    @property
    def extension(self) -> str:
        return {"nso_csv": ".csv", "sso_csv": ".csv", "xlsx": ".xlsx", "bot_html": ".html", "geojson": ".geojson"}[self.kind]


def _nso(table: str) -> str:
    return f"https://catalogapi.nso.go.th/api/index?table={table}&format=csv"


DG = "https://data.go.th/dataset/"

SOURCES: tuple[SourceSpec, ...] = (
    SourceSpec(
        key="nso_u_region", title="จำนวนผู้ว่างงาน จำแนกตามภาค และเขตการปกครอง (รายไตรมาส)",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0003_01"),
        landing_url=DG + "0706_02_0003", unit="พันคน", frequency="รายไตรมาส",
        role="ชุดหลัก: ยอดผู้ว่างงานรวมและรายภูมิภาค", required=True, ckan_package="0706_02_0003",
    ),
    SourceSpec(
        key="nso_u_cube", title="จำนวนผู้ว่างงาน จำแนกตามระยะเวลาที่หางานทำ ระดับการศึกษา เพศ ภาค",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0003_02"),
        landing_url=DG + "0706_02_0003", unit="พันคน", frequency="รายไตรมาส",
        role="ตารางข้ามมิติ (ภาค × เพศ × การศึกษา) สำหรับตัวกรองร่วม", ckan_package="0706_02_0003",
    ),
    SourceSpec(
        key="nso_u_edu", title="จำนวนผู้ว่างงาน จำแนกตามระดับการศึกษาที่สำเร็จ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20536_25"),
        landing_url=DG + "0706_02_0003", unit="พันคน", frequency="รายไตรมาส",
        role="ผู้ว่างงานรายระดับการศึกษา (ระดับประเทศ)", ckan_package="0706_02_0003",
    ),
    SourceSpec(
        key="nso_u_age_status", title="จำนวนผู้ว่างงาน จำแนกตามกลุ่มอายุ สถานภาพแรงงาน",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0003_04"),
        landing_url=DG + "0706_02_0003", unit="พันคน", frequency="รายไตรมาส",
        role="ผู้ว่างงานรายกลุ่มอายุ (ใช้ตรวจสอบยอดรวมข้ามตาราง)", ckan_package="0706_02_0003",
    ),
    SourceSpec(
        key="nso_u_province", title="ผู้ว่างงานและอัตราการว่างงาน รายจังหวัด เพศ (รายไตรมาส)",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("SFD_SPB0208"),
        landing_url=DG + "0706_02_0003", unit="คน / ร้อยละ", frequency="รายไตรมาส",
        role="ผู้ว่างงานรายเพศและรายจังหวัด", ckan_package="0706_02_0003",
    ),
    SourceSpec(
        key="nso_lf_region_area_sex", title="จำนวนกำลังแรงงานรวม จำแนกตามภาค เขตการปกครอง เพศ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0001_01"),
        landing_url=DG + "0706_02_0001", unit="พันคน", frequency="รายไตรมาส",
        role="ตัวหารของอัตราการว่างงาน (กำลังแรงงานรวม)", required=True, ckan_package="0706_02_0001",
    ),
    SourceSpec(
        key="nso_lf_region_sex", title="จำนวนกำลังแรงงานรวม จำแนกตามภาค และเพศ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20534_1"),
        landing_url=DG + "0706_02_0001", unit="พันคน", frequency="รายไตรมาส",
        role="ตัวหารสำรองสำหรับอัตราการว่างงานรายเพศ", ckan_package="0706_02_0001",
    ),
    SourceSpec(
        key="nso_emp_region_sex", title="จำนวนผู้มีงานทำ จำแนกตามภาค และเพศ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20535_1"),
        landing_url=DG + "0706_02_0002", unit="พันคน", frequency="รายไตรมาส",
        role="ใช้ตรวจสอบความสอดคล้องของตัวหาร", ckan_package="0706_02_0002",
    ),
    SourceSpec(
        key="nso_emp_region_sex_edu", title="จำนวนผู้มีงานทำ จำแนกตามภาค ระดับการศึกษา และเพศ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20535_10"),
        landing_url=DG + "0706_02_0002", unit="พันคน", frequency="รายไตรมาส",
        role="ตัวหารของอัตราการว่างงานรายระดับการศึกษา", ckan_package="0706_02_0002",
    ),
    SourceSpec(
        key="nso_rate_old", title="อัตราการว่างงาน จำแนกตามภาค เขตการปกครอง เพศ กลุ่มอายุ (2556–2568)",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0020_01"),
        landing_url=DG + "0706_02_0016", unit="ร้อยละ", frequency="รายไตรมาส",
        role="อัตราที่ สสช. เผยแพร่ ใช้ตรวจสอบอัตราที่คำนวณเอง", ckan_package="0706_02_0016",
    ),
    SourceSpec(
        key="nso_rate_new", title="อัตราการว่างงาน จำแนกตามภาค เพศ กลุ่มอายุ (2563–2569)",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20542_22"),
        landing_url=DG + "0706_02_0016", unit="ร้อยละ", frequency="รายไตรมาส",
        role="อัตราที่ สสช. เผยแพร่ (ล่าสุด) และอัตรารายกลุ่มอายุ", ckan_package="0706_02_0016",
    ),
    SourceSpec(
        key="nso_er_sex_age", title="อัตราการมีงานทำต่อประชากรวัยแรงงาน จำแนกตามภาค เขตการปกครอง เพศ กลุ่มอายุ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0016_03"),
        landing_url=DG + "0706_02_0011", unit="ร้อยละ", frequency="รายไตรมาส",
        role="อัตรามีงานทำ (ชุดหลัก: ประเทศ/ภาค/เพศ/อายุ)", ckan_package="0706_02_0011",
    ),
    SourceSpec(
        key="nso_er_edu", title="อัตราการมีงานทำต่อประชากรวัยแรงงาน จำแนกตามภาค เขตการปกครอง ระดับการศึกษา",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0016_02"),
        landing_url=DG + "0706_02_0011", unit="ร้อยละ", frequency="รายไตรมาส",
        role="อัตรามีงานทำรายการศึกษา และตรวจยอดรวมข้ามตาราง", ckan_package="0706_02_0011",
    ),
    SourceSpec(
        key="nso_er_region_sex", title="อัตราการมีงานทำต่อประชากรวัยแรงงาน จำแนกตามภาค และเพศ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20540"),
        landing_url=DG + "0706_02_0011", unit="ร้อยละ", frequency="รายไตรมาส",
        role="ตรวจยอดรวมข้ามตารางของอัตรามีงานทำ (2563+)", ckan_package="0706_02_0011",
    ),
    SourceSpec(
        key="nso_w_age", title="ค่าจ้างเฉลี่ยของลูกจ้าง จำแนกตามภาค เขตการปกครอง เพศ กลุ่มอายุ",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0024_01"),
        landing_url=DG + "0706_02_0019", unit="บาทต่อเดือน", frequency="รายไตรมาส",
        role="ค่าจ้างเฉลี่ย (ชุดหลัก: ประเทศ/ภาค/เพศ/อายุ)",
    ),
    SourceSpec(
        key="nso_w_edu", title="ค่าจ้างเฉลี่ยของลูกจ้าง จำแนกตามภาค เขตการปกครอง เพศ ระดับการศึกษา",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("OS_02_0024_02"),
        landing_url=DG + "0706_02_0019", unit="บาทต่อเดือน", frequency="รายไตรมาส",
        role="ค่าจ้างรายการศึกษา และตรวจยอดรวมข้ามตาราง",
    ),
    SourceSpec(
        key="nso_w_industry", title="ค่าจ้างเฉลี่ยของลูกจ้าง จำแนกตามภาค และหมวดอุตสาหกรรม",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("LFS_02_20545_18"),
        landing_url=DG + "0706_02_0019", unit="บาท (ต่อเดือน)", frequency="รายไตรมาส",
        role="ค่าจ้างรายอุตสาหกรรม และตรวจยอดรวมข้ามตาราง (2563+)",
    ),
    SourceSpec(
        key="nesdc_gdp", title="ผลิตภัณฑ์มวลรวมในประเทศรายไตรมาส ปริมาณลูกโซ่ (ด้านรายจ่าย)",
        org="สำนักงานสภาพัฒนาการเศรษฐกิจและสังคมแห่งชาติ (สศช.)", kind="xlsx",
        url="https://www.nesdc.go.th/wordpress/wp-content/uploads/2026/03/ChainVolumeMeasures.xlsx",
        landing_url=DG + "dataset_17_01", unit="ล้านบาท (CVM) / ร้อยละ YoY", frequency="รายไตรมาส",
        role="GDP Growth รายไตรมาส (YoY, ไม่ปรับฤดูกาล)", ckan_package="dataset_17_01",
        resolve_via_ckan="XLSX", encoding="",
    ),
    SourceSpec(
        key="sso_benefit", title="ผู้ใช้บริการสิทธิประโยชน์กรณีว่างงาน มาตรา 33 และ 39 จำแนกตามสาเหตุ",
        org="สำนักงานประกันสังคม", kind="sso_csv",
        url="https://catalog.sso.go.th/dataset/311698d3-cd1f-4c74-820e-48e0796d2547/resource/"
            "e8d1b8f4-8d5b-44ba-ae8e-e3a2d424da9f/download/-33-39-.csv",
        landing_url=DG + "unemployment-benefit", unit="กรณี (ครั้งที่ใช้สิทธิ)", frequency="รายปี",
        role="ตัวแทน (Proxy): เหตุผลการใช้สิทธิว่างงานของผู้ประกันตน", encoding="cp874",
        ckan_package="unemployment-benefit", resolve_via_ckan="CSV",
    ),
    SourceSpec(
        key="nso_province_region", title="กำลังแรงงานรายจังหวัด พร้อมภาคที่ สสช. กำหนดในแต่ละปี (ST_02_2005005_4)",
        org="สำนักงานสถิติแห่งชาติ (สสช.)", kind="nso_csv", url=_nso("ST_02_2005005_4"),
        landing_url=DG + "0706_02_0001", unit="พันคน", frequency="รายไตรมาส",
        role="นิยามจังหวัด→ภาคตามที่ สสช. ใช้จริงในแต่ละปี (สำหรับแผนที่ภูมิภาค)", ckan_package="0706_02_0001",
    ),
    SourceSpec(
        key="geo_provinces", title="ขอบเขตจังหวัดประเทศไทย 77 จังหวัด (geoBoundaries gbOpen THA ADM1)",
        org="geoBoundaries (geoLab, William & Mary) — ข้อมูลจาก OpenStreetMap", kind="geojson",
        url="https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/THA/ADM1/geoBoundaries-THA-ADM1_simplified.geojson",
        landing_url="https://www.geoboundaries.org/", unit="พิกัดภูมิศาสตร์", frequency="ชุดเดียว (ปีอ้างอิง 2560)",
        role="รูปร่างจังหวัดสำหรับแผนที่ภูมิภาค (สัญญาอนุญาต ODbL 1.0 ต้องอ้างอิงแหล่งที่มา)", encoding="utf-8",
        notes="Open Data Commons Open Database License 1.0",
    ),
    SourceSpec(
        key="bot_reasons", title="ผู้ว่างงานที่เคยทำงาน จำแนกตามเหตุผลที่ออกจากงาน (EC_RL_019)",
        org="ธนาคารแห่งประเทศไทย (ธปท.) — ที่มา: สสช.", kind="bot_html",
        url="https://app.bot.or.th/BTWS_STAT/statistics/BOTWEBSTAT.aspx?reportID=669&language=TH",
        landing_url="https://app.bot.or.th/BTWS_STAT/statistics/BOTWEBSTAT.aspx?reportID=669&language=TH",
        unit="พันคน", frequency="รายไตรมาส",
        role="หลักฐานโดยตรง: เหตุผลที่ผู้ว่างงานออกจากงานเดิม (ถึง Q4/2565)", encoding="utf-8",
        ckan_package="ds-834",
        extra={"from_year_ce": 2012, "to_year_ce": 2022},
    ),
)

SOURCES_BY_KEY = {s.key: s for s in SOURCES}

# Metadata-only look-ups on data.go.th (CKAN package_show) shown on the
# methodology page. The first one is the dataset named in the project brief.
CKAN_METADATA_PACKAGES = (
    "0706_02_0011",
    "0706_02_0019",
    "0706_02_0003",
    "0706_02_0016",
    "0706_02_0001",
    "0706_02_0002",
    "dataset_17_01",
    "unemployment-benefit",
    "ds-834",
)

# File received from a third party (not downloaded from a publisher): only its employed-persons column is used.
EXTERNAL_MASTER = BASE_DIR / "data" / "external" / "final_labor_master_data.csv"
HEADCOUNT_TOL = 0.01      # employed persons must match the NSO region x sex table within 1 %
HEADCOUNT_ABS_TOL = 0.5   # ... or 0.5 thousand persons

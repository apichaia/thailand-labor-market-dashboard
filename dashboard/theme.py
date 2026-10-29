"""Colours, fonts and CSS. The Kanit font is bundled in static/fonts (served by Streamlit, works offline); if those files are missing it loads
from Google Fonts, and system Thai fonts are the last fallback (the app never depends on any of them)."""
from pathlib import Path

_FONT_CSS = Path(__file__).resolve().parent.parent / "static" / "fonts" / "kanit.css"
_KANIT = _FONT_CSS.read_text(encoding="utf-8") if _FONT_CSS.exists() else "@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@400;600;700;800&display=swap');"

CREAM = "#F8F4EC"     # page background
PINK = "#FF8FB7"      # soft accent (tab underline, secondary series, key lines)
MAGENTA = "#E83C91"   # strong accent (selected chips, second series, links)
PLUM = "#43334C"      # text, top bar, primary series

PRIMARY = PLUM        # primary chart series
BLUE = MAGENTA        # links
MIDBLUE = PINK        # secondary series / dividers (legacy name)
ACCENT = MAGENTA      # second series (e.g. female)
ORANGE = PINK         # active tab underline
BAR = PLUM            # top bar
NAVBAR = "#54425F"    # tab bar: a lighter plum so it separates from the top bar
TEXT = PLUM
NAVY = PRIMARY
SLATE = MIDBLUE
TEAL = PRIMARY        # legacy name: first/primary series colour
BG = CREAM
WHITE = "#FFFFFF"
AMBER = "#E5A23B"     # warnings stay amber/red so they never read as data colours
RED = "#C94C4C"
MUTED = "#746B78"
BORDER = "#E8DFDA"
GRID_Y = "#EFE6E0"
GRID_X = "#F4EDE7"
SHADOW = "rgba(67,51,76,.10)"

FONT_STACK = "'Kanit','Sarabun','Noto Sans Thai','Leelawadee UI','Tahoma',sans-serif"

# categorical series colours: distinguishable without relying on hue alone
# (charts also vary dash/marker). Red is reserved for errors, amber for flags.
SERIES = [PLUM, MAGENTA, PINK, "#7B6B86", "#B9A3C0", "#A24A74", "#F2C1D3"]

CSS = f"""
<style>
{_KANIT}
html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {{ font-family: {FONT_STACK}; }}
.stApp {{ background: {BG}; color: {TEXT}; }}
.block-container {{ padding-top: 0.8rem; max-width: 1700px; }}
h1, h2, h3, h4 {{ color: {TEXT}; font-weight: 700; letter-spacing: 0; }}
header[data-testid="stHeader"] {{ background: transparent; }}
/* the filters live in the top bar now: no side panel */
/* sidebar holds the filters (see CSS_V2) */

/* ---- top bar ---- */
.st-key-topbar {{ background: {BAR}; border-radius: 12px 12px 0 0; padding: 14px 20px 12px 20px; }}
.tb-title {{ color:#fff; font-weight:800; font-size:1.5rem; line-height:1.3; }}
.tb-sub {{ color:#E9DDE6; font-size:.95rem; margin-top:2px; }}
.tui-meta {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }}
.chip {{ display:inline-flex; align-items:center; gap:6px; background: rgba(255,255,255,.10); border:1px solid rgba(255,255,255,.28);
  color:#fff; padding:4px 12px; border-radius:999px; font-size:.86rem; }}
.chip.ok::before {{ content:"✔"; color:#FF8FB7; }}
.chip.warn {{ background:{AMBER}; color:{TEXT}; border-color:{AMBER}; font-weight:600; }}
.chip.warn::before {{ content:"⚠"; }}
.chip.err {{ background:{RED}; border-color:{RED}; font-weight:600; }}
.chip.err::before {{ content:"✖"; }}
.st-key-bar_actions [data-testid="stHorizontalBlock"] {{ flex-wrap: nowrap !important; gap: 6px; }}
.st-key-bar_actions [data-testid="stColumn"] {{ min-width: 0 !important; flex: 1 1 0 !important; width: auto !important; }}
.st-key-topbar button {{ background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.35); border-radius: 10px; color:#fff; }}
.st-key-topbar button p {{ color:#fff !important; }}
.st-key-topbar button:hover {{ background: rgba(255,255,255,.2); border-color:#fff; }}
.st-key-topbar [data-testid="stExpander"] {{ border: 1px solid rgba(255,255,255,.28); border-radius: 10px; background: rgba(255,255,255,.05); margin-top: 6px; }}
.st-key-topbar [data-testid="stExpander"] details, .st-key-topbar [data-testid="stExpander"] summary {{ background: transparent !important; color:#fff; }}
.st-key-topbar [data-testid="stExpander"] summary:hover {{ background: rgba(255,255,255,.08) !important; }}
.st-key-topbar [data-testid="stExpander"] summary p, .st-key-topbar [data-testid="stExpander"] summary svg {{ color:#fff !important; fill:#fff; }}
.st-key-topbar label p, .st-key-topbar [data-testid="stCaptionContainer"] {{ color:#F3E6EE !important; }}
.st-key-topbar [data-baseweb="select"] *, .st-key-topbar input {{ color: {TEXT} !important; }}
.st-key-topbar [data-baseweb="tag"] {{ background: {ACCENT}; }}
.st-key-topbar [data-baseweb="tag"] * {{ color:#fff !important; }}

/* ---- numbered tab bar: white text, orange underline under the open page ---- */
.st-key-nav_page {{ background: {NAVBAR}; border-radius: 0 0 12px 12px; padding: 0 10px; margin: -0.7rem 0 0.2rem 0; width: 100% !important; box-sizing: border-box; }}
.st-key-nav_page [data-testid="stRadio"], .st-key-nav_page [role="radiogroup"] {{ width: 100%; }}
.st-key-nav_page [role="radiogroup"] {{ gap: 0; flex-wrap: wrap; }}
.st-key-nav_page label {{ background: transparent; border: none; border-bottom: 3px solid transparent; border-radius: 0; padding: 12px 16px 9px 16px; margin: 0; cursor: pointer; }}
.st-key-nav_page label > div:first-child {{ display: none; }}
.st-key-nav_page label p {{ color: #E7D9E3; font-weight: 600; }}
.st-key-nav_page label:hover p {{ color:#fff; }}
.st-key-nav_page label:has(input:checked) {{ border-bottom-color: {ORANGE}; }}
.st-key-nav_page label:has(input:checked) p {{ color:#fff; font-weight: 800; }}
/* sub-navigation inside a page keeps the pill look */
.st-key-nav_demo [role="radiogroup"], .st-key-nav_factors [role="radiogroup"], .st-key-nav_pop [role="radiogroup"], .st-key-nav_region [role="radiogroup"], .st-key-nav_eco [role="radiogroup"], .st-key-nav_evidence [role="radiogroup"] {{ gap: 4px 4px; flex-wrap: wrap; }}
.st-key-nav_demo, .st-key-nav_factors, .st-key-nav_pop, .st-key-nav_region, .st-key-nav_eco, .st-key-nav_evidence {{ margin-bottom: 6px; }}
.st-key-nav_demo label, .st-key-nav_factors label, .st-key-nav_pop label, .st-key-nav_region label, .st-key-nav_eco label, .st-key-nav_evidence label {{ background:{WHITE}; border:1px solid {BORDER}; border-radius:10px; padding:7px 16px; margin:0; cursor:pointer; }}
.st-key-nav_demo label > div:first-child, .st-key-nav_factors label > div:first-child, .st-key-nav_pop label > div:first-child, .st-key-nav_region label > div:first-child, .st-key-nav_eco label > div:first-child, .st-key-nav_evidence label > div:first-child {{ display:none; }}
.st-key-nav_demo label p, .st-key-nav_factors label p, .st-key-nav_pop label p, .st-key-nav_region label p, .st-key-nav_eco label p, .st-key-nav_evidence label p {{ color:{PRIMARY}; font-weight:700; }}
.st-key-nav_demo label:has(input:checked), .st-key-nav_factors label:has(input:checked), .st-key-nav_pop label:has(input:checked), .st-key-nav_region label:has(input:checked), .st-key-nav_eco label:has(input:checked), .st-key-nav_evidence label:has(input:checked) {{ background:{PRIMARY}; border-color:{PRIMARY}; }}
.st-key-nav_demo label:has(input:checked) p, .st-key-nav_factors label:has(input:checked) p, .st-key-nav_pop label:has(input:checked) p, .st-key-nav_region label:has(input:checked) p, .st-key-nav_eco label:has(input:checked) p, .st-key-nav_evidence label:has(input:checked) p {{ color:#fff; }}

/* ---- key finding + chips ---- */
.callout {{ background:#FFEFF5; border:1px solid {PINK}; border-left:6px solid {MAGENTA}; border-radius:10px; padding:12px 16px; font-size:1rem; color:{PLUM}; line-height:1.55; }}
.callout .muted {{ color:{MUTED}; font-size:.88rem; }}
button[data-variant="pills"] {{ border-radius:999px; background:{WHITE}; border:1px solid {BORDER}; color:{TEXT}; padding:2px 14px; }}
button[data-variant="pills"] p {{ color:{TEXT}; }}
button[data-variant="pills"][aria-checked="true"], button[data-variant="pills"][data-selected="true"] {{ background:{MAGENTA} !important; border-color:{MAGENTA} !important; font-weight:700; }}
button[data-variant="pills"][aria-checked="true"] p, button[data-variant="pills"][aria-checked="true"] span {{ color:#fff !important; font-weight:700; }}

/* ---- cards ---- */
.card {{ background:{WHITE}; border-radius:12px; box-shadow:0 1px 3px {SHADOW}; padding:16px 18px; height:100%; display:flex; flex-direction:column; }}
[class*="st-key-card_"] {{ background:{WHITE}; border:none !important; border-radius:12px; box-shadow:0 1px 3px {SHADOW}; padding:10px 14px !important; }}
/* cards in one row share the row height (no empty strip under the shorter card) */
[data-testid="stMain"] [data-testid="stColumn"] > [data-testid="stVerticalBlock"] {{ height:100%; }}
[data-testid="stMain"] [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:only-child,
[data-testid="stMain"] [data-testid="stColumn"] > [data-testid="stVerticalBlock"] > [data-testid="stLayoutWrapper"]:only-child > [class*="st-key-card_"] {{ height:100%; }}
[data-testid="stMain"] [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .card),
[data-testid="stMain"] [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .card) [data-testid="stMarkdown"],
[data-testid="stMain"] [data-testid="stElementContainer"]:has(> [data-testid="stMarkdown"] .card) [data-testid="stMarkdownContainer"] {{ height:100%; }}
[data-testid="stMain"] [data-testid="stMarkdown"]:has(.card) > div {{ height:100%; }}
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {{ gap: 0.7rem; }}
.kpi-label {{ color:{MUTED}; font-size:.95rem; font-weight:600; display:flex; align-items:center; gap:6px; }}
.kpi-value {{ color:{TEXT}; font-size:2.2rem; font-weight:800; line-height:1.15; margin-top:8px; }}
.kpi-unit {{ color:{MUTED}; font-size:1rem; font-weight:500; margin-left:6px; }}
.kpi-sub {{ color:{MUTED}; font-size:.9rem; margin-top:6px; line-height:1.55; }}
.kpi-divider {{ border-top: 2px solid {PINK}; margin: 14px 0 10px 0; }}
.kpi-stats {{ display:flex; flex-direction:column; gap:3px; font-size:.95rem; margin-top:0; }}
.kpi-stats b {{ color:{TEXT}; font-weight:800; }}
.kpi-src {{ display:none; }}   /* source is in the card's hover text and the methodology page */
.kpi-na {{ color:{MUTED}; font-size:1.05rem; font-weight:700; margin-top:10px; }}
.notice {{ border-radius:10px; padding:11px 14px; margin:8px 0; font-size:.95rem; border:1px solid {BORDER}; background:{WHITE}; }}
.notice b {{ margin-right:6px; }}
.notice.info {{ border-left:5px solid {PRIMARY}; }}
.notice.warn {{ border-left:5px solid {AMBER}; background:#FFF9EE; }}
.notice.err {{ border-left:5px solid {RED}; background:#FFF3F3; }}
.caption {{ color:{MUTED}; font-size:.85rem; margin:2px 0 14px 0; line-height:1.5; }}
.caption a {{ color:{BLUE}; }}
.rlg-wrap {{ display:flex; flex-wrap:wrap; gap:6px 14px; font-size:.86rem; margin:2px 4px 4px 4px; }}
.rlg {{ display:inline-flex; align-items:center; gap:5px; color:{TEXT}; white-space:nowrap; }}
.rlg i {{ display:inline-block; width:13px; height:13px; border-radius:3px; flex:none; }}
.rlg b {{ font-weight:800; }}
.rlg-wrap.vertical {{ flex-direction:column; flex-wrap:nowrap; gap:9px; font-size:.95rem; margin-top:30px; }}
.rlg-title {{ font-weight:700; font-size:.9rem; color:{MUTED}; margin-bottom:2px; }}
.rlg-wrap.compact {{ font-size:.78rem; gap:3px 10px; }}
.rlg-wrap.compact .rlg i {{ width:11px; height:11px; }}
.card-title {{ font-weight:700; font-size:1rem; color:{TEXT}; margin: 4px 4px 0 4px; }}
.tip {{ position:relative; display:inline-flex; align-items:center; justify-content:center; width:18px; height:18px; border-radius:50%;
  background:{BORDER}; color:{PRIMARY}; font-size:.72rem; font-weight:700; cursor:help; flex:none; }}
.tip:hover::after, .tip:focus::after {{ content: attr(data-tip); position:absolute; z-index:1000; left:50%; top:24px; transform:translateX(-30%);
  width:290px; background:{PRIMARY}; color:#fff; padding:9px 11px; border-radius:8px; font-size:.82rem; font-weight:400; line-height:1.45; text-align:left; white-space:normal; }}
.section-title {{ margin:18px 0 6px 0; font-size:1.2rem; font-weight:700; color:{TEXT}; }}
.badge {{ display:inline-block; padding:2px 9px; border-radius:6px; font-size:.78rem; font-weight:600; border:1px solid {BORDER}; color:{PRIMARY}; background:#fff; }}
.badge.amber {{ border-color:{AMBER}; color:#8a5a00; background:#FFF4DC; }}

/* small laptops / tablets in landscape: card rows wrap into two lines instead of squeezing four columns
   (phones below 640px are stacked by Streamlit itself) */
@media (min-width: 641px) and (max-width: 1280px) {{
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] {{ flex-wrap: wrap; }}
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {{ min-width: 46% !important; }}
  .kpi-value {{ font-size: 2rem; }}
}}
@media (max-width: 900px) {{ .tb-title {{ font-size:1.25rem; }} }}
@media (max-width: 640px) {{
  .block-container {{ padding: 0.5rem 0.6rem 3rem 0.6rem; }}
  .st-key-topbar {{ padding: 12px 14px 10px 14px; }}
  .tb-title {{ font-size: 1.15rem; }}
  .tb-sub {{ display: none; }}
  .chip {{ font-size: .78rem; padding: 3px 9px; }}
  .st-key-nav_page [role="radiogroup"] {{ flex-wrap: nowrap; overflow-x: auto; }}
  .st-key-nav_page label {{ padding: 10px 12px 8px 12px; white-space: nowrap; }}
  .card {{ padding: 14px 16px; }}
  .kpi-value {{ font-size: 1.8rem; }}
  .section-title {{ font-size: 1.1rem; }}
  .notice, .callout {{ font-size: .9rem; padding: 9px 11px; }}
  .tip:hover::after, .tip:focus::after {{ position: fixed; left: 12px; right: 12px; top: 18%; width: auto; transform: none; }}
}}
.stPlotlyChart, [data-testid="stPlotlyChart"] {{ max-width: 100%; }}
[data-testid="stDataFrame"] {{ max-width: 100%; }}
</style>
"""


CSS_V2 = """
<style>
/* ================= dashboard look: sidebar + hero + gradient cards ================= */
.stApp { background: linear-gradient(180deg, #FBF7F1 0%, #F8F4EC 60%, #F6EEF0 100%); }
.block-container { padding-top: 0.6rem; max-width: 1760px; }

/* ---- sidebar ---- */
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid %BORDER%; min-width: 300px; }
section[data-testid="stSidebar"] > div { padding-top: .4rem; }
section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] { padding: .2rem .6rem 0 .6rem; }
.logo { display:flex; align-items:center; gap:12px; padding: 14px 14px; margin: 4px 0 10px 0; border-radius: 18px;
  background: linear-gradient(135deg, %PLUM% 0%, #6B3A7D 60%, %MAGENTA% 140%); color:#fff; }
[data-testid="stSidebarHeader"] { height: 30px !important; min-height: 30px !important; padding-top: 0 !important; padding-bottom: 0 !important; }   /* the header only holds the collapse button: keep it slim so the logo sits near the top */
[data-testid="stSidebarUserContent"] { padding-top: 0 !important; }
.logo { margin-top: 0 !important; }
.logo .mark { font-size: 2.1rem; line-height:1; }
.logo .t1 { font-weight: 800; letter-spacing: .08em; font-size: 1.35rem; line-height:1.05; }
.logo .t2 { font-size: .8rem; opacity: .9; }
.side-title { font-weight: 800; font-size: 1.15rem; color: %PLUM%; margin: 6px 2px 8px 2px; }
[class*="st-key-flt_"] { background:#FBF6F1; border:1px solid %BORDER%; border-radius: 14px; padding: 10px 12px 8px 12px; margin-bottom: 6px; }
[class*="st-key-flt_"] label p, [class*="st-key-flt_"] [data-testid="stWidgetLabel"] p { font-weight: 700; color: %PLUM%; }
section[data-testid="stSidebar"] button[data-variant="pills"] { padding: 2px 10px; font-size: .85rem; }
.src-box { display:flex; gap:10px; align-items:flex-start; background:#FBF6F1; border:1px solid %BORDER%; border-radius:14px; padding:10px 12px;
  font-size:.82rem; color:%MUTED%; line-height:1.45; margin-top: 8px; }
.src-box b { color: %PLUM%; display:block; }
.info-box { background:#FBF6F1; border:1px solid %BORDER%; border-radius:14px; padding:8px 12px; margin-top: 8px; }
.info-box .ir { display:flex; gap:10px; align-items:flex-start; padding: 6px 0; border-bottom: 1px dashed %BORDER%; }
.info-box .ir:last-child { border-bottom: none; }
.info-box .ic { flex:none; width: 22px; text-align:center; font-size: 1.05rem; }
.info-box .ic svg { display:block; margin:0 auto; color:#E83C91; }
.sdot { display:inline-block; width:12px; height:12px; border-radius:50%; margin-top:3px; }
.info-box .k { display:block; font-size:.72rem; color:%MUTED%; line-height:1.1; }
.info-box .v { display:block; font-size:.9rem; font-weight:700; color:%PLUM%; line-height:1.3; }
.info-box .ir.src .v { font-weight:500; font-size:.8rem; }
.side-reset button { background: linear-gradient(90deg, %MAGENTA%, %PINK%) !important; color:#fff !important; border:none !important; border-radius: 12px !important; font-weight: 700; }
.side-reset button p { color:#fff !important; }

/* ---- hero banner ---- */
.st-key-hero { position: relative; border-radius: 24px; padding: 20px 26px 16px 26px; overflow: hidden; margin-bottom: 14px;
  background-image: linear-gradient(95deg, rgba(67,51,76,.86) 0%, rgba(67,51,76,.55) 42%, rgba(232,60,145,.22) 100%), url(app/static/hero.png);
  background-size: cover; background-position: center 6%; box-shadow: 0 6px 20px rgba(67,51,76,.18); }
.st-key-hero h1.hero-t { color:#fff; font-size: 2.1rem; font-weight: 800; margin: 0; line-height: 1.2; text-shadow: 0 2px 8px rgba(0,0,0,.35); }
.st-key-hero .hero-s { color:#FFE9F2; font-size: 1.02rem; margin-top: 4px; text-shadow: 0 1px 6px rgba(0,0,0,.4); }
.st-key-hero h1.hero-t, .st-key-hero .hero-s { text-align: center; }
.st-key-hero { min-height: 190px; display: flex; flex-direction: column; justify-content: center; }   /* tall enough to see the skyline and the workers moving */
.st-key-hero h1.hero-t, .st-key-hero .hero-s { position: relative; z-index: 2; }
.hero-chips { display:flex; flex-wrap:wrap; gap:10px; margin-top: 14px; }
.hero-chip { display:flex; gap:10px; align-items:center; background: rgba(255,255,255,.93); border-radius: 14px; padding: 8px 14px; min-width: 150px; }
.hero-chip .ic { font-size: 1.3rem; }
.hero-chip .k { font-size: .72rem; color: %MUTED%; line-height:1.1; }
.hero-chip .v { font-size: .98rem; font-weight: 700; color: %PLUM%; line-height:1.25; }
.hero-chip.warn { background:#FFF4DF; } .hero-chip.err { background:#FFE2E2; }
/* page navigation: three pills in the banner */
.st-key-nav_page { background: rgba(255,255,255,.95); border-radius: 999px; padding: 4px; margin: 0; width: auto !important; display:inline-block; box-shadow: 0 8px 24px rgba(67,51,76,.10); }
.st-key-nav_page [role="radiogroup"] { flex-wrap: nowrap; gap: 2px; width: auto; }
.st-key-nav_page label { border: none; border-radius: 999px; padding: 8px 22px; }
.st-key-nav_page label p { color: %PLUM% !important; font-weight: 700; }
.st-key-nav_page label:has(input:checked) { background: linear-gradient(90deg, %MAGENTA%, %PINK%); border-bottom-color: transparent; }
.st-key-nav_page label:has(input:checked) p { color:#fff !important; }
.st-key-hero button[kind="secondary"], .st-key-hero [data-testid="stBaseButton-secondary"] { background: rgba(255,255,255,.18); color:#fff; border: 1px solid rgba(255,255,255,.7); border-radius: 12px; }
.st-key-hero [data-testid="stBaseButton-secondary"] p { color:#fff !important; }

/* ---- gradient KPI cards ---- */
.gcard { position:relative; display:flex; flex-wrap:wrap; align-items:center; align-content:space-between; gap:8px 9px; border-radius: 20px; padding: 14px 14px 12px 14px; min-height: 172px; color:#fff;
  box-shadow: 0 6px 16px rgba(67,51,76,.20); overflow:hidden; }
.gcard.g1 { background: linear-gradient(135deg, %MAGENTA% 0%, %PINK% 100%); }
.gcard.g2 { background: linear-gradient(135deg, #7A3F8F 0%, #B05AA0 100%); }
.gcard.g3 { background: linear-gradient(135deg, %PLUM% 0%, #8A4A7E 100%); }
.gcard.g4 { background: linear-gradient(135deg, #5B3A75 0%, #A44C93 100%); }
.gcard .gc-icon { width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; border-radius: 50%; background: rgba(255,255,255,.22); border: 2px solid rgba(255,255,255,.55);
  display:flex; align-items:center; justify-content:center; font-size: 1.5rem; flex: none; }
.gcard .gc-body { flex: 1; min-width: 0; }
.gcard .gc-label { font-size: .92rem; white-space: normal; line-height: 1.25; font-weight: 700; opacity: .96; }   /* the longer summary titles wrap instead of running off the card */
.gcard .gc-value { font-size: clamp(1.4rem, 1.9vw, 1.9rem); font-weight: 800; line-height: 1.15; display:flex; flex-wrap:wrap; align-items:baseline; column-gap:5px; }
.gcard .gc-value span { font-size: .8rem; font-weight: 600; opacity: .95; white-space: nowrap; }
.gcard .gc-scope { font-size: .74rem; opacity: .88; margin-top: 2px; line-height: 1.25; min-height: 2.5em; }
.gcard .gc-delta { font-size: .86rem; margin-top: 2px; opacity: .97; }
.gcard .gc-delta small { opacity: .85; margin-left: 4px; }
.gcard .gc-na { font-size: 1.05rem; font-weight: 700; margin-top: 8px; }
.gcard .gc-spark { flex: 1 1 100%; width: 100%; order: 3; opacity: .95; min-height: 36px; }
.gcard .gc-spark svg { width: 100%; height: 40px; display:block; overflow: visible; }
@media (max-width: 900px) { .gcard .gc-value { font-size: 1.8rem; } }

/* ---- cards that hold charts ---- */
[class*="st-key-card_"] { border-radius: 18px !important; box-shadow: 0 3px 10px rgba(67,51,76,.08); }
.card-title { display:flex; align-items:center; gap:8px; font-weight: 800; font-size: 1.05rem; color: %PLUM%; }
.card-title::before { content:""; width: 8px; height: 22px; border-radius: 4px; background: linear-gradient(180deg, %MAGENTA%, %PINK%); display:inline-block; }
.ins { display:flex; gap:12px; align-items:flex-start; background:#FFF6FA; border-radius:14px; padding: 13px 14px; margin-bottom: 11px; }
.ins .n { flex:none; width: 30px; height:30px; border-radius:50%; background: linear-gradient(135deg, %MAGENTA%, %PINK%); color:#fff; font-weight:800; display:flex; align-items:center; justify-content:center; }
.ins b { color: %PLUM%; }
.ins .s { font-size:.84rem; color:%MUTED%; }
.pstrip { display:flex; flex-wrap:wrap; align-items:center; gap:6px 8px; margin: 18px 0 12px 0; font-size:.8rem; color:%PLUM%; }
.pstrip-t { font-weight:700; color:%MUTED%; margin-right:2px; }
.pchip { background:#fff; border:1px solid %BORDER%; border-radius:999px; padding:3px 10px; white-space:nowrap; }
.pchip.old { background:#FFF4E0; border-color:#F2C27B; }
.pchip.na { color:%MUTED%; border-style:dashed; }
.pstrip-k { display:inline-flex; align-items:center; gap:5px; color:%MUTED%; font-size:.74rem; }
.pstrip-k i { width:11px; height:11px; border-radius:50%; background:#FFF4E0; border:1px solid #F2C27B; display:inline-block; }

@media (max-width: 640px) {
  .st-key-hero { padding: 14px 14px 12px 14px; }
  .st-key-hero h1.hero-t { font-size: 1.45rem; }
  .st-key-hero .hero-s { font-size: .86rem; }
  .st-key-nav_page { float: none; display:block; width: 100% !important; overflow-x:auto; }
  .st-key-nav_page label { padding: 7px 14px; white-space: nowrap; }
  .hero-chip { min-width: 46%; flex: 1; padding: 6px 10px; }
}
</style>
""".replace("%PLUM%", PLUM).replace("%MAGENTA%", MAGENTA).replace("%PINK%", PINK).replace("%BORDER%", BORDER).replace("%MUTED%", MUTED)


CSS_FX = """
<style>
@keyframes lm-rise { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
@keyframes lm-reveal { from { clip-path: inset(0 100% 0 0); opacity: .4; } to { clip-path: inset(0 0 0 0); opacity: 1; } }
@keyframes lm-draw { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }
@keyframes lm-pan { from { background-position: 0% 38%; } to { background-position: 100% 38%; } }
@keyframes lm-pop { from { opacity: 0; transform: scale(.4); } to { opacity: 1; transform: none; } }

.gcard { animation: lm-rise .6s cubic-bezier(.2,.7,.2,1) backwards; transition: transform .22s ease, box-shadow .22s ease; }
.gcard.g1 { animation-delay: 0s; } .gcard.g2 { animation-delay: .08s; } .gcard.g3 { animation-delay: .16s; } .gcard.g4 { animation-delay: .24s; }
.gcard:hover { transform: translateY(-5px); box-shadow: 0 14px 28px rgba(67,51,76,.25); }
.gcard .gc-value b { font-weight: inherit; font-variant-numeric: tabular-nums; }
.gcard .gc-icon { animation: lm-pop .55s .25s cubic-bezier(.3,1.4,.5,1) backwards; }
@keyframes lm-twinkle { 0%, 100% { transform: scale(1); opacity: .95; } 50% { transform: scale(.55) rotate(18deg); opacity: .55; } }
@keyframes lm-spin-slow { from { transform: rotate(0); } to { transform: rotate(360deg); } }
.gcard .gc-spark .st { transform-box: fill-box; transform-origin: center; animation: lm-pop .45s backwards; }
@keyframes lm-flapL { from { transform: rotate(16deg) scaleY(1); } to { transform: rotate(-24deg) scaleY(.8); } }
@keyframes lm-flapR { from { transform: rotate(-16deg) scaleY(1); } to { transform: rotate(24deg) scaleY(.8); } }
@keyframes lm-bob { from { transform: translateY(1.5px); } to { transform: translateY(-2px); } }
.gcard .gc-spark .bat { animation: lm-pop .5s 1.1s cubic-bezier(.3,1.4,.5,1) backwards, lm-bob 1.1s ease-in-out 1.6s infinite alternate; }
.gcard .gc-spark .bat .wl, .gcard .gc-spark .bat .wr { transform-box: fill-box; animation: lm-flapL .34s ease-in-out infinite alternate; }
.gcard .gc-spark .bat .wl { transform-origin: 100% 40%; }
.gcard .gc-spark .bat .wr { transform-origin: 100% 40%; animation-name: lm-flapL; }
@media (prefers-reduced-motion: reduce) { html:not(.lm-motion) .gcard .gc-spark .bat, html:not(.lm-motion) .gcard .gc-spark .bat * { animation: none !important; } }

html:not(.lm-js) [class*="st-key-card_"] { animation: lm-rise .55s cubic-bezier(.2,.7,.2,1) backwards; }
[class*="st-key-card_"] { transition: transform .2s ease, box-shadow .2s ease, opacity .3s ease; }
[class*="st-key-card_"]:hover { transform: translateY(-3px); box-shadow: 0 10px 22px rgba(67,51,76,.16); }
[data-testid="stPlotlyChart"] { animation: lm-reveal 1s ease-out backwards; }

.st-key-hero { background-size: cover; }

button, label[data-baseweb="radio"], [data-testid="stBaseButton-secondary"] { transition: transform .15s ease, box-shadow .15s ease, background-color .15s ease; }
.st-key-nav_page label:hover, .st-key-nav_pop label:hover, .st-key-nav_region label:hover { transform: translateY(-2px); }
button:active { transform: scale(.97); }

@media (prefers-reduced-motion: reduce) {
  html:not(.lm-motion) *, html:not(.lm-motion) *::before, html:not(.lm-motion) *::after { animation: none !important; transition: none !important; }
}
</style>
<style>
@keyframes lm-bob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
@keyframes lm-shadow { 0%, 100% { transform: scaleX(1); opacity: .9; } 50% { transform: scaleX(.78); opacity: .6; } }
@keyframes lm-blink { 0%, 90%, 100% { transform: scaleY(1); } 94% { transform: scaleY(.08); } }
@keyframes lm-wave { 0%, 100% { transform: rotate(-14deg); } 50% { transform: rotate(16deg); } }
@keyframes lm-q { 0%, 100% { transform: translateY(0) rotate(-8deg); } 50% { transform: translateY(-6px) rotate(8deg); } }
@keyframes lm-wobble { 0%, 100% { transform: rotate(-3deg); } 50% { transform: rotate(3deg); } }
@keyframes lm-drift { 0%, 100% { transform: translate(0, 0); } 50% { transform: translate(16px, -14px); } }
@keyframes lm-wiggle { 0%, 100% { transform: rotate(0); } 25% { transform: rotate(-14deg); } 75% { transform: rotate(14deg); } }
@keyframes lm-hop { 0%, 100% { transform: translateY(0); } 40% { transform: translateY(-9px); } 70% { transform: translateY(-2px); } }
@keyframes lm-spin { from { transform: rotateY(0); } to { transform: rotateY(360deg); } }

.mc { width: 100%; height: auto; overflow: visible; display: block; }
.mc .mc-bob { animation: lm-bob 3.2s ease-in-out infinite; }
.mc .mc-shadow { animation: lm-shadow 3.2s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
.mc .mc-eyes { animation: lm-blink 4.5s infinite; transform-box: fill-box; transform-origin: center; }
.mc .mc-armR { animation: lm-wave 1.5s ease-in-out infinite; transform-box: view-box; transform-origin: 63px 58px; }
.mc .mc-q { animation: lm-q 2.4s ease-in-out infinite; transform-box: fill-box; transform-origin: center; }
.mc.mc-wobble-unused .mc-bob { animation: lm-bob 3.2s ease-in-out infinite, lm-wobble 2.6s ease-in-out infinite; transform-box: view-box; transform-origin: 45px 100px; }

.st-key-hero [data-testid="stElementContainer"]:has(.mascot-wrap) { position: absolute; right: 30px; bottom: 6px; width: 78px; height: auto; margin: 0; z-index: 2; pointer-events: none; }
.mascot-wrap { }
.st-key-hero::before, .st-key-hero::after { content: ""; position: absolute; border-radius: 50%; pointer-events: none; z-index: 0; }
.st-key-hero::before { width: 130px; height: 130px; right: 25%; top: -40px; background: radial-gradient(circle, rgba(255,143,183,.38), rgba(255,143,183,0) 70%); }
.st-key-hero::after { width: 90px; height: 90px; left: 46%; bottom: -30px; background: radial-gradient(circle, rgba(252,246,156,.32), rgba(252,246,156,0) 70%); }

.gcard:hover .gc-icon { animation: lm-wiggle .6s ease-in-out; }
.gcard.g2:hover .gc-icon { animation: lm-hop .6s ease-in-out; }
.gcard.g3:hover .gc-icon { animation: lm-spin .9s ease-in-out; }
.gcard.g4:hover .gc-icon { animation: lm-hop .6s ease-in-out; }

.empty-card { display: flex; align-items: center; gap: 14px; background: #FFF9EE; border: 1px solid #E8DFDA; border-left: 5px solid #F5B942; border-radius: 12px; padding: 8px 16px; margin: 8px 0; color: #43334C; }
.empty-card.err { border-left-color: #E5484D; background: #FFF3F3; }
.empty-card .empty-char { flex: none; width: 58px; }

@media (max-width: 760px) { .st-key-hero [data-testid="stElementContainer"]:has(.mascot-wrap) { display: none; } .empty-card .empty-char { width: 46px; } }

/* a second mascot roams along the bottom of the screen (fx.py moves it and switches the state classes below) */
[data-testid="stElementContainer"]:has(.mascot-fixed) { position: fixed; left: 0; right: 0; bottom: 10px; width: auto; height: 0; margin: 0; z-index: 40; pointer-events: none; }
.mf-pos { position: absolute; bottom: 0; right: 18px; width: 62px; will-change: left, bottom; }
.mf-pos.go { right: auto; }
.mf-pop, .mf-flip { transform-origin: 50% 100%; }
.mf-pop { pointer-events: auto; cursor: pointer; }
.mf-flip { transition: transform .25s ease; }
.lm-js .mascot-fixed .mf-pop { transition: opacity .35s ease, transform .6s cubic-bezier(.3, 1.6, .5, 1); }
.lm-js .mascot-fixed:not(.show) .mf-pop { opacity: 0; transform: translateY(80px) scale(.3); }
.lm-js .mascot-fixed.show.hop .mf-pop { animation: lm-hop-big .7s ease-out; }
.mf-bubble { position: absolute; bottom: 100%; left: 31px; margin-bottom: 4px; transform: translateX(-50%) scale(.6); transform-origin: 50% 100%;
  white-space: nowrap; background: #fff; color: #43334C; border: 2px solid #43334C; border-radius: 14px; padding: 5px 12px; font-size: .84rem; font-weight: 600;
  opacity: 0; transition: opacity .25s ease, transform .35s cubic-bezier(.3, 1.6, .5, 1); box-shadow: 0 4px 10px rgba(67,51,76,.2); }
.mf-bubble.on { opacity: 1; transform: translateX(-50%) scale(1); }
.mf-bubble.long { white-space: normal; width: 270px; text-align: left; line-height: 1.45; font-weight: 500; }
.mf-bubble.below { bottom: auto; top: 100%; margin: 4px 0 0 0; transform-origin: 50% 0; }
.mf-bubble.below::after { top: auto; bottom: 100%; border-top-color: transparent; border-bottom-color: #43334C; }
.mf-bubble::after { content: ""; position: absolute; top: 100%; left: var(--tail, 50%); margin-left: -6px; border: 6px solid transparent; border-top-color: #43334C; }

@keyframes lm-step-a { 0%, 100% { transform: rotate(-24deg); } 50% { transform: rotate(24deg); } }
@keyframes lm-step-b { 0%, 100% { transform: rotate(24deg); } 50% { transform: rotate(-24deg); } }
@keyframes lm-bob-fast { 0%, 100% { transform: translateY(0) rotate(-2.5deg); } 50% { transform: translateY(-4px) rotate(2.5deg); } }
@keyframes lm-swing { from { transform: rotate(-22deg); } to { transform: rotate(22deg); } }
@keyframes lm-dance { from { transform: rotate(-10deg) translateY(0); } to { transform: rotate(10deg) translateY(-7px); } }
@keyframes lm-look { 0%, 100% { transform: rotate(0); } 30% { transform: rotate(-7deg); } 70% { transform: rotate(7deg); } }
.mc .mc-legL, .mc .mc-legR { transform-box: fill-box; transform-origin: 50% 0; }
.mc .mc-armL { transform-box: view-box; transform-origin: 27px 58px; }
.mascot-fixed.walking .mc-legL { animation: lm-step-a .4s linear infinite; }
.mascot-fixed.walking .mc-legR { animation: lm-step-b .4s linear infinite; }
.mascot-fixed.walking .mc-bob { animation: lm-bob-fast .4s ease-in-out infinite; }
.mascot-fixed.walking .mc-armR { animation: lm-swing .4s ease-in-out infinite alternate; }
.mascot-fixed.walking .mc-armL { animation: lm-swing .4s ease-in-out infinite alternate-reverse; }
.mascot-fixed.dance .mc { animation: lm-dance .42s ease-in-out infinite alternate; transform-origin: 50% 100%; }
.mascot-fixed.dance .mc-armR { animation: lm-wave .3s ease-in-out infinite; }
.mascot-fixed.dance .mc-armL { animation: lm-wave .3s ease-in-out infinite reverse; }
.mascot-fixed.jump .mc { animation: lm-hop-big .8s ease-out; transform-origin: 50% 100%; }
.mascot-fixed.look .mc { animation: lm-look 1.8s ease-in-out; transform-origin: 50% 100%; }
@keyframes lm-point { 0%, 100% { transform: rotate(-30deg); } 50% { transform: rotate(-4deg); } }
@keyframes lm-nod { 0%, 100% { transform: rotate(0); } 50% { transform: rotate(-3deg) translateY(1px); } }
.mascot-fixed.explain .mc { animation: lm-nod 1.1s ease-in-out infinite; transform-origin: 50% 100%; }
.mascot-fixed.explain .mc-armR { animation: lm-point .9s ease-in-out infinite; }
.mascot-fixed.sleep .mc-eyes { animation: none; transform: scaleY(.08); }
.mascot-fixed.sleep .mc-armR { animation: none; }
.mascot-fixed.sleep .mc-bob { animation-duration: 5s; }
.st-key-hero .mascot-wrap { pointer-events: auto; cursor: pointer; }
.mascot-wrap.hop { animation: lm-hop-big .7s ease-out; }
@keyframes lm-hop-big { 0% { transform: translateY(0) scale(1, 1); } 25% { transform: translateY(2px) scale(1.12, .86); } 55% { transform: translateY(-22px) scale(.92, 1.1); } 80% { transform: translateY(0) scale(1.08, .92); } 100% { transform: none; } }
.mc .mc-pupil { transition: transform .12s ease-out; }

/* progressive reveal: only hidden when the script is running (it adds .in as the card enters the screen) */
@keyframes lm-pop-card {
  0% { opacity: 0; transform: translateY(46px) scale(.92); }
  55% { opacity: 1; transform: translateY(-9px) scale(1.025); }
  78% { transform: translateY(3px) scale(.995); }
  100% { opacity: 1; transform: none; }
}
.lm-js [class*="st-key-card_"]:not(.in) { opacity: 0; transform: translateY(46px) scale(.92); }
.lm-js [class*="st-key-card_"].in { animation: lm-pop-card .75s cubic-bezier(.25,.8,.3,1) backwards; }
/* the chart inside draws itself (left to right) when its card pops up, not at page load while it is still off screen */
.lm-js [class*="st-key-card_"] [data-testid="stPlotlyChart"] { animation: none; clip-path: inset(0 100% 0 0); }
.lm-js [class*="st-key-card_"].in [data-testid="stPlotlyChart"] { clip-path: inset(0 0 0 0); transition: clip-path 1s .25s ease-out; }
@media (max-width: 760px) { .mf-pos { width: 48px; right: 8px; } .mf-bubble { font-size: .74rem; } }
@media (prefers-reduced-motion: reduce) { html:not(.lm-motion).lm-js [class*="st-key-card_"] [data-testid="stPlotlyChart"] { clip-path: none; } html:not(.lm-motion) .mc *, html:not(.lm-motion) .mc, html:not(.lm-motion) .st-key-hero::before, html:not(.lm-motion) .st-key-hero::after, html:not(.lm-motion) .gcard:hover .gc-icon { animation: none !important; } }
.lm-motion-btn { display: none; width: 100%; margin-top: 8px; padding: 8px 12px; border: 1px dashed #E83C91; border-radius: 12px; background: #FFF4F8; color: #43334C; font: inherit; font-size: .82rem; font-weight: 600; cursor: pointer; text-align: left; }
.lm-os-reduced .lm-motion-btn { display: block; }
.lm-motion-btn:hover { background: #FFE3EE; }
</style>
"""


# Bento look: lavender canvas, big soft cards, with the filters kept open in the left panel.
CSS_BENTO = """
<style>
.stApp { background: radial-gradient(1100px 560px at 88% -8%, rgba(255,143,183,.20), transparent 60%),
                     radial-gradient(900px 520px at -8% 28%, rgba(171,70,210,.11), transparent 58%),
                     linear-gradient(180deg, #F8F4EC 0%, #F3EDF8 100%) !important; }
.block-container { padding-top: 1.1rem !important; max-width: 1560px; }

/* Kanit everywhere text appears (icons keep their own icon font, code keeps a monospace font) */
html, body, .stApp, [data-testid="stHeader"], [data-testid="stHeader"] span, [data-testid="stSidebar"], [data-testid="stPopoverBody"], [data-testid="stTooltipContent"],
[data-testid="stMarkdownContainer"], [data-testid="stCaptionContainer"], [data-baseweb="popover"], [data-baseweb="select"], [data-testid="stMetricValue"],
[data-testid="stMetricLabel"], [data-testid="stDataFrame"], [data-testid="stAlert"], [data-testid="stExpander"], button, input, textarea, label, p {
  font-family: 'Kanit', 'Sarabun', 'Noto Sans Thai', 'Leelawadee UI', 'Tahoma', sans-serif !important; }

/* ---------- the left panel: the filters stay open (a soft, rounded edge to match the bento cards) ---------- */
section[data-testid="stSidebar"] { border-right: none !important; border-radius: 0 28px 28px 0; box-shadow: 8px 0 30px rgba(67,51,76,.10); }
.rail-logo { width: 40px; height: 40px; display: flex; align-items: flex-end; justify-content: center; gap: 4px; padding-bottom: 5px; }
.rail-logo i { display: block; width: 7px; border-radius: 3px; background: #fff; }

/* ---------- pop-up windows opened from the rail ---------- */
[data-testid="stPopoverBody"] { border-radius: 24px !important; padding: 16px 18px 12px 18px !important; min-width: 350px; max-width: 390px; max-height: 82vh;
  border: 1px solid #E8DFDA !important; box-shadow: 0 24px 60px rgba(43,33,51,.28) !important; animation: lm-pop-card .45s cubic-bezier(.22,1,.36,1) backwards; }
.pop-title { font-weight: 800; font-size: 1.05rem; color: #43334C; margin: 0 0 8px 0; }
.pop-title::before { content: ""; display: inline-block; width: 8px; height: 18px; border-radius: 6px; margin-right: 8px; vertical-align: -3px; background: linear-gradient(#E83C91, #FF8FB7); }

/* ---------- bento cards ---------- */
[class*="st-key-card_"] { border-radius: 28px !important; box-shadow: 0 10px 34px rgba(67,51,76,.09) !important; padding: 14px 18px !important; }
.gcard { border-radius: 28px; }
.st-key-kpi_row [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
.st-key-kpi_row .gcard { min-height: 212px; }   /* the four cards share one height whatever their text length */
h1, h2, h3, h4, h5, h6, h1 span, h2 span, h3 span, h4 span, [data-testid="stHeading"] *, [data-testid="stHeadingWithActionElements"] * { font-family: 'Kanit', 'Sarabun', 'Noto Sans Thai', 'Leelawadee UI', 'Tahoma', sans-serif !important; }   /* Streamlit sets its own sans on headings */   /* Streamlit pulls markdown up by 1rem: the cards would then overflow their row and sit on top of the strip below */
.st-key-hero { border-radius: 30px; }
[class*="st-key-page_"] { animation: lm-page .75s cubic-bezier(.22,1,.36,1) backwards; }
@keyframes lm-page { from { opacity: 0; transform: translateY(22px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { html:not(.lm-motion) [class*="st-key-page_"], html:not(.lm-motion) [data-testid="stPopoverBody"] { animation: none !important; } }

/* ---------- phones: the panel is the usual drawer (Streamlit's own button opens it) ---------- */
@media (max-width: 760px) {
  .block-container { padding-bottom: 40px !important; }
  [data-testid="stPopoverBody"] { min-width: 0; max-width: 92vw; }
  /* the roaming mascot would cover the charts on a narrow screen */
  [data-testid="stElementContainer"]:has(.mascot-fixed) { display: none; }
  /* the four cards sit 2 x 2 so the charts start on the first screen */
  .st-key-kpi_row [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; gap: 8px !important; }
  .st-key-kpi_row [data-testid="stColumn"] { flex: 1 1 calc(50% - 4px) !important; width: calc(50% - 4px) !important; min-width: calc(50% - 4px) !important; }
  .st-key-kpi_row .gcard { min-height: 0; padding: 10px 10px 8px 10px; gap: 4px 6px; border-radius: 20px; }
  .st-key-kpi_row .gcard .gc-icon { display: none; }
  .st-key-kpi_row .gcard .gc-label { font-size: .8rem; white-space: normal; line-height: 1.2; }
  .st-key-kpi_row .gcard .gc-value { font-size: 1.35rem; }
  .st-key-kpi_row .gcard .gc-delta { font-size: .74rem; }
  .st-key-kpi_row .gcard .gc-scope { font-size: .66rem; min-height: 0; }
  .st-key-kpi_row .gcard .gc-spark { min-height: 24px; }
  .st-key-kpi_row .gcard .gc-spark svg { height: 26px; }
}
[data-testid="stElementContainer"]:has(.mascot-off) { display: none; }
/* ---------- ranked list (regions by rate) ---------- */
.rklist { display: flex; flex-direction: column; gap: 22px; padding: 10px 2px 30px; }
.rk { display: flex; align-items: center; gap: 16px; }
.rk-n { flex: 0 0 22px; font-size: 1.15rem; font-weight: 700; color: #E83C91; text-align: center; font-variant-numeric: tabular-nums; }
.rk-b { flex: 1; min-width: 0; }
.rk-t { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.rk-t b { font-size: 1.05rem; font-weight: 700; color: #43334C; }
.rk-t span { font-size: 1.02rem; font-weight: 700; color: #E83C91; font-variant-numeric: tabular-nums; }
.rk-bar { height: 8px; border-radius: 8px; background: #F0E8F3; margin-top: 9px; overflow: hidden; }
.rk-bar i { display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, #E83C91, #FF8FB7); transform-origin: left; animation: lm-grow .8s cubic-bezier(.22,1,.36,1) backwards; }
@keyframes lm-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.rk.dim { opacity: .38; }
@media (prefers-reduced-motion: reduce) { html:not(.lm-motion) .rk-bar i { animation: none; } }
html.lm-dark .rk-t b { color: #EDE6F2; } html.lm-dark .rk-bar { background: #3A2E47; }
/* ---------- "the page in five seconds" ---------- */
.story { margin: 14px 0 6px; padding: 16px 20px; border-radius: 24px; background: #fff; box-shadow: 0 8px 26px rgba(67,51,76,.08); display: flex; gap: 22px; align-items: stretch; flex-wrap: wrap; }
.story-t { font-weight: 700; font-size: 1.02rem; color: #43334C; min-width: 150px; flex: 0 0 150px; }
.story-t small { display: block; font-weight: 400; font-size: .72rem; color: #7A6C86; margin-top: 4px; line-height: 1.35; }
.story-i { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 12px 22px; flex: 1 1 520px; }
.sf { display: flex; gap: 10px; align-items: flex-start; }
.sf > i { font-style: normal; flex: 0 0 30px; height: 30px; border-radius: 10px; display: grid; place-items: center; font-size: .78rem; color: #fff; background: linear-gradient(135deg, #FF8FB7, #E83C91); }
.sf small { display: block; color: #7A6C86; font-size: .72rem; }
.sf span { font-size: .92rem; line-height: 1.4; color: #43334C; }
@media (max-width: 760px) { .story-t { flex-basis: 100%; } }
.story.cmp .sf > i { color: transparent; }
.story.cmp .sf:last-child > i { color: #fff; background: linear-gradient(135deg, #FF8FB7, #E83C91); }
.cmp-t { width: 100%; border-collapse: collapse; background: #fff; border-radius: 18px; overflow: hidden; box-shadow: 0 8px 26px rgba(67,51,76,.08); margin-top: 6px; }
.cmp-t th, .cmp-t td { padding: 12px 16px; text-align: right; font-size: .92rem; border-bottom: 1px solid #F0EAF5; }
.cmp-t th:first-child, .cmp-t td:first-child { text-align: left; font-weight: 600; }
.cf-note { margin: 4px 0 6px; padding: 10px 14px; border-radius: 14px; background: #F3EEF6; color: #43334C; font-size: .86rem; line-height: 1.5; }
.cf-t td, .cf-t th { text-align: left !important; vertical-align: top; font-size: .84rem; }
html.lm-dark .cf-note { background: #2E2438; color: #EDE6F2; }
.cmp-t thead th { color: #7A6C86; font-weight: 600; font-size: .8rem; }
</style>
"""


CSS_3D = """
<style>
/* ---------- the 3D mascot: boxes with six faces ---------- */
.cb { position: absolute; width: var(--w); height: var(--h); transform-style: preserve-3d; }
.cb > i { position: absolute; display: block; backface-visibility: hidden; border-radius: var(--rad, 6px); }
.cb > .f { inset: 0; transform: translateZ(calc(var(--d) / 2)); background: var(--c); }
.cb > .k { inset: 0; transform: rotateY(180deg) translateZ(calc(var(--d) / 2)); background: var(--k); }
.cb > .r { width: var(--d); height: var(--h); top: 0; left: calc((var(--w) - var(--d)) / 2); transform: rotateY(90deg) translateZ(calc(var(--w) / 2)); background: var(--s); }
.cb > .l { width: var(--d); height: var(--h); top: 0; left: calc((var(--w) - var(--d)) / 2); transform: rotateY(-90deg) translateZ(calc(var(--w) / 2)); background: var(--s); }
.cb > .t { width: var(--w); height: var(--d); left: 0; top: calc((var(--h) - var(--d)) / 2); transform: rotateX(90deg) translateZ(calc(var(--h) / 2)); background: var(--t); }
.cb > .b { width: var(--w); height: var(--d); left: 0; top: calc((var(--h) - var(--d)) / 2); transform: rotateX(-90deg) translateZ(calc(var(--h) / 2)); background: var(--b); }
.limb { position: absolute; width: 0; height: 0; transform-style: preserve-3d; transform-origin: 0 0; }

.mc3d { position: relative; width: 62px; height: 106px; perspective: 700px; perspective-origin: 50% 36%; --ry: -28deg; }
.mf-flip .mc3d { --ry: inherit; }
html.lm-notip div[data-baseweb="popover"]:has([data-testid="stTooltipContent"]) { display: none !important; }   /* after a rail click the tip must not linger */
.mc3d-in { position: absolute; left: 0; top: 0; width: 94px; height: 160px; transform: scale(.66); transform-origin: 0 0; transform-style: preserve-3d; }
.rig { position: absolute; inset: 0; transform-style: preserve-3d; transform-origin: 47px 90px; transform: rotateY(var(--ry, -28deg)); transition: transform .5s cubic-bezier(.3, .7, .3, 1); }
.m3-bob { position: absolute; inset: 0; transform-style: preserve-3d; animation: lm3-breathe 3.2s ease-in-out infinite; }
.m3-shadow { position: absolute; left: 6px; bottom: -2px; width: 50px; height: 9px; border-radius: 50%; background: rgba(43,33,51,.30); filter: blur(2px); }

/* face (on the front face of the head) */
.m3-skull .f { overflow: hidden; }
.fringe { position: absolute; left: -2px; right: -2px; top: -2px; height: 38%; background: #43334C; border-radius: 0 0 60% 40% / 0 0 100% 70%; }
.m3-eyes { position: absolute; left: 0; right: 0; top: 46%; height: 15px; display: flex; justify-content: center; gap: 10px; animation: lm3-blink 4.6s infinite; transform-origin: 50% 50%; }
.m3-eyes .eye { width: 11px; height: 15px; border-radius: 50%; background: #fff; border: 1.4px solid #43334C; display: flex; align-items: center; justify-content: center; overflow: hidden; }
.m3-pupil { display: block; width: 6px; height: 8px; border-radius: 50%; background: #43334C; transition: transform .12s ease-out; }
.cheek { position: absolute; top: 64%; width: 8px; height: 6px; border-radius: 50%; background: #FFB3D1; opacity: .85; }
.cheek.c1 { left: 7px; } .cheek.c2 { right: 7px; }
.mouth { position: absolute; left: 50%; top: 74%; transform: translateX(-50%); }
.mouth.smile { width: 14px; height: 7px; border-bottom: 2.6px solid #43334C; border-radius: 0 0 14px 14px; }
.mouth.flat { width: 10px; height: 0; border-top: 2.4px solid #43334C; border-radius: 2px; top: 78%; }
.brow { position: absolute; top: 36%; height: 0; border-top: 2.4px solid #43334C; border-radius: 3px; }
.brow.b1 { left: 9px; width: 12px; transform: rotate(-14deg); } .brow.b2 { right: 9px; width: 12px; transform: rotate(4deg); }

/* shirt details (on the front face of the torso) */
.m3-torso .f { overflow: hidden; }
.collar { position: absolute; left: 11px; top: 0; width: 22px; height: 13px; background: #E6DCEC; clip-path: polygon(0 0, 100% 0, 50% 100%); }
.tie { position: absolute; left: 50%; top: 11px; width: 10px; height: 33px; margin-left: -5px; background: #E83C91; clip-path: polygon(22% 0, 78% 0, 100% 22%, 60% 100%, 40% 100%, 0 22%); }
.knot { position: absolute; left: 50%; top: 8px; width: 9px; height: 7px; margin-left: -4.5px; background: #C42A78; border-radius: 2px; }
.badge { position: absolute; left: 62%; top: 26px; width: 12px; height: 9px; border-radius: 2px; background: #FF8FB7; border: 1px solid #43334C; }

/* the question mark floats beside the head (outside the 3D rig, so it never turns) */
.m3-q { position: absolute; left: 40px; top: -6px; width: 24px; height: 24px; border-radius: 50%; background: #FCF69C; border: 2px solid #43334C; color: #43334C;
  font: 800 .95rem/20px Kanit, sans-serif; text-align: center; animation: lm-q 2.4s ease-in-out infinite; }

/* resting pose */
.m3-armL { transform: rotateZ(6deg); } .m3-armR { transform: rotateZ(-6deg); }
.m3-head { transition: transform .4s ease; }

@keyframes lm3-breathe { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-2.5px); } }
@keyframes lm3-blink { 0%, 90%, 100% { transform: scaleY(1); } 94% { transform: scaleY(.08); } }
@keyframes lm3-legA { 0%, 100% { transform: rotateX(-30deg); } 50% { transform: rotateX(30deg); } }
@keyframes lm3-legB { 0%, 100% { transform: rotateX(30deg); } 50% { transform: rotateX(-30deg); } }
@keyframes lm3-armA { 0%, 100% { transform: rotateX(24deg) rotateZ(5deg); } 50% { transform: rotateX(-24deg) rotateZ(5deg); } }
@keyframes lm3-armB { 0%, 100% { transform: rotateX(-24deg) rotateZ(-5deg); } 50% { transform: rotateX(24deg) rotateZ(-5deg); } }
@keyframes lm3-stepbob { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
@keyframes lm3-wave { 0%, 100% { transform: rotateZ(-150deg) rotateX(0); } 50% { transform: rotateZ(-118deg) rotateX(8deg); } }
@keyframes lm3-armsup { 0%, 100% { transform: rotateZ(-130deg); } 50% { transform: rotateZ(-95deg); } }
@keyframes lm3-armsupL { 0%, 100% { transform: rotateZ(130deg); } 50% { transform: rotateZ(95deg); } }
@keyframes lm3-dance { 0%, 100% { transform: translateY(0) rotateY(-26deg); } 25% { transform: translateY(-9px) rotateY(0deg); } 50% { transform: translateY(0) rotateY(26deg); } 75% { transform: translateY(-9px) rotateY(0deg); } }
@keyframes lm3-look { 0%, 100% { transform: rotateY(0); } 30% { transform: rotateY(-48deg); } 65% { transform: rotateY(40deg); } }
@keyframes lm3-nod { 0%, 100% { transform: rotateX(0); } 50% { transform: rotateX(9deg); } }
@keyframes lm3-point { 0%, 100% { transform: rotateZ(-98deg) rotateX(0); } 50% { transform: rotateZ(-84deg) rotateX(-6deg); } }

.mascot-fixed.walking .m3-legL { animation: lm3-legA var(--T, .72s) ease-in-out infinite; }
.mascot-fixed.walking .m3-legR { animation: lm3-legB var(--T, .72s) ease-in-out infinite; }
.mascot-fixed.walking .m3-armL { animation: lm3-armA var(--T, .72s) ease-in-out infinite; }
.mascot-fixed.walking .m3-armR { animation: lm3-armB var(--T, .72s) ease-in-out infinite; }
.mascot-fixed.walking .m3-bob { animation: lm3-stepbob calc(var(--T, .72s) / 2) ease-in-out infinite; }
.mascot-fixed.wave .m3-armR { animation: lm3-wave .55s ease-in-out infinite; }
.mascot-fixed.dance .m3-bob { animation: lm3-dance 1.1s ease-in-out infinite; }
.mascot-fixed.dance .m3-armR { animation: lm3-armsup .55s ease-in-out infinite; }
.mascot-fixed.dance .m3-armL { animation: lm3-armsupL .55s ease-in-out infinite reverse; }
.mascot-fixed.jump .mc3d { animation: lm-hop-big .8s ease-out; transform-origin: 50% 100%; }
.mascot-fixed.jump .m3-armR { transform: rotateZ(-150deg); } .mascot-fixed.jump .m3-armL { transform: rotateZ(150deg); }
.mascot-fixed.look .m3-head { animation: lm3-look 1.9s ease-in-out; }
.mascot-fixed.sleep .m3-eyes { animation: none; transform: scaleY(.1); }
.mascot-fixed.sleep .m3-head { transform: rotateX(20deg) rotateZ(7deg); }
.mascot-fixed.sleep .m3-bob { animation-duration: 5s; }
.mascot-fixed.explain .m3-armR { animation: lm3-point .9s ease-in-out infinite; }
.mascot-fixed.explain .m3-head { animation: lm3-nod 1.1s ease-in-out infinite; }

/* puzzled mascot in the empty-state cards looks about slowly */
.m3-idle-look .m3-head { animation: lm3-look 4.5s ease-in-out infinite; }
.empty-card .empty-char { width: 62px; }
.empty-card .mc3d { margin-top: -4px; }

/* ---------- the ghost: floats instead of standing, big dark eyes with a moving shine, round mouth ---------- */
@keyframes lm3-float { 0%, 100% { transform: translateY(2px) rotateZ(-1.5deg); } 50% { transform: translateY(-7px) rotateZ(1.5deg); } }
@keyframes lm3-glide { 0%, 100% { transform: translateY(0) rotateZ(-2deg); } 50% { transform: translateY(-5px) rotateZ(2deg); } }
@keyframes lm3-fringe { 0%, 100% { transform: rotateX(-14deg); } 50% { transform: rotateX(14deg); } }
@keyframes lm3-fringeB { 0%, 100% { transform: rotateX(14deg); } 50% { transform: rotateX(-14deg); } }
.mc3d.ghost .m3-bob { animation: lm3-float 2.8s ease-in-out infinite; }
.mc3d.ghost .m3-legL { animation: lm3-fringe 2.2s ease-in-out infinite; }
.mc3d.ghost .m3-legR { animation: lm3-fringeB 2.2s ease-in-out infinite; }
.mc3d.ghost .m3-shadow { animation: lm3-shadow 2.8s ease-in-out infinite; }
@keyframes lm3-shadow { 0%, 100% { transform: scale(1); opacity: .9; } 50% { transform: scale(.78); opacity: .55; } }
.mascot-fixed.walking .mc3d.ghost .m3-bob { animation: lm3-glide calc(var(--T, .72s) * 1.3) ease-in-out infinite; }
.mascot-fixed.walking .mc3d.ghost .m3-legL { animation: lm3-fringe calc(var(--T, .72s) * .8) ease-in-out infinite; }
.mascot-fixed.walking .mc3d.ghost .m3-legR { animation: lm3-fringeB calc(var(--T, .72s) * .8) ease-in-out infinite; }
.mascot-fixed.walking .mc3d.ghost .m3-armL { animation: lm3-armA calc(var(--T, .72s) * 1.3) ease-in-out infinite; }
.mascot-fixed.walking .mc3d.ghost .m3-armR { animation: lm3-armB calc(var(--T, .72s) * 1.3) ease-in-out infinite; }
.mascot-fixed.dance .mc3d.ghost .m3-bob { animation: lm3-dance 1.1s ease-in-out infinite; }
.ghost .m3-eyes { top: 40%; gap: 12px; }
.ghost .m3-eyes .eye { width: 13px; height: 19px; background: #2B2133; border-color: #2B2133; }
.ghost .m3-pupil { width: 5px; height: 6px; background: #fff; align-self: flex-start; margin-top: 3px; }
.ghost .cheek { top: 60%; width: 9px; height: 6px; background: #FFB3D1; }
.ghost .cheek.c1 { left: 6px; } .ghost .cheek.c2 { right: 6px; }
.ghost .mouth.gmouth { top: 66%; width: 12px; height: 7px; background: #2B2133; border: 0; border-radius: 0 0 12px 12px; }
.ghost .mouth.gmouth.o { width: 9px; height: 11px; border-radius: 50%; top: 64%; }
.ghost .brow { top: 30%; }
.ghost .badge { left: 56%; top: 20px; background: #FF8FB7; }
.ghost .m3-torso .f, .ghost .m3-skull .f { overflow: hidden; }
.mc3d.ghost::before { content: ""; position: absolute; left: -12px; top: 8px; width: 88px; height: 88px; border-radius: 50%; pointer-events: none;
  background: radial-gradient(circle, rgba(185,165,240,.5), rgba(185,165,240,0) 70%); }
@media (prefers-reduced-motion: reduce) { html:not(.lm-motion) .mc3d * { animation: none !important; transition: none !important; } }
</style>
"""


# Dark mode: switched by fx.py (class "lm-dark" on <html>). Charts are drawn on a transparent background in both modes; in dark mode the chart
# layer is colour-inverted (and hue-rotated back) so text, grid and series stay readable on the dark cards.
CSS_DARK = """
<style>
html.lm-dark { color-scheme: dark; }
html.lm-dark .stApp, html.lm-dark [data-testid="stAppViewContainer"], html.lm-dark [data-testid="stHeader"] {
  background: radial-gradient(1100px 560px at 88% -8%, rgba(255,143,183,.13), transparent 60%), radial-gradient(900px 520px at -8% 28%, rgba(171,70,210,.16), transparent 58%),
              linear-gradient(180deg, #17121D 0%, #1E1727 100%) !important; color: #EDE6F2; }
html.lm-dark [data-testid="stVerticalBlockBorderWrapper"], html.lm-dark [class*="st-key-card_"] { background: #261E30 !important; border-color: #3A2E47 !important; box-shadow: 0 10px 34px rgba(0,0,0,.35) !important; }
html.lm-dark .stMarkdown, html.lm-dark [data-testid="stMarkdownContainer"], html.lm-dark [data-testid="stCaptionContainer"], html.lm-dark label, html.lm-dark h1, html.lm-dark h2, html.lm-dark h3,
html.lm-dark h4, html.lm-dark .card-title, html.lm-dark [data-testid="stWidgetLabel"] p { color: #EDE6F2 !important; }
html.lm-dark [data-testid="stCaptionContainer"] { color: #B9ABC6 !important; }
html.lm-dark .stPlotlyChart { filter: invert(.9) hue-rotate(180deg); }
html.lm-dark .story, html.lm-dark .cmp-t, html.lm-dark .pchip, html.lm-dark .lm-motion-btn { background: #261E30; color: #EDE6F2; border-color: #3A2E47; }
html.lm-dark .story-t, html.lm-dark .sf span, html.lm-dark .cmp-t td, html.lm-dark .pop-title { color: #EDE6F2; }
html.lm-dark .story-t small, html.lm-dark .sf small, html.lm-dark .cmp-t th { color: #B9ABC6; }
html.lm-dark .cmp-t th, html.lm-dark .cmp-t td { border-bottom-color: #3A2E47; }
html.lm-dark [data-testid="stPopoverBody"], html.lm-dark [data-baseweb="popover"] > div { background: #261E30 !important; border-color: #3A2E47 !important; color: #EDE6F2; }
html.lm-dark [data-testid="stSelectbox"] [role="group"], html.lm-dark [data-testid="stMultiSelect"] [role="group"], html.lm-dark [data-testid="stNumberInput"] [role="group"], html.lm-dark [data-testid="stTextInput"] [role="group"], html.lm-dark [data-baseweb="select"] > div, html.lm-dark [data-baseweb="input"] > div, html.lm-dark [data-baseweb="base-input"] { background: #1E1727 !important; color: #EDE6F2 !important; border-color: #3A2E47 !important; }
html.lm-dark [data-testid="stSelectbox"] input, html.lm-dark [data-testid="stSelectbox"] svg, html.lm-dark [data-baseweb="select"] span, html.lm-dark [data-baseweb="select"] input, html.lm-dark [data-baseweb="menu"] li { color: #EDE6F2 !important; }
html.lm-dark [data-baseweb="menu"], html.lm-dark ul[role="listbox"] { background: #261E30 !important; }
html.lm-dark [data-testid="stSegmentedControl"] button, html.lm-dark [data-testid="stPills"] button { background: #1E1727 !important; color: #EDE6F2 !important; border-color: #3A2E47 !important; }
html.lm-dark [data-testid="stSegmentedControl"] button[aria-checked="true"], html.lm-dark [data-testid="stPills"] button[aria-checked="true"], html.lm-dark [data-testid="stPills"] button[aria-pressed="true"] {
  background: #E83C91 !important; color: #fff !important; border-color: #E83C91 !important; }
html.lm-dark [data-testid="stExpander"] { background: #261E30; border-color: #3A2E47; color: #EDE6F2; }
html.lm-dark [data-testid="stDialog"] > div, html.lm-dark div[role="dialog"] { background: #261E30 !important; color: #EDE6F2; }
html.lm-dark .empty-card { background: #2B2236; border-color: #3A2E47; color: #EDE6F2; }
html.lm-dark .rmap path { stroke: #261E30; }
html.lm-dark .st-key-nav_page { background: #261E30; }
html.lm-dark .st-key-nav_page label p { color: #EDE6F2 !important; }
html.lm-dark .st-key-nav_page label:has(input:checked) p { color: #fff !important; }
html.lm-dark .rlg, html.lm-dark .rlg b, html.lm-dark .ins { color: #EDE6F2; }
html.lm-dark .mf-bubble { background: #261E30; color: #EDE6F2; border-color: #FF8FB7; }
</style>
"""

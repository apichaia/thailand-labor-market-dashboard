"""Colours, fonts and CSS. Thai font loads from Google Fonts when online and
falls back to system Thai fonts when offline (the app never depends on it)."""

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
@import url('https://fonts.googleapis.com/css2?family=Kanit:wght@300;400;500;600;700;800&display=swap');
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
.info-box .k { display:block; font-size:.72rem; color:%MUTED%; line-height:1.1; }
.info-box .v { display:block; font-size:.9rem; font-weight:700; color:%PLUM%; line-height:1.3; }
.info-box .ir.src .v { font-weight:500; font-size:.8rem; }
.side-reset button { background: linear-gradient(90deg, %MAGENTA%, %PINK%) !important; color:#fff !important; border:none !important; border-radius: 12px !important; font-weight: 700; }
.side-reset button p { color:#fff !important; }

/* ---- hero banner ---- */
.st-key-hero { position: relative; border-radius: 24px; padding: 20px 26px 16px 26px; overflow: hidden; margin-bottom: 14px;
  background-image: linear-gradient(95deg, rgba(67,51,76,.86) 0%, rgba(67,51,76,.55) 42%, rgba(232,60,145,.22) 100%), url(app/static/hero.png);
  background-size: cover; background-position: center 38%; box-shadow: 0 6px 20px rgba(67,51,76,.18); }
.st-key-hero h1.hero-t { color:#fff; font-size: 2.1rem; font-weight: 800; margin: 0; line-height: 1.2; text-shadow: 0 2px 8px rgba(0,0,0,.35); }
.st-key-hero .hero-s { color:#FFE9F2; font-size: 1.02rem; margin-top: 4px; text-shadow: 0 1px 6px rgba(0,0,0,.4); }
.hero-chips { display:flex; flex-wrap:wrap; gap:10px; margin-top: 14px; }
.hero-chip { display:flex; gap:10px; align-items:center; background: rgba(255,255,255,.93); border-radius: 14px; padding: 8px 14px; min-width: 150px; }
.hero-chip .ic { font-size: 1.3rem; }
.hero-chip .k { font-size: .72rem; color: %MUTED%; line-height:1.1; }
.hero-chip .v { font-size: .98rem; font-weight: 700; color: %PLUM%; line-height:1.25; }
.hero-chip.warn { background:#FFF4DF; } .hero-chip.err { background:#FFE2E2; }
/* page navigation: three pills in the banner */
.st-key-hero .st-key-nav_page { background: rgba(255,255,255,.95); border-radius: 999px; padding: 4px; margin: 0; width: auto !important; display:inline-block; float:right; }
.st-key-hero .st-key-nav_page [role="radiogroup"] { flex-wrap: nowrap; gap: 2px; width: auto; }
.st-key-hero .st-key-nav_page label { border: none; border-radius: 999px; padding: 8px 22px; }
.st-key-hero .st-key-nav_page label p { color: %PLUM% !important; font-weight: 700; }
.st-key-hero .st-key-nav_page label:has(input:checked) { background: linear-gradient(90deg, %MAGENTA%, %PINK%); border-bottom-color: transparent; }
.st-key-hero .st-key-nav_page label:has(input:checked) p { color:#fff !important; }
.st-key-hero button[kind="secondary"], .st-key-hero [data-testid="stBaseButton-secondary"] { background: rgba(255,255,255,.18); color:#fff; border: 1px solid rgba(255,255,255,.7); border-radius: 12px; }
.st-key-hero [data-testid="stBaseButton-secondary"] p { color:#fff !important; }

/* ---- gradient KPI cards ---- */
.gcard { position:relative; display:flex; flex-wrap:wrap; align-items:center; align-content:space-between; gap:8px 9px; border-radius: 20px; padding: 14px 14px 12px 14px; min-height: 172px; color:#fff;
  box-shadow: 0 6px 16px rgba(67,51,76,.20); overflow:hidden; }
.gcard.g1 { background: linear-gradient(135deg, %MAGENTA% 0%, %PINK% 100%); }
.gcard.g2 { background: linear-gradient(135deg, #7A3F8F 0%, #B05AA0 100%); }
.gcard.g3 { background: linear-gradient(135deg, %PLUM% 0%, #8A4A7E 100%); }
.gcard.g4 { background: linear-gradient(135deg, #5B3A75 0%, #A44C93 100%); }
.gcard .gc-icon { width: 42px; height: 42px; font-size: 1.15rem; border-radius: 50%; background: rgba(255,255,255,.22); border: 2px solid rgba(255,255,255,.55);
  display:flex; align-items:center; justify-content:center; font-size: 1.5rem; flex: none; }
.gcard .gc-body { flex: 1; min-width: 0; }
.gcard .gc-label { font-size: .92rem; white-space: nowrap; font-weight: 700; opacity: .96; }
.gcard .gc-value { font-size: clamp(1.4rem, 1.9vw, 1.9rem); font-weight: 800; line-height: 1.15; display:flex; flex-wrap:wrap; align-items:baseline; column-gap:5px; }
.gcard .gc-value span { font-size: .8rem; font-weight: 600; opacity: .95; white-space: nowrap; }
.gcard .gc-scope { font-size: .74rem; opacity: .88; margin-top: 2px; line-height: 1.25; min-height: 2.5em; }
.gcard .gc-delta { font-size: .86rem; margin-top: 2px; opacity: .97; }
.gcard .gc-delta small { opacity: .85; margin-left: 4px; }
.gcard .gc-na { font-size: 1.05rem; font-weight: 700; margin-top: 8px; }
.gcard .gc-spark { flex: 1 1 100%; width: 100%; order: 3; opacity: .95; min-height: 36px; }
.gcard .gc-spark svg { width: 100%; height: 36px; display:block; }
@media (max-width: 900px) { .gcard .gc-value { font-size: 1.8rem; } }

/* ---- cards that hold charts ---- */
[class*="st-key-card_"] { border-radius: 18px !important; box-shadow: 0 3px 10px rgba(67,51,76,.08); }
.card-title { display:flex; align-items:center; gap:8px; font-weight: 800; font-size: 1.05rem; color: %PLUM%; }
.card-title::before { content:""; width: 8px; height: 22px; border-radius: 4px; background: linear-gradient(180deg, %MAGENTA%, %PINK%); display:inline-block; }
.ins { display:flex; gap:12px; align-items:flex-start; background:#FFF6FA; border-radius:14px; padding: 10px 12px; margin-bottom: 8px; }
.ins .n { flex:none; width: 30px; height:30px; border-radius:50%; background: linear-gradient(135deg, %MAGENTA%, %PINK%); color:#fff; font-weight:800; display:flex; align-items:center; justify-content:center; }
.ins b { color: %PLUM%; }
.ins .s { font-size:.84rem; color:%MUTED%; }

@media (max-width: 640px) {
  .st-key-hero { padding: 14px 14px 12px 14px; }
  .st-key-hero h1.hero-t { font-size: 1.45rem; }
  .st-key-hero .hero-s { font-size: .86rem; }
  .st-key-hero .st-key-nav_page { float: none; display:block; width: 100% !important; overflow-x:auto; }
  .st-key-hero .st-key-nav_page label { padding: 7px 14px; white-space: nowrap; }
  .hero-chip { min-width: 46%; flex: 1; padding: 6px 10px; }
}
</style>
""".replace("%PLUM%", PLUM).replace("%MAGENTA%", MAGENTA).replace("%PINK%", PINK).replace("%BORDER%", BORDER).replace("%MUTED%", MUTED)

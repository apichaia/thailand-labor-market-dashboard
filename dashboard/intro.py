"""The intro film shown before the dashboard.

It is a HyperFrames composition: one self-contained HTML page (CSS layout + one paused, seekable GSAP timeline registered in
``window.__timelines``). The same page is used twice:

* inside the app it plays live as a full-screen overlay (so it can show the newest numbers and starts at once),
* ``tools/build_intro.py`` writes it into a HyperFrames project and ``npx hyperframes render`` turns it into an MP4.

Only values read from the validated tables are shown (see ``data_processing/intro_payload.py``)."""
from __future__ import annotations

import html
import json

import streamlit as st

DURATION = 10.0
CARD_GRADIENTS = ["linear-gradient(135deg,#C92A7C,#E8509A)", "linear-gradient(135deg,#7A3F8F,#B05AA0)", "linear-gradient(135deg,#43334C,#8A4A7E)", "linear-gradient(135deg,#5B3A75,#A44C93)"]

CSS = """
:root { --cream: #F8F4EC; --pink: #FF8FB7; --mag: #E83C91; --plum: #43334C; --lav: #AB46D2; }
#cmp { position: relative; width: 1920px; height: 1080px; overflow: hidden; color: #43334C; font-family: 'Kanit', sans-serif;
  background: radial-gradient(1300px 760px at 82% 8%, #FFD3E6 0, transparent 62%), radial-gradient(1000px 760px at 8% 96%, #E4D2F6 0, transparent 58%), #F8F4EC; }
#cmp .clip { position: absolute; inset: 0; }
#cmp .blob { position: absolute; border-radius: 50%; }
#cmp #b1 { width: 520px; height: 520px; left: -140px; top: -160px; background: radial-gradient(circle, rgba(255,143,183,.55), rgba(255,143,183,0) 70%); }
#cmp #b2 { width: 640px; height: 640px; right: 380px; bottom: -300px; background: radial-gradient(circle, rgba(171,70,210,.30), rgba(171,70,210,0) 70%); }
#cmp #b3 { width: 360px; height: 360px; right: -90px; top: 120px; background: radial-gradient(circle, rgba(252,246,156,.65), rgba(252,246,156,0) 70%); }
#cmp #logo { position: absolute; left: 150px; top: 44px; width: 100px; height: 100px; border-radius: 30px; background: linear-gradient(135deg, #FF8FB7, #E83C91);
  box-shadow: 0 18px 40px rgba(232,60,145,.45); display: flex; align-items: flex-end; justify-content: center; gap: 11px; padding-bottom: 22px; }
#cmp #logo i { display: block; width: 18px; border-radius: 6px; background: #fff; }
#cmp #t1 { position: absolute; left: 150px; top: 250px; margin: 0; font-size: 140px; line-height: 1.08; font-weight: 800; letter-spacing: -2px; transform-origin: 0 0; }
#cmp #t1 .line { display: block; overflow: hidden; padding-bottom: 12px; }
#cmp #t1 .w { display: inline-block; }
#cmp #t1 .line:nth-child(2) .w { background: linear-gradient(90deg, #E83C91, #AB46D2); -webkit-background-clip: text; background-clip: text; color: transparent; }
#cmp #sub { position: absolute; left: 154px; top: 612px; font-size: 46px; font-weight: 400; opacity: .78; }
#cmp #map { position: absolute; left: 1200px; top: 70px; width: 660px; height: 930px; overflow: visible; filter: drop-shadow(0 26px 30px rgba(67,51,76,.22)); }
#cmp #map .reg { transform-box: fill-box; transform-origin: 50% 50%; }
#cmp #map path { stroke: #fff; stroke-width: 4; stroke-linejoin: round; }
#cmp #legend { position: absolute; left: 150px; top: 690px; width: 900px; display: flex; flex-wrap: wrap; gap: 18px 16px; }
#cmp .chip { display: inline-flex; align-items: center; gap: 14px; padding: 12px 26px 12px 18px; border-radius: 999px; background: #fff; box-shadow: 0 8px 22px rgba(67,51,76,.12); font-size: 36px; font-weight: 600; }
#cmp .chip i { display: block; width: 26px; height: 26px; border-radius: 50%; }
#cmp #cards { position: absolute; left: 150px; top: 470px; width: 900px; display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }
#cmp .card { border-radius: 36px; padding: 18px 32px 14px; color: #fff; box-shadow: 0 18px 40px rgba(67,51,76,.25); }
#cmp .card .l { font-size: 30px; font-weight: 600; opacity: .95; }
#cmp .card .v { font-size: 80px; font-weight: 800; line-height: 1.1; font-variant-numeric: tabular-nums; }
#cmp .card .v small { font-size: 32px; font-weight: 600; margin-left: 10px; opacity: .95; }
#cmp .card .p { font-size: 28px; opacity: .95; }
#cmp #cta { position: absolute; left: 150px; top: 960px; padding: 16px 44px; border-radius: 999px; font-size: 40px; font-weight: 700; color: #fff;
  background: linear-gradient(90deg, #B8226F, #E83C91); box-shadow: 0 14px 34px rgba(232,60,145,.45); }
"""


def _fmt(v: float, dec: int) -> str:
    return f"{v:,.{dec}f}"


def body(payload: dict | None) -> str:
    """The inside of the composition root (HTML)."""
    payload = payload or {}
    mp, kpis = payload.get("map"), payload.get("kpis") or []
    parts = ['<div class="blob" id="b1"></div><div class="blob" id="b2"></div><div class="blob" id="b3"></div>',
             '<section id="stage" class="clip" data-start="0" data-duration="%s" data-track-index="1">' % DURATION,
             '<div id="logo"><i style="height:30px"></i><i style="height:52px"></i><i style="height:74px"></i></div>',
             '<h1 id="t1"><span class="line"><span class="w">ศูนย์วิเคราะห์</span></span><span class="line"><span class="w">ตลาดแรงงานไทย</span></span></h1>',
             '<p id="sub">การจ้างงาน · การว่างงาน · ค่าจ้าง · ห้าภูมิภาคของไทย</p>']
    if mp:
        x, y, w, h = mp["viewBox"]
        regs = "".join(f'<g class="reg" id="r-{r["id"]}"><path d="{r["d"]}" fill="{r["color"]}"/></g>' for r in mp["regions"])
        parts.append(f'<svg id="map" viewBox="{x} {y} {w} {h}" preserveAspectRatio="xMidYMid meet">{regs}</svg>')
        chips = "".join(f'<span class="chip"><i style="background:{r["color"]}"></i>{html.escape(r["name"])}</span>' for r in mp["regions"])
        parts.append(f'<div id="legend">{chips}</div>')
    if kpis:
        cards = "".join(
            f'<div class="card" style="background:{CARD_GRADIENTS[i % 4]}"><div class="l">{html.escape(k["label"])}</div>'
            f'<div class="v"><span class="n" data-val="{k["value"]}" data-dec="{k["dec"]}">{_fmt(0, k["dec"])}</span><small>{html.escape(k["unit"])}</small></div>'
            f'<div class="p">{html.escape(k["period"])}</div></div>' for i, k in enumerate(kpis[:4]))
        parts.append(f'<div id="cards">{cards}</div>')
    parts.append('<div id="cta">เริ่มสำรวจข้อมูล →</div></section>')
    return "".join(parts)


SCRIPT = r"""
window.__timelines = window.__timelines || {};
(function () {
  const tl = gsap.timeline({ paused: true });
  const cmp = document.querySelector("#cmp");
  const $ = (sel) => Array.from(cmp.querySelectorAll(sel));          // scoped: the app page has ids of its own
  tl.to($("#b1"), { x: 120, y: 90, duration: 10, ease: "sine.inOut" }, 0);
  tl.to($("#b2"), { x: -90, y: -110, duration: 10, ease: "sine.inOut" }, 0);
  tl.to($("#b3"), { x: -70, y: 120, duration: 10, ease: "sine.inOut" }, 0);
  // scene 1: logo and title
  tl.from($("#logo"), { scale: 0, rotation: -28, duration: 0.8, ease: "back.out(2)" }, 0.1);
  tl.from($("#logo i"), { scaleY: 0, transformOrigin: "50% 100%", duration: 0.5, ease: "power3.out", stagger: 0.12 }, 0.5);
  tl.from($("#t1 .w"), { yPercent: 115, opacity: 0, duration: 0.95, ease: "power4.out", stagger: 0.2 }, 0.45);
  tl.from($("#sub"), { opacity: 0, y: 30, duration: 0.8, ease: "power2.out" }, 1.35);
  // scene 2: the five regions pop up one by one
  if ($("#map").length) {
    tl.from($("#map .reg"), { opacity: 0, scale: 0.55, duration: 0.7, ease: "back.out(1.8)", stagger: 0.38 }, 2.4);
    tl.from($("#legend .chip"), { opacity: 0, x: -50, duration: 0.55, ease: "power3.out", stagger: 0.38 }, 2.4);
    tl.to($("#map"), { scale: 1.04, transformOrigin: "50% 50%", duration: 7.6, ease: "none" }, 2.4);
    tl.to($("#legend"), { opacity: 0, y: -24, duration: 0.45, ease: "power2.in" }, 5.0);
  }
  // scene 3: the title steps aside and the latest numbers count up
  tl.to($("#sub"), { opacity: 0, duration: 0.35 }, 5.0);
  tl.to($("#t1"), { y: -90, scale: 0.78, duration: 0.85, ease: "power3.inOut" }, 5.0);
  const nums = $("#cards .n");
  if (nums.length) {
    tl.from($("#cards .card"), { y: 70, clipPath: "inset(100% 0% 0% 0% round 36px)", duration: 0.8, ease: "power3.out", stagger: 0.14 }, 5.45);
    nums.forEach((el, i) => {
      const target = parseFloat(el.dataset.val), dec = parseInt(el.dataset.dec, 10), o = { v: 0 };
      tl.to(o, { v: target, duration: 1.6, ease: "power2.out",
                 onUpdate: () => { el.textContent = o.v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }); } }, 5.6 + i * 0.14);
    });
  }
  tl.from($("#cta"), { opacity: 0, y: 36, scale: 0.9, duration: 0.65, ease: "back.out(2)" }, 6.9);
  tl.to({}, { duration: 0.01 }, __DURATION__ - 0.01);
  window.__timelines["main"] = tl;
  tl.seek(0);
})();
""".replace("__DURATION__", str(DURATION))


def standalone_html(payload: dict | None) -> str:
    """The composition as a HyperFrames project page (``index.html``)."""
    return f"""<!doctype html>
<html lang="th" data-resolution="landscape">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link href="https://fonts.googleapis.com/css2?family=Kanit:wght@400;600;700;800&display=swap" rel="stylesheet" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: 1920px; height: 1080px; overflow: hidden; background: #F8F4EC; }}
{CSS}
    </style>
  </head>
  <body>
    <div id="cmp" data-composition-id="main" data-start="0" data-duration="{DURATION}" data-width="1920" data-height="1080">
      {body(payload)}
    </div>
    <script>
{SCRIPT}
    </script>
  </body>
</html>
"""


# ---------------------------------------------------------------------------
# inside the app: the same page plays live as a full-screen overlay
# ---------------------------------------------------------------------------

_JS = r"""
export default function(component) {
    const { data } = component;
    const w = window;
    if (!data || !data.play) return;           // later reruns only keep this element in place; they must not restart or touch the film
    if (w.__lmIntro) return;
    w.__lmIntro = true;                          // plays on every visit (once per page load); the settings menu can replay it
    const ov = document.createElement('div');
    ov.id = 'lm-intro';
    ov.style.cssText = 'position:fixed;inset:0;z-index:2147483000;overflow:hidden;opacity:1;transition:opacity .7s ease;'
        + 'background:radial-gradient(1200px 700px at 80% 5%,#FFD3E6,transparent 60%),radial-gradient(900px 700px at 5% 95%,#E4D2F6,transparent 55%),#F8F4EC;font-family:Kanit,sans-serif;';
    const st = document.createElement('style');
    st.textContent = data.css + '#lm-intro button{font-family:Kanit,sans-serif;cursor:pointer}';
    ov.appendChild(st);
    const stage = document.createElement('div');
    stage.style.cssText = 'position:absolute;left:50%;top:50%;width:1920px;height:1080px;transform-origin:50% 50%;';
    stage.innerHTML = '<div id="cmp">' + data.body + '</div>';
    ov.appendChild(stage);
    const skip = document.createElement('button');
    skip.textContent = 'ข้ามอินโทร ›';
    skip.style.cssText = 'position:absolute;right:28px;top:22px;padding:10px 22px;border-radius:999px;border:2px solid #43334C;background:rgba(255,255,255,.75);color:#43334C;font-size:16px;font-weight:600;';
    const enter = document.createElement('button');
    enter.textContent = 'เข้าสู่แดชบอร์ด →';
    enter.style.cssText = 'position:absolute;left:50%;bottom:34px;transform:translateX(-50%);padding:14px 40px;border:none;border-radius:999px;background:linear-gradient(90deg,#E83C91,#FF8FB7);'
        + 'color:#fff;font-size:20px;font-weight:700;box-shadow:0 12px 30px rgba(232,60,145,.45);opacity:0;pointer-events:none;transition:opacity .5s ease;';
    ov.appendChild(skip); ov.appendChild(enter);
    document.body.appendChild(ov);
    const fit = () => { const s = Math.min(innerWidth / 1920, innerHeight / 1080); stage.style.transform = 'translate(-50%,-50%) scale(' + s + ')'; };
    fit(); w.addEventListener('resize', fit);
    let closed = false, timer = null;
    function finish() {
        if (closed) return;
        closed = true;
        try { w.localStorage.setItem(SEEN, '1'); } catch (e) { /* private window: the film simply plays again next visit */ }
        clearTimeout(timer);
        w.removeEventListener('resize', fit);
        ov.style.opacity = '0';
        setTimeout(() => { ov.remove(); w.__lmIntro = false; }, 750);   // no message back to Python: it would rerun the whole page
    }
    skip.onclick = finish;
    enter.onclick = finish;
    function play() {
        try {
            new Function(data.js)();
            const tl = w.__timelines && w.__timelines.main;
            if (!tl) { finish(); return; }
            setTimeout(() => { enter.style.opacity = '1'; enter.style.pointerEvents = 'auto'; }, 7800);
            tl.eventCallback('onComplete', () => { timer = setTimeout(finish, 2000); });   // leaves on its own after the last frame
            tl.play(0);
        } catch (e) { finish(); }
    }
    if (w.gsap) { play(); return; }
    const sc = document.createElement('script');                  // without internet the intro is skipped, never blocking the dashboard
    sc.src = 'https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js';
    sc.onload = play;
    sc.onerror = finish;
    document.head.appendChild(sc);
    setTimeout(() => { if (!w.gsap) finish(); }, 6000);
}
"""

_INTRO = st.components.v2.component("lm_intro", js=_JS)


def mount(payload: dict | None) -> None:
    """Start the film once per visit, and only on the first visit in this browser unless replayed. The component is drawn on EVERY run, in the same place: if it appeared and vanished, every element
    after it would shift position and the whole page would be rebuilt (a blank flash with duplicated mascots when the film ended)."""
    play = bool(payload) and not st.session_state.get("intro_started", False)
    if play:
        st.session_state["intro_started"] = True
        force = st.session_state.pop("intro_force", False)
        _INTRO(data={"play": True, "force": force, "css": CSS, "body": body(payload), "js": SCRIPT}, key="lm_intro")
    else:
        _INTRO(data={"play": False}, key="lm_intro")


def replay() -> None:
    st.session_state["intro_started"] = False
    st.session_state["intro_force"] = True   # plays even though this browser has already seen it

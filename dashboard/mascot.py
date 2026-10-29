"""The dashboard's mascot: a friendly salaried office worker (white shirt, magenta tie, ID badge on a lanyard) drawn as inline SVG and
animated with CSS (see theme.CSS_FX).

Original artwork made of simple shapes: no image files, nothing downloaded. The animation classes are
``mc-bob`` (floating / walking bob), ``mc-eyes`` (blinking), ``mc-pupil`` (looks at the pointer), ``mc-armL`` / ``mc-armR``
(arms: swinging, waving, pointing), ``mc-legL`` / ``mc-legR`` (steps) and ``mc-q`` (the question mark)."""
from __future__ import annotations

_SKIN = "#FFD9C2"
_HAIR = "#43334C"
_SHIRT = "#FFFFFF"
_TIE = "#E83C91"
_PANTS = "#43334C"
_LINE = "#43334C"


def _arm(cls: str, d: str, hand: tuple[float, float]) -> str:
    """A shirt sleeve (white with a dark outline) ending in a skin-coloured hand."""
    return (f'<g class="{cls}"><path d="{d}" stroke="{_LINE}" stroke-width="9" stroke-linecap="round" fill="none"/>'
            f'<path d="{d}" stroke="{_SHIRT}" stroke-width="6" stroke-linecap="round" fill="none"/>'
            f'<circle cx="{hand[0]}" cy="{hand[1]}" r="4.6" fill="{_SKIN}" stroke="{_LINE}" stroke-width="1.4"/></g>')


# legs, left arm, [right arm], shirt, collar, tie, belt, ID badge, neck, head, hair, [face]
_BODY = (
    '<ellipse class="mc-shadow" cx="45" cy="105" rx="22" ry="4" fill="rgba(67,51,76,.28)"/>'
    '<g class="mc-bob">'
    + f'<rect class="mc-legL" x="31" y="86" width="11" height="16" rx="5" fill="{_PANTS}"/>'
    + f'<rect class="mc-legR" x="48" y="86" width="11" height="16" rx="5" fill="{_PANTS}"/>'
    + '<ellipse cx="35" cy="103" rx="7" ry="3" fill="#2B2133"/><ellipse cx="55" cy="103" rx="7" ry="3" fill="#2B2133"/>'
    + _arm("mc-armL", "M27 60 Q17 68 17 80", (17, 83))
    + "@@RIGHT_ARM@@"
    + f'<rect x="24" y="50" width="42" height="42" rx="12" fill="{_SHIRT}" stroke="{_LINE}" stroke-width="1.6"/>'
    + f'<path d="M37 50 L45 60 L53 50" fill="#F1E7EE" stroke="{_LINE}" stroke-width="1.4" stroke-linejoin="round"/>'
    + f'<path d="M45 59 L41.5 63 L45 82 L48.5 63 Z" fill="{_TIE}" stroke="{_LINE}" stroke-width="1.2" stroke-linejoin="round"/>'
    + f'<rect x="24" y="86" width="42" height="5" rx="2.5" fill="{_PANTS}"/>'
    + '<path d="M37 50 L40 70 M53 50 L50 70" stroke="#FF8FB7" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
    + '<rect x="38.5" y="68" width="13" height="9" rx="2" fill="#FF8FB7" stroke="#43334C" stroke-width="1"/>'
    + '<rect x="40.5" y="70" width="5" height="2" rx="1" fill="#fff"/><rect x="40.5" y="73.2" width="8" height="1.4" rx=".7" fill="#fff" opacity=".8"/>'
    + f'<rect x="40" y="43" width="10" height="9" rx="3" fill="{_SKIN}" stroke="{_LINE}" stroke-width="1.2"/>'
    + f'<circle cx="45" cy="30" r="17" fill="{_SKIN}" stroke="{_LINE}" stroke-width="1.6"/>'
    + f'<path d="M28 30 Q27 11 45 11 Q63 11 62 30 Q58 20 49 20 Q40 22 34 19 Q29 22 28 30 Z" fill="{_HAIR}"/>'
    + "@@FACE@@"
    + '</g>')

_FACE_HAPPY = (
    '<g class="mc-eyes"><ellipse cx="38" cy="32" rx="3.8" ry="4.6" fill="#fff" stroke="#43334C" stroke-width=".8"/>'
    '<ellipse cx="52" cy="32" rx="3.8" ry="4.6" fill="#fff" stroke="#43334C" stroke-width=".8"/>'
    '<circle class="mc-pupil" cx="38.4" cy="32.6" r="2.1" fill="#43334C"/><circle class="mc-pupil" cx="52.4" cy="32.6" r="2.1" fill="#43334C"/></g>'
    '<circle cx="32" cy="38" r="2.8" fill="#FFB3D1" opacity=".85"/><circle cx="58" cy="38" r="2.8" fill="#FFB3D1" opacity=".85"/>'
    '<path d="M40 40 Q45 45.5 50 40" stroke="#43334C" stroke-width="2" fill="none" stroke-linecap="round"/>')

_FACE_UNSURE = (
    '<g class="mc-eyes"><ellipse cx="38" cy="32" rx="3.8" ry="4.6" fill="#fff" stroke="#43334C" stroke-width=".8"/>'
    '<ellipse cx="52" cy="32" rx="3.8" ry="4.6" fill="#fff" stroke="#43334C" stroke-width=".8"/>'
    '<circle cx="40" cy="31" r="2.1" fill="#43334C"/><circle cx="54" cy="31" r="2.1" fill="#43334C"/></g>'
    '<path d="M34 25 Q38 21.5 42 24.5" stroke="#43334C" stroke-width="1.6" stroke-linecap="round" fill="none"/>'
    '<path d="M48 26 L56 26" stroke="#43334C" stroke-width="1.6" stroke-linecap="round"/>'
    '<path d="M40 42 Q43 39.5 45 42 T50 42" stroke="#43334C" stroke-width="1.9" fill="none" stroke-linecap="round"/>')

# the waving arm turns about the right shoulder (see theme.CSS_FX: transform-origin 63px 58px)
_ARM_WAVE = _arm("mc-armR", "M63 58 Q75 52 74 38", (74, 35))
_ARM_REST = _arm("mc-armR", "M63 60 Q73 68 73 80", (73, 83))


def _build(right_arm: str, face: str) -> str:
    return _BODY.replace("@@RIGHT_ARM@@", right_arm).replace("@@FACE@@", face)


def happy(extra_class: str = "") -> str:
    """Waving, blinking mascot (the banner and the roaming one)."""
    return (f'<svg class="mc {extra_class}" viewBox="0 0 92 110" role="img" aria-label="มาสคอตพนักงานเงินเดือน">'
            + _build(_ARM_WAVE, _FACE_HAPPY) + '</svg>')


def unsure(extra_class: str = "") -> str:
    """Puzzled mascot with a floating question mark (shown where a chart has no data)."""
    q = ('<g class="mc-q"><circle cx="74" cy="16" r="11" fill="#FCF69C" stroke="#43334C" stroke-width="2"/>'
         '<text x="74" y="21.5" text-anchor="middle" font-size="15" font-weight="800" fill="#43334C" font-family="Kanit, sans-serif">?</text></g>')
    return (f'<svg class="mc {extra_class}" viewBox="0 0 92 110" role="img" aria-label="ไม่มีข้อมูล">'
            + _build(_ARM_REST, _FACE_UNSURE) + q + '</svg>')


# ---------------------------------------------------------------------------------------------------------------------
# 3D version: a toy-like office worker made of CSS 3D boxes (no image, no WebGL, nothing downloaded). Every part is a box with six
# faces (see theme.CSS_3D); the limbs hang from joints so they can swing like a walking person, and the whole body turns
# (rotateY) to face the direction it walks. Class names: m3-legL/R, m3-armL/R, m3-head, m3-eyes, m3-pupil, m3-bob, m3-q.
# ---------------------------------------------------------------------------------------------------------------------

def _box(cls: str, w: float, h: float, d: float, x: float, y: float, *, front: str = "#fff", back: str | None = None, side: str | None = None,
         top: str | None = None, bottom: str = "#2B2133", inner: str = "", rad: int = 6, extra: str = "") -> str:
    """A box ``w x h x d`` (px, design units) whose top-left is (x, y). ``front`` / ``side`` / ``top`` are CSS backgrounds."""
    vars_ = (f"--w:{w}px;--h:{h}px;--d:{d}px;--c:{front};--k:{back or front};--s:{side or front};--t:{top or front};--b:{bottom};"
             f"--rad:{rad}px;left:{x}px;top:{y}px;{extra}")
    return (f'<div class="cb {cls}" style="{vars_}"><i class="f">{inner}</i><i class="k"></i><i class="r"></i><i class="l"></i>'
            '<i class="t"></i><i class="b"></i></div>')


def _limb(cls: str, jx: float, jy: float, inner: str) -> str:
    """A part that swings about the joint at (jx, jy)."""
    return f'<div class="limb {cls}" style="left:{jx}px;top:{jy}px">{inner}</div>'


_SK, _SK2 = "#FFD9C2", "#EBBFA3"
_HR = "#43334C"
_FACE_OK = (
    '<b class="fringe"></b>'
    '<div class="m3-eyes"><span class="eye"><u class="m3-pupil"></u></span><span class="eye"><u class="m3-pupil"></u></span></div>'
    '<b class="cheek c1"></b><b class="cheek c2"></b><b class="mouth smile"></b>')
_FACE_UNSURE = (
    '<b class="fringe"></b>'
    '<div class="m3-eyes"><span class="eye"><u class="m3-pupil"></u></span><span class="eye"><u class="m3-pupil"></u></span></div>'
    '<b class="brow b1"></b><b class="brow b2"></b><b class="mouth flat"></b>')


def _figure(face: str, extra_class: str, bubble: str = "") -> str:
    torso = _box(
        "m3-torso", 44, 52, 26, 25, 62,
        front="linear-gradient(#fff 0 86%, #43334C 86%)", side="linear-gradient(#E6DCEC 0 86%, #342A3C 86%)", top="#fff", bottom="#2B2133",
        inner='<b class="collar"></b><b class="tie"></b><b class="knot"></b><b class="badge"></b>', rad=4)
    head = _limb("m3-head", 47, 60, _box(
        "m3-skull", 48, 44, 40, -24, -44,
        front=_SK, back=_HR, side=f"linear-gradient({_HR} 0 44%, {_SK2} 44%)", top=_HR, bottom=_SK2, inner=face, rad=7))
    arm = lambda cls, jx: _limb(cls, jx, 68,
                                _box("", 12, 32, 12, -6, 0, front="#fff", side="#E6DCEC", top="#fff", bottom="#E6DCEC", rad=3)
                                + _box("", 11, 11, 11, -5.5, 31, front=_SK, side=_SK2, top=_SK, bottom=_SK2, rad=3))
    leg = lambda cls, jx: _limb(cls, jx, 112,
                                _box("", 16, 34, 16, -8, 0, front="#43334C", side="#342A3C", top="#43334C", bottom="#2B2133", rad=3)
                                + _box("", 18, 9, 27, -9, 33, front="#2B2133", side="#1E1624", top="#352A3F", bottom="#150F1A", rad=3, extra="transform:translateZ(5px);"))
    rig = ('<div class="m3-bob">' + leg("m3-legL", 38) + leg("m3-legR", 56) + torso + arm("m3-armL", 19) + arm("m3-armR", 75) + head + '</div>')
    return (f'<div class="mc3d {extra_class}" role="img" aria-label="มาสคอตพนักงานเงินเดือน (3 มิติ)"><div class="m3-shadow"></div>'
            f'<div class="mc3d-in"><div class="rig">{rig}</div></div>{bubble}</div>')


# --- the ghost: a friendly sheet-ghost that still works at a desk (ID badge on its sheet). Same part classes as the worker, so every pose
# and walk of the script works unchanged: the "legs" are the swaying fringe of the sheet, and it floats above its shadow.
_GH_FRONT = "radial-gradient(ellipse at 50% 28%, #FFFFFF 58%, #EDE6F8 100%)"
_GH_SIDE = "linear-gradient(90deg, #DDD3F1, #EFE9FA)"

_GHOST_EYES = ('<div class="m3-eyes"><span class="eye"><u class="m3-pupil"></u></span><span class="eye"><u class="m3-pupil"></u></span></div>'
               '<b class="cheek c1"></b><b class="cheek c2"></b>')
_GHOST_HAPPY = _GHOST_EYES + '<b class="mouth gmouth"></b>'
_GHOST_UNSURE = _GHOST_EYES + '<b class="brow b1"></b><b class="brow b2"></b><b class="mouth gmouth o"></b>'


def _ghost(face: str, extra_class: str, bubble: str = "") -> str:
    body = _box("m3-torso", 50, 56, 32, 22, 70, front=_GH_FRONT, back="#F3EEF9", side=_GH_SIDE, top="#fff", bottom="#CBBFE6",
                inner='<b class="badge"></b>', rad=8)
    head = _limb("m3-head", 47, 70, _box(
        "m3-skull", 54, 46, 36, -27, -46, front=_GH_FRONT, back="#F3EEF9", side=_GH_SIDE, top="#fff", bottom="#E3DBF3", inner=face, rad=12))
    arm = lambda cls, jx: _limb(cls, jx, 88, _box("", 11, 30, 11, -5.5, 0, front="#fff", side="#DDD3F1", top="#fff", bottom="#DDD3F1", rad=5))
    piece = lambda x, h: _box("", 12.5, h, 30, x, 0, front="linear-gradient(#FFFFFF, #EDE6F8 55%, #D9CEF0)", back="#F3EEF9", side="#DDD3F1", top="#fff", bottom="#CBBFE6", rad=4)
    fringeL = _limb("m3-legL", 34.5, 126, piece(-12.5, 17) + piece(0, 24))
    fringeR = _limb("m3-legR", 59.5, 126, piece(-12.5, 24) + piece(0, 17))
    rig = '<div class="m3-bob">' + fringeL + fringeR + body + arm("m3-armL", 19) + arm("m3-armR", 75) + head + '</div>'
    return (f'<div class="mc3d ghost {extra_class}" role="img" aria-label="มาสคอตผีน้อยพนักงานเงินเดือน (3 มิติ)"><div class="m3-shadow"></div>'
            f'<div class="mc3d-in"><div class="rig">{rig}</div></div>{bubble}</div>')


def happy3d(extra_class: str = "") -> str:
    """The 3D mascot (a friendly ghost), smiling."""
    return _ghost(_GHOST_HAPPY, extra_class)


def unsure3d(extra_class: str = "") -> str:
    """The 3D ghost puzzled, with a floating question mark (shown where a chart has no data)."""
    return _ghost(_GHOST_UNSURE, "m3-idle-look " + extra_class, '<div class="m3-q">?</div>')


def worker3d(extra_class: str = "") -> str:
    """The earlier 3D salaried-worker version (kept for reference)."""
    return _figure(_FACE_OK, extra_class)

"""Plotly figure builders. Every chart: units in axis titles, hover tooltips,
gaps shown as gaps (never interpolated), flagged points marked with a symbol."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from analytics import metrics
from dashboard import theme

FONT = dict(family=theme.FONT_STACK, size=14, color=theme.NAVY)


def _label(idx: int) -> str:
    return f"ไตรมาส {idx % 4 + 1}/{idx // 4}"


def _axis_labels(lo: int, hi: int):
    cats = [_label(i) for i in range(lo, hi + 1)]
    years = (hi - lo) / 4
    step = 1 if years <= 8 else (2 if years <= 20 else 4)
    tickvals = [c for c in cats if c.startswith("ไตรมาส 1/") and int(c.split("/")[1]) % step == 0]
    ticktext = [c.split("/")[1] for c in tickvals]
    return cats, tickvals, ticktext


def _legend_rows(fig: go.Figure, chars_per_row: int = 30) -> int:
    """Rows a bottom legend needs (phone-width safe), 0 when Plotly shows no legend."""
    names = [t.name for t in fig.data if t.name and t.showlegend is not False]
    if len(names) < 2:
        return 0
    return max(1, math.ceil(sum(len(n) + 7 for n in names) / chars_per_row))


def style(fig: go.Figure, *, height=420, ytitle="", legend_bottom=True, top=30, xtitle_room=True) -> go.Figure:
    """Common look. The legend sits in the figure's bottom margin (yref=container) and
    the margin grows with the number of legend rows, so it never overlaps ticks/titles."""
    rows = _legend_rows(fig) if legend_bottom else 0
    legend_px = rows * 20 + 12 if rows else 0
    bottom = 62 + legend_px if xtitle_room else 28 + legend_px
    fig.update_layout(
        font=FONT, height=height + legend_px, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=8, r=12, t=top, b=bottom), hovermode="closest",
        hoverlabel=dict(font=dict(family=theme.FONT_STACK, size=13)),
        showlegend=bool(rows),
        legend=dict(orientation="h", xref="paper", x=0, xanchor="left", yref="container", y=0, yanchor="bottom",
                    font=dict(size=12), tracegroupgap=0) if rows else dict(),
    )
    fig.update_yaxes(title_text=ytitle, title_standoff=6, gridcolor=theme.GRID_Y, zeroline=False, automargin=True,
                     tickfont=dict(size=12), title_font=dict(size=12))
    fig.update_xaxes(gridcolor=theme.GRID_X, automargin=True, tickfont=dict(size=12), title_standoff=8)
    return fig


def _pad_range(fig: go.Figure, values, factor: float = 1.22) -> None:
    """Leave room to the right of horizontal bars for their value labels."""
    vals = [v for v in values if v == v]
    if vals:
        fig.update_xaxes(range=[0, max(vals) * factor])


def _wrap(label: str) -> str:
    """Break long Thai labels at spaces/brackets so axis labels stay narrow."""
    out = label.replace(" (", "<br>(")
    if len(out) > 22 and " " in out and "<br>" not in out:
        out = out.replace(" ", "<br>", 1)
    return out


def _category_x(fig, lo, hi, row=None, col=None):
    cats, tv, tt = _axis_labels(lo, hi)
    kw = dict(type="category", categoryorder="array", categoryarray=cats, tickvals=tv, ticktext=tt,
              title_text="ปี พ.ศ.")
    if row:
        fig.update_xaxes(row=row, col=col, **kw)
    else:
        fig.update_xaxes(**kw)


def shade_excluded(fig: go.Figure, lo: int, hi: int, idxs, label: str = "ไม่แสดงค่า") -> None:
    """Grey bands over the quarters whose values were left out because the source tables disagree (runs of neighbouring quarters are one band)."""
    runs: list[list[int]] = []
    for i in sorted({int(i) for i in idxs if lo <= int(i) <= hi}):
        if runs and i == runs[-1][1] + 1:
            runs[-1][1] = i
        else:
            runs.append([i, i])
    for a, b in runs:
        fig.add_vrect(x0=a - lo - 0.5, x1=b - lo + 0.5, fillcolor="rgba(120,110,130,0.16)", line_width=0, layer="below",
                      annotation_text=label if b > a else "ขัดแย้ง", annotation_position="top", annotation_font=dict(size=11, color=theme.MUTED))


def _full(df: pd.DataFrame, by: list[str] | None = None) -> pd.DataFrame:
    """Reindex to every quarter between min and max so missing quarters appear as gaps."""
    lo, hi = int(df["period_idx"].min()), int(df["period_idx"].max())
    full = pd.DataFrame({"period_idx": range(lo, hi + 1)})
    full["x"] = full["period_idx"].map(_label)
    return full


def rgba(color: str, alpha: float) -> str:
    """'#rrggbb' -> 'rgba(r,g,b,alpha)' (other colour formats are returned unchanged)."""
    c = str(color).lstrip("#")
    if len(c) == 6:
        try:
            return f"rgba({int(c[0:2], 16)},{int(c[2:4], 16)},{int(c[4:6], 16)},{alpha})"
        except ValueError:
            pass
    return color


def area_under(fig: go.Figure, x, y, color: str, row: int | None = None, col: int | None = None, alpha: float = 0.16) -> dict:
    """Soft area under a line, in the line's own colour. Call BEFORE adding the line and pass ``**result`` to its go.Scatter.

    The area is drawn down to a hidden baseline just under the lowest value (not down to zero, which would flatten the
    line); gaps in the data stay empty, so nothing looks measured where there is no value."""
    vals = pd.Series(list(y), dtype="float64").dropna()
    if vals.empty:
        return {}
    span = float(vals.max() - vals.min()) or abs(float(vals.max())) or 1.0
    lo, hi = float(vals.min()) - span * 0.25, float(vals.max()) + span * 0.12
    pos = {} if row is None else {"row": row, "col": col}
    fig.add_trace(go.Scatter(x=list(x), y=[lo] * len(list(x)), mode="lines", line=dict(width=0), hoverinfo="skip", showlegend=False), **pos)
    fig.update_yaxes(range=[lo, hi], **pos)
    return dict(fill="tonexty", fillcolor=rgba(color, alpha))


def trend_line(df: pd.DataFrame, y: str, ytitle: str, hover_unit: str, *, flag_col: str | None = None,
               sig_col: str | None = None, color=theme.PRIMARY, decimals=2, height=400, focus: tuple[int, int] | None = None) -> go.Figure:
    """Single-series trend. ``flag_col`` False -> point drawn as amber diamond (data-quality flag);
    ``sig_col`` True -> larger ring (statistically unusual เทียบปีก่อน change)."""
    d = df.sort_values("period_idx")
    full = _full(d).merge(d, on="period_idx", how="left")
    fig = go.Figure()
    area = area_under(fig, full["x"], full[y], color)
    fig.add_trace(go.Scatter(
        x=full["x"], y=full[y], mode="lines+markers", name=ytitle, connectgaps=False, **area,
        line=dict(color=color, width=2.6), marker=dict(size=6, color=color),
        customdata=np.c_[full["x"]],
        hovertemplate="<b>%{x}</b><br>" + ytitle + ": %{y:,." + str(decimals) + "f} " + hover_unit + "<extra></extra>",
    ))
    if flag_col and flag_col in full:
        bad = full[(full[flag_col] == False) & full[y].notna()]  # noqa: E712
        if len(bad):
            fig.add_trace(go.Scatter(x=bad["x"], y=bad[y], mode="markers", name="ตรวจพบความไม่สอดคล้องของข้อมูล",
                                     marker=dict(size=11, symbol="diamond", color=theme.AMBER, line=dict(color=theme.NAVY, width=1)),
                                     hovertemplate="<b>%{x}</b><br>ข้อมูลไตรมาสนี้มีความไม่สอดคล้องข้ามตาราง<extra></extra>"))
    if sig_col and sig_col in full:
        s = full[(full[sig_col] == True) & full[y].notna()]  # noqa: E712
        if len(s):
            fig.add_trace(go.Scatter(x=s["x"], y=s[y], mode="markers", name="เปลี่ยนแปลง เทียบปีก่อน ผิดปกติเชิงสถิติ",
                                     marker=dict(size=14, symbol="circle-open", color=theme.AMBER, line=dict(width=3, color=theme.AMBER)),
                                     hovertemplate="<b>%{x}</b><br>เทียบปีก่อน ผิดปกติเชิงสถิติ<extra></extra>"))
    style(fig, ytitle=f"{ytitle} ({hover_unit})", height=height)
    _category_x(fig, int(d["period_idx"].min()), int(d["period_idx"].max()))
    return fig


# one colour per education level (the same level has the same colour in every chart), taken from the region palette so the page reads as one set
EDU_COLORS = ["#FF6FB5", "#AB46D2", "#55D8C1", "#92D9F7", "#FCF69C", "#C9B8D6"]


def hbar_education(df: pd.DataFrame, value: str, order: list[str], xtitle: str, unit: str, decimals=1, height: int | None = None) -> go.Figure:
    d = df.set_index("edu_group").reindex(order).dropna(subset=[value]).reset_index()
    fig = go.Figure(go.Bar(
        y=[_wrap(x) for x in d["edu_group"]], x=d[value], orientation="h",
        marker_color=[EDU_COLORS[order.index(x) % len(EDU_COLORS)] if x in order else theme.PRIMARY for x in d["edu_group"]], customdata=d["edu_group"],
        text=[f"{v:,.{decimals}f}" for v in d[value]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{customdata}</b><br>" + xtitle + ": %{x:,." + str(decimals) + "f} " + unit + "<extra></extra>"))
    style(fig, height=height or max(300, 70 * len(d) + 80), legend_bottom=False)
    _pad_range(fig, d[value])
    fig.update_yaxes(autorange="reversed", title_text="", gridcolor="white")
    fig.update_xaxes(title_text=f"{xtitle} ({unit})")
    return fig


def grouped_bar(df: pd.DataFrame, x: str, y: str, group: str, ytitle: str, unit: str, decimals=1) -> go.Figure:
    fig = go.Figure()
    colors = {"ชาย": theme.PRIMARY, "หญิง": theme.ACCENT}
    patterns = {"ชาย": "", "หญิง": "/"}
    for g, sub in df.groupby(group):
        fig.add_trace(go.Bar(
            x=[str(v).replace(" ", "<br>", 1) for v in sub[x]], y=sub[y], name=str(g), customdata=sub[x],
            marker=dict(color=colors.get(g, theme.NAVY), pattern_shape=patterns.get(g, "x")),
            hovertemplate="<b>%{customdata}</b><br>" + str(g) + ": %{y:,." + str(decimals) + "f} " + unit + "<extra></extra>"))
    style(fig, ytitle=f"{ytitle} ({unit})")
    fig.update_layout(barmode="group")
    return fig


def multi_line(df: pd.DataFrame, y: str, group: str, ytitle: str, unit: str, decimals=2, height=420,
               dash_col: str | None = None, focus: tuple[int, int] | None = None, colors: dict | None = None,
               excluded=None) -> go.Figure:
    fig = go.Figure()
    d = df.sort_values("period_idx")
    base = _full(d)
    dashes = ["solid", "dash", "dot", "dashdot"]
    for i, (g, sub) in enumerate(d.groupby(group, sort=False)):
        full = base.merge(sub, on="period_idx", how="left")
        fig.add_trace(go.Scatter(
            x=full["x"], y=full[y], mode="lines+markers", name=str(g), connectgaps=False,
            line=dict(color=(colors or {}).get(g) or theme.SERIES[i % len(theme.SERIES)], width=2.2, dash=dashes[(i // len(theme.SERIES)) % 4]),
            marker=dict(size=5, symbol=["circle", "square", "diamond", "triangle-up", "x", "cross", "star"][i % 7]),
            hovertemplate="<b>%{x}</b><br>" + str(g) + ": %{y:,." + str(decimals) + "f} " + unit + "<extra></extra>"))
    style(fig, ytitle=f"{ytitle} ({unit})", height=height)
    _category_x(fig, int(d["period_idx"].min()), int(d["period_idx"].max()))
    if excluded:
        shade_excluded(fig, int(d["period_idx"].min()), int(d["period_idx"].max()), excluded)
    return fig


def region_bar(df: pd.DataFrame, value: str, xtitle: str, unit: str, decimals=1, highlight=None) -> go.Figure:
    """Bars per region; with ``highlight`` the other regions fade (they stay visible: the chart is a comparison)."""
    d = df.sort_values(value, ascending=True)
    fig = go.Figure(go.Bar(
        y=d["region"], x=d[value], orientation="h", marker_color=[REGION_COLORS.get(r_, theme.MIDBLUE) for r_ in d["region"]],
        marker_opacity=[1.0 if (not highlight or r_ in highlight) else 0.28 for r_ in d["region"]],
        text=[f"{v:,.{decimals}f}" for v in d[value]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>" + xtitle + ": %{x:,." + str(decimals) + "f} " + unit + "<extra></extra>"))
    style(fig, height=max(300, 56 * len(d) + 90), legend_bottom=False)
    _pad_range(fig, d[value])
    fig.update_xaxes(title_text=f"{xtitle} ({unit})")
    fig.update_yaxes(title_text="", gridcolor="white")
    return fig


def province_ranks(df: pd.DataFrame, value: str, top: int, decimals: int = 2, max_extra: int = 5) -> pd.DataFrame:
    """The ``top`` highest provinces plus any that tie with the last one (at most ``max_extra`` more), with a shared rank
    for equal values as published (rounded to ``decimals``): column ``rank`` (1, 1, 3, ...) and ``tied``."""
    d = df.dropna(subset=[value]).copy()
    d["_v"] = d[value].round(decimals)
    d = d.sort_values(["_v", "province"], ascending=[False, True])
    if d.empty:
        return d.drop(columns="_v")
    cut = d["_v"].iloc[min(top, len(d)) - 1]
    d = d[d["_v"] >= cut].head(top + max_extra)
    d["rank"] = d["_v"].rank(method="min", ascending=False).astype(int)
    d["tied"] = d["_v"].duplicated(keep=False)
    return d.drop(columns="_v")


def province_bar(df: pd.DataFrame, value: str, xtitle: str, unit: str, top: int = 15, decimals=2) -> go.Figure:
    """Highest provinces; equal values share a rank ("อันดับ 3=") and a tie with the last place is kept, not cut at random."""
    d = province_ranks(df, value, top, decimals).iloc[::-1]
    labels = [f"{p_} ({r_}{'=' if t_ else ''})" for p_, r_, t_ in zip(d["province"], d["rank"], d["tied"])]
    fig = go.Figure(go.Bar(
        y=labels, x=d[value], orientation="h", marker_color=theme.PRIMARY,
        text=[f"{v:,.{decimals}f}" for v in d[value]], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>" + xtitle + ": %{x:,." + str(decimals) + "f} " + unit + "<extra></extra>"))
    style(fig, height=max(320, 30 * len(d) + 90), legend_bottom=False)
    _pad_range(fig, d[value])
    fig.update_xaxes(title_text=f"{xtitle} ({unit})")
    fig.update_yaxes(title_text="", gridcolor="white")
    return fig


def two_panel(df: pd.DataFrame) -> go.Figure:
    """Unemployment rate (top) and GDP growth (bottom) on the same quarters (shared x)."""
    d = df.sort_values("period_idx")
    full = _full(d).merge(d, on="period_idx", how="left")
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.17,
                        subplot_titles=("อัตราการว่างงาน (ร้อยละ)", "อัตราเติบโตของ GDP (ร้อยละ เทียบปีก่อน)"))
    fig.update_annotations(font_size=13, xanchor="left", x=0)
    area = area_under(fig, full["x"], full["rate_pct"], theme.PRIMARY, row=1, col=1)
    fig.add_trace(go.Scatter(x=full["x"], y=full["rate_pct"], mode="lines+markers", name="อัตราการว่างงาน", connectgaps=False, **area,
                             line=dict(color=theme.PRIMARY, width=2.6), marker=dict(size=5),
                             hovertemplate="<b>%{x}</b><br>อัตราการว่างงาน: %{y:.2f} ร้อยละ<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=full["x"], y=full["gdp_yoy_pct"], name="อัตราเติบโตของ GDP (เทียบปีก่อน)", marker_color=theme.MIDBLUE,
                         hovertemplate="<b>%{x}</b><br>อัตราเติบโตของ GDP: %{y:.1f} ร้อยละ เทียบปีก่อน<extra></extra>"), row=2, col=1)
    fig.add_hline(y=0, line_color=theme.MUTED, line_width=1, row=2, col=1)
    style(fig, height=600, top=44)
    fig.update_yaxes(title_text="ร้อยละ", row=1, col=1)
    fig.update_yaxes(title_text="ร้อยละ", row=2, col=1)
    _category_x(fig, int(d["period_idx"].min()), int(d["period_idx"].max()), row=2, col=1)
    return fig


def scatter_gdp(df: pd.DataFrame, xcol: str, ycol: str, ytitle: str, yunit: str) -> go.Figure:
    d = df.dropna(subset=[xcol, ycol])
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d[xcol], y=d[ycol], mode="markers", name="รายไตรมาส",
        marker=dict(size=10, color=d["year_be"], colorscale=[[0, "#FFD3E3"], [0.5, theme.PINK], [1, theme.PLUM]], showscale=True,
                    colorbar=dict(title=dict(text="ปี พ.ศ.", side="top"), orientation="h", thickness=10, len=0.7, x=0, xanchor="left",
                                  y=1.02, yanchor="bottom", tickfont=dict(size=11)), line=dict(color="white", width=1)),
        text=d["period_label"],
        hovertemplate="<b>%{text}</b><br>อัตราเติบโตของ GDP: %{x:.1f} ร้อยละ เทียบปีก่อน<br>" + ytitle + ": %{y:.2f} " + yunit + "<extra></extra>"))
    fit = metrics.ols_line(d[xcol], d[ycol])
    if fit:
        xs = np.array([d[xcol].min(), d[xcol].max()])
        fig.add_trace(go.Scatter(x=xs, y=fit[0] * xs + fit[1], mode="lines", name="เส้นแนวโน้มเชิงเส้น (กำลังสองน้อยที่สุด)",
                                 line=dict(color=theme.AMBER, width=2.5, dash="dash"), hoverinfo="skip"))
    style(fig, height=470, ytitle=f"{ytitle} ({yunit})", top=78)
    fig.update_xaxes(title_text="อัตราเติบโตของ GDP เทียบปีก่อน (ร้อยละ)")
    return fig


def stacked_reasons(df: pd.DataFrame) -> go.Figure:
    d = df.sort_values("period_idx")
    base = _full(d)
    fig = go.Figure()
    cats = list(dict.fromkeys(d["category"]))
    for i, cat in enumerate(cats):
        sub = base.merge(d[d["category"] == cat][["period_idx", "value_k"]], on="period_idx", how="left")
        fig.add_trace(go.Bar(x=sub["x"], y=sub["value_k"] * 1000.0, name=cat, marker_color=theme.SERIES[i % len(theme.SERIES)],
                             hovertemplate="<b>%{x}</b><br>" + cat + ": %{y:,.0f} คน<extra></extra>"))
    fig.update_layout(barmode="stack")
    style(fig, height=460, ytitle="ผู้ว่างงานที่เคยทำงาน (คน)")
    _category_x(fig, int(d["period_idx"].min()), int(d["period_idx"].max()))
    return fig


def sso_bar(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    for i, (reason, sub) in enumerate(df.groupby("reason", sort=False)):
        fig.add_trace(go.Bar(x=sub["year_be"].astype(str), y=sub["cases"], name=reason, marker_color=theme.SERIES[i % len(theme.SERIES)],
                             hovertemplate="<b>ปี %{x}</b><br>" + reason + ": %{y:,.0f} กรณี<extra></extra>"))
    fig.update_layout(barmode="group")
    style(fig, height=380, ytitle="จำนวนกรณีที่ใช้สิทธิ")
    fig.update_xaxes(title_text="ปี พ.ศ.", type="category")
    return fig


def donut(df: pd.DataFrame, label: str, value: str, unit: str, centre_title: str, decimals: int = 1, height: int = 300) -> go.Figure:
    """Share of a total split in two or three groups; the total sits in the hole."""
    colors = {"ชาย": theme.PRIMARY, "หญิง": theme.ACCENT}
    d = df.dropna(subset=[value])
    total = d[value].sum()
    fig = go.Figure(go.Pie(
        labels=d[label], values=d[value], hole=0.62, sort=False, direction="clockwise",
        marker=dict(colors=[colors.get(x, theme.MIDBLUE) for x in d[label]], line=dict(color="white", width=2)),
        textinfo="percent", textfont=dict(size=13, color="white"),
        hovertemplate="<b>%{label}</b><br>%{value:,." + str(decimals) + "f} " + unit + " (%{percent})<extra></extra>"))
    fig.update_layout(
        font=FONT, height=height, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=8, r=8, t=16, b=52), showlegend=True,
        legend=dict(orientation="h", yref="container", y=0, yanchor="bottom", x=0.5, xanchor="center", font=dict(size=13)),
        annotations=[dict(text=f"<b>{total:,.{decimals}f}</b><br><span style='font-size:12px'>{unit}</span><br>"
                               f"<span style='font-size:11px'>{centre_title}</span>", x=0.5, y=0.5, showarrow=False, font=dict(size=18))],
        hoverlabel=dict(font=dict(family=theme.FONT_STACK, size=13)))
    return fig


# One fixed colour per region (same colour in every year/basis). Red and amber stay reserved for errors/flags.
REGION_COLORS = {
    "กรุงเทพมหานคร": "#ff6fb5",
    "ภาคเหนือ": "#ab46d2",
    "ภาคตะวันออกเฉียงเหนือ": "#55d8c1",
    "ภาคกลาง": "#fcf69c",
    "ภาคใต้": "#92d9f7",
}
NO_VALUE_COLOR = "#D9D9D9"
REGION_ORDER = list(REGION_COLORS)


def _region_color(region: str, value) -> str:
    return REGION_COLORS.get(region, "#7A7A7A") if value == value else NO_VALUE_COLOR



def region_map(geo: dict, df: pd.DataFrame, label: str, unit: str, decimals: int = 2, height: int = 320):
    """Map of Thailand where every region has its own colour (all provinces of a region share it).

    Returns None when no region has a value. Regions without a value (not selected, or no data for the
    quarter) are grey and say so on hover. Values are shown in the hover text and in ``region_map_legend``.
    """
    d = df.copy()
    if d["value"].notna().sum() == 0:
        return None
    d["hover"] = ("<b>" + d["region"] + "</b><br>จังหวัด" + d["province"] + "<br>"
                  + label + ": " + d["value"].map(lambda x: f"{x:,.{decimals}f} {unit}" if x == x else "ไม่มีข้อมูล"))
    fig = go.Figure()
    for region, g in d.groupby("region", sort=False):
        color = _region_color(region, g["value"].iloc[0])
        fig.add_trace(go.Choropleth(
            geojson=geo, locations=g["iso"], z=[1] * len(g), showscale=False, name=region,
            colorscale=[[0, color], [1, color]], marker_line_color="white", marker_line_width=0.7,
            text=g["hover"], hovertemplate="%{text}<extra></extra>"))
    fig.update_traces(selected=dict(marker=dict(opacity=1)), unselected=dict(marker=dict(opacity=1)))
    fig.update_geos(fitbounds="locations", visible=False, bgcolor="white", projection_type="mercator")
    fig.update_layout(font=FONT, height=height, paper_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=4, b=4), showlegend=False,
                      clickmode="event+select", dragmode="select",
                      hoverlabel=dict(font=dict(family=theme.FONT_STACK, size=13)))
    return fig


def region_map_legend(df: pd.DataFrame, label: str, unit: str, decimals: int = 2, compact: bool = False, vertical: bool = False) -> str:
    """HTML colour key: each region (highest value first) with its own colour swatch and its value
    (colour is never the only carrier of meaning)."""
    import html as _html

    rows = df.drop_duplicates("region").set_index("region")["value"]
    order = rows.sort_values(ascending=False, na_position="last").index
    items = []
    for region in order:
        v = rows[region]
        val = (f"{v:,.{decimals}f}" if compact else f"{v:,.{decimals}f} {unit}") if v == v else "ไม่มีข้อมูล"
        items.append(f'<span class="rlg"><i style="background:{_region_color(region, v)}"></i>{_html.escape(region)} <b>{_html.escape(val)}</b></span>')
    cls = (" compact" if compact else "") + (" vertical" if vertical else "")
    title = f'<div class="rlg-title">{_html.escape(label)} ({_html.escape(unit)}) แยกตามภูมิภาค</div>' if vertical else ""
    return f'<div class="rlg-wrap{cls}" aria-label="คำอธิบายสีของแผนที่: {_html.escape(label)}">' + title + "".join(items) + "</div>"


# ---------------------------------------------------------------------------
# clickable SVG map (Plotly cannot select a polygon by clicking it on a geo map)
# ---------------------------------------------------------------------------

_COS = 0.972  # cos(13.5 deg): Thailand's mean latitude, so the map is not stretched sideways
_PATHS: dict[str, tuple[str, tuple[float, float, float, float]]] = {}


def _province_paths(geo: dict) -> dict:
    """iso -> (SVG path, bbox) in 0.01-degree units; built once (the geometry never changes)."""
    if _PATHS:
        return _PATHS
    for ft in geo["features"]:
        geom = ft["geometry"]
        polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
        parts, xs, ys = [], [], []
        for poly in polys:
            for ring in poly:
                pts, last = [], None
                for lon, lat in ring:
                    pt = (round(lon * _COS * 100), round(-lat * 100))
                    if pt != last:
                        pts.append(pt)
                        last = pt
                if len(pts) >= 3:
                    parts.append("M" + "L".join(f"{x} {y}" for x, y in pts) + "Z")
                    xs += [p[0] for p in pts]
                    ys += [p[1] for p in pts]
        if parts:
            _PATHS[ft["id"]] = ("".join(parts), (min(xs), min(ys), max(xs), max(ys)))
    return _PATHS


def region_svg_map(geo: dict, df: pd.DataFrame, label: str, unit: str, decimals: int = 2) -> str | None:
    """SVG map, one colour per region; each province carries ``data-region`` so a click can select the region.

    ``df`` holds only the provinces to draw (all of them, or just the zoomed region): the view box fits what is drawn.
    """
    import html as _html

    d = df.copy()
    if d["value"].notna().sum() == 0:
        return None
    paths = _province_paths(geo)
    d = d[d["iso"].isin(paths)]
    if d.empty:
        return None
    x0 = min(paths[i][1][0] for i in d["iso"]); y0 = min(paths[i][1][1] for i in d["iso"])
    x1 = max(paths[i][1][2] for i in d["iso"]); y1 = max(paths[i][1][3] for i in d["iso"])
    pad = max(x1 - x0, y1 - y0) * 0.03
    out = [f'<svg class="rmap" viewBox="{x0 - pad:.0f} {y0 - pad:.0f} {x1 - x0 + 2 * pad:.0f} {y1 - y0 + 2 * pad:.0f}" '
           f'role="img" aria-label="แผนที่ภูมิภาค: {_html.escape(label)}" preserveAspectRatio="xMidYMid meet">']
    for r in d.itertuples():
        v = r.value
        tip = f"{r.region} · จังหวัด{r.province} · {label}: " + (f"{v:,.{decimals}f} {unit}" if v == v else "ไม่มีข้อมูล")
        out.append(f'<path d="{paths[r.iso][0]}" fill="{_region_color(r.region, v)}" data-region="{_html.escape(r.region)}"><title>{_html.escape(tip)}</title></path>')
    out.append("</svg>")
    return "".join(out)


MAP_CSS = """
.rmap { width: 100%; height: 100%; max-height: 520px; display: block; }
.rmap path { stroke: #fff; stroke-width: 7; stroke-linejoin: round; cursor: pointer; transition: opacity .3s ease; }
.rmap.dim path { opacity: .45; }
.rmap.dim path.on { opacity: 1; }
.rmap.zooming path { pointer-events: none; }
.rmap.zooming path:not(.zt) { opacity: 0; }
"""

# Clicking a region zooms the view box onto it (about .5 s), the other regions fade out, and only then is the click sent to
# Python, whose redraw starts on the very same view box. "Back to the whole country" zooms out from the old view box.
# Viewers who ask for reduced motion get no animation.
MAP_JS = """
export default function(component) {
    const { data, setTriggerValue, parentElement } = component;
    const w = window;
    let box = parentElement.querySelector('.mapbox');
    if (!box) { box = document.createElement('div'); box.className = 'mapbox'; parentElement.appendChild(box); }
    box.innerHTML = data || '';
    const svg = box.querySelector('svg');
    if (!svg) return;
    const paths = Array.from(svg.querySelectorAll('path[data-region]'));
    const reduce = () => !!(w.matchMedia && w.matchMedia('(prefers-reduced-motion: reduce)').matches);
    const regions = new Set(paths.map((p) => p.getAttribute('data-region')));
    const zoomed = regions.size === 1;
    const nums = (v) => v.trim().split(' ').map(Number);
    const finalVb = svg.getAttribute('viewBox');

    function animateVb(from, to, ms, done) {
        const a = nums(from), b = nums(to), t0 = Date.now();
        let ended = false;
        function end() { if (ended) return; ended = true; svg.setAttribute('viewBox', to); if (done) done(); }
        function step() {
            if (ended) return;
            const k = Math.min(1, (Date.now() - t0) / ms), e = 1 - Math.pow(1 - k, 3);
            svg.setAttribute('viewBox', a.map((x, i) => (x + (b[i] - x) * e).toFixed(1)).join(' '));
            if (k < 1) setTimeout(step, 16); else end();
        }
        step();
        setTimeout(end, ms + 250);
    }

    // zoom out: the previous map showed one region; start from its view box and open up to the whole country
    const prev = w.__lmMapView;
    if (!zoomed && prev && prev.zoomed && Date.now() - prev.t < 4000 && !reduce()) animateVb(prev.vb, finalVb, 550);
    w.__lmMapView = { zoomed: zoomed, vb: finalVb, t: Date.now() };

    function targetBox(region) {
        let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
        paths.filter((p) => p.getAttribute('data-region') === region).forEach((p) => {
            const b = p.getBBox();
            x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
        });
        const pad = Math.max(x1 - x0, y1 - y0) * 0.03;
        return [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad].map((v) => v.toFixed(0)).join(' ');
    }

    paths.forEach((p) => {
        const r = p.getAttribute('data-region');
        p.onmouseenter = () => { svg.classList.add('dim'); paths.forEach((q) => q.classList.toggle('on', q.getAttribute('data-region') === r)); };
        p.onmouseleave = () => { svg.classList.remove('dim'); paths.forEach((q) => q.classList.remove('on')); };
        p.onclick = () => {
            if (zoomed || reduce()) { setTriggerValue('region', r); return; }
            svg.classList.remove('dim');
            svg.classList.add('zooming');
            paths.forEach((q) => q.classList.toggle('zt', q.getAttribute('data-region') === r));
            animateVb(svg.getAttribute('viewBox'), targetBox(r), 520, () => setTriggerValue('region', r));
        };
    });
}
"""

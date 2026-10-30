"""Employment rate and average wage (NSO tables behind data.go.th 0706_02_0011 and 0706_02_0019).

Why the checks below exist (found by testing the real tables):
* the same national wage is published by three tables; from 2567 Q2 to 2568 Q3 they disagree by 10-31 %,
  and two quarters jump ~20 % above their neighbours -> a quarter whose national wage fails these checks is
  removed from every wage table (nobody can say which table is right);
* one table repeats keys with conflicting values (2567 Q4, labelled 'Total') -> conflicting keys are dropped;
* small groups publish 0 baht or exactly 0 % / 100 % -> treated as missing, not as a measurement.
Nothing is estimated, averaged across groups or interpolated. Dropped cells stay empty and are reported.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import config
from data_processing import clean as c
from data_processing import normalize as nz
from data_processing import validation as v

EMP_UNIT = "ร้อยละ"
WAGE_UNITS = {"บาทต่อเดือน", "บาท"}
NATIONAL = "ทั่วประเทศ"
RESIDUAL_EDU = ("อื่น ๆ", "ไม่ทราบ", "อื่น ๆ และไม่ทราบ")   # residual categories: kept in the tables, left out of charts

# a value counts as "the same" when it differs only by publication rounding
SAME_TOL = {"emp_pct": 0.005, "wage": 1.0}


# ---------------------------------------------------------------------------
# label helpers ('Total' appears in one corrupted batch of the wage tables)
# ---------------------------------------------------------------------------


def _is_total_word(s) -> bool:
    return isinstance(s, str) and s.strip().lower() == "total"


def _region(x):
    return NATIONAL if _is_total_word(x) else nz.normalize_region(x)


def _sex(x):
    return "รวม" if _is_total_word(x) else nz.normalize_sex(x)


def _area(x):
    return "รวม" if _is_total_word(x) else nz.normalize_area(x)


def _age(x):
    return "รวม" if _is_total_word(x) else nz.normalize_age_group(x)


def _edu(x):
    s = nz.clean_label(x)
    if s is None:
        return None
    if _is_total_word(s) or s in nz.TOTAL_LABELS:
        return "รวม"
    if s in ("อื่น ๆ", "การศึกษาอื่นๆ"):
        return "อื่น ๆ"
    if s == "การศึกษาอื่นๆ และไม่ทราบ":
        return "อื่น ๆ และไม่ทราบ"
    return s


def _industry(x):
    s = nz.clean_label(x)
    if s is None:
        return None
    return "รวม" if (_is_total_word(s) or s in nz.TOTAL_LABELS) else s


def merge_industry_names(names: pd.Series, years: pd.Series) -> tuple[pd.Series, dict[str, str]]:
    """Truncated / re-spaced spellings of one industry (e.g. '...เทคนิ' / '...เทคนิค') split one series in two.
    Map each name to the longest spelling it is a prefix of (ignoring spaces); on a tie, the newest year's spelling."""
    keep = [n for n in names.dropna().unique() if n != "รวม"]
    norm = lambda s: s.replace(" ", "")  # noqa: E731
    latest = {n: int(years[names == n].max()) for n in keep}
    mapping = {}
    for a in keep:
        cands = [b for b in keep if norm(b).startswith(norm(a))]
        best = max(cands, key=lambda b: (len(norm(b)), latest[b]))
        if best != a:
            mapping[a] = best
    return names.replace(mapping), mapping


# ---------------------------------------------------------------------------
# one generic cleaner for the six tables
# ---------------------------------------------------------------------------


def _clean_table(raw: pd.DataFrame, table: str, dims: dict, unit, value_name: str):
    """dims = {column: label function}. Returns (tidy frame, report)."""
    df, rep = c._prep(raw, table, ["year", "quarter", *dims, "value", "unit"], unit)
    if df is None:
        return c._fail(rep)
    df = nz.add_period_columns(df)
    for col, fn in dims.items():
        df[col] = df[col].map(fn)
    df[value_name] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=list(dims) + [value_name])
    rep.add(v.check_period_validity(df, table))

    if "industry" in df.columns:
        df["industry"], merged = merge_industry_names(df["industry"], df["year_be"])
        if merged:
            rep.add(v.Issue("info", "label_merge", table, f"รวมชื่อหมวดอุตสาหกรรมที่สะกดต่างกัน {len(merged)} ชื่อ", len(merged), {"mapping": merged}))

    # impossible cells (small groups publish 0 baht, or exactly 0 % / 100 %)
    if value_name == "wage":
        bad = df[value_name] <= 0
        what = "ค่าจ้าง 0 บาท"
    else:
        bad = df[value_name].isin([0.0, 100.0])
        what = "อัตรามีงานทำ 0% หรือ 100% พอดี"
        rep.add(v.check_value_range(df, value_name, table, 0, 100, "ร้อยละ"))
        bad = bad | (df[value_name] < 0) | (df[value_name] > 100)
    if bad.any():
        rep.add(v.Issue("warning", "implausible", table, f"พบ{what} {int(bad.sum())} แถว (กลุ่มตัวอย่างเล็ก/ไม่มีข้อมูลจริง) — ไม่นำมาใช้", int(bad.sum())))
        df = df[~bad]

    # repeated keys: rounding-only repeats collapse; conflicting repeats are dropped
    keys = ["period_idx", *dims]
    g = df.groupby(keys, sort=False)[value_name].agg(["min", "max", "mean", "size"])
    multi = g[g["size"] > 1]
    if len(multi):
        conflict = multi[(multi["max"] - multi["min"]) > SAME_TOL[value_name]]
        if len(conflict):
            periods = sorted({int(i[0]) for i in conflict.index})
            rep.add(v.Issue("warning", "conflicting_duplicates", table,
                            f"คีย์ซ้ำที่ค่าขัดแย้งกัน {len(conflict)} คีย์ใน " + ", ".join(nz.period_label(p // 4, p % 4 + 1) for p in periods[:4])
                            + " — ไม่ใช้ค่าเหล่านั้น", len(conflict), {"periods": periods}))
        bad_keys = conflict.index
        collapsed = multi.drop(index=bad_keys)["mean"].rename(value_name)
        singles = g[g["size"] == 1]["mean"].rename(value_name)
        vals = pd.concat([singles, collapsed]).reset_index()
    else:
        vals = g["mean"].rename(value_name).reset_index()
    meta = df.drop_duplicates("period_idx")[["period_idx", "year_be", "quarter", "period_label", "date"]]
    out = vals.merge(meta, on="period_idx", how="left")
    if "area" in dims:
        other = ["period_idx"] + [k for k in dims if k != "area"]
        bkk = out[out["region"] == "กรุงเทพมหานคร"]
        have_total = set(map(tuple, bkk.loc[bkk["area"] == "รวม", other].to_numpy().tolist()))
        muni = bkk[bkk["area"] == "ในเขตเทศบาล"]
        add = muni[[tuple(r) not in have_total for r in muni[other].to_numpy().tolist()]]
        if len(add):
            out = pd.concat([out, add.assign(area="รวม")], ignore_index=True)
            rep.add(v.Issue("info", "bangkok_total", table, f"กรุงเทพมหานครมีเฉพาะแถว 'ในเขตเทศบาล' (ทั้งจังหวัดเป็นเขตเทศบาล) ใช้เป็นยอดรวม {len(add)} แถว", len(add)))
    if "region" in out.columns:
        out = c._add_region_basis(out)
    lead = ["year_be", "quarter", "period_idx", "period_label", "date"]
    out = out[lead + [x for x in out.columns if x not in lead]].sort_values(["period_idx", *dims]).reset_index(drop=True)
    if out.empty:
        rep.add(v.Issue("error", "empty", table, "ไม่มีแถวที่ใช้ได้หลังตรวจสอบ"))
        return c._fail(rep)
    return out, rep


def clean_emp_edu(raw, table="nso_er_edu"):
    return _clean_table(raw, table, {"region": _region, "area": _area, "level_of_edu": _edu}, EMP_UNIT, "emp_pct")


def clean_emp_sex_age(raw, table="nso_er_sex_age"):
    return _clean_table(raw, table, {"region": _region, "area": _area, "sex": _sex, "age_group": _age}, EMP_UNIT, "emp_pct")


def clean_emp_region_sex(raw, table="nso_er_region_sex"):
    return _clean_table(raw, table, {"region": _region, "sex": _sex}, EMP_UNIT, "emp_pct")


def clean_wage_age(raw, table="nso_w_age"):
    return _clean_table(raw, table, {"region": _region, "area": _area, "sex": _sex, "age_group": _age}, WAGE_UNITS, "wage")


def clean_wage_edu(raw, table="nso_w_edu"):
    return _clean_table(raw, table, {"region": _region, "area": _area, "sex": _sex, "level_of_edu": _edu}, WAGE_UNITS, "wage")


def clean_wage_industry(raw, table="nso_w_industry"):
    return _clean_table(raw, table, {"region": _region, "industry": _industry}, WAGE_UNITS, "wage")


# ---------------------------------------------------------------------------
# cross-table checks and the analysis-ready tables
# ---------------------------------------------------------------------------


def _pick(df, **eq) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    m = pd.Series(True, index=df.index)
    for k, val in eq.items():
        m &= df[k] == val
    return df[m]


def _national_series(df, value, **eq) -> pd.Series:
    d = _pick(df, region=NATIONAL, **eq)
    return d.drop_duplicates("period_idx").set_index("period_idx")[value] if len(d) else pd.Series(dtype=float)


def _empty_region_series() -> pd.Series:
    return pd.Series(dtype=float, index=pd.MultiIndex.from_arrays([[], []], names=["period_idx", "region"]))


def _columns(series: dict) -> pd.DataFrame:
    """Candidate series side by side (an empty frame when no source has the measure)."""
    return pd.concat(series, axis=1) if series else pd.DataFrame()


def _jump_failures(s: pd.Series, tol: float) -> set:
    """Quarters more than ``tol`` away from the median of their 5-quarter neighbourhood (continuous quarters only)."""
    if len(s) < 5:
        return set()
    s = s.sort_index()
    med = s.rolling(5, center=True, min_periods=3).median()
    return set(s.index[((s / med - 1).abs() > tol).to_numpy()])


def _table_name(key: str) -> str:
    """'ชื่อสั้น (รหัสตาราง สสช.)' for a source key, e.g. the table code at the end of its URL."""
    import re

    spec = config.SOURCES_BY_KEY.get(key)
    m = re.search(r"((?:OS|LFS|ST)_\d+_[0-9A-Z_]+)", spec.url) if spec is not None else None
    return m.group(1) if m else key


def _period_meta(idxs) -> pd.DataFrame:
    idxs = sorted({int(i) for i in idxs})
    return pd.DataFrame({
        "period_idx": idxs, "year_be": [i // 4 for i in idxs], "quarter": [i % 4 + 1 for i in idxs],
        "period_label": [nz.period_label(i // 4, i % 4 + 1) for i in idxs],
        "date": [pd.Timestamp(year=i // 4 - config.BE_OFFSET, month=3 * (i % 4) + 1, day=1) for i in idxs]})


def _fmt_periods(idxs) -> str:
    return ", ".join(nz.period_label(int(i) // 4, int(i) % 4 + 1) for i in sorted(idxs))


def build(b, t: dict) -> None:
    """Fill ``b.tables`` with lm_national, lm_region, lm_sex_age, lm_edu, lm_industry (and exclusions)."""
    er_edu, er_sa, er_rs = t.get("er_edu"), t.get("er_sa"), t.get("er_rs")
    w_age, w_edu, w_ind = t.get("w_age"), t.get("w_edu"), t.get("w_ind")
    if all(x is None for x in (er_edu, er_sa, er_rs, w_age, w_edu, w_ind)):
        return
    tot = {"area": "รวม", "sex": "รวม"}

    # ---- national employment: three tables must agree --------------------------------------------------
    emp_c = {"sex_age": _national_series(er_sa, "emp_pct", area="รวม", sex="รวม", age_group="รวม"),
             "edu": _national_series(er_edu, "emp_pct", area="รวม", level_of_edu="รวม"),
             "region_sex": _national_series(er_rs, "emp_pct", sex="รวม")}
    emp_frame = _columns({k: s for k, s in emp_c.items() if len(s)})
    emp_bad: set = set()
    if len(emp_frame):
        spread = emp_frame.max(axis=1) - emp_frame.min(axis=1)
        emp_bad = set(spread.index[(spread > config.EMP_AGREE_TOL_PP) & (emp_frame.notna().sum(axis=1) >= 2)])
        if emp_bad:
            b.report.add(v.Issue("warning", "emp_tables_conflict", "employment_rate",
                                 f"อัตรามีงานทำระดับประเทศจาก {emp_frame.shape[1]} ตารางไม่ตรงกัน (เกิน {config.EMP_AGREE_TOL_PP} จุด) {len(emp_bad)} ไตรมาส: {_fmt_periods(emp_bad)} — ไม่ใช้",
                                 len(emp_bad)))
    emp_nat = emp_frame.bfill(axis=1).iloc[:, 0] if len(emp_frame) else pd.Series(dtype=float)
    conf = b.availability.setdefault("conflicts", {})
    emp_names = {"sex_age": "ตารางเพศ×อายุ " + _table_name("nso_er_sex_age"), "edu": "ตารางการศึกษา " + _table_name("nso_er_edu"),
                 "region_sex": "ตารางภาค×เพศ " + _table_name("nso_er_region_sex")}
    conf["emp"] = [{"period_idx": int(p), "values": {emp_names[k]: float(emp_frame.at[p, k]) for k in emp_frame.columns if pd.notna(emp_frame.at[p, k])},
                    "gap": float(spread[p]), "unit": "%", "gap_unit": "จุด",
                    "reason": f"ตาราง สสช. {emp_frame.shape[1]} ตารางให้อัตรามีงานทำระดับประเทศต่างกันเกิน {config.EMP_AGREE_TOL_PP} จุด"} for p in sorted(emp_bad)] if len(emp_frame) else []
    # ---- national wage: three tables must agree, and no unexplained jump ------------------------------
    wage_c = {"age": _national_series(w_age, "wage", area="รวม", sex="รวม", age_group="รวม"),
              "edu": _national_series(w_edu, "wage", area="รวม", sex="รวม", level_of_edu="รวม"),
              "industry": _national_series(w_ind, "wage", industry="รวม")}
    wage_frame = _columns({k: s for k, s in wage_c.items() if len(s)})
    wage_bad: dict[int, str] = {}
    if len(wage_frame):
        lo, hi = wage_frame.min(axis=1), wage_frame.max(axis=1)
        disagree = ((hi / lo - 1) > config.WAGE_AGREE_TOL) & (wage_frame.notna().sum(axis=1) >= 2)
        wage_bad.update({int(i): "ตารางต้นทางให้ค่าจ้างเฉลี่ยประเทศไม่ตรงกัน" for i in disagree.index[disagree]})
        wage_ref = wage_frame.median(axis=1).dropna()
        jumps = _jump_failures(wage_ref.drop(index=[i for i in wage_bad if i in wage_ref.index]), config.WAGE_JUMP_TOL)
        wage_bad.update({int(i): "ค่าจ้างเด้งผิดจากไตรมาสข้างเคียงเกิน 10%" for i in jumps})
        if wage_bad:
            b.report.add(v.Issue("warning", "wage_tables_conflict", "avg_wage",
                                 f"ค่าจ้างเฉลี่ยระดับประเทศไม่ผ่านการตรวจ {len(wage_bad)} ไตรมาส ({_fmt_periods(wage_bad)}): ตารางต้นทางขัดแย้งกันหรือเด้งผิดปกติ "
                                 "และไม่มีเหตุผลทางข้อมูลที่จะเลือกตารางใดเป็นฝ่ายถูก จึงไม่ใช้ค่าจ้างของไตรมาสเหล่านี้ในทุกตาราง", len(wage_bad),
                                 {"periods": sorted(wage_bad)}))
    wage_nat = wage_frame.bfill(axis=1).iloc[:, 0] if len(wage_frame) else pd.Series(dtype=float)
    wage_names = {"age": "ตารางกลุ่มอายุ " + _table_name("nso_w_age"), "edu": "ตารางการศึกษา " + _table_name("nso_w_edu"),
                  "industry": "ตารางอุตสาหกรรม " + _table_name("nso_w_industry")}
    rows = []
    if len(wage_frame):
        ref_ok = wage_ref.drop(index=[i for i in wage_bad if i in wage_ref.index]) if len(wage_ref) else wage_ref
        med = ref_ok.sort_index().rolling(5, center=True, min_periods=3).median() if len(ref_ok) >= 5 else pd.Series(dtype=float)
        for p in sorted(wage_bad):
            vals = {wage_names[k]: float(wage_frame.at[p, k]) for k in wage_frame.columns if p in wage_frame.index and pd.notna(wage_frame.at[p, k])}
            gap = (max(vals.values()) / min(vals.values()) - 1) * 100 if len(vals) >= 2 and min(vals.values()) > 0 else None
            rows.append({"period_idx": int(p), "values": vals, "gap": gap, "unit": "บาท", "gap_unit": "%", "reason": wage_bad[p]})
    conf["wage"] = rows
    b.excluded["lm_wage"] = sorted(wage_bad)
    b.excluded["lm_emp"] = sorted(emp_bad)

    def drop_bad(df, value, bad):
        return df[~df["period_idx"].isin(list(bad))] if df is not None and len(df) else df

    er_edu, er_sa, er_rs = (drop_bad(x, "emp_pct", emp_bad) for x in (er_edu, er_sa, er_rs))
    w_age, w_edu, w_ind = (drop_bad(x, "wage", set(wage_bad)) for x in (w_age, w_edu, w_ind))

    # ---- national table ---------------------------------------------------------------------------------
    idx = sorted(set(emp_nat.index) | set(wage_nat.index))
    nat = pd.DataFrame({"period_idx": idx})
    nat["emp_pct"] = nat["period_idx"].map(emp_nat.drop(index=list(emp_bad), errors="ignore"))
    nat["wage"] = nat["period_idx"].map(wage_nat.drop(index=list(wage_bad), errors="ignore"))
    nat["emp_note"] = np.where(nat["period_idx"].isin(list(emp_bad)), "ตารางต้นทางขัดแย้งกัน", "")
    nat["wage_note"] = nat["period_idx"].map(lambda i: wage_bad.get(int(i), ""))
    meta = _period_meta(idx + [int(i) for x in (er_sa, w_age, er_edu, w_edu, er_rs, w_ind) if x is not None and len(x) for i in x["period_idx"].unique()])
    nat = meta.merge(nat, on="period_idx", how="right").sort_values("period_idx").reset_index(drop=True)
    b.tables["lm_national"] = nat

    # ---- regions: both tables agree with a second table (sex / education / industry totals) -------------
    def region_main(df, value, **eq):
        d = _pick(df, **eq)
        if d.empty:
            return _empty_region_series()
        d = d[d["region"] != NATIONAL]
        return d.set_index(["period_idx", "region"])[value] if len(d) else _empty_region_series()

    def agree(cands, tol_abs, tol_rel):
        """First available value per (quarter, region); keys where two tables disagree are dropped."""
        cands = [x for x in cands if len(x)]
        if not cands:
            return _empty_region_series(), 0
        fr = pd.concat(cands, axis=1)
        spread = fr.max(axis=1) - fr.min(axis=1)
        limit = np.maximum(tol_abs, tol_rel * fr.max(axis=1).abs())
        bad = (spread > limit) & (fr.notna().sum(axis=1) >= 2)
        val = fr.bfill(axis=1).iloc[:, 0]
        return val[~bad], int(bad.sum())

    emp_r, n_emp_bad = agree([region_main(er_sa, "emp_pct", area="รวม", sex="รวม", age_group="รวม"),
                              region_main(er_edu, "emp_pct", area="รวม", level_of_edu="รวม"), region_main(er_rs, "emp_pct", sex="รวม")],
                             config.EMP_AGREE_TOL_PP, 0)
    wage_r, n_wage_bad = agree([region_main(w_age, "wage", area="รวม", sex="รวม", age_group="รวม"),
                                region_main(w_edu, "wage", area="รวม", sex="รวม", level_of_edu="รวม"), region_main(w_ind, "wage", industry="รวม")],
                               0, config.WAGE_AGREE_TOL)
    for n, label in ((n_emp_bad, "อัตรามีงานทำ"), (n_wage_bad, "ค่าจ้าง")):
        if n:
            b.report.add(v.Issue("warning", "region_tables_conflict", "labour_market",
                                 f"{label}รายภาคจากตารางต่างกันไม่ตรงกัน {n} จุด (ภาค×ไตรมาส) — ไม่ใช้ค่านั้น", n))
    reg = pd.concat([emp_r.rename("emp_pct"), wage_r.rename("wage")], axis=1)
    reg = reg.reset_index() if len(reg) else pd.DataFrame(columns=["period_idx", "region", "emp_pct", "wage"])
    reg = reg.merge(meta, on="period_idx", how="left")
    reg = c._add_region_basis(reg) if len(reg) else reg
    b.tables["lm_region"] = reg.sort_values(["period_idx", "region"]).reset_index(drop=True)

    # ---- breakdown tables used by the page (national total of the other dimensions) ---------------------
    parts = []
    if er_sa is not None and len(er_sa):
        parts.append(_pick(er_sa, region=NATIONAL, area="รวม")[["period_idx", "sex", "age_group", "emp_pct"]])
    sex_age = None
    if parts:
        sex_age = parts[0]
    if w_age is not None and len(w_age):
        wa = _pick(w_age, region=NATIONAL, area="รวม")[["period_idx", "sex", "age_group", "wage"]]
        sex_age = wa if sex_age is None else sex_age.merge(wa, on=["period_idx", "sex", "age_group"], how="outer")
    if sex_age is not None:
        b.tables["lm_sex_age"] = sex_age.merge(meta, on="period_idx", how="left").sort_values(["period_idx", "sex", "age_group"]).reset_index(drop=True)

    edu = None
    if er_edu is not None and len(er_edu):
        edu = er_edu.rename(columns={"level_of_edu": "edu"})[["period_idx", "region", "area", "edu", "emp_pct"]].assign(sex="รวม")
    if w_edu is not None and len(w_edu):
        we = w_edu.rename(columns={"level_of_edu": "edu"})[["period_idx", "region", "area", "sex", "edu", "wage"]]
        if edu is None:
            edu = we
        else:
            edu = edu.merge(we, on=["period_idx", "region", "area", "sex", "edu"], how="outer")
    if edu is not None:
        b.tables["lm_edu"] = edu.merge(meta, on="period_idx", how="left").sort_values(["period_idx", "region", "area", "sex", "edu"]).reset_index(drop=True)
    if w_ind is not None and len(w_ind):
        b.tables["lm_industry"] = w_ind[["period_idx", "region", "industry", "wage"]].merge(meta, on="period_idx", how="left").reset_index(drop=True)

    # the regional unemployment table gains the two new measures (same keys, no new rows)
    if b.has("region_series") and b.has("lm_region"):
        add = b.tables["lm_region"][["period_idx", "region", "emp_pct", "wage"]]
        b.tables["region_series"] = b.tables["region_series"].drop(columns=[x for x in ("emp_pct", "wage") if x in b.tables["region_series"].columns]) \
            .merge(add, on=["period_idx", "region"], how="left", validate="one_to_one")

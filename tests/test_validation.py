import pandas as pd
import pytest

from data_processing import clean, normalize as nz, validation as v
from tests.fixtures import u_region_raw


def test_schema_missing_column_is_error():
    raw = u_region_raw().drop(columns=["area"])
    df, rep = clean.clean_u_region(raw)
    assert df.empty and not rep.ok
    assert any(i.check == "schema" for i in rep.errors)


def test_schema_ok_and_bom_in_header_handled():
    df, rep = clean.clean_u_region(u_region_raw())
    assert rep.ok and len(df) == 24
    assert {"year_be", "quarter", "region", "area", "value_k"} <= set(df.columns)


def test_duplicate_detection_blocks_table():
    raw = pd.concat([u_region_raw(), u_region_raw().head(1)])
    df, rep = clean.clean_u_region(raw)
    assert df.empty
    assert any(i.check == "duplicates" for i in rep.errors)


def test_unit_check_rejects_wrong_unit():
    raw = u_region_raw()
    raw["unit"] = "คน"
    df, rep = clean.clean_u_region(raw)
    assert df.empty and any(i.check == "unit" for i in rep.errors)


def test_unit_missing_column():
    issues = v.check_unit(pd.DataFrame({"value": [1]}), "unit", "พันคน", "t")
    assert issues and issues[0].severity == "error"


def test_year_era_not_converted_silently():
    raw = u_region_raw()
    raw["﻿year"] = raw["﻿year"] - 543  # looks like CE
    df, rep = clean.clean_u_region(raw)
    assert df.empty and any(i.check == "year_era" for i in rep.errors)


def test_be_ce_conversion_range_checked():
    assert nz.be_to_ce(2569) == 2026
    assert nz.ce_to_be(2025) == 2568
    with pytest.raises(ValueError):
        nz.be_to_ce(2026)


def test_negative_values_flagged():
    raw = u_region_raw()
    raw.loc[0, "value"] = -1.0
    df, rep = clean.clean_u_region(raw)
    assert df.empty and any(i.check == "negative" for i in rep.errors)


def test_non_numeric_value_flagged():
    raw = u_region_raw().astype({"value": object})
    raw.loc[0, "value"] = "abc"
    df, rep = clean.clean_u_region(raw)
    assert df.empty and any(i.check == "dtype" for i in rep.errors)


def test_missing_values_not_filled():
    d = pd.DataFrame({"value_k": [1.0, None]})
    issues = v.check_missing(d, ["value_k"], "t")
    assert issues and d["value_k"].isna().sum() == 1


def test_empty_dataset_is_reported():
    df, rep = clean.clean_u_region(pd.DataFrame())
    assert df.empty and any(i.check == "empty" for i in rep.errors)


def test_double_counting_total_mixed_with_components():
    d = pd.DataFrame({"period_idx": [1, 1, 1], "sex": ["รวม", "ชาย", "หญิง"]})
    issues = v.check_double_counting(d, "sex", ["period_idx"], "t")
    assert issues and issues[0].severity == "error"


def test_double_counting_clean_partition_ok():
    d = pd.DataFrame({"period_idx": [1, 1], "sex": ["ชาย", "หญิง"]})
    assert v.check_double_counting(d, "sex", ["period_idx"], "t") == []


def test_reconciliation_flags_mismatched_period():
    parts = pd.Series({1: 100.0, 2: 150.0})
    total = pd.Series({1: 100.2, 2: 100.0})
    issues, failed = v.reconcile(parts, total, "t", "x")
    assert failed == {2} and issues


def test_education_labels_grouped_without_double_count():
    assert nz.normalize_education_group("มัธยมศึกษาตอนปลาย สายวิชาการ") == nz.normalize_education_group("มัธยมศึกษาตอนปลาย สายอาชีวศึกษา")
    assert nz.normalize_education_group("รวม") is None
    assert nz.normalize_education_group("???") == nz.EDU_UNMAPPED


def test_region_label_variants_unified():
    assert nz.normalize_region("2) กลาง") == "ภาคกลาง" == nz.normalize_region("ภาคกลาง")

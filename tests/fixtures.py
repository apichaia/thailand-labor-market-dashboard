"""TEST FIXTURES - SYNTHETIC DATA FOR UNIT TESTS ONLY.

These numbers are invented to exercise code paths. They must never be loaded
by the dashboard (the app reads only data/raw, which comes from public sources).
"""
import pandas as pd

TEST_ONLY = "TEST FIXTURE - NOT REAL DATA"


def u_region_raw():
    rows = []
    for y in (2567, 2568):
        for q in (1, 2, 3, 4):
            for region, area, val in (("กรุงเทพมหานคร", "เขตเทศบาล", 10.0), ("ภาคเหนือ", "เขตเทศบาล", 5.0), ("ภาคเหนือ", "นอกเขตเทศบาล", 15.0)):
                rows.append({"﻿year": y, "quarter": f"ไตรมาส {q}", "region": region, "area": area, "value": val, "unit": "พันคน", "source": TEST_ONLY})
    return pd.DataFrame(rows)

from datetime import date
from types import SimpleNamespace

from app.services.alerts import detect_dry_spell, detect_ndvi_stress, water_balance
from app.services.fertilizer import oc_status, plan_fertilizer
from app.services.recommend import current_season, score_crop


def _days(rains, et0=5.0):
    return [
        {"date": f"2026-01-{i + 1:02d}", "rain_mm": r, "et0_mm": et0} for i, r in enumerate(rains)
    ]


def test_dry_spell_detected_and_severe_when_ongoing():
    spell = detect_dry_spell(_days([0.0] * 16))
    assert spell is not None
    assert spell.length_days == 16
    assert spell.severity == "severe"
    assert spell.ongoing


def test_rainy_days_break_the_run():
    spell = detect_dry_spell(_days([0, 0, 0, 5.0, 0, 0, 0, 0, 0, 0, 0, 3.0, 0, 0, 0, 0]))
    assert spell is not None
    assert spell.start == "2026-01-05"
    assert spell.length_days == 7
    assert not spell.ongoing


def test_no_spell_when_runs_are_short():
    assert detect_dry_spell(_days([0, 0, 0, 4.0, 0, 0, 0, 3.0, 0, 0])) is None


def test_water_balance_hand_computed():
    # etc = 1.2*5.0*7 = 42.0; rain_eff = 0.8*1.0*7 = 5.6
    # loam: fc 0.28, wp 0.14 -> theta_crit 0.21; buffer (0.28-0.21)*300 = 21.0
    wb = water_balance(_days([1.0] * 7), kc=1.2, soil_moisture=0.28, texture="loam")
    assert wb.etc_mm == 42.0
    assert wb.rain_eff_mm == 5.6
    assert wb.soil_buffer_mm == 21.0
    assert wb.irrigation_mm == 15.4
    assert wb.level == "light"


def test_water_balance_no_need_when_wet():
    wb = water_balance(_days([10.0] * 7, et0=3.0), kc=1.0, soil_moisture=0.30, texture="clay loam")
    assert wb.irrigation_mm == 0.0
    assert wb.level == "none"


def _crop(**kw):
    base = dict(
        crop="groundnut",
        label_en="Groundnut",
        label_te="వేరుశనగ",
        label_hi="मूंगफली",
        season="kharif",
        duration_days=110,
        water_need_mm=550,
        kc_mid=1.15,
        soil_ph_min=6.0,
        soil_ph_max=7.5,
        soil_texture="sandy loam",
        min_temp_c=25,
        max_temp_c=32,
        rainfed_ok="yes",
        groundwater_need="low",
        source="test",
    )
    base.update(kw)
    return SimpleNamespace(**base)


SITE = dict(rain_mm=400, capacity_mm=150, ph=7.0, texture="clay loam", gw_category="semi-critical")


def test_out_of_season_crop_excluded():
    assert score_crop(_crop(season="rabi"), season="kharif", **SITE) is None


def test_water_hungry_crop_penalised_with_reason():
    paddy = _crop(
        crop="paddy",
        season="both",
        water_need_mm=1250,
        groundwater_need="high",
        soil_texture="clay",
    )
    p = score_crop(paddy, season="kharif", **SITE)
    g = score_crop(_crop(), season="kharif", **SITE)
    assert p is not None and g is not None
    assert p["score"] < g["score"]
    assert any("likely available" in r for r in p["reasons"])
    assert set(p["breakdown"]) == {"water", "groundwater", "ph", "texture"}


def test_season_from_month():
    assert current_season(7) == "kharif"
    assert current_season(12) == "rabi"


def _ndvi_window(d: date, ndvi):
    return {"date_start": d, "ndvi": ndvi}


def test_ndvi_stress_fires_on_anniversary_anomaly():
    as_of = date(2026, 3, 1)
    windows = [
        _ndvi_window(date(2025, 3, 3), 0.65),  # healthy same period last year
        _ndvi_window(date(2026, 2, 19), 0.45),
        _ndvi_window(date(2026, 3, 1), 0.40),  # 0.25 below baseline -> severe
    ]
    s = detect_ndvi_stress(windows, as_of)
    assert s is not None
    assert s.severity == "severe"
    assert s.baseline == 0.65
    assert s.anomaly == -0.25


def test_ndvi_seasonal_dry_down_does_not_alarm():
    # Low NDVI now, but it was equally low the same period last year -> no alert.
    as_of = date(2026, 3, 1)
    windows = [
        _ndvi_window(date(2025, 3, 3), 0.32),
        _ndvi_window(date(2026, 2, 19), 0.35),
        _ndvi_window(date(2026, 3, 1), 0.31),
    ]
    assert detect_ndvi_stress(windows, as_of) is None


def test_ndvi_stale_reading_ignored():
    as_of = date(2026, 3, 1)
    windows = [_ndvi_window(date(2026, 1, 1), 0.2)]  # >35 days old
    assert detect_ndvi_stress(windows, as_of) is None


def test_ndvi_sharp_trend_triggers_without_baseline():
    as_of = date(2026, 7, 20)
    windows = [
        _ndvi_window(date(2026, 6, 20), 0.70),
        _ndvi_window(date(2026, 6, 30), 0.68),
        _ndvi_window(date(2026, 7, 10), 0.66),
        _ndvi_window(date(2026, 7, 20), 0.45),  # 0.23 below recent mean
    ]
    s = detect_ndvi_stress(windows, as_of)
    assert s is not None
    assert s.trend is not None and s.trend <= -0.15


def test_oc_status_thresholds():
    assert oc_status(0.4) == "low"
    assert oc_status(0.6) == "medium"
    assert oc_status(1.5) == "high"


def test_fertilizer_high_oc_eases_nitrogen_and_computes_urea():
    # maize N120: high OC (SOC 15 g/kg = 1.5%) -> N x0.85 = 102; DAP for P60 = 130 kg/ha,
    # supplying 0.18*130 = 23.4 kg N, so urea = (102 - 23.4)/0.46 ~= 171 kg/ha.
    plan = plan_fertilizer(crop="maize", n_kg_ha=120, p_kg_ha=60, k_kg_ha=40, soc_g_kg=15.0, ph=6.7)
    assert plan.oc_status == "high"
    n_dose = next(d.kg_ha for d in plan.doses if d.nutrient == "N")
    assert n_dose == 102
    assert plan.dap_kg_ha == 130
    assert 165 <= plan.urea_kg_ha <= 176
    # SoilGrids OC is modeled, so every OC-driven plan carries the Soil Health Card caveat
    assert any("Soil Health Card" in n for n in plan.notes)


def test_fertilizer_low_oc_recommends_manure_and_full_n():
    plan = plan_fertilizer(crop="paddy", n_kg_ha=100, p_kg_ha=50, k_kg_ha=50, soc_g_kg=3.0, ph=5.5)
    assert plan.oc_status == "low"
    n_dose = next(d.kg_ha for d in plan.doses if d.nutrient == "N")
    assert n_dose == 110  # low OC boosts N by 10%
    assert any("farmyard manure" in a for a in plan.amendments)
    assert any("lime" in a for a in plan.amendments)  # acidic pH 5.5


def test_fertilizer_legume_zero_potash_no_mop():
    plan = plan_fertilizer(
        crop="pigeonpea", n_kg_ha=20, p_kg_ha=50, k_kg_ha=0, soc_g_kg=6.0, ph=7.0
    )
    assert plan.mop_kg_ha == 0
    assert next(d.kg_ha for d in plan.doses if d.nutrient == "K2O") == 0

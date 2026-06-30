"""Deterministic fertilizer advisory from soil test data + crop norms.

No LLM: nutrient math must be reproducible and citable. Method follows the
soil-test-based adjustment used by Indian state agriculture departments —
crop package-of-practices N-P2O5-K2O (data/crop_requirements.csv, ICAR/TNAU)
tuned by the plot's soil organic carbon (a proxy for N supply) and pH.

Organic-carbon ratings (Indian Soil Health Card): low <0.50%, medium
0.50-0.75%, high >0.75% (SOC g/kg / 10 = OC%). Low OC soils get full/boosted
N and an organic-matter recommendation; high OC soils need less applied N.
Urea is 46% N, DAP 46% P2O5 + 18% N, MOP 60% K2O.
"""

from dataclasses import dataclass, field

OC_LOW, OC_HIGH = 0.50, 0.75
# Gentle adjustment: SoilGrids organic carbon is a 250 m satellite-modeled
# estimate and tends to read high for semi-arid Indian soils, so we do not swing
# N aggressively on it — the free government Soil Health Card is authoritative.
N_FACTOR = {"low": 1.10, "medium": 1.0, "high": 0.85}
UREA_N, MOP_K = 0.46, 0.60
SHC_CAVEAT = "organic carbon is a satellite estimate — confirm with a free Soil Health Card"


@dataclass
class NutrientDose:
    nutrient: str  # N | P2O5 | K2O
    kg_ha: float


@dataclass
class FertilizerPlan:
    crop: str
    oc_pct: float | None
    oc_status: str | None
    ph: float | None
    doses: list[NutrientDose]
    urea_kg_ha: float
    dap_kg_ha: float
    mop_kg_ha: float
    amendments: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def oc_status(oc_pct: float) -> str:
    if oc_pct < OC_LOW:
        return "low"
    if oc_pct <= OC_HIGH:
        return "medium"
    return "high"


def plan_fertilizer(
    *,
    crop: str,
    n_kg_ha: float,
    p_kg_ha: float,
    k_kg_ha: float,
    soc_g_kg: float | None,
    ph: float | None,
) -> FertilizerPlan:
    oc_pct = round(soc_g_kg / 10, 2) if soc_g_kg is not None else None
    status = oc_status(oc_pct) if oc_pct is not None else None

    n_adj = round(n_kg_ha * N_FACTOR.get(status or "medium", 1.0))
    doses = [
        NutrientDose("N", float(n_adj)),
        NutrientDose("P2O5", round(p_kg_ha)),
        NutrientDose("K2O", round(k_kg_ha)),
    ]

    # Straight fertilisers: DAP supplies all P2O5 (and some N), urea tops up N, MOP supplies K2O.
    dap = round(p_kg_ha / 0.46) if p_kg_ha > 0 else 0
    n_from_dap = dap * 0.18
    urea = round(max(0.0, n_adj - n_from_dap) / UREA_N)
    mop = round(k_kg_ha / MOP_K) if k_kg_ha > 0 else 0

    amendments: list[str] = []
    notes: list[str] = []
    if status == "low":
        amendments.append("apply 5-10 t/ha farmyard manure or compost to build organic carbon")
    if status == "high":
        notes.append("soil reads rich in organic carbon; applied N eased slightly")
    if status is not None:
        notes.append(SHC_CAVEAT)
    if ph is not None and ph < 6.0:
        amendments.append("acidic soil: apply agricultural lime before sowing")
    elif ph is not None and ph > 8.0:
        amendments.append("alkaline soil: apply gypsum to improve nutrient uptake")
    if p_kg_ha > 0 and ph is not None and (ph < 6.0 or ph > 7.8):
        notes.append("phosphorus uptake is lower at this pH; place P near the root zone")
    notes.append("split N: half at sowing, half at 30-40 days")

    return FertilizerPlan(
        crop=crop,
        oc_pct=oc_pct,
        oc_status=status,
        ph=ph,
        doses=doses,
        urea_kg_ha=float(urea),
        dap_kg_ha=float(dap),
        mop_kg_ha=float(mop),
        amendments=amendments,
        notes=notes,
    )

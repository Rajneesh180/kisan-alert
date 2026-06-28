"""Deterministic trilingual SMS templates for alerts.

The app renders exactly what a gateway would send (a DLT-registered gateway is
a roadmap item). Unicode SMS segments are 70 UCS-2 chars; texts are kept within
~2 segments. No LLM involved: alert SMS must be reproducible and reviewable.
"""

TEMPLATES = {
    ("dry_spell", "en"): (
        "KISAN ALERT {village}: ~{length} dry days from {start}. {crop}: plan "
        "protective irrigation. Reply PANI for advice."
    ),
    ("dry_spell", "hi"): (
        "किसान अलर्ट {village}: {start} से {length} दिन सूखा. {crop}: सुरक्षात्मक "
        "सिंचाई करें. सलाह हेतु PANI भेजें."
    ),
    ("dry_spell", "te"): (
        "కిసాన్ అలర్ట్ {village}: {start} నుండి {length} రోజులు పొడి వాతావరణం. {crop}: "
        "రక్షక తడి ఇవ్వండి. సలహాకు PANI పంపండి."
    ),
    ("irrigation", "en"): (
        "KISAN ALERT {village}: {crop} needs ~{mm}mm water this week "
        "(rain {rain}mm expected). {action}"
    ),
    ("irrigation", "hi"): (
        "किसान अलर्ट {village}: {crop} को इस सप्ताह ~{mm}mm पानी चाहिए "
        "(वर्षा {rain}mm संभावित). {action}"
    ),
    ("irrigation", "te"): (
        "కిసాన్ అలర్ట్ {village}: {crop}కు ఈ వారం ~{mm}mm నీరు అవసరం (వర్షం {rain}mm అంచనా). {action}"
    ),
    ("crops", "en"): (
        "KISAN {village} ({season}): best crops - {c1}, {c2}. ~{avail}mm water likely. "
        "Reply PANI for irrigation advice."
    ),
    ("crops", "hi"): (
        "किसान {village} ({season}): उपयुक्त फसलें - {c1}, {c2}. ~{avail}mm पानी संभावित. "
        "सिंचाई सलाह हेतु PANI भेजें."
    ),
    ("crops", "te"): (
        "కిసాన్ {village} ({season}): అనువైన పంటలు - {c1}, {c2}. ~{avail}mm నీరు అంచనా. "
        "తడి సలహాకు PANI పంపండి."
    ),
    ("crop_stress", "en"): (
        "KISAN ALERT {village}: satellite shows {crop} growth below normal "
        "(NDVI {ndvi}). Check field for water/pest stress. Reply PANI."
    ),
    ("crop_stress", "hi"): (
        "किसान अलर्ट {village}: उपग्रह में {crop} की बढ़त सामान्य से कम "
        "(NDVI {ndvi}). खेत में पानी/कीट जांचें. PANI भेजें."
    ),
    ("crop_stress", "te"): (
        "కిసాన్ అలర్ట్ {village}: ఉపగ్రహంలో {crop} ఎదుగుదల సాధారణం కంటే తక్కువ "
        "(NDVI {ndvi}). పొలంలో నీరు/తెగుళ్లు చూడండి. PANI పంపండి."
    ),
    ("help", "en"): (
        "Kisan Alert: send PANI for water advice, FASAL for crop advice. "
        "For plant problems visit your RSK with a photo."
    ),
    ("help", "hi"): (
        "किसान अलर्ट: पानी सलाह हेतु PANI, फसल सलाह हेतु FASAL भेजें. पौधों की समस्या हो तो फोटो लेकर RSK जाएं."
    ),
    ("help", "te"): (
        "కిసాన్ అలర్ట్: నీటి సలహాకు PANI, పంట సలహాకు FASAL పంపండి. మొక్కల సమస్యలకు ఫోటోతో RSKకి వెళ్లండి."
    ),
}

ACTIONS = {
    "light": {
        "en": "One light irrigation advised.",
        "hi": "एक हल्की सिंचाई करें.",
        "te": "ఒక తేలికపాటి తడి ఇవ్వండి.",
    },
    "urgent": {
        "en": "Irrigate now - crop stress risk.",
        "hi": "तुरंत सिंचाई करें - फसल को खतरा.",
        "te": "వెంటనే తడి ఇవ్వండి - పంటకు ప్రమాదం.",
    },
}

LANGS = ("en", "hi", "te")


def render(kind: str, lang: str, **params) -> str:
    return TEMPLATES[(kind, lang)].format(**params)


def segments(text: str) -> int:
    per = 160 if text.isascii() else 70
    return max(1, -(-len(text) // per))


def render_all(
    kind: str, crop_labels: dict[str, str], action_key: str | None = None, **params
) -> dict[str, str]:
    out = {}
    for lang in LANGS:
        p = dict(params, crop=crop_labels[lang])
        if action_key:
            p["action"] = ACTIONS[action_key][lang]
        out[lang] = TEMPLATES[(kind, lang)].format(**p)
    return out

"""Human labels for TM2 code-prefix groupings, derived from the real chapter
structure of WHO's Traditional Medicine Module 2 (the SK.. through ST..
ranges seen in the actual ICD-11 data) -- not an invented taxonomy. Shared
by the Coverage dashboard and the Analytics dashboard so both report the
same categories.
"""

CATEGORY_LABELS = {
    "SK": "Neurological, Eye, Ear, Nose & Throat",
    "SL": "Respiratory, Cardiovascular & ENT",
    "SM": "Gastrointestinal, Urinary & Reproductive",
    "SN": "Skin, Hair & Reproductive Health",
    "SP": "Musculoskeletal, Metabolic & Febrile",
    "SQ": "Mental, Emotional & Behavioural",
    "SR": "Childhood Disorders & Dosha/Pattern Imbalances",
    "SS": "Body Constitution Patterns",
    "ST": "Temperament & Constitutional Patterns",
}


def category_for_code(code: str) -> str:
    prefix = code[:2].upper() if code else ""
    return CATEGORY_LABELS.get(prefix, f"Other ({prefix})" if prefix else "Uncategorized")

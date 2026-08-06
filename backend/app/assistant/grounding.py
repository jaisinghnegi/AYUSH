"""Lightweight retrieval-augmented context for the Ayurveda Assistant.

Before asking Groq to answer, we search our own real, verified data
(NAMASTE codes, ICD-11 entities, and the verified NAMASTE<->TM2 mapping
table) for anything relevant to the user's message, and hand that to the
model as grounding context. This is what stops the assistant from
inventing plausible-but-wrong codes: it's told to prefer real retrieved
data and to say "no verified code" rather than guess when nothing matches.
"""

import re

from app.codecs.icd import IcdCodec, IcdFilter
from app.codecs.mapping import mapping_table
from app.codecs.namaste import Language, NamasteCodec, NamasteFilter

_STOPWORDS = {
    "the", "is", "a", "an", "and", "or", "in", "of", "to", "what", "how",
    "does", "do", "for", "with", "on", "about", "relate", "related",
    "code", "codes", "this", "that", "are", "can", "you", "tell", "me",
    "please", "explain", "which", "who", "when", "where", "why",
}


def _extract_keywords(message: str, limit: int = 4) -> list[str]:
    words = re.findall(r"[A-Za-z]{4,}", message)
    keywords = []
    seen = set()
    for w in words:
        lw = w.lower()
        if lw in _STOPWORDS or lw in seen:
            continue
        seen.add(lw)
        keywords.append(w)
        if len(keywords) >= limit:
            break
    return keywords


async def build_context(message: str) -> str:
    keywords = _extract_keywords(message)
    if not keywords:
        return ""

    namaste_codec = NamasteCodec()
    icd_codec = IcdCodec()

    namaste_hits = []
    icd_hits = []
    seen_namaste_ids = set()
    seen_icd_ids = set()

    for kw in keywords:
        if len(namaste_hits) < 5:
            for hit in await namaste_codec.search_codes(
                NamasteFilter(code=None, language=Language.BOTH, search_term=kw), 3
            ):
                if hit.namc_id not in seen_namaste_ids:
                    seen_namaste_ids.add(hit.namc_id)
                    namaste_hits.append(hit)

        if len(icd_hits) < 5:
            for hit in await icd_codec.search_codes(IcdFilter(search_term=kw), 3):
                if hit.id not in seen_icd_ids:
                    seen_icd_ids.add(hit.id)
                    icd_hits.append(hit)

    lines: list[str] = []

    for n in namaste_hits[:5]:
        entries = mapping_table.lookup_by_namaste(n.namc_code) or mapping_table.lookup_by_namaste(
            str(n.namc_id)
        )
        if entries:
            e = entries[0]
            lines.append(
                f'- NAMASTE "{n.namc_term}" (id {n.namc_id}) has a VERIFIED mapping to '
                f'ICD-11 TM2 code {e.icd11_tm2_code}: "{e.icd11_tm2_title}"'
            )
        else:
            lines.append(
                f'- NAMASTE "{n.namc_term}" (id {n.namc_id}), code {n.namc_code} -- '
                f"no verified ICD-11 TM2 mapping exists in our database for this term"
            )

    for i in icd_hits[:5]:
        title = i.title or "(no title)"
        lines.append(f'- ICD-11 code {i.code}: "{title}"')

    if not lines:
        return ""

    return (
        "Relevant verified data retrieved from the AyuSetu database for this question "
        "(these are real records, not examples):\n"
        + "\n".join(lines)
        + "\n\nWhen answering, prefer these real codes over any you might otherwise recall. "
        "If none of the above actually answers the question, say plainly that you don't have "
        "a verified code for it in this system rather than guessing one."
    )

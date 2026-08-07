from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.db import mongo


class Language(str, Enum):
    ENGLISH = "english"
    HINDI = "hindi"
    BOTH = "both"


@dataclass
class NamasteFilter:
    code: Optional[str] = None
    language: Language = Language.BOTH
    search_term: Optional[str] = None


@dataclass
class NamasteCode:
    sr_no: int
    namc_id: int
    namc_code: str
    namc_term: str
    namc_term_diacritical: str
    namc_term_devanagari: str
    short_definition: Optional[str] = None
    long_definition: Optional[str] = None
    ontology_branches: Optional[str] = None

    @staticmethod
    def from_document(doc: dict) -> "NamasteCode":
        return NamasteCode(
            sr_no=doc.get("field_1", 0),
            namc_id=doc.get("field_1_1", 0),
            namc_code=doc.get("AYU", ""),
            namc_term=doc.get("vyAdhi-viniScayaH", ""),
            namc_term_diacritical=doc.get("vyādhi-viniścayaḥ", ""),
            namc_term_devanagari=doc.get("व्याधि-विनिश्चयः", ""),
            short_definition=doc.get("Unnamed: 6"),
            long_definition=doc.get("Unnamed: 7"),
            ontology_branches=doc.get("Unnamed: 8"),
        )

    def parse_codes(self) -> tuple[str, Optional[str]]:
        # Parse the namc_code field to separate NAMASTE and ICD codes.
        if "(" in self.namc_code and ")" in self.namc_code:
            # Format: "AAA-1 (SR-11)" or "SR11 (AAA-1)"
            parts = self.namc_code.split("(", 1)
            if len(parts) == 2:
                nam_code = parts[0].strip()
                icd_code = parts[1].replace(")", "").strip()
                return nam_code, icd_code
        elif " - " in self.namc_code:
            # Format: "AAA-1 - SR-11"
            parts = self.namc_code.split(" - ")
            if len(parts) == 2:
                nam_code = parts[0].strip()
                icd_code = parts[1].strip()
                return nam_code, icd_code

        # Default: only NAMASTE code, no ICD mapping.
        return self.namc_code, None


def _relevance_key(code: "NamasteCode", search_term: str) -> tuple[int, int]:
    """Lower is more relevant. Mongo's regex $or has no notion of relevance,
    so a search for a short canonical term like "jvara" can just as easily
    surface a long compound entry like "yakShmajajvaraH" first (whichever
    happened to be inserted earlier) -- which then tends to be missing a
    description, since compound derivative entries are less likely to have
    one filled in. Ranking exact/prefix matches first, then shortest match,
    fixes both problems: the canonical entry surfaces, and it's more likely
    to be the one that's actually documented.
    """
    term_lower = search_term.lower()
    candidates = [
        code.namc_term,
        code.namc_term_diacritical,
        code.namc_term_devanagari,
        code.namc_code,
    ]

    best_rank = 3  # 0=exact, 1=starts-with, 2=word-boundary contains, 3=substring
    shortest_len = 9999
    for candidate in candidates:
        if not candidate:
            continue
        candidate_lower = candidate.lower()
        if term_lower not in candidate_lower:
            continue
        shortest_len = min(shortest_len, len(candidate))
        if candidate_lower == term_lower:
            best_rank = min(best_rank, 0)
        elif candidate_lower.startswith(term_lower):
            best_rank = min(best_rank, 1)
        else:
            best_rank = min(best_rank, 3)

    return (best_rank, shortest_len)


# Common alternate transliterations of Sanskrit terms that don't literally
# match the codebook's own ASCII transliteration scheme (e.g. the codebook
# spells it "vicarcikA", not "vicharchika"). Not an attempt at general
# transliteration normalization -- just known gaps, added as they're found,
# so a reasonable spelling still finds the real entry instead of nothing.
COMMON_SEARCH_ALIASES: dict[str, str] = {
    "vicharchika": "vicarcik",
}


class NamasteCodec:
    async def search_codes(self, filter: NamasteFilter, limit: Optional[int] = None) -> list[NamasteCode]:
        print(f"🔍 Searching NAMASTE codes with filter: {filter}")

        client = await mongo.get_instance()
        ayurveda_db = client.get_database_by_name("ayurveda_db")
        collection = ayurveda_db["namc_codes"]

        query: dict = {}

        # Use regex search for better partial matching instead of text search.
        if filter.search_term:
            search_terms = {filter.search_term}
            alias = COMMON_SEARCH_ALIASES.get(filter.search_term.lower())
            if alias:
                search_terms.add(alias)

            or_clauses = []
            for term in search_terms:
                or_clauses.extend(
                    [
                        {"vyAdhi-viniScayaH": {"$regex": term, "$options": "i"}},
                        {"vyādhi-viniścayaḥ": {"$regex": term, "$options": "i"}},
                        {"व्याधि-विनिश्चयः": {"$regex": term, "$options": "i"}},
                        {"AYU": {"$regex": term, "$options": "i"}},
                    ]
                )
            query["$or"] = or_clauses

        if filter.code:
            query["AYU"] = {"$regex": filter.code, "$options": "i"}

        print(f"📊 MongoDB NAMASTE query: {query}")

        # Fetch a wider pool than requested so relevance ranking (below) has
        # something to actually rank -- capping at the DB layer before
        # ranking would just return whatever Mongo happened to match first.
        fetch_limit = max((limit or 20) * 5, 50)
        cursor = collection.find(query).limit(fetch_limit)

        results = [NamasteCode.from_document(doc) async for doc in cursor]

        if filter.search_term:
            results.sort(key=lambda code: min(_relevance_key(code, term) for term in search_terms))

        if limit is not None:
            results = results[:limit]

        print(f"✅ Found {len(results)} NAMASTE codes")
        return results

    async def get_all_codes(self, limit: Optional[int] = None) -> list[NamasteCode]:
        return await self.search_codes(NamasteFilter(), limit)

    def format_response(self, codes: list[NamasteCode], language: Language) -> list[dict]:
        results = []
        for code in codes:
            if language == Language.HINDI:
                display_name = code.namc_term_devanagari
            elif language == Language.ENGLISH:
                display_name = code.namc_term_diacritical
            else:
                display_name = f"{code.namc_term_diacritical} / {code.namc_term_devanagari}"

            nam_code, icd_code = code.parse_codes()

            results.append(
                {
                    "sr_no": code.sr_no,
                    "namc_id": code.namc_id,
                    "nam_code": nam_code,
                    "icd_code": icd_code,
                    "term": code.namc_term,
                    "display": display_name,
                    "short_definition": code.short_definition,
                    "long_definition": code.long_definition,
                    "ontology_branches": code.ontology_branches,
                }
            )
        return results

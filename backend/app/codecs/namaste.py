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


class NamasteCodec:
    async def search_codes(self, filter: NamasteFilter, limit: Optional[int] = None) -> list[NamasteCode]:
        print(f"🔍 Searching NAMASTE codes with filter: {filter}")

        client = await mongo.get_instance()
        ayurveda_db = client.get_database_by_name("ayurveda_db")
        collection = ayurveda_db["namc_codes"]

        query: dict = {}

        # Use regex search for better partial matching instead of text search.
        if filter.search_term:
            query["$or"] = [
                {"vyAdhi-viniScayaH": {"$regex": filter.search_term, "$options": "i"}},
                {"vyādhi-viniścayaḥ": {"$regex": filter.search_term, "$options": "i"}},
                {"व्याधि-विनिश्चयः": {"$regex": filter.search_term, "$options": "i"}},
                {"AYU": {"$regex": filter.search_term, "$options": "i"}},
            ]

        if filter.code:
            query["AYU"] = {"$regex": filter.code, "$options": "i"}

        print(f"📊 MongoDB NAMASTE query: {query}")

        cursor = collection.find(query)
        if limit is not None:
            cursor = cursor.limit(limit)

        results = [NamasteCode.from_document(doc) async for doc in cursor]

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

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from app.db import mongo


class IcdDiscipline(str, Enum):
    BIOMEDICINE = "BIOMEDICINE"
    TM1 = "TM1"
    TM2 = "TM2"


@dataclass
class IcdFilter:
    discipline: Optional[IcdDiscipline] = None
    search_term: Optional[str] = None
    parent_filter: Optional[str] = None


def _coerce_code(value: Any) -> str:
    # Mirrors the Rust custom deserializer: handle mixed int/string/None codes.
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(int(value))
    return str(value)


@dataclass
class IcdCode:
    id: str
    code: str
    title: str
    definition: Optional[str] = None
    parent: Optional[str] = None
    browser_url: Optional[str] = None
    coding_note: Optional[str] = None
    synonyms: Optional[str] = None
    exclusions: Optional[str] = None
    inclusions: Optional[str] = None
    is_leaf: Optional[str] = None

    @staticmethod
    def from_document(doc: dict) -> "IcdCode":
        return IcdCode(
            id=doc.get("id", ""),
            code=_coerce_code(doc.get("code")),
            title=doc.get("title", ""),
            definition=doc.get("definition"),
            parent=doc.get("parent"),
            browser_url=doc.get("browserUrl"),
            coding_note=doc.get("codingNote"),
            synonyms=doc.get("synonyms"),
            exclusions=doc.get("exclusions"),
            inclusions=doc.get("inclusions"),
            is_leaf=doc.get("isLeaf"),
        )


class IcdCodec:
    async def search_codes(self, filter: IcdFilter, limit: Optional[int] = None) -> list[IcdCode]:
        print(f"🔍 Searching ICD codes with filter: {filter}")

        client = await mongo.get_instance()
        icd_db = client.get_database_by_name("icd11_database")
        collection = icd_db["icd11_entities"]

        query: dict = {}

        # TM1 and TM2 entities live at the same /mms/ URL path as everything
        # else in this dataset -- WHO only distinguishes them by a "(TM1)" /
        # "(TM2)" suffix in the title, so that's what we have to filter on.
        if filter.discipline == IcdDiscipline.BIOMEDICINE:
            query["title"] = {"$not": {"$regex": r"\((TM1|TM2)\)"}}
        elif filter.discipline == IcdDiscipline.TM1:
            query["title"] = {"$regex": r"\(TM1\)"}
        elif filter.discipline == IcdDiscipline.TM2:
            query["title"] = {"$regex": r"\(TM2\)"}

        if filter.search_term:
            query["$or"] = [
                {"title": {"$regex": filter.search_term, "$options": "i"}},
                {"definition": {"$regex": filter.search_term, "$options": "i"}},
                {"code": {"$regex": filter.search_term, "$options": "i"}},
            ]

        if filter.parent_filter:
            query["parent"] = filter.parent_filter

        print(f"📊 MongoDB ICD query: {query}")

        cursor = collection.find(query)
        if limit is not None:
            cursor = cursor.limit(limit)

        results = [IcdCode.from_document(doc) async for doc in cursor]

        print(f"✅ Found {len(results)} ICD codes")
        return results

    async def get_biomedicine_codes(self, limit: Optional[int] = None) -> list[IcdCode]:
        return await self.search_codes(IcdFilter(discipline=IcdDiscipline.BIOMEDICINE), limit)

    async def get_tm2_codes(self, limit: Optional[int] = None) -> list[IcdCode]:
        return await self.search_codes(IcdFilter(discipline=IcdDiscipline.TM2), limit)

    async def get_all_codes(self, limit: Optional[int] = None) -> list[IcdCode]:
        return await self.search_codes(IcdFilter(), limit)

    def format_response(self, codes: list[IcdCode]) -> list[dict]:
        return [
            {
                "id": code.id,
                "code": code.code,
                "title": code.title,
                "definition": code.definition,
                "parent": code.parent,
                "browserUrl": code.browser_url,
                "codingNote": code.coding_note,
                "synonyms": code.synonyms,
                "exclusions": code.exclusions,
                "inclusions": code.inclusions,
                "isLeaf": code.is_leaf,
            }
            for code in codes
        ]

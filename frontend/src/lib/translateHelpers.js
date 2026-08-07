export const NAMASTE_SYSTEM = "http://namaste-codes.org";
export const ICD11_SYSTEM = "http://id.who.int/icd/release/11/mms";

// Pull the FHIR Parameters shape from /ConceptMap/$translate down to
// {found, code, display, equivalence, candidates, message}. `candidates` is
// our own (non-FHIR-standard) addition: when there's no verified crosswalk
// entry, the backend can still surface real embedding-similarity-ranked
// suggestions -- kept clearly separate from a verified "match" so a UI can
// never present a guess as a confirmed mapping.
export function parseTranslateResponse(data) {
  const params = data?.parameter || [];
  const result = params.find((p) => p.name === "result")?.valueBoolean;
  const message = params.find((p) => p.name === "message")?.valueString;

  const candidates = params
    .filter((p) => p.name === "candidate")
    .map((p) => {
      const concept = p.part?.find((part) => part.name === "concept")?.valueCoding;
      const similarity = p.part?.find((part) => part.name === "similarity")?.valueDecimal;
      return { code: concept?.code, display: concept?.display, similarity };
    });

  if (!result) return { found: false, message, candidates };

  const match = params.find((p) => p.name === "match");
  const concept = match?.part?.find((p) => p.name === "concept")?.valueCoding;
  const equivalence = match?.part?.find((p) => p.name === "equivalence")?.valueCode;

  return {
    found: true,
    code: concept?.code,
    display: concept?.display,
    equivalence,
    message,
    candidates,
  };
}

// TM2 titles are plain English ("Fever disorder (TM2)"), so we can derive a
// real search keyword from real verified data instead of guessing.
export function deriveKeyword(tm2Display) {
  if (!tm2Display) return "";
  return tm2Display
    .replace(/\(TM[12]\)/i, "")
    .replace(/\bdisorder\b/i, "")
    .trim();
}

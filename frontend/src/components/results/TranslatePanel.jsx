import React, { useState, useEffect } from "react";
import "./TranslatePanel.css";
import { API_BASE } from "../../lib/authApi";
import { parseTranslateResponse, deriveKeyword, NAMASTE_SYSTEM, ICD11_SYSTEM } from "../../lib/translateHelpers";

const STAGE = {
  LOADING: "loading",
  RESOLVED: "resolved",
  UNAVAILABLE: "unavailable",
};

// A search result can come from either side (NAMASTE or ICD-11), from three
// different endpoints (namaste_search, icd_search, terminology_search --
// regex and semantic paths each shape fields slightly differently), so this
// has to check a few possible field names rather than assume one shape.
function detectTranslateTarget(item) {
  const looksNamaste = item.code_system === "NAMASTE" || item.source === "NAMASTE";
  const namasteId = item.sr_no ?? (looksNamaste && item.code != null ? item.code : undefined);
  if (namasteId != null) {
    return { direction: "namaste", code: namasteId };
  }

  const looksIcd = item.code_system === "ICD" || item.source === "ICD-11";
  const icdCode =
    item.icd_code && item.icd_code !== "None"
      ? item.icd_code
      : looksIcd && item.code
      ? item.code
      : undefined;
  if (icdCode) {
    return { direction: "icd", code: icdCode };
  }

  return null;
}

const TranslatePanel = ({ item }) => {
  const [stage, setStage] = useState(STAGE.LOADING);
  const [resolved, setResolved] = useState(null);
  const [biomedicine, setBiomedicine] = useState([]);
  const [candidates, setCandidates] = useState([]);

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      const target = detectTranslateTarget(item);
      if (!target) {
        setStage(STAGE.UNAVAILABLE);
        return;
      }

      const system = target.direction === "namaste" ? NAMASTE_SYSTEM : ICD11_SYSTEM;

      try {
        const res = await fetch(
          `${API_BASE}/ConceptMap/$translate?code=${encodeURIComponent(target.code)}&system=${encodeURIComponent(system)}`
        );
        const data = await res.json();
        const parsed = parseTranslateResponse(data);
        if (cancelled) return;

        if (!parsed.found) {
          setCandidates(parsed.candidates || []);
          setStage(STAGE.UNAVAILABLE);
          return;
        }

        setResolved({ ...parsed, direction: target.direction });
        setStage(STAGE.RESOLVED);

        // Only chase a Biomedicine cross-reference when we resolved
        // NAMASTE -> TM2 -- if the source was already an ICD code there's
        // nothing further to look up.
        if (target.direction === "namaste") {
          const keyword = deriveKeyword(parsed.display);
          if (keyword) {
            const bioRes = await fetch(
              `${API_BASE}/icd/search?search=${encodeURIComponent(keyword)}&discipline=biomedicine&limit=50`
            );
            const bioData = await bioRes.json();
            if (cancelled) return;

            const lowerKeyword = keyword.toLowerCase();
            const ranked = [...(bioData.results || [])].sort((a, b) => {
              const aHit = (a.title || "").toLowerCase().includes(lowerKeyword) ? 0 : 1;
              const bHit = (b.title || "").toLowerCase().includes(lowerKeyword) ? 0 : 1;
              return aHit - bHit;
            });
            setBiomedicine(ranked.slice(0, 3));
          }
        }
      } catch (err) {
        console.error("TranslatePanel resolve failed:", err);
        if (!cancelled) setStage(STAGE.UNAVAILABLE);
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [item]);

  return (
    <div className="tp-container">
      {stage === STAGE.LOADING && (
        <div className="tp-loading">
          <span className="tp-spinner" />
          Looking up verified crosswalk...
        </div>
      )}

      {stage === STAGE.UNAVAILABLE && (
        <div className="tp-unavailable-block">
          <div className="tp-unavailable">
            No verified NAMASTE ↔ ICD-11 TM2 mapping exists for this code yet.
          </div>

          {candidates.length > 0 && (
            <div className="tp-candidates">
              <span className="tp-label">AI-ranked candidates (unverified, by semantic similarity)</span>
              {candidates.map((c, i) => (
                <div key={i} className="tp-candidate-item">
                  <div className="tp-candidate-bar-track">
                    <div
                      className="tp-candidate-bar-fill"
                      style={{ width: `${Math.round((c.similarity || 0) * 100)}%` }}
                    />
                  </div>
                  <span className="tp-candidate-text">
                    <strong>{c.code}</strong> {c.display}
                  </span>
                  <span className="tp-candidate-score">{Math.round((c.similarity || 0) * 100)}%</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {stage === STAGE.RESOLVED && resolved && (
        <div className="tp-resolved">
          <div className="tp-row">
            <span className="tp-badge">✓ Verified</span>
            <span className="tp-label">
              {resolved.direction === "namaste" ? "Resolves to ICD-11 TM2" : "Resolves to NAMASTE"}
            </span>
          </div>
          <div className="tp-code-line">
            <strong>{resolved.code}</strong> {resolved.display}
          </div>

          {biomedicine.length > 0 && (
            <div className="tp-biomed">
              <span className="tp-label">Related ICD-11 Biomedicine (via search)</span>
              {biomedicine.map((b) => (
                <div key={b.id} className="tp-biomed-item">
                  <strong>{b.code}</strong> {b.title}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default TranslatePanel;

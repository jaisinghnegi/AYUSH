import React, { useState, useEffect, useRef, useCallback } from "react";
import "./TranslateShowcase.css";
import { API_BASE } from "../../lib/authApi";
import { parseTranslateResponse, deriveKeyword } from "../../lib/translateHelpers";

const DEBOUNCE_MS = 300;
const SUGGESTION_LIMIT = 6;

const STAGE = {
  IDLE: "idle",
  RESOLVING: "resolving",
  TM2_REVEALED: "tm2_revealed",
  NO_MAPPING: "no_mapping",
  FULLY_RESOLVED: "fully_resolved",
};

const TranslateShowcase = () => {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedTerm, setSelectedTerm] = useState(null);
  const [stage, setStage] = useState(STAGE.IDLE);
  const [tm2, setTm2] = useState(null);
  const [biomedicine, setBiomedicine] = useState([]);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (selectedTerm || query.trim().length < 2) {
      setSuggestions([]);
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(
          `${API_BASE}/namaste/search?search=${encodeURIComponent(query)}&limit=${SUGGESTION_LIMIT}`
        );
        const data = await res.json();
        setSuggestions(data.results || []);
        setShowSuggestions(true);
      } catch (err) {
        console.error("NAMASTE suggestion search failed:", err);
      }
    }, DEBOUNCE_MS);

    return () => clearTimeout(debounceRef.current);
  }, [query, selectedTerm]);

  const resolveTerm = useCallback(async (term) => {
    setSelectedTerm(term);
    setShowSuggestions(false);
    setSuggestions([]);
    setStage(STAGE.RESOLVING);
    setTm2(null);
    setBiomedicine([]);

    try {
      const res = await fetch(
        `${API_BASE}/ConceptMap/$translate?code=${encodeURIComponent(term.sr_no)}&system=${encodeURIComponent(
          "http://namaste-codes.org"
        )}`
      );
      const data = await res.json();
      const parsed = parseTranslateResponse(data);

      if (!parsed.found) {
        setStage(STAGE.NO_MAPPING);
        return;
      }

      setTm2(parsed);
      setStage(STAGE.TM2_REVEALED);

      const keyword = deriveKeyword(parsed.display);
      if (keyword) {
        // Small pause so the TM2 reveal lands before the biomedicine panel
        // starts animating in -- this is the "watch it resolve" beat.
        await new Promise((r) => setTimeout(r, 550));
        const bioRes = await fetch(
          `${API_BASE}/icd/search?search=${encodeURIComponent(keyword)}&discipline=biomedicine&limit=50`
        );
        const bioData = await bioRes.json();
        // The search matches title/definition/code with no relevance
        // ranking, so a keyword that's merely mentioned in a long
        // definition can outrank an entry actually titled after it.
        // Prefer real title matches for the 3 we show -- still the same
        // real search results, just better ordered for what's most
        // illustrative of the match.
        const lowerKeyword = keyword.toLowerCase();
        const ranked = [...(bioData.results || [])].sort((a, b) => {
          const aTitle = (a.title || "").toLowerCase().includes(lowerKeyword) ? 0 : 1;
          const bTitle = (b.title || "").toLowerCase().includes(lowerKeyword) ? 0 : 1;
          return aTitle - bTitle;
        });
        setBiomedicine(ranked.slice(0, 3));
      }

      setStage(STAGE.FULLY_RESOLVED);
    } catch (err) {
      console.error("Translate showcase failed:", err);
      setStage(STAGE.NO_MAPPING);
    }
  }, []);

  const reset = () => {
    setQuery("");
    setSelectedTerm(null);
    setSuggestions([]);
    setShowSuggestions(false);
    setStage(STAGE.IDLE);
    setTm2(null);
    setBiomedicine([]);
  };

  return (
    <div className="ts-container">
      <div className="ts-header">
        <h2 className="ts-title">AyuSetu, live</h2>
        <p className="ts-subtitle">Type a NAMASTE term and watch it resolve to real ICD-11 codes.</p>
      </div>

      <div className="ts-search-wrapper">
        <input
          type="text"
          className="ts-input"
          placeholder="Try jvara, kasa, kamala, hikka..."
          value={selectedTerm ? selectedTerm.display : query}
          onChange={(e) => {
            const value = e.target.value;
            if (selectedTerm) {
              setSelectedTerm(null);
              setStage(STAGE.IDLE);
              setTm2(null);
              setBiomedicine([]);
            }
            setQuery(value);
          }}
          onFocus={() => suggestions.length > 0 && setShowSuggestions(true)}
        />
        {selectedTerm && (
          <button className="ts-reset-btn" onClick={reset} aria-label="Search another term">
            ✖
          </button>
        )}

        {showSuggestions && suggestions.length > 0 && (
          <ul className="ts-suggestions">
            {suggestions.map((s) => (
              <li key={s.sr_no} onClick={() => resolveTerm(s)}>
                <span className="ts-suggestion-term">{s.display}</span>
                <span className="ts-suggestion-display">{s.term}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {stage !== STAGE.IDLE && (
        <div className="ts-resolve-area">
          <div className={`ts-node ts-node-namaste ts-visible`}>
            <span className="ts-node-label">NAMASTE</span>
            <span className="ts-node-code">{selectedTerm?.display}</span>
            <span className="ts-node-display">{selectedTerm?.term}</span>
          </div>

          <div className={`ts-arrow ${stage !== STAGE.RESOLVING ? "ts-visible" : "ts-pulsing"}`}>→</div>

          {stage === STAGE.RESOLVING && (
            <div className="ts-node ts-node-pending ts-visible">
              <span className="ts-spinner" />
              <span className="ts-node-label">Resolving...</span>
            </div>
          )}

          {stage === STAGE.NO_MAPPING && (
            <div className="ts-node ts-node-unmapped ts-visible">
              <span className="ts-node-label">No verified TM2 mapping</span>
              <span className="ts-node-display">This term isn't in our verified crosswalk yet.</span>
            </div>
          )}

          {(stage === STAGE.TM2_REVEALED || stage === STAGE.FULLY_RESOLVED) && tm2 && (
            <div className="ts-node ts-node-tm2 ts-reveal">
              <span className="ts-badge ts-badge-verified">✓ Verified</span>
              <span className="ts-node-label">ICD-11 TM2</span>
              <span className="ts-node-code">{tm2.code}</span>
              <span className="ts-node-display">{tm2.display}</span>
            </div>
          )}

          {stage === STAGE.FULLY_RESOLVED && biomedicine.length > 0 && (
            <>
              <div className="ts-arrow ts-visible">→</div>
              <div className="ts-biomed-group ts-reveal-delayed">
                <span className="ts-badge ts-badge-related">Related, via search</span>
                <span className="ts-node-label">ICD-11 Biomedicine</span>
                {biomedicine.map((b) => (
                  <div key={b.id} className="ts-biomed-item">
                    <strong>{b.code}</strong> {b.title}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default TranslateShowcase;

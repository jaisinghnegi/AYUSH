import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Analytics.css";
import { API_BASE } from "../../lib/authApi";

const Analytics = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/analytics`)
      .then((res) => res.json())
      .then((json) => !cancelled && setData(json))
      .catch((err) => !cancelled && setError(err.message));
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="an-page">
      <div className="an-header">
        <button className="an-back" onClick={() => navigate(-1)}>&larr; Back</button>
        <h1>Analytics</h1>
        <p className="an-subtitle">
          Real-time morbidity analytics built from actual encounters saved through this app --
          not a mockup. It grows as doctors use the Composer to dual-code diagnoses.
        </p>
      </div>

      {error && <div className="an-error">Failed to load analytics: {error}</div>}
      {!data && !error && <div className="an-loading">Loading real usage data...</div>}

      {data && (
        <>
          <div className="an-stat-grid">
            <div className="an-stat-card">
              <span className="an-stat-number">{data.total_encounters}</span>
              <span className="an-stat-label">Encounters recorded</span>
            </div>
            <div className="an-stat-card">
              <span className="an-stat-number">{data.total_unique_patients}</span>
              <span className="an-stat-label">Unique patients</span>
            </div>
            <div className="an-stat-card">
              <span className="an-stat-number">{data.total_diagnoses_recorded}</span>
              <span className="an-stat-label">Diagnoses recorded</span>
            </div>
            <div className="an-stat-card">
              <span className="an-stat-number an-green">{data.verified_diagnoses}</span>
              <span className="an-stat-label">Verified mappings used</span>
            </div>
            <div className="an-stat-card">
              <span className="an-stat-number an-amber">{data.unverified_diagnoses}</span>
              <span className="an-stat-label">Unverified pairings used</span>
            </div>
          </div>

          {data.total_encounters === 0 ? (
            <div className="an-empty">
              No encounters saved yet. Log in, search for a term, add it to the Composer, and
              click "Generate FHIR Bundle" -- it'll show up here.
            </div>
          ) : (
            <>
              <div className="an-card">
                <h3>Most common dual-coded diagnoses</h3>
                <div className="an-list">
                  {data.most_common_diagnoses.map((d, i) => (
                    <div key={i} className="an-list-row">
                      <span className="an-list-rank">{i + 1}</span>
                      <span className="an-list-label">{d.display}{d.code ? ` (${d.code})` : ""}</span>
                      <span className="an-list-count">{d.count}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="an-card">
                <h3>Diagnoses by category</h3>
                <div className="an-breakdown">
                  {data.diagnoses_by_category.map((row) => {
                    const max = data.diagnoses_by_category[0]?.count || 1;
                    const pct = (row.count / max) * 100;
                    return (
                      <div key={row.category} className="an-breakdown-row">
                        <span className="an-breakdown-label">{row.category}</span>
                        <div className="an-breakdown-bar-track">
                          <div className="an-breakdown-bar-fill" style={{ width: `${pct}%` }} />
                        </div>
                        <span className="an-breakdown-count">{row.count}</span>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="an-card">
                <h3>Recent encounters</h3>
                <div className="an-list">
                  {data.recent_encounters.map((e) => (
                    <div key={e.id} className="an-list-row">
                      <span className="an-list-label">{e.patient_name}</span>
                      <span className="an-list-meta">{e.diagnosis_count} diagnos{e.diagnosis_count === 1 ? "is" : "es"}</span>
                      <span className="an-list-meta">{new Date(e.created_at).toLocaleString()}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="an-footer">{data.note}</div>
        </>
      )}
    </div>
  );
};

export default Analytics;

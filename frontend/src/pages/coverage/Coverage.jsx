import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import "./Coverage.css";
import { API_BASE } from "../../lib/authApi";

const Coverage = () => {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/coverage`)
      .then((res) => res.json())
      .then((json) => !cancelled && setData(json))
      .catch((err) => !cancelled && setError(err.message));
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="cov-page">
      <div className="cov-header">
        <button className="cov-back" onClick={() => navigate(-1)}>&larr; Back</button>
        <h1>Coverage</h1>
        <p className="cov-subtitle">
          We only claim a NAMASTE &harr; ICD-11 TM2 mapping is verified when it's directly
          traceable to both the NAMASTE codebook and live WHO ICD-11 data. Here's exactly how
          much of the dataset that covers, and how much doesn't &mdash; honestly.
        </p>
      </div>

      {error && <div className="cov-error">Failed to load coverage data: {error}</div>}

      {!data && !error && <div className="cov-loading">Loading real coverage stats...</div>}

      {data && (
        <>
          <div className="cov-card cov-headline">
            <div className="cov-bar">
              <div
                className="cov-bar-verified"
                style={{ width: `${data.namaste.verified_percentage}%` }}
                title={`${data.namaste.verified_percentage}% verified`}
              />
            </div>
            <div className="cov-headline-stats">
              <div>
                <span className="cov-stat-number cov-green">{data.namaste.verified_percentage}%</span>
                <span className="cov-stat-label">Verified &amp; cross-checked ({data.namaste.verified} codes)</span>
              </div>
              <div>
                <span className="cov-stat-number cov-amber">{data.namaste.unverified_percentage}%</span>
                <span className="cov-stat-label">Not yet mapped ({data.namaste.unverified} codes)</span>
              </div>
              <div>
                <span className="cov-stat-number">{data.namaste.total}</span>
                <span className="cov-stat-label">Total NAMASTE codes</span>
              </div>
            </div>
          </div>

          <div className="cov-card">
            <h3>WHO TM2 vocabulary reach</h3>
            <p>
              Of the <strong>{data.tm2.total_who_tm2_codes}</strong> real TM2 codes WHO publishes,
              our verified mappings actually use <strong>{data.tm2.distinct_codes_used_in_verified_mappings}</strong>
              {" "}distinct ones &mdash; <strong>{data.tm2.vocabulary_coverage_percentage}%</strong> of the TM2 vocabulary.
            </p>
          </div>

          <div className="cov-card">
            <h3>The 789 verified mappings, by category</h3>
            <p className="cov-note">Categories are WHO's own TM2 chapter groupings, not an invented taxonomy.</p>
            <div className="cov-breakdown">
              {data.breakdown_by_category.map((row) => {
                const pct = (row.count / data.namaste.verified) * 100;
                return (
                  <div key={row.category} className="cov-breakdown-row">
                    <span className="cov-breakdown-label">{row.category}</span>
                    <div className="cov-breakdown-bar-track">
                      <div className="cov-breakdown-bar-fill" style={{ width: `${pct}%` }} />
                    </div>
                    <span className="cov-breakdown-count">{row.count}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="cov-card cov-honesty">
            <h3>Why isn't everything mapped?</h3>
            <p>{data.unmapped_reason}</p>
            <h3>Discipline coverage</h3>
            <p>{data.discipline_note}</p>
          </div>

          <div className="cov-footer">
            Mapping version {data.mapping_version} &middot; last verified{" "}
            {new Date(data.mapping_verified_at).toLocaleString()}
          </div>
        </>
      )}
    </div>
  );
};

export default Coverage;

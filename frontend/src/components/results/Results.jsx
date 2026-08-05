import "./Results.css"
import { useState, useCallback } from "react";

const Results = ({item, handleAddToComposer}) => {
    //api should probably do this one
    let title, description, nam_code, icd_code;

    const hasNamCode = (item.nam_code != null);
    const hasIcdCode = (item.icd_code != null);

    if (hasNamCode && hasIcdCode) {
        // --- Both codes are present ---
        title = item.display || 'Untitled';
        description = item.long_definition || "No description available.";
        nam_code = item.nam_code;
        icd_code = item.icd_code;
    } else if (hasNamCode) {
        // --- Only NAMASTE code is present ---
        title = item.display || 'Untitled';
        description = item.long_definition || "No description available.";
        nam_code = item.nam_code;
        icd_code = "None";
    } else if (hasIcdCode) {
        // --- Only ICD code is present ---
        title = item.title || 'Untitled'; 
        description = item.definition || "No description available."; 
        nam_code = "None";
        icd_code = item.icd_code;
    } else {
        // --- Fallback state ---
        title = "Invalid Item";
        description = "No code information is available for this item.";
        nam_code = "N/A";
        icd_code = "N/A";
    }

    // add to clipboard thing
    const [copiedButton, setCopiedButton] = useState(null);

    const handleCopy = useCallback((textToCopy, buttonId) => {
        if (!textToCopy || textToCopy === "None" || textToCopy === "N/A") return;

        navigator.clipboard.writeText(textToCopy).then(() => {
            setCopiedButton(buttonId);
            setTimeout(() => {
                setCopiedButton(null);
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text: ', err);
        });
    }, []); 

    return(
    <>
        <div className="outer">
            <div className="tags">
                <div>
                    <span className="label">NAMASTE</span>
                    <div>
                    <p>{nam_code}</p>
                    </div>
                </div>

                <div>
                    <span className="label">ICD-11</span>
                    <div>
                    <p>{icd_code}</p>
                    </div>
                </div>
            </div>

            <div className="text">
                <h2>{title}</h2>
                <p>{description}</p>
            </div>

            <div className="buttons">
                <button
                    onClick={() => handleCopy(nam_code, 'namaste')}
                    disabled={!hasNamCode}
                >

                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    {copiedButton === 'namaste' ? 'Copied!' : 'Copy NAMASTE Code'}
                </button>
                <button
                    onClick={() => handleCopy(icd_code, 'icd')}
                    disabled={!hasIcdCode}
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                        <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                    </svg>
                    {copiedButton === 'icd' ? 'Copied!' : 'Copy ICD-11 TM-2 Code'}
                </button>
                <button id="add-button" onClick={() => handleAddToComposer(item)}>
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <line x1="12" y1="5" x2="12" y2="19"></line>
                        <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Add to Composer
                </button>
            </div>
        </div>
    </>
    );
};

export default Results;
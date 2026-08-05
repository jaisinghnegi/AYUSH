import React, { useState } from "react";
import { genXlsx } from "./genXlsx.js";
import { genPdf } from "./genPdf.js";
import "./Composer.css";

const Composer = ({ items, onRemove }) => {
  const [showDownloadOptions, setShowDownloadOptions] = useState(false);
  const [showPatientPopup, setShowPatientPopup] = useState(false);
  const [patientInfo, setPatientInfo] = useState({
    name: '',
    email: '',
    phone: ''
  });
  const [hasPatientInfo, setHasPatientInfo] = useState(false);

  // Handle patient info changes
  const handlePatientInfoChange = (field, value) => {
    setPatientInfo(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Save patient information and close popup
  const savePatientInfo = () => {
    const hasInfo = patientInfo.name || patientInfo.email || patientInfo.phone;
    setHasPatientInfo(hasInfo);
    setShowPatientPopup(false);
  };

  // Clear patient information
  const clearPatientInfo = () => {
    setPatientInfo({
      name: '',
      email: '',
      phone: ''
    });
    setHasPatientInfo(false);
  };

  // Helper function to generate FHIR Bundle
  const generateFHIRBundle = () => {
    return {
      resourceType: "Bundle",
      id: `bundle-${Date.now()}`,
      type: "collection",
      timestamp: new Date().toISOString(),
      total: items.length,
      patient: patientInfo.name || patientInfo.email || patientInfo.phone ? {
        name: patientInfo.name,
        email: patientInfo.email,
        phone: patientInfo.phone
      } : null,
      entry: items.map((item, index) => ({
        fullUrl: `urn:uuid:${item.id || index}`,
        resource: {
          resourceType: "CodeableConcept",
          id: item.id || `code-${index}`,
          coding: [
            ...(item.icd_code ? [{
              system: "http://hl7.org/fhir/sid/icd-10",
              code: item.icd_code,
              display: item.display || item.title
            }] : []),
            ...(item.nam_code ? [{
              system: "http://terminology.hl7.org/CodeSystem/v2-0203",
              code: item.nam_code,
              display: item.display || item.title
            }] : [])
          ],
          text: {
            status: "generated",
            div: `<div>${item.display || item.title}</div>`
          }
        }
      }))
    };
  };

  const handleDownload = (format) => {
    console.log(`Downloading as ${format}`);
    setShowDownloadOptions(false);
    
    try {
      const fhirBundle = generateFHIRBundle();
      
      switch (format) {
        case 'JSON':
          // Download as JSON
          const dataStr = JSON.stringify(fhirBundle, null, 2);
          const dataBlob = new Blob([dataStr], { type: 'application/json' });
          
          const url = URL.createObjectURL(dataBlob);
          const link = document.createElement('a');
          link.href = url;
          link.download = `fhir-bundle-${new Date().toISOString().split('T')[0]}.json`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          URL.revokeObjectURL(url);
          break;

        case 'PDF':
            genPdf(items, patientInfo).catch(err => {console.error("PDF generation failed:", err);});
          break;

        case 'Excel':
          genXlsx(items, patientInfo)
          break;

        default:
          alert('Unsupported format');
      }
    } catch (error) {
      console.error('Download failed:', error);
      alert('Download failed. Please try again.');
    }
  };

  const toggleDownloadOptions = () => {
    setShowDownloadOptions(!showDownloadOptions);
  };

  const togglePatientPopup = () => {
    setShowPatientPopup(!showPatientPopup);
  };

  return (
    <div className="composer-wrapper">
      <div className="composer-title">
        <div className="green-line"></div>
        <h2>Composer</h2>
      </div>
      
      {/* Patient Information Button and Display */}
      <div className="patient-info-section">
        <button 
          className="patient-info-btn"
          onClick={togglePatientPopup}
        >
          <svg className="patient-icon" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 12C14.2091 12 16 10.2091 16 8C16 5.79086 14.2091 4 12 4C9.79086 4 8 5.79086 8 8C8 10.2091 9.79086 12 12 12Z"/>
            <path d="M18 18C18 15.7909 16.2091 14 14 14H10C7.79086 14 6 15.7909 6 18V20H18V18Z"/>
          </svg>
          {hasPatientInfo ? 'Edit Patient Information' : 'Patient Information'}
        </button>

        {/* Display saved patient information */}
        {hasPatientInfo && (
          <div className="patient-info-display">
            <button className="clear-patient-info" onClick={clearPatientInfo}>
              &times;
            </button>
            <h4>Patient Information</h4>
            {patientInfo.name && <p><strong>Name:</strong> {patientInfo.name}</p>}
            {patientInfo.email && <p><strong>Email:</strong> {patientInfo.email}</p>}
            {patientInfo.phone && <p><strong>Phone:</strong> {patientInfo.phone}</p>}
          </div>
        )}
      </div>

      {/* Patient Information Popup */}
      {showPatientPopup && (
        <div className="patient-popup-overlay">
          <div className="patient-popup">
            <div className="popup-header">
              <h3>Patient Information</h3>
              <button className="close-popup" onClick={togglePatientPopup}>
                &times;
              </button>
            </div>
            <div className="popup-content">
              <div className="input-group">
                <label>Patient Name</label>
                <input
                  type="text"
                  placeholder="Enter patient name"
                  value={patientInfo.name}
                  onChange={(e) => handlePatientInfoChange('name', e.target.value)}
                />
              </div>
              <div className="input-group">
                <label>Email Address</label>
                <input
                  type="email"
                  placeholder="Enter email address"
                  value={patientInfo.email}
                  onChange={(e) => handlePatientInfoChange('email', e.target.value)}
                />
              </div>
              <div className="input-group">
                <label>Phone Number</label>
                <input
                  type="tel"
                  placeholder="Enter phone number"
                  value={patientInfo.phone}
                  onChange={(e) => handlePatientInfoChange('phone', e.target.value)}
                />
              </div>
              <button className="save-patient-btn" onClick={savePatientInfo}>
                Save Information
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="composer-container">
        <div className="composer-content">
          {/** Empty content **/}
          {items.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">
                <div className="hamburger-lines">
                  <div className="line"></div>
                  <div className="line"></div>
                  <div className="line"></div>
                </div>
                <div className="plus-icon">+</div>
              </div>
              <p className="empty-text">
                Your List is Empty. Select Codes From Search Results.
              </p>
            </div>
          ) : (
            /** actually has content **/
            <ul className="composer-list">
              {items.map(item => {
                const displayCode = [item.icd_code, item.nam_code].filter(Boolean).join(' / ');
                return (
                  <li key={item.id} className="composer-item">
                    <div className="item-details">
                      <span className="item-title">{item.display || item.title}</span>
                      <span className="item-code">
                        {displayCode || 'N/A'}
                      </span>
                    </div>
                    <button onClick={() => onRemove(item)} className="remove-btn">
                      &times;
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
      <div className="composer-footer">
        <button
          className="download-btn"
          onClick={toggleDownloadOptions}
          disabled={items.length === 0}
        >
          <svg className="download-icon" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z"/>
            <path d="M14 2V8H20"/>
          </svg>
          Generate FHIR Bundle
        </button>
        {showDownloadOptions && (
          <div className="download-dropdown">
            <button
              className="dropdown-item"
              onClick={() => handleDownload('JSON')}
            >
              JSON Format
            </button>
            <button
              className="dropdown-item"
              onClick={() => handleDownload('PDF')}
            >
              PDF Format
            </button>
            <button
              className="dropdown-item"
              onClick={() => handleDownload('Excel')}
            >
              Excel Format
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Composer;
import React, { useState, useRef, useEffect } from 'react';
import './searchbar.css';

const SearchBar = ({ onSubmit, onClear, results }) => {

  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [activeFilters, setActiveFilters] = useState({
    systems: [],
    organSystem: 'All',
    discipline: [],
    language: []
  });
  const [searchType, setSearchType] = useState('regex'); 

  const recognitionRef = useRef(null);

  useEffect(() => {
    // Check if browser supports speech recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setSearchQuery(transcript);
        setIsListening(false);
      };

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  const handleSearchChange = (e) => {
    setSearchQuery(e.target.value);
  };

  const handleClearAll = () => {
    setSearchQuery('');
    setSearchType('regex'); 
    setActiveFilters({
      systems: [],
      organSystem: 'All',
      discipline: [],
      language: []  
    });
    if (onClear) {
      onClear();
    }
  };

  const toggleFilter = (category, value) => {
    setActiveFilters(prev => {
      if (category === 'organSystem') {
        return { ...prev, [category]: value };
      }
      
      const currentValues = prev[category];
      if (currentValues.includes(value)) {
        return { 
          ...prev, 
          [category]: currentValues.filter(item => item !== value) 
        };
      } else {
        return { 
          ...prev, 
          [category]: [...currentValues, value] 
        };
      }
    });
  };

  const getFilterCount = () => {
    let count = 0;
    if (activeFilters.organSystem !== 'All') count++;
    count += activeFilters.systems.length;
    count += activeFilters.discipline.length;
    count += activeFilters.language.length;
    return count;
  };

  const handleSubmit = (e) => {
    e.preventDefault(); 
    
    const searchData = {
      query: searchQuery,
      filters: activeFilters,
      type: searchType  
    };
    
    if (onSubmit) {
      onSubmit(searchData);
    }
  };

  const startVoiceSearch = () => {
    if (!recognitionRef.current) {
      alert('Voice search is not supported in your browser');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      setIsListening(true);
      recognitionRef.current.start();
    }
  };

  const stopVoiceSearch = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    setIsListening(false);
  };

  return (
    <div className="global-search-container">
      <div style={{display: "flex", flexDirection: "row"}}>
        {/* this one class 'green-line' is in composer.css */}
        <div className="green-line"></div>
        <h2 className="search-title">Global Search</h2>
      </div>

      <form className="search-input-container" onSubmit={handleSubmit}>
        <div className="search-type-selector">
          <select 
            className="search-type-dropdown"
            value={searchType}
            onChange={(e) => setSearchType(e.target.value)}
            aria-label="Select search type"
          >
            <option value="regex ">Auto</option>
            <option value="regex">Direct</option>
            <option value="semantic">Semantic</option>
          </select>
        </div>

        <input
          type="text"
          className="search-input"
          placeholder="Search by code, title, or synonym..."
          value={searchQuery}
          onChange={handleSearchChange}
        />
        
        {/* Voice Search Button */}
        <button 
          type="button" 
          className={`voice-search-btn ${isListening ? 'listening' : ''}`}
          onClick={startVoiceSearch}
          aria-label="Voice Search"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
            <line x1="12" y1="19" x2="12" y2="22"></line>
            <line x1="8" y1="22" x2="16" y2="22"></line>
          </svg>
        </button>

        {/* Search Submit Button */}
        <button type="submit" className="search-submit-btn" aria-label="Search">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
        </button>
      </form>

      {/* Voice Search Overlay */}
      {isListening && (
        <div className="voice-search-overlay" onClick={stopVoiceSearch}>
          <div className="voice-search-modal" onClick={(e) => e.stopPropagation()}>
            <div className="voice-animation-container">
              <div className="voice-pulse-ring"></div>
              <div className="voice-pulse-ring delay-1"></div>
              <div className="voice-pulse-ring delay-2"></div>
              <div className="voice-microphone-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"></path>
                  <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                  <line x1="12" y1="19" x2="12" y2="22"></line>
                  <line x1="8" y1="22" x2="16" y2="22"></line>
                </svg>
              </div>
            </div>
            <h3 className="voice-search-title">Listening...</h3>
            <p className="voice-search-subtitle">Speak now to search</p>
            <button className="voice-cancel-btn" onClick={stopVoiceSearch}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="search-controls">
        <div className="filters-section">
          <button 
            className={`filters-btn ${showFilters ? 'active' : ''}`}
            onClick={() => setShowFilters(!showFilters)}
          >
            Filters
            {getFilterCount() > 0 && (
              <span className="filter-count">{getFilterCount()}</span>
            )}
          </button>
          
         
        <div className="results-count">{`Results: ${results ? results.length : 0}`}</div>


         

        </div>
        
        <button className="clear-all-btn" onClick={handleClearAll}>
          Clear all
        </button>
      </div>

      {showFilters && (
        <div className="filters-dropdown">
          <div className="filters-content">
            <div className="filter-category">
              <h4>Systems</h4>
              {['NAMASTE', 'ICD-11 TM2', 'ICD-11 Biomedicine'].map(system => (
                <div key={system} className="filter-option">
                  <input
                    type="checkbox"
                    id={`system-${system}`}
                    checked={activeFilters.systems.includes(system)}
                    onChange={() => toggleFilter('systems', system)}
                  />
                  <label htmlFor={`system-${system}`} className="filter-label">
                    {system}
                  </label>
                </div>
              ))}
            </div>

            <div className="filter-category">
              <h4>Organ System</h4>
              <select 
                value={activeFilters.organSystem}
                onChange={(e) => toggleFilter('organSystem', e.target.value)}
                className="organ-system-select"
              >
                <option value="All">All</option>
                {/* Add other organ system options here */}
              </select>
            </div>

            <div className="filter-category">
              <h4>Discipline</h4>
              {['Ayurveda', 'Siddha', 'Unani'].map(discipline => (
                <div key={discipline} className="filter-option">
                  <input
                    type="checkbox"
                    id={`discipline-${discipline}`}
                    checked={activeFilters.discipline.includes(discipline)}
                    onChange={() => toggleFilter('discipline', discipline)}
                  />
                  <label htmlFor={`discipline-${discipline}`} className="filter-label">
                    {discipline}
                  </label>
                </div>
              ))}
            </div>

            <div className="filter-category">
              <h4>Language</h4>
              {['English', 'Hindi'].map(language => (
                <div key={language} className="filter-option">
                  <input
                    type="checkbox"
                    id={`language-${language}`}
                    checked={activeFilters.language.includes(language)}
                    onChange={() => toggleFilter('language', language)}
                  />
                  <label htmlFor={`language-${language}`} className="filter-label">
                    {language}
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchBar;
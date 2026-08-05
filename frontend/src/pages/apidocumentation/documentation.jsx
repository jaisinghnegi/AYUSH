import React, { useState, useEffect, useRef } from 'react';
import { ArrowLeft, ChevronUp, Book, Shield, Globe, Code, Map, FileText, CheckCircle, ExternalLink } from 'lucide-react';
import './documentation.css';

const Documentation = () => {
  const [activeSection, setActiveSection] = useState('overview');
  const [showBackToTop, setShowBackToTop] = useState(false);
  const sectionRefs = useRef({});

  // Set up section refs
  const setSectionRef = (id, element) => {
    if (element) {
      sectionRefs.current[id] = element;
    }
  };

  function useScrollActiveNav() {
    useEffect(() => {
      const activeLink = document.querySelector(".nav-link.active");
      if (activeLink) {
        activeLink.scrollIntoView({
          behavior: "smooth",
          inline: "center",
          block: "nearest"
        });
      }
    }, [activeSection]);
  }

  useScrollActiveNav();

  useEffect(() => {
    const handleScroll = () => {
      const scrollPosition = window.scrollY + 100;
      
      // Show/hide back to top button
      setShowBackToTop(window.scrollY > 400);
      
      // Find the current section
      let currentSection = 'overview';
      Object.entries(sectionRefs.current).forEach(([id, element]) => {
        if (element && scrollPosition >= element.offsetTop) {
          currentSection = id;
        }
      });
      
      setActiveSection(currentSection);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (sectionId, smooth = true) => {
    const element = sectionRefs.current[sectionId];
    if (element) {
      window.scrollTo({
        top: element.offsetTop - 100,
        behavior: smooth ? 'smooth' : 'auto'
      });
    }
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavClick = (sectionId, e) => {
    e.preventDefault();
    scrollToSection(sectionId);
  };

  const handleBackClick = () => {
    window.history.back();
  };

  const sections = [
    { id: 'overview', title: 'Overview', icon: Book },
    { id: 'authentication', title: 'Authentication', icon: Shield },
    { id: 'endpoints', title: 'API Endpoints', icon: Globe },
    { id: 'codesystem', title: 'CodeSystem', icon: Code },
    { id: 'conceptmap', title: 'ConceptMap', icon: Map },
    { id: 'examples', title: 'Examples', icon: FileText },
    { id: 'compliance', title: 'Compliance', icon: CheckCircle }
  ];

  return (
    <div className="documentation-container">
      {/* Header */}
      <header className="doc-header">
        <div className="header-overlay"></div>
        <div className="header-content">
          <button 
            onClick={handleBackClick}
            className="back-button"
          >
            <ArrowLeft className="back-icon" />
            <span>Back</span>
          </button>
          <div className="header-text">
            <h1>AyuSetu API</h1>
            <p>Bridging traditional Indian medicine with global ICD-11 standards through FHIR-compliant APIs</p>
            <div className="badge-container">
              <span className="badge">FHIR R4 Compliant</span>
              <span className="badge">ICD-11 Compatible</span>
              <span className="badge">OAuth 2.0 Secured</span>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="doc-nav">
        <ul className="nav-list">
          {sections.map(({ id, title, icon: Icon }) => (
            <li key={id} className="nav-item">
              <a
                href={`#${id}`}
                className={`nav-link ${activeSection === id ? 'active' : ''}`}
                onClick={(e) => handleNavClick(id, e)}
              >
                <Icon className="nav-icon" />
                {title}
              </a>
            </li>
          ))}
        </ul>
      </nav>

      {/* Main Content */}
      <main className="doc-main">
        <Section id="overview" title="Overview" icon={Book} ref={ref => setSectionRef('overview', ref)}>
          <p className="section-description">
            AyuSetu API is a FHIR R4-compliant terminology micro-service that bridges India's NAMASTE codes with WHO ICD-11 
            standards (Traditional Medicine Module 2 and Biomedicine). This service enables dual-coding of Ayurveda, Siddha, 
            and Unani diagnoses for interoperability with global health systems.
          </p>
          
          <div className="feature-grid">
            <FeatureCard
              title="FHIR Compliance"
              description="Fully compliant with FHIR R4 standards and India's 2016 EHR requirements"
              icon={CheckCircle}
            />
            <FeatureCard
              title="Dual Coding"
              description="Seamless mapping between NAMASTE codes and ICD-11 TM2/Biomedicine codes"
              icon={Map}
            />
            <FeatureCard
              title="Secure Access"
              description="Enterprise-grade OAuth 2.0 authentication with ABHA token integration"
              icon={Shield}
            />
          </div>

          <div className="benefits-box">
            <h3>Key Benefits</h3>
            <div className="benefits-grid">
              <div className="benefit-item">
                <CheckCircle className="benefit-icon" />
                <span>4,500+ standardized terminology terms</span>
              </div>
              <div className="benefit-item">
                <CheckCircle className="benefit-icon" />
                <span>WHO compliant international standards</span>
              </div>
              <div className="benefit-item">
                <CheckCircle className="benefit-icon" />
                <span>Real-time code translation</span>
              </div>
              <div className="benefit-item">
                <CheckCircle className="benefit-icon" />
                <span>Comprehensive audit trails</span>
              </div>
            </div>
          </div>
        </Section>

        <Section id="authentication" title="Authentication" icon={Shield} ref={ref => setSectionRef('authentication', ref)}>
          <p className="section-description">
            All API endpoints require OAuth 2.0 authentication using ABHA (Ayushman Bharat Health Account) tokens. 
            Include your access token in the Authorization header of each request.
          </p>
          
          <CodeBlock language="http">
{`# Example Authorization Header
Authorization: Bearer <your_access_token>

# Getting an access token
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&client_id=YOUR_CLIENT_ID&client_secret=YOUR_CLIENT_SECRET`}
          </CodeBlock>

          <div className="security-note">
            <p>
              <strong>Security Note:</strong> Always store your client credentials securely and never expose them in client-side code.
            </p>
          </div>
        </Section>

        <Section id="endpoints" title="API Endpoints" icon={Globe} ref={ref => setSectionRef('endpoints', ref)}>
          <div className="endpoints-container">
            <Endpoint 
              method="GET" 
              title="ValueSet Lookup" 
              url="/ValueSet/$expand?url=urn:oid:namaste-codes&filter={search_term}"
              description="Search NAMASTE terms with intelligent auto-complete functionality. Returns matching concepts with their corresponding ICD-11 mappings."
            >
{`// Example Request
GET /ValueSet/$expand?url=urn:oid:namaste-codes&filter=fever

// Example Response
{
  "resourceType": "ValueSet",
  "expansion": {
    "contains": [{
      "system": "http://namaste-codes.org",
      "code": "NAMASTE-123",
      "display": "Jwara (Fever)",
      "designation": [{
        "value": "Fever"
      }]
    }]
  }
}`}
            </Endpoint>
            
            <Endpoint 
              method="POST" 
              title="Translate Operation" 
              url="/ConceptMap/$translate"
              description="Convert between NAMASTE and ICD-11 TM2 codes with confidence scoring."
            >
{`// Example Request
POST /ConceptMap/$translate
{
  "resourceType": "Parameters",
  "parameter": [{
    "name": "code",
    "valueCode": "NAMASTE-123"
  }, {
    "name": "system",
    "valueUri": "http://namaste-codes.org"
  }]
}

// Example Response
{
  "resourceType": "Parameters",
  "parameter": [{
    "name": "result",
    "valueBoolean": true
  }, {
    "name": "message",
    "valueString": "Concept translated"
  }, {
    "name": "match",
    "part": [{
      "name": "equivalence",
      "valueCode": "equivalent"
    }, {
      "name": "concept",
      "valueCoding": {
        "system": "http://who.int/icd-11/tm2",
        "code": "TM2-456",
        "display": "Disorder characterized by fever"
      }
    }]
  }]
}`}
            </Endpoint>
            
            <Endpoint 
              method="POST" 
              title="Encounter Upload" 
              url="/"
              description="Upload FHIR Bundle containing encounter data with dual-coded diagnoses for comprehensive health records."
            >
{`// Example Request
POST /
{
  "resourceType": "Bundle",
  "type": "transaction",
  "entry": [{
    "resource": {
      "resourceType": "Encounter",
      "status": "finished",
      "class": {
        "system": "http://terminology.hl7.org/CodeSystem/v3-ActCode",
        "code": "AMB",
        "display": "ambulatory"
      },
      "subject": {
        "reference": "Patient/123"
      },
      "reasonCode": [{
        "coding": [{
          "system": "http://namaste-codes.org",
          "code": "NAMASTE-123",
          "display": "Jwara (Fever)"
        }, {
          "system": "http://who.int/icd-11/tm2",
          "code": "TM2-456",
          "display": "Disorder characterized by fever"
        }]
      }]
    }
  }]
}`}
            </Endpoint>
          </div>
        </Section>

        <Section id="codesystem" title="NAMASTE CodeSystem" icon={Code} ref={ref => setSectionRef('codesystem', ref)}>
          <p className="section-description">
            The NAMASTE CodeSystem contains over 4,500 standardized terms for Ayurveda, Siddha and Unani disorders, 
            meticulously aligned with WHO Standardised International Terminologies for Ayurveda.
          </p>
          
          <CodeBlock language="json">
{`{
  "resourceType": "CodeSystem",
  "url": "http://namaste-codes.org",
  "version": "2.1",
  "name": "NAMASTECodeSystem",
  "title": "National AYUSH Morbidity & Standardized Terminologies Electronic",
  "status": "active",
  "content": "complete",
  "concept": [{
    "code": "NAMASTE-123",
    "display": "Jwara (Fever)",
    "definition": "A disorder characterized by elevated body temperature...",
    "designation": [{
      "use": {
        "system": "http://who.int/icd-11/tm2",
        "code": "TM2-456"
      },
      "value": "Disorder characterized by fever"
    }]
  }]
}`}
          </CodeBlock>
        </Section>

        <Section id="conceptmap" title="ConceptMap for Mappings" icon={Map} ref={ref => setSectionRef('conceptmap', ref)}>
          <p className="section-description">
            The ConceptMap resource defines precise mappings between NAMASTE codes and ICD-11 TM2/Biomedicine codes,
            ensuring semantic interoperability across healthcare systems.
          </p>
          
          <CodeBlock language="json">
{`{
  "resourceType": "ConceptMap",
  "url": "http://ayu-setu.org/ConceptMap/namaste-to-icd11",
  "version": "1.0",
  "name": "NAMASTEToICD11",
  "title": "NAMASTE to ICD-11 Mapping",
  "status": "active",
  "sourceScope": {
    "uri": "http://namaste-codes.org"
  },
  "targetScope": {
    "uri": "http://who.int/icd-11/tm2"
  },
  "group": [{
    "source": "http://namaste-codes.org",
    "target": "http://who.int/icd-11/tm2",
    "element": [{
      "code": "NAMASTE-123",
      "target": [{
        "code": "TM2-456",
        "equivalence": "equivalent"
      }]
    }]
  }]
}`}
          </CodeBlock>
        </Section>

        <Section id="examples" title="Integration Examples" icon={FileText} ref={ref => setSectionRef('examples', ref)}>
          <div className="examples-container">
            <div className="example-section">
              <h3>
                <Code className="example-icon" />
                Web Application (JavaScript)
              </h3>
              <CodeBlock language="javascript">
{`// Search for NAMASTE terms with debounced input
async function searchNamasteTerms(searchTerm) {
  try {
    const response = await fetch(
      \`/ValueSet/$expand?url=urn:oid:namaste-codes&filter=\${encodeURIComponent(searchTerm)}\`,
      {
        headers: {
          'Authorization': 'Bearer ' + accessToken,
          'Content-Type': 'application/json',
          'Accept': 'application/fhir+json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(\`HTTP error! status: \${response.status}\`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Search failed:', error);
    throw error;
  }
}

// Translate NAMASTE to ICD-11 TM2 with error handling
async function translateCode(code, system) {
  try {
    const response = await fetch('/ConceptMap/$translate', {
      method: 'POST',
      headers: {
        'Authorization': 'Bearer ' + accessToken,
        'Content-Type': 'application/fhir+json',
        'Accept': 'application/fhir+json'
      },
      body: JSON.stringify({
        resourceType: 'Parameters',
        parameter: [{
          name: 'code',
          valueCode: code
        }, {
          name: 'system',
          valueUri: system
        }]
      })
    });
    
    if (!response.ok) {
      throw new Error(\`Translation failed: \${response.status}\`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('Translation error:', error);
    throw error;
  }
}`}
              </CodeBlock>
            </div>

            <div className="best-practices">
              <h4>Integration Best Practices</h4>
              <ul>
                <li>
                  <CheckCircle className="practice-icon" />
                  <span>Implement proper error handling and retry logic</span>
                </li>
                <li>
                  <CheckCircle className="practice-icon" />
                  <span>Use debouncing for search inputs to reduce API calls</span>
                </li>
                <li>
                  <CheckCircle className="practice-icon" />
                  <span>Cache frequently accessed terminology mappings</span>
                </li>
                <li>
                  <CheckCircle className="practice-icon" />
                  <span>Validate FHIR resources before submission</span>
                </li>
              </ul>
            </div>
          </div>
        </Section>

        <Section id="compliance" title="Compliance Standards" icon={CheckCircle} ref={ref => setSectionRef('compliance', ref)}>
          <p className="section-description">
            AyuSetu API is meticulously designed to comply with India's 2016 EHR Standards and international 
            healthcare interoperability standards, ensuring seamless integration with existing healthcare ecosystems.
          </p>
          
          <div className="compliance-grid">
            <div className="compliance-card">
              <h3>Technical Standards</h3>
              <ul>
                <ComplianceItem text="FHIR R4 API compliant" />
                <ComplianceItem text="SNOMED CT and LOINC semantics" />
                <ComplianceItem text="ISO 22600 access control standards" />
                <ComplianceItem text="ICD-11 Coding Rules compliance" />
              </ul>
            </div>
            
            <div className="compliance-card">
              <h3>Security & Governance</h3>
              <ul>
                <ComplianceItem text="ABHA-linked OAuth 2.0 authentication" />
                <ComplianceItem text="Comprehensive audit trails" />
                <ComplianceItem text="Consent management integration" />
                <ComplianceItem text="Data versioning and lineage" />
              </ul>
            </div>
          </div>

          <div className="regulatory-box">
            <h3>Regulatory Compliance</h3>
            <p>
              AyuSetu API adheres to strict regulatory requirements for healthcare data interoperability and privacy.
            </p>
            <div className="compliance-badges">
              <span className="compliance-badge">India EHR 2016</span>
              <span className="compliance-badge">FHIR R4</span>
              <span className="compliance-badge">WHO ICD-11</span>
              <span className="compliance-badge">ABHA Compatible</span>
            </div>
          </div>
        </Section>
      </main>

      {/* Back to Top Button */}
      {showBackToTop && (
        <button
          onClick={scrollToTop}
          className="back-to-top"
          aria-label="Back to top"
        >
          <ChevronUp className="top-icon" />
        </button>
      )}

      {/* Footer */}
      <footer className="doc-footer">
        <div className="footer-content">
          <h3>AyuSetu API</h3>
          <p>
            Empowering healthcare interoperability through traditional medicine terminology standards.
          </p>
          <div className="footer-links">
            <a href="mailto:support@ayusetu.org" className="footer-link">
              <ExternalLink className="link-icon" />
              support@ayusetu.org
            </a>
          </div>
          <div className="footer-bottom">
            <p>
              © 2025 AyuSetu API. All rights reserved. | Built for healthcare interoperability
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
};

// Sub-components
const Section = React.forwardRef(({ id, title, icon: Icon, children }, ref) => (
  <section id={id} className="doc-section" ref={ref}>
    <div className="section-header">
      <div className="section-icon-container">
        <Icon className="section-icon" />
      </div>
      <h2 className="section-title">{title}</h2>
    </div>
    <div className="section-content">{children}</div>
  </section>
));

const FeatureCard = ({ title, description, icon: Icon }) => {
  return (
    <div className="feature-card">
      <div className="feature-icon-container">
        <Icon className="feature-icon" />
      </div>
      <h3 className="feature-title">{title}</h3>
      <p className="feature-description">{description}</p>
    </div>
  );
};

const CodeBlock = ({ children, language = 'javascript' }) => (
  <div className="code-block">
    <div className="code-language">{language}</div>
    <div className="code-content">
      <pre>
        <code>{children}</code>
      </pre>
    </div>
  </div>
);

const Endpoint = ({ method, title, url, description, children }) => {
  return (
    <div className="endpoint-card">
      <div className="endpoint-header">
        <div className="endpoint-info">
          <h3 className="endpoint-title">{title}</h3>
          <p className="endpoint-description">{description}</p>
        </div>
        <span className={`method-tag method-${method.toLowerCase()}`}>
          {method}
        </span>
      </div>
      
      <div className="endpoint-url">
        {url}
      </div>
      
      <CodeBlock language="json">
        {children}
      </CodeBlock>
    </div>
  );
};

const ComplianceItem = ({ text }) => (
  <li className="compliance-item">
    <CheckCircle className="compliance-check" />
    <span>{text}</span>
  </li>
);

export default Documentation;
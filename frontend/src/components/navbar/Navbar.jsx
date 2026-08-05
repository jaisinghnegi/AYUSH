import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import "./Navbar.css";

const Navbar = ({ isDarkMode, onToggleTheme }) => {
    const navigate = useNavigate();
    const location = useLocation();
    const [isLoggingOut, setIsLoggingOut] = useState(false);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [isScrolled, setIsScrolled] = useState(false);

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 10);
        };
        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    const handleLogout = async () => {
        setIsLoggingOut(true);
        
        // Add a small delay for better UX and animation visibility
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Clear any session data
        localStorage.clear();
        sessionStorage.clear();
        
        // Add fade out effect to body
        document.body.classList.add('logout-fade');
        
        // Navigate to home page after fade effect
        setTimeout(() => {
            navigate('/');
            setIsLoggingOut(false);
            document.body.classList.remove('logout-fade');
        }, 500);
    };

    const isActive = (path) => {
        return location.pathname === path ? 'active' : '';
    };

    const toggleMenu = () => {
        setIsMenuOpen(!isMenuOpen);
    };

    return(
        <>
            <div className={`navbar-spacer ${isScrolled ? 'scrolled' : ''}`}></div>
            <nav className={`${isScrolled ? 'scrolled' : ''}`}>
                <div className="left">
                    <img src="/assets/Logo.png" alt="Our logo" width={50} height={50}/>
                    <div className="left-text"> 
                        <h2>AyuSetu</h2>
                        <p>NAMASTE & ICD-11 Dual Coding Interface</p>
                    </div>
                </div>
                
                <div className="right">
                    <div className={`nav-links ${isMenuOpen ? 'nav-open' : ''}`}>
                        <a 
                            className={`nav-link ${isActive('/docs')}`}
                            href="/docs"
                            onClick={(e) => {
                                e.preventDefault();
                                navigate('/docs');
                                setIsMenuOpen(false);
                            }}
                        >
                            API Documentation
                        </a>
                        
                        <button 
                            className={`logout-btn ${isLoggingOut ? 'logging-out' : ''}`} 
                            onClick={handleLogout}
                            disabled={isLoggingOut}
                        >
                            {isLoggingOut ? (
                                <>
                                    <div className="logout-spinner"></div>
                                    <span>Logging out...</span>
                                </>
                            ) : (
                                'Logout'
                            )}
                        </button>
                        
                        <label className="theme-switch" htmlFor="theme-toggle-checkbox">
                            <input
                                type="checkbox"
                                id="theme-toggle-checkbox"
                                checked={isDarkMode}
                                onChange={onToggleTheme}
                            />
                            <div className="slider">
                                <div className="switch-text">
                                    {isDarkMode ? 'DARK MODE' : 'LIGHT MODE'}
                                </div>
                            </div>
                        </label>
                    </div>
                    
                    <div className="logo-group">
                        <img id="ayush" src="/assets/MoA_logo.png" alt="Ministry of Ayush logo" width={50} height={50} />
                        <img id="who" src="/assets/WHO_logo.png" alt="WHO logo" width={50} height={50} />
                    </div>
                    
                    <button 
                        className={`hamburger ${isMenuOpen ? 'hamburger-open' : ''}`}
                        onClick={toggleMenu}
                        aria-label="Toggle menu"
                    >
                        <span></span>
                        <span></span>
                        <span></span>
                    </button>
                </div>
            </nav>
            
            {/* Overlay when menu is open on mobile */}
            {isMenuOpen && (
                <div 
                    className="menu-overlay"
                    onClick={() => setIsMenuOpen(false)}
                ></div>
            )}
        </>
    );
};

export default Navbar;
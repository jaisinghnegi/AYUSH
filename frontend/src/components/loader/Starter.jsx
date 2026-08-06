import React, { useEffect, useState } from 'react';
import './Starter.css';

const Starter = () => {
  const [isAnimating, setIsAnimating] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    startLoadingAnimation();
  }, []);

  const startLoadingAnimation = () => {
    setIsAnimating(false);
    setIsComplete(false);
    
    setTimeout(() => {
      setIsAnimating(true);
    }, 100);
    
    setTimeout(() => {
      completeLoading();
    }, 2500);
  };

  const completeLoading = () => {
    setIsComplete(true);
  };

  const restartLoading = () => {
    startLoadingAnimation();
  };

  const skipToSite = () => {
    completeLoading();
  };

  return (
    <>
      {!isComplete && (
        <div className={`loading-overlay ${isAnimating ? 'animate-out' : ''}`}>
          <div className="rectangle side-rect"></div>
          <div className="rectangle main-rect"></div>
          <div className="rectangle main-rect"></div>
          <div className="rectangle main-rect"></div>
          <div className="rectangle main-rect"></div>
          <div className="rectangle side-rect"></div>
          
          <div className="logo-space">
              <img src="/assets/mainlogo.png" alt="main_logo" />
          </div>  
        </div>
      )}



      <div className={`website-content ${isComplete ? 'show' : ''}`}>
        <div className="content-box">
        </div>
      </div>
    </>
  );
};

export default Starter;
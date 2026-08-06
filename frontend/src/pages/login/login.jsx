import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './login.css';
import { loginWithPassword, requestOtp, verifyOtp, saveSession } from '../../lib/authApi';

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [otpMode, setOtpMode] = useState(false);
  const [otpSent, setOtpSent] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);

    try {
      const { token, user } = await loginWithPassword({ email, password });
      saveSession({ token, user });
      navigate('/home');
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleOTPLogin = async () => {
    if (!otpMode) {
      setOtpMode(true);
      return;
    }

    if (!email.trim()) {
      alert('Enter your email first');
      return;
    }

    if (submitting) return;
    setSubmitting(true);

    try {
      const { delivered } = await requestOtp({ email, purpose: 'login' });
      setOtpSent(true);
      alert(delivered ? 'Code sent to your email' : 'Code generated (check server logs -- email delivery is not configured yet)');
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setSubmitting(true);

    try {
      const { token, user } = await verifyOtp({ email, code: otpCode, purpose: 'login' });
      saveSession({ token, user });
      navigate('/home');
    } catch (err) {
      alert(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleForgotPassword = () => {
    alert('Forgot password requested');
  };

  const handleSignUp = () => {
    navigate('/register');
  };

  return (
    <div className="login-container">
      <div className="login-content">
        <div className="login-form-section">
          <div className="form-container">
            <div className="logo-section">
              <div className="logo">
                <div className="logo-image"></div>
              </div>
            </div>

            <div className="welcome-section">
              <h1 className="welcome-title">Welcome back</h1>
              <p className="welcome-subtitle">Enter your details to continue</p>
            </div>

            <form className="login-form" onSubmit={otpMode && otpSent ? handleVerifyOtp : handleSubmit}>
              <div className="form-group">
                <label htmlFor="email" className="form-label">Email</label>
                <input
                  type="email"
                  id="email"
                  className="form-input"
                  placeholder="Your email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={otpMode && otpSent}
                  required
                />
              </div>

              {!otpMode && (
                <div className="form-group">
                  <label htmlFor="password" className="form-label">Password</label>
                  <div className="password-input-container">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      id="password"
                      className="form-input"
                      placeholder="Enter password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                    />
                    <button
                      type="button"
                      className="password-toggle"
                      onClick={() => setShowPassword(!showPassword)}
                    >
                      <svg
                        width="18"
                        height="18"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                      >
                        {showPassword ? (
                          <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
                        ) : (
                          <>
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </>
                        )}
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {otpMode && otpSent && (
                <div className="form-group">
                  <label htmlFor="otp" className="form-label">Verification code</label>
                  <input
                    type="text"
                    id="otp"
                    className="form-input"
                    placeholder="6-digit code"
                    value={otpCode}
                    onChange={(e) => setOtpCode(e.target.value)}
                    maxLength={6}
                    required
                  />
                </div>
              )}

              {!otpMode && (
                <div className="forgot-password-section">
                  <button
                    type="button"
                    className="forgot-password-link"
                    onClick={handleForgotPassword}
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              {(!otpMode || (otpMode && otpSent)) && (
                <button type="submit" className="login-button" disabled={submitting}>
                  {otpMode ? 'Verify code' : 'Log in'}
                </button>
              )}

              {!otpSent && (
                <button
                  type="button"
                  className="otp-button"
                  onClick={handleOTPLogin}
                  disabled={submitting}
                >
                  {otpMode ? 'Send code' : 'Login with OTP'}
                </button>
              )}

              {otpMode && (
                <button
                  type="button"
                  className="otp-button"
                  onClick={() => { setOtpMode(false); setOtpSent(false); setOtpCode(''); }}
                >
                  Use password instead
                </button>
              )}
            </form>

            <div className="signup-section">
              <span className="signup-text">Don't have an account? </span>
              <button className="signup-link" onClick={handleSignUp}>
                Sign up
              </button>
            </div>
          </div>

          <div className="log-footer">
            <p>© 2025 ALL RIGHTS RESERVED</p>
          </div>
        </div>

        <div className="hero-section">
          <div className="hero-background">
            <img
              src="/assets/logindekstopbackground.png"
              alt="Desktop Hero"
              className="hero-image-desktop"
            />
            <img
              src="/assets/loginmobilebackground.png"
              alt="Mobile Hero"
              className="hero-image-mobile"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;

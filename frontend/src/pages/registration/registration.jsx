import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Phone, User, Mail, MessageSquare, CheckCircle, Loader } from 'lucide-react';


const RegistrationPage = () => {
  const [formData, setFormData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    nickname: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const navigate = useNavigate();

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validateForm = () => {
    const newErrors = {};
    
    if (!formData.firstName.trim()) {
      newErrors.firstName = 'First name is required';
    } else if (formData.firstName.trim().length < 4) {
      newErrors.firstName = 'First name must be at least 4 characters';
    }
    
    if (!formData.lastName.trim()) {
      newErrors.lastName = 'Last name is required';
    } else if (formData.lastName.trim().length < 4) {
      newErrors.lastName = 'Last name must be at least 4 characters';
    }
    
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(formData.email)) {
      newErrors.email = 'Valid email address is required';
    }
    
    if (!formData.phone.trim()) {
      newErrors.phone = 'Phone number is required';
    }
    
    if (!formData.nickname.trim()) {
      newErrors.nickname = 'Nickname is required';
    } else if (formData.nickname.trim().length < 4) {
      newErrors.nickname = 'Nickname must be at least 4 characters';
    }


    if (!formData.password.trim()) {
      newErrors.password = 'Password is required';
    } else if (formData.password.trim().length < 8) {
      newErrors.password = 'password must be at least 8 characters';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async () => {
  if (validateForm()) {
    setIsSubmitting(true);

    try {
      // Simulate waiting for submission, e.g., API call
      await new Promise(resolve => setTimeout(resolve, 1000));

      // Retrieve existing users from localStorage
      const existingUsers = JSON.parse(localStorage.getItem('users')) || [];

      // Check if email already registered
      const emailExists = existingUsers.some(user => user.email === formData.email);
      if (emailExists) {
        alert('Email already registered!');
        setIsSubmitting(false);
        return;
      }


      // Create new user object
      const newUser = {
        firstName: formData.firstName,
        lastName: formData.lastName,
        email: formData.email,
        phone: formData.phone,
        nickname: formData.nickname,
        password: formData.password // For simplicity, set OTP as password
      };

      // Save new user to localStorage
      existingUsers.push(newUser);
      localStorage.setItem('users', JSON.stringify(existingUsers));

      console.log('Registration completed:', newUser);

      setIsSubmitting(false);
      setShowSuccess(true);

      // Redirect after 3 seconds
      setTimeout(() => {
        navigate('/');
      }, 3000);

    } catch (error) {
      setIsSubmitting(false);
      console.error('Registration failed:', error);
    }
  }
};


  if (showSuccess) {
    return (
      <div style={styles.successOverlay}>
        <div style={styles.successContent}>
          <div style={styles.successIcon}>
            <CheckCircle size={80} color={'#57D24B'} />
          </div>
          <h2 style={styles.successTitle}>Registration Successful!</h2>
          <p style={styles.successMessage}>
            Welcome to AyuSetu! Your account has been created successfully.
            <br />
            Redirecting to login page...
          </p>
          <div style={styles.loadingBar}>
            <div style={styles.loadingProgress}></div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.logo}>
          <img src="/assets/mainlogo.png" alt="Logo" style={styles.logoImg} />
        </div>
      </div>

      {/* Full screen form area */}
      <div style={styles.formWrapper}>
        <div style={styles.formContainer}>
          <div style={styles.formGrid}>
            <div style={styles.inputGroup}>
              <label style={styles.label}>
                First Name <span style={styles.required}>*</span>
              </label>
              <p style={styles.labelSubtext}>Minimum 4 characters</p>
              <div style={styles.inputWrapper}>
                <User size={20} style={styles.inputIcon} />
                <input
                  type="text"
                  name="firstName"
                  value={formData.firstName}
                  onChange={handleInputChange}
                  style={{
                    ...styles.input,
                    ...(errors.firstName ? styles.inputError : {}),
                    ...(formData.firstName && !errors.firstName ? styles.inputFilled : {})
                  }}
                  placeholder="Enter your first name"
                />
              </div>
              {errors.firstName && <span style={styles.errorText}>{errors.firstName}</span>}
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>
                Last Name <span style={styles.required}>*</span>
              </label>
              <p style={styles.labelSubtext}>Minimum 4 characters</p>
              <div style={styles.inputWrapper}>
                <User size={20} style={styles.inputIcon} />
                <input
                  type="text"
                  name="lastName"
                  value={formData.lastName}
                  onChange={handleInputChange}
                  style={{
                    ...styles.input,
                    ...(errors.lastName ? styles.inputError : {}),
                    ...(formData.lastName && !errors.lastName ? styles.inputFilled : {})
                  }}
                  placeholder="Enter your last name"
                />
              </div>
              {errors.lastName && <span style={styles.errorText}>{errors.lastName}</span>}
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>
                Email Address <span style={styles.required}>*</span>
              </label>
              <p style={styles.labelSubtext}>Use your professional email</p>
              <div style={styles.inputWrapper}>
                <Mail size={20} style={styles.inputIcon} />
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleInputChange}
                  style={{
                    ...styles.input,
                    ...(errors.email ? styles.inputError : {}),
                    ...(formData.email && !errors.email ? styles.inputFilled : {})
                  }}
                  placeholder="Enter your email address"
                />
              </div>
              {errors.email && <span style={styles.errorText}>{errors.email}</span>}
            </div>

            <div style={{...styles.inputGroup, gridColumn: 'span 2'}}>
              <label style={styles.label}>
                Phone Number <span style={styles.required}>*</span>
              </label>
              <p style={styles.labelSubtext}>Include country code (e.g., +91 for India)</p>
              <div style={styles.inputWrapper}>
                <Phone size={20} style={styles.inputIcon} />
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleInputChange}
                  style={{
                    ...styles.input,
                    ...(errors.phone ? styles.inputError : {}),
                    ...(formData.phone && !errors.phone ? styles.inputFilled : {})
                  }}
                  placeholder="Enter your phone number"
                />
              </div>
              {errors.phone && <span style={styles.errorText}>{errors.phone}</span>}
            </div>

            <div style={styles.inputGroup}>
              <label style={styles.label}>
                Nickname <span style={styles.required}>*</span>
              </label>
              <p style={styles.labelSubtext}>Display name (min 4 characters)</p>
              <div style={styles.inputWrapper}>
                <MessageSquare size={20} style={styles.inputIcon} />
                <input
                  type="text"
                  name="nickname"
                  value={formData.nickname}
                  onChange={handleInputChange}
                  style={{
                    ...styles.input,
                    ...(errors.nickname ? styles.inputError : {}),
                    ...(formData.nickname && !errors.nickname ? styles.inputFilled : {})
                  }}
                  placeholder="Choose your nickname"
                />
              </div>
              {errors.nickname && <span style={styles.errorText}>{errors.nickname}</span>}
            </div>
              
                          <div style={styles.inputGroup}>
              <label style={styles.label}>
                password <span style={styles.required}>*</span>
              </label>
              <p style={styles.labelSubtext}>Display name (min 8 characters)</p>
              <div style={styles.inputWrapper}>
                <MessageSquare size={20} style={styles.inputIcon} />
                <input
                  type="text"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  style={{
                    ...styles.input,
                    ...(errors.password ? styles.inputError : {}),
                    ...(formData.password && !errors.password ? styles.inputFilled : {})
                  }}
                  placeholder="Set your password"
                />
              </div>
              {errors.password && <span style={styles.errorText}>{errors.password}</span>}
            </div>
          </div>
        </div>
      </div>
      
      
      {/* Footer */}
      <div style={styles.footer}>
        <button style={styles.helpButton}>
          <Phone size={16} />
          Need Help?
        </button>
        
        <button 
          onClick={handleSubmit} 
          disabled={isSubmitting}
          style={{
            ...styles.submitButton,
            ...(isSubmitting ? styles.submitButtonDisabled : {})
          }}
        >
          {isSubmitting ? (
            <>
              <Loader size={18} style={styles.spinner} />
              Processing...
            </>
          ) : (
            <>
              Complete Registration
              <CheckCircle size={18} />
            </>
          )}
        </button>
      </div>
    </div>
  );
};

const styles = {
  container: {
    height: '100vh',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    background: 'linear-gradient(135deg, #57D24B 0%, #4bc441 100%)',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    overflow: 'hidden'
  },
  header: {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    color: '#ffffff',
    padding: '20px 40px',
    display: 'flex',
    justifyContent: 'flex-start',
    alignItems: 'center',
    borderBottom: '1px solid rgba(255, 255, 255, 0.2)'
  },
  logo: {
    display: 'flex',
    alignItems: 'center'
  },
  logoImg: {
    height: '40px',
    width: 'auto',
    objectFit: 'contain'
  },
  formWrapper: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '0',
    width: '100%'
  },
  formContainer: {
    background: '#ffffff',
    borderRadius: '0',
    padding: '40px',
    width: '100%',
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
    boxShadow: 'none'
  },
  formGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
    gap: '50px'
  },
  inputGroup: {
    display: 'flex',
    flexDirection: 'column'
  },
  label: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#1a1a1a',
    marginBottom: '4px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  required: {
    color: '#57D24B'
  },
  labelSubtext: {
    fontSize: '12px',
    color: '#64748b',
    marginBottom: '8px',
    margin: '0 0 8px 0'
  },
  inputWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center'
  },
  input: {
    width: '100%',
    padding: '12px 16px 12px 44px',
    border: '2px solid #e2e8f0',
    borderRadius: '10px',
    fontSize: '16px',
    color: '#1a1a1a',
    background: '#ffffff',
    transition: 'all 0.3s ease',
    outline: 'none',
    boxSizing: 'border-box'
  },
  inputFilled: {
    borderColor: '#57D24B',
    background: '#f0fdf4'
  },
  inputError: {
    borderColor: '#ef4444',
    background: '#fef2f2'
  },
  inputIcon: {
    position: 'absolute',
    left: '14px',
    color: '#9ca3af',
    zIndex: 1,
    pointerEvents: 'none'
  },
  errorText: {
    color: '#ef4444',
    fontSize: '12px',
    marginTop: '4px'
  },
  footer: {
    padding: '20px 40px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderTop: '1px solid rgba(255, 255, 255, 0.2)'
  },
  helpButton: {
    padding: '12px 20px',
    background: 'rgba(255, 255, 255, 0.2)',
    border: 'none',
    borderRadius: '8px',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease'
  },
  submitButton: {
    padding: '14px 32px',
    background: '#ffffff',
    border: 'none',
    borderRadius: '10px',
    color: '#57D24B',
    fontSize: '16px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    transition: 'all 0.3s ease',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
  },
  submitButtonDisabled: {
    background: '#9ca3af',
    color: '#ffffff',
    cursor: 'not-allowed'
  },
  spinner: {
    animation: 'spin 1s linear infinite'
  },
  successOverlay: {
    position: 'fixed',
    top: '0',
    left: '0',
    width: '100%',
    height: '100%',
    background: 'rgb(255, 255, 255)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000
  },
  successContent: {
    background: '#ffffff',
    borderRadius: '20px',
    padding: '48px',
    textAlign: 'center',
    maxWidth: '400px',
    width: '90%',
    boxShadow: '0 20px 40px rgba(255, 255, 255, 0.3)'
  },
  successIcon: {
    marginBottom: '24px'
  },
  successTitle: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#1a1a1a',
    marginBottom: '16px',
    margin: '0 0 16px 0'
  },
  successMessage: {
    fontSize: '16px',
    color: '#64748b',
    lineHeight: '1.6',
    marginBottom: '32px',
    margin: '0 0 32px 0'
  },
  loadingBar: {
    width: '100%',
    height: '4px',
    background: '#e2e8f0',
    borderRadius: '2px',
    overflow: 'hidden'
  },
  loadingProgress: {
    width: '100%',
    height: '100%',
    background: 'linear-gradient(135deg, #57D24B 0%, #4bc441 100%)',
    borderRadius: '2px',
    animation: 'loadingProgress 3s ease-out forwards',
    transform: 'translateX(-100%)'
  }
};

// Add keyframes
const styleSheet = document.createElement("style");
styleSheet.innerText = `
  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  
  @keyframes loadingProgress {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(0%); }
  }
  
  @media (max-width: 768px) {
    .form-grid {
      grid-template-columns: 1fr !important;
    }
  }
`;
document.head.appendChild(styleSheet);

export default RegistrationPage;
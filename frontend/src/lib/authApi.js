import axios from 'axios';

export const API_BASE = 'http://127.0.0.1:8080';

function extractErrorMessage(err, fallback) {
  return err?.response?.data?.error || fallback;
}

export async function registerUser({ email, name, password, phone }) {
  try {
    const res = await axios.post(`${API_BASE}/auth/register`, { email, name, password, phone });
    return res.data;
  } catch (err) {
    throw new Error(extractErrorMessage(err, 'Registration failed. Please try again.'));
  }
}

export async function loginWithPassword({ email, password }) {
  try {
    const res = await axios.post(`${API_BASE}/auth/login`, { email, password });
    return res.data;
  } catch (err) {
    throw new Error(extractErrorMessage(err, 'Login failed. Please try again.'));
  }
}

export async function requestOtp({ email, purpose = 'login' }) {
  try {
    const res = await axios.post(`${API_BASE}/auth/otp/request`, { email, purpose });
    return res.data;
  } catch (err) {
    throw new Error(extractErrorMessage(err, 'Could not send OTP. Please try again.'));
  }
}

export async function verifyOtp({ email, code, purpose = 'login' }) {
  try {
    const res = await axios.post(`${API_BASE}/auth/otp/verify`, { email, code, purpose });
    return res.data;
  } catch (err) {
    throw new Error(extractErrorMessage(err, 'Invalid or expired code.'));
  }
}

export function saveSession({ token, user }) {
  localStorage.setItem('authToken', token);
  localStorage.setItem('authUser', JSON.stringify(user));
}

export function getToken() {
  return localStorage.getItem('authToken');
}

export function getCurrentUser() {
  const raw = localStorage.getItem('authUser');
  return raw ? JSON.parse(raw) : null;
}

export function logout() {
  localStorage.removeItem('authToken');
  localStorage.removeItem('authUser');
}

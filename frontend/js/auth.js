/* auth.js — shared auth helpers used by all pages */

const TOKEN_KEY = 'nexabank_token';

function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function parseJwt(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(base64));
  } catch {
    return null;
  }
}

function requireAuth() {
  const token = getToken();
  if (!token) { window.location.href = '/login.html'; return null; }
  const payload = parseJwt(token);
  if (!payload || payload.exp < Date.now() / 1000) {
    clearToken();
    window.location.href = '/login.html';
    return null;
  }
  return payload;
}

function requireAdmin() {
  const payload = requireAuth();
  if (!payload) return null;
  if (!payload.is_admin) { window.location.href = '/dashboard.html'; return null; }
  return payload;
}

async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });

  if (res.status === 204) return null;

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.detail || `Request failed (${res.status})`;
    throw new Error(Array.isArray(msg) ? msg.map(e => e.msg).join('; ') : msg);
  }
  return data;
}

function apiPost(path, body) {
  return apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
}

function apiGet(path) {
  return apiFetch(path);
}

function apiDelete(path) {
  return apiFetch(path, { method: 'DELETE' });
}

/* ── UI helpers ── */
function showAlert(el, message, type = 'error') {
  el.className = `alert alert-${type} show`;
  el.textContent = message;
}

function hideAlert(el) {
  el.classList.remove('show');
}

function showFieldError(inputId, errId) {
  document.getElementById(inputId)?.classList.add('error');
  const err = document.getElementById(errId);
  if (err) err.style.display = 'block';
}

function clearErrors() {
  document.querySelectorAll('input.error').forEach(el => el.classList.remove('error'));
  document.querySelectorAll('.form-error').forEach(el => el.style.display = 'none');
  document.querySelectorAll('.alert.show').forEach(el => el.classList.remove('show'));
}

function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(amount);
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function statusBadge(s) {
  const map = { completed: 'success', pending: 'warning', failed: 'danger' };
  return `<span class="badge badge-${map[s] || 'muted'}">${s}</span>`;
}

function typeBadge(t) {
  const map = { deposit: 'info', withdrawal: 'warning', transfer: 'muted' };
  return `<span class="badge badge-${map[t] || 'muted'}">${t}</span>`;
}

/* Logout wired up globally after DOM ready */
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    clearToken();
    window.location.href = '/login.html';
  });
});

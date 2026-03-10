/**
 * NexaBank API Client
 * Centralized fetch wrapper for all API calls
 */
const API_BASE = window.location.origin;

function getToken() {
    return localStorage.getItem('nexabank_token');
}

function setToken(token) {
    localStorage.setItem('nexabank_token', token);
}

function clearToken() {
    localStorage.removeItem('nexabank_token');
    localStorage.removeItem('nexabank_user');
}

async function apiRequest(method, path, body = null, isFormData = false) {
    const token = getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    if (!isFormData && body) headers['Content-Type'] = 'application/json';

    const opts = { method, headers };
    if (body) opts.body = isFormData ? body : JSON.stringify(body);

    try {
        const res = await fetch(`${API_BASE}${path}`, opts);
        if (res.status === 401) {
            clearToken();
            window.location.href = '/login/';
            return;
        }
        const data = res.headers.get('content-type')?.includes('application/json')
            ? await res.json()
            : null;
        if (!res.ok) {
            const msg = data?.detail || `HTTP ${res.status}`;
            throw new Error(Array.isArray(msg) ? msg.map(e => e.msg).join(', ') : msg);
        }
        return data;
    } catch (err) {
        if (err.message.includes('fetch')) throw new Error('Network error. Please check your connection.');
        throw err;
    }
}

const api = {
    get: (path) => apiRequest('GET', path),
    post: (path, body) => apiRequest('POST', path, body),
    put: (path, body) => apiRequest('PUT', path, body),
    upload: (path, formData) => apiRequest('POST', path, formData, true),

    // Auth
    login: (email, password) => api.post('/api/auth/login', { email, password }),
    signup: (name, email, password) => api.post('/api/auth/signup', { name, email, password }),

    // Users
    getMe: () => api.get('/api/users/me'),
    updateMe: (data) => api.put('/api/users/me', data),
    uploadAvatar: (file) => {
        const fd = new FormData();
        fd.append('file', file);
        return api.upload('/api/users/me/avatar', fd);
    },

    // Accounts
    getAccount: () => api.get('/api/accounts/me'),
    getStats: () => api.get('/api/accounts/stats'),

    // Transactions
    getTransactions: (limit = 50) => api.get(`/api/transactions/?limit=${limit}`),
    getTransaction: (id) => api.get(`/api/transactions/${id}`),
    deposit: (amount) => api.post('/api/transactions/deposit', { amount }),
    transfer: (receiver_account_number, amount, description) =>
        api.post('/api/transactions/transfer', { receiver_account_number, amount, description }),

    // PDF
    receiptUrl: (txId) => `${API_BASE}/api/pdf/receipt/${txId}?token=${getToken()}`,
    statementUrl: (from, to) => {
        let url = `${API_BASE}/api/pdf/statement`;
        const params = new URLSearchParams();
        if (from) params.set('date_from', from);
        if (to) params.set('date_to', to);
        const q = params.toString();
        return q ? `${url}?${q}` : url;
    },

    setToken,
    getToken,
    clearToken,
};

window.NexaAPI = api;

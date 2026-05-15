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

        // Handle globals (401 Unauthorized globally)
        if (res.status === 401 && path !== '/api/auth/login') {
            clearToken();
            window.location.href = '/login/';
            throw new Error('Session expired');
        }

        let data = null;
        if (res.status !== 204) {
            const contentType = res.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                const text = await res.text();
                data = text ? JSON.parse(text) : null;
            }
        }
        if (!res.ok) {
            let msg = data?.detail || `HTTP ${res.status}`;

            // Handle blocked users directly universally
            if (res.status === 403 && data?.detail?.error === 'ACCOUNT_BLOCKED') {
                const usrObj = data?.detail?.user;
                if (usrObj) {
                    sessionStorage.setItem('blocked_user', JSON.stringify(usrObj));
                } else {
                    const localUsr = localStorage.getItem('nexabank_user');
                    if (localUsr) sessionStorage.setItem('blocked_user', localUsr);
                }

                clearToken();
                window.location.href = '/blocked/';
                throw new Error(data?.detail?.message || 'ACCOUNT_BLOCKED');
            }

            // Handle validation errors (422 Unprocessable Entity)
            if (res.status === 422 && Array.isArray(data?.detail)) {
                const firstError = data.detail[0];
                const loc = firstError.loc || [];
                // Use backend error message if it exists and isn't a technical pydantic string
                const backendMsg = firstError.msg;
                const field = loc[loc.length - 1];

                if (field === 'email') msg = 'Please enter a valid email address.';
                else if (field === 'password') msg = backendMsg || 'Password does not meet security requirements.';
                else if (field === 'first_name' || field === 'last_name') msg = backendMsg || 'Please enter a valid name (min 3 characters, no numbers).';
                else msg = backendMsg || 'Invalid data provided.';
            }
            // Handle specific auth errors
            else if (res.status === 401) {
                msg = 'Invalid email or password.';
            }
            // Handle forbidden/unconfirmed errors
            else if (res.status === 403) {
                msg = typeof data?.detail === 'string' ? data.detail : (data?.detail?.message || 'Access denied.');
            }

            throw new Error(Array.isArray(msg) ? msg.map(e => e.msg || e).join(', ') : msg);
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
    patch: (path, body) => apiRequest('PATCH', path, body),
    del: (path) => apiRequest('DELETE', path),
    upload: (path, formData) => apiRequest('POST', path, formData, true),

    // Auth
    login: (email, password) => api.post('/api/auth/login', { email, password }),
    signup: (firstName, lastName, email, password) => api.post('/api/auth/register', {
        first_name: firstName,
        last_name: lastName,
        email,
        password
    }),
    verifyEmail: (email, token) => api.get(`/api/auth/verify?email=${encodeURIComponent(email)}&token=${encodeURIComponent(token)}`),
    setPin: (pin) => api.post('/api/auth/set-pin', { pin }),
    changePassword: (current_password, new_password) => api.post('/api/auth/change-password', { current_password, new_password }),
    changePin: (current_pin, new_pin) => api.post('/api/auth/change-pin', { current_pin, new_pin }),

    // Users
    getMe: () => api.get('/api/auth/me'),
    updateMe: (data) => api.put('/api/users/me', data),
    updateProfile: (data) => api.patch('/api/users/profile', data),
    uploadAvatar: (file) => {
        const fd = new FormData();
        fd.append('file', file);
        return api.upload('/api/users/me/avatar', fd);
    },

    // Accounts
    getAccount: () => api.get('/api/accounts/me'),
    getStats: () => api.get('/api/accounts/stats'),

    // Transactions
    getTransactions: (limit = 50) => api.get(`/api/transactions?limit=${limit}`),
    getTransaction: (id) => api.get(`/api/transactions/${id}`),
    deposit: (amount, pin) => api.post('/api/transactions/deposit', { amount, pin }),
    transfer: (receiver_account_number, amount, pin, description) =>
        api.post('/api/transactions/transfer', { receiver_account_number, amount, pin, description }),

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

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
        
        // Handle 401 Unauthorized
        if (res.status === 401 && path !== '/api/auth/login') {
            clearToken();
            window.location.href = '/login/';
            return;
        }

        const data = res.headers.get('content-type')?.includes('application/json')
            ? await res.json()
            : null;
        if (!res.ok) {
            let msg = data?.detail || `HTTP ${res.status}`;
            
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
                msg = data?.detail || 'Access denied.';
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

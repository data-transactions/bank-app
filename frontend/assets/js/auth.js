/**
 * NexaBank Auth Helpers
 */

/** Decode a JWT payload without verifying the signature. */
function parseJwt(token) {
    try {
        const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(base64));
    } catch {
        return null;
    }
}
window.parseJwt = parseJwt;

/**
 * Redirect to the correct dashboard based on the role claim in the JWT.
 * Admins  → /admin/
 * Regular → /dashboard/
 */
function redirectToDashboard() {
    const token = NexaAPI.getToken();
    const payload = token ? parseJwt(token) : null;
    window.location.href = (payload?.role === 'admin' || payload?.role === 'super_admin') ? '/admin/' : '/dashboard/';
}
window.redirectToDashboard = redirectToDashboard;

const Auth = {
    requireAuth() {
        const token = NexaAPI.getToken();
        if (!token) {
            window.location.href = '/login/';
            return false;
        }
        return true;
    },

    requireGuest() {
        const token = NexaAPI.getToken();
        if (token) {
            redirectToDashboard();
            return false;
        }
        return true;
    },

    logout() {
        NexaAPI.clearToken();
        window.location.href = '/';
    },
};

window.Auth = Auth;

// Password policy
function validatePassword(password) {
    const checks = {
        length: password.length >= 8,
        upper: /[A-Z]/.test(password),
        lower: /[a-z]/.test(password),
        special: /[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;']/.test(password),
    };
    const score = Object.values(checks).filter(Boolean).length;
    return { checks, score, valid: score === 4 };
}
window.validatePassword = validatePassword;

function getPasswordStrengthClass(score) {
    if (score <= 1) return 'strength-weak';
    if (score === 2) return 'strength-fair';
    if (score === 3) return 'strength-good';
    return 'strength-strong';
}
window.getPasswordStrengthClass = getPasswordStrengthClass;

/**
 * URL Helper for reverse proxy support
 * Automatically prepends ROOT_PATH to all URLs
 */

// Initialize ROOT_PATH from global variable set in base template
const ROOT_PATH = window.ROOT_PATH || '';

/**
 * Generate a URL with proper root path prefix
 * @param {string} path - The path to append (e.g., '/api/cries/history')
 * @returns {string} - Full URL with root path
 */
function url(path) {
    // Ensure path starts with /
    if (!path.startsWith('/')) {
        path = '/' + path;
    }
    return ROOT_PATH + path;
}

/**
 * Navigate to a URL with proper root path
 * @param {string} path - The path to navigate to
 */
function navigate(path) {
    window.location.href = url(path);
}

/**
 * Fetch with automatic root path handling
 * @param {string} path - The API path
 * @param {object} options - Fetch options
 * @returns {Promise} - Fetch promise
 */
function apiFetch(path, options = {}) {
    return fetch(url(path), options);
}

// Export for use in other scripts
window.url = url;
window.navigate = navigate;
window.apiFetch = apiFetch;

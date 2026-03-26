/* ============================================================
   app.js – Shared utilities for VaultVerify frontend
   ============================================================ */

/**
 * A wrapper around the native fetch() that automatically injects
 * the Authorization: Bearer header from localStorage.
 * On 401, the user is redirected to login automatically.
 *
 * @param {string} url
 * @param {RequestInit} options
 * @returns {Promise<Response>}
 */
async function authFetch(url, options = {}) {
  const token = localStorage.getItem('token');

  const headers = {
    ...(options.headers || {}),
  };

  // Inject bearer token if present
  if (token) {
    headers['Authorization'] = 'Bearer ' + token;
  }

  // IMPORTANT: Do NOT set Content-Type for FormData –
  // the browser sets the correct multipart boundary automatically.
  // Only set JSON content-type for plain object bodies.
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('role');
    localStorage.removeItem('username');
    window.location.href = '/static/login.html';
    return response; // prevent further execution
  }

  return response;
}

/**
 * Show a temporary in-page alert banner.
 * @param {string} containerId  - id of the element to render into
 * @param {string} message
 * @param {'error'|'success'|'info'} type
 * @param {number} autoDismissMs - 0 = never
 */
function showAlert(containerId, message, type = 'error', autoDismissMs = 5000) {
  const container = document.getElementById(containerId);
  if (!container) return;

  container.innerHTML = `<div class="alert alert-${type}">${message}</div>`;

  if (autoDismissMs > 0) {
    setTimeout(() => {
      if (container) container.innerHTML = '';
    }, autoDismissMs);
  }
}

/**
 * Destroy the session and send the user to the login page.
 */
function logout() {
  localStorage.removeItem('token');
  localStorage.removeItem('role');
  localStorage.removeItem('username');
  window.location.href = '/static/login.html';
}

/**
 * Guard: if no token stored, kick back to login.
 * Call at the top of every protected page's script.
 */
function requireAuth() {
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = '/static/login.html';
  }
}

/**
 * Format an ISO date string to a human-readable local date.
 * @param {string} isoString
 * @returns {string}
 */
function formatDate(isoString) {
  if (!isoString) return '—';
  const d = new Date(isoString);
  return d.toLocaleDateString('en-IN', {
    year:  'numeric',
    month: 'short',
    day:   'numeric',
    hour:  '2-digit',
    minute:'2-digit',
  });
}

/**
 * Map a status string to its badge CSS class.
 * @param {string} status
 * @returns {string}
 */
function statusBadge(status) {
  const map = {
    'DIGITAL_PENDING':  'badge-pending',
    'PHYSICAL_PENDING': 'badge-physical',
    'CERTIFIED':        'badge-cert',
    'REJECTED':         'badge-rejected',
  };
  const label = {
    'DIGITAL_PENDING':  'Digital Pending',
    'PHYSICAL_PENDING': 'Physical Pending',
    'CERTIFIED':        'Certified',
    'REJECTED':         'Rejected',
  };
  const cls = map[status] || 'badge-pending';
  const txt = label[status] || status;
  return `<span class="badge ${cls}">${txt}</span>`;
}

/**
 * Build a comma-separated list of document anchor links from an array of URLs.
 * @param {string[]} urls
 * @returns {string} HTML
 */
function docLinks(urls) {
  if (!urls || urls.length === 0) return '<span class="text-muted text-sm">None</span>';
  return urls.map((u, i) =>
    `<a href="${u}" target="_blank" class="doc-link">📄 Doc ${i + 1}</a>`
  ).join('');
}

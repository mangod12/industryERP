/**
 * KumarBrothers Steel ERP - Frontend Configuration
 * Centralized configuration for API endpoints and authentication
 */

const KBConfig = {
  // API Configuration — auto-detect protocol and host
  // If we are served from the same domain as the API (standard production), use current origin.
  // If we are in local dev on separate ports, it falls back to :8000
  API_BASE: window.location.port === '8000' || !window.location.port
    ? window.location.origin
    : `${window.location.protocol}//${window.location.hostname}:8000`,

  // Available roles in the system
  ROLES: Object.freeze({
    BOSS: 'Boss',
    SUPERVISOR: 'Software Supervisor',
    STORE_KEEPER: 'Store Keeper',
    QA_INSPECTOR: 'QA Inspector',
    DISPATCH_OPERATOR: 'Dispatch Operator',
    USER: 'User'
  }),

  // Role permissions mapping (mirrors backend)
  PERMISSIONS: {
    'Boss': ['*'], // Full access
    'Software Supervisor': [
      'inventory:view', 'inventory:create', 'inventory:update', 'inventory:adjust',
      'grn:view', 'grn:create', 'grn:approve',
      'dispatch:view', 'dispatch:create', 'dispatch:approve',
      'qa:view',
      'production:view', 'production:update', 'production:consume',
      'report:view', 'report:export', 'settings:view',
      // Delete permissions for supervisors
      'customers:delete', 'excel:delete',
      // Allow creating users via UI
      'users:create'
    ],
    'Store Keeper': [
      'inventory:view', 'inventory:create', 'inventory:update',
      'grn:view', 'grn:create',
      'dispatch:view', 'dispatch:create',
      'production:view', 'production:consume',
      'report:view'
    ],
    'QA Inspector': [
      'inventory:view', 'grn:view',
      'qa:view', 'qa:inspect', 'qa:approve', 'qa:reject', 'qa:hold',
      'report:view'
    ],
    'Dispatch Operator': [
      'inventory:view',
      'dispatch:view', 'dispatch:create',
      'production:view',
      'report:view'
    ],
    'User': [
      'inventory:view', 'grn:view', 'dispatch:view',
      'production:view', 'report:view'
    ],
    'Fabricator': [
      'production:view', 'report:view'
    ],
    'Painter': [
      'production:view', 'report:view'
    ],
    'Dispatch': [
      'production:view', 'report:view', 'dispatch:view'
    ]
  }
};

/**
 * Authentication Manager - handles tokens and user state
 */
const KBAuth = {
  // Storage keys
  TOKEN_KEY: 'kb_token',
  ROLE_KEY: 'kb_role',
  USER_KEY: 'kb_user',

  /**
   * Get the current auth token
   */
  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  /**
   * Get the current user's role
   */
  getRole() {
    return localStorage.getItem(this.ROLE_KEY) || 'User';
  },

  /**
   * Get stored user info
   */
  getUser() {
    try {
      const user = localStorage.getItem(this.USER_KEY);
      return user ? JSON.parse(user) : null;
    } catch (e) {
      return null;
    }
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    const token = this.getToken();
    if (!token) return false;

    // Check if token is expired (basic JWT decode)
    try {
      const payload = this.getPayload();
      if (!payload) return false;
      const exp = payload.exp * 1000; // Convert to milliseconds
      return Date.now() < exp;
    } catch (e) {
      return false;
    }
  },

  /**
   * Get decoded token payload
   */
  getPayload() {
    const token = this.getToken();
    if (!token) return null;
    try {
      return JSON.parse(atob(token.split('.')[1]));
    } catch (e) {
      return null;
    }
  },

  /**
   * Save authentication data after login
   */
  saveAuth(token, role, user = null) {
    localStorage.setItem(this.TOKEN_KEY, token);
    localStorage.setItem(this.ROLE_KEY, role);
    if (user) {
      localStorage.setItem(this.USER_KEY, JSON.stringify(user));
    }
  },

  /**
   * Clear authentication data (logout)
   */
  clearAuth() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.ROLE_KEY);
    localStorage.removeItem(this.USER_KEY);
  },

  /**
   * Check if current user has a specific permission
   */
  hasPermission(permission) {
    const role = this.getRole();
    const perms = KBConfig.PERMISSIONS[role] || [];
    return perms.includes('*') || perms.includes(permission);
  },

  /**
   * Check if current user has one of the allowed roles
   */
  hasRole(...allowedRoles) {
    const role = this.getRole();
    return allowedRoles.includes(role);
  },

  /**
   * Redirect to login if not authenticated
   */
  requireAuth() {
    if (!this.isAuthenticated()) {
      window.location.href = 'login.html';
      return false;
    }
    return true;
  }
};

/**
 * API Client - handles all HTTP requests with authentication
 */
const KBApi = {
  /**
   * Make an authenticated API request
   */
  async request(endpoint, options = {}) {
    const url = endpoint.startsWith('http') ? endpoint : `${KBConfig.API_BASE}${endpoint}`;

    // Set default headers
    const headers = {
      ...options.headers
    };

    // Add auth token if available
    const token = KBAuth.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    // Add Content-Type for JSON body
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(options.body);
    }

    const response = await fetch(url, {
      ...options,
      headers
    });

    // Handle 401 - redirect to login
    if (response.status === 401) {
      KBAuth.clearAuth();
      if (!window.location.pathname.includes('login.html')) {
        window.location.href = 'login.html';
      }
      throw new Error('Session expired. Please login again.');
    }

    return response;
  },

  /**
   * GET request
   */
  async get(endpoint, params = {}) {
    const url = new URL(endpoint.startsWith('http') ? endpoint : `${KBConfig.API_BASE}${endpoint}`);
    Object.keys(params).forEach(key => {
      if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
        url.searchParams.append(key, params[key]);
      }
    });
    return this.request(url.toString());
  },

  /**
   * POST request
   */
  async post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: data
    });
  },

  /**
   * PUT request
   */
  async put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: data
    });
  },

  /**
   * DELETE request
   */
  async delete(endpoint) {
    return this.request(endpoint, {
      method: 'DELETE'
    });
  },

  /**
   * Upload file(s)
   */
  async upload(endpoint, formData) {
    return this.request(endpoint, {
      method: 'POST',
      body: formData // FormData is sent as-is (no JSON stringify)
    });
  }
};

/**
 * UI Helpers for role-based visibility
 */
const KBUI = {
  /**
   * Initialize role-based UI visibility
   * Elements with data-permission="permission1,permission2" are shown only if user has any of those permissions
   * Elements with data-role="Role1,Role2" are shown only if user has one of those roles
   */
  initRoleBasedUI() {
    const role = KBAuth.getRole();

    // Handle data-permission attributes
    document.querySelectorAll('[data-permission]').forEach(el => {
      const required = el.getAttribute('data-permission').split(',').map(p => p.trim());
      const hasAny = required.some(p => KBAuth.hasPermission(p));
      el.style.display = hasAny ? '' : 'none';
    });

    // Handle data-role attributes
    document.querySelectorAll('[data-role]').forEach(el => {
      const allowed = el.getAttribute('data-role').split(',').map(r => r.trim());
      el.style.display = allowed.includes(role) ? '' : 'none';
    });

    // Update role display elements
    const roleDisplay = document.getElementById('current-role');
    if (roleDisplay) {
      roleDisplay.textContent = role;
    }

    const userDisplay = document.getElementById('current-user');
    if (userDisplay) {
      const user = KBAuth.getUser();
      userDisplay.textContent = user?.full_name || user?.username || role;
    }
  },

  /**
   * Show a toast notification
   */
  showToast(message, type = 'success') {
    if (window.showToast) {
      window.showToast(message, type);
    } else {
      console.log(`[${type}] ${message}`);
    }
  },

  /**
   * Escape HTML to prevent XSS
   */
  escapeHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[c]));
  }
};

// Export for use in other scripts
window.KBConfig = KBConfig;
window.KBAuth = KBAuth;
window.KBApi = KBApi;
window.KBUI = KBUI;
// API_BASE globally accessible
window.API_BASE = KBConfig.API_BASE;

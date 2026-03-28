/**
 * KBSteel ERP — Canonical HTML Escape Utility
 * =============================================
 * Single source of truth for HTML escaping across the frontend.
 * Import via <script src="js/modules/escapeHtml.js"></script> before page scripts.
 */
(function() {
  'use strict';

  const ESCAPE_MAP = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  };

  /**
   * Escape HTML special characters to prevent XSS.
   * @param {*} str - Value to escape (coerced to string)
   * @returns {string} Escaped HTML-safe string
   */
  function escapeHtml(str) {
    return String(str || '').replace(/[&<>"']/g, function(c) {
      return ESCAPE_MAP[c];
    });
  }

  // Expose globally
  window.escapeHtml = escapeHtml;
})();

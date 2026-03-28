/**
 * KBError — Unified error handling replacing mix of alert/toast/console.error.
 */
(function() {
  'use strict';

  var KBError = {
    handle: function(error, context) {
      var message = '';
      if (typeof error === 'string') {
        message = error;
      } else if (error && error.message) {
        message = error.message;
      } else if (error && error.detail) {
        message = error.detail;
      } else {
        message = 'An unexpected error occurred';
      }

      console.error('[KBError]', context || '', message, error);

      if (window.showToast) {
        window.showToast(message, 'danger');
      }
    },

    handleResponse: async function(response, context) {
      if (response.ok) return response;

      var detail = '';
      try {
        var body = await response.json();
        detail = body.detail || body.message || JSON.stringify(body);
      } catch (e) {
        detail = response.statusText || 'Request failed';
      }

      this.handle({ message: detail }, context);
      throw new Error(detail);
    },

    withRetry: async function(fn, maxRetries, delay) {
      if (!maxRetries) maxRetries = 3;
      if (!delay) delay = 1000;
      var lastError;
      for (var i = 0; i < maxRetries; i++) {
        try {
          return await fn();
        } catch (e) {
          lastError = e;
          if (i < maxRetries - 1) {
            await new Promise(function(r) { setTimeout(r, delay * (i + 1)); });
          }
        }
      }
      throw lastError;
    }
  };

  window.KBError = KBError;
})();

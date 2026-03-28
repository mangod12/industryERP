/**
 * KBStore — Centralized state management with cache and event bus.
 */
(function() {
  'use strict';

  const _state = {};
  const _cache = {};
  const _listeners = {};

  const KBStore = {
    set(key, value) {
      _state[key] = value;
      this._emit(key, value);
    },

    get(key, defaultValue) {
      return key in _state ? _state[key] : defaultValue;
    },

    on(key, callback) {
      if (!_listeners[key]) _listeners[key] = [];
      _listeners[key].push(callback);
      return function unsubscribe() {
        _listeners[key] = _listeners[key].filter(function(cb) { return cb !== callback; });
      };
    },

    _emit(key, value) {
      if (_listeners[key]) {
        _listeners[key].forEach(function(cb) { cb(value); });
      }
    },

    cache(key, fetcher, ttlMs) {
      if (ttlMs === undefined) ttlMs = 30000;
      var entry = _cache[key];
      if (entry && (Date.now() - entry.timestamp) < ttlMs) {
        return Promise.resolve(entry.data);
      }
      return fetcher().then(function(data) {
        _cache[key] = { data: data, timestamp: Date.now() };
        return data;
      });
    },

    invalidate(key) {
      if (key) {
        delete _cache[key];
      } else {
        Object.keys(_cache).forEach(function(k) { delete _cache[k]; });
      }
    }
  };

  window.KBStore = KBStore;
})();

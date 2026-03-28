/**
 * Debounce utility for search inputs.
 * Usage: input.addEventListener('input', debounce(handler, 300));
 */
(function() {
  'use strict';

  function debounce(fn, delay) {
    if (!delay) delay = 300;
    var timer;
    return function() {
      var context = this;
      var args = arguments;
      clearTimeout(timer);
      timer = setTimeout(function() {
        fn.apply(context, args);
      }, delay);
    };
  }

  window.debounce = debounce;
})();

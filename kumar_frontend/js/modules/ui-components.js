/**
 * KBComponents — Shared UI component factories.
 */
(function() {
  'use strict';

  var esc = window.escapeHtml || function(s) { return String(s || ''); };

  var KBComponents = {
    statCard: function(opts) {
      var title = esc(opts.title);
      var value = esc(opts.value);
      var icon = opts.icon || 'bi-info-circle';
      var color = opts.color || 'primary';
      return '<div class="col-md-3 col-sm-6 mb-3">' +
        '<div class="card border-' + color + ' h-100">' +
          '<div class="card-body text-center">' +
            '<i class="bi ' + icon + ' fs-2 text-' + color + '"></i>' +
            '<h3 class="mt-2 mb-0">' + value + '</h3>' +
            '<small class="text-muted">' + title + '</small>' +
          '</div>' +
        '</div></div>';
    },

    progressBar: function(opts) {
      var pct = Math.min(100, Math.max(0, opts.percentage || 0));
      var label = esc(opts.label || '');
      var color = opts.color || 'primary';
      return '<div class="mb-2">' +
        '<div class="d-flex justify-content-between mb-1">' +
          '<small>' + label + '</small>' +
          '<small>' + pct.toFixed(1) + '%</small>' +
        '</div>' +
        '<div class="progress" style="height:8px">' +
          '<div class="progress-bar bg-' + color + '" style="width:' + pct + '%"></div>' +
        '</div></div>';
    },

    skeleton: function(lines) {
      if (!lines) lines = 3;
      var html = '<div class="placeholder-glow">';
      for (var i = 0; i < lines; i++) {
        var w = 40 + Math.floor(Math.random() * 50);
        html += '<span class="placeholder col-' + Math.ceil(w / 10) + '"></span> ';
      }
      return html + '</div>';
    },

    confirmModal: function(opts) {
      var title = esc(opts.title || 'Confirm');
      var body = esc(opts.body || 'Are you sure?');
      var confirmText = esc(opts.confirmText || 'Confirm');
      var id = opts.id || 'confirmModal';
      return '<div class="modal fade" id="' + id + '" tabindex="-1">' +
        '<div class="modal-dialog"><div class="modal-content">' +
          '<div class="modal-header">' +
            '<h5 class="modal-title">' + title + '</h5>' +
            '<button type="button" class="btn-close" data-bs-dismiss="modal"></button>' +
          '</div>' +
          '<div class="modal-body"><p>' + body + '</p></div>' +
          '<div class="modal-footer">' +
            '<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>' +
            '<button type="button" class="btn btn-danger" id="' + id + '-confirm">' + confirmText + '</button>' +
          '</div>' +
        '</div></div></div>';
    },

    emptyState: function(message) {
      return '<div class="text-center text-muted py-5">' +
        '<i class="bi bi-inbox fs-1"></i>' +
        '<p class="mt-2">' + esc(message || 'No data found') + '</p>' +
      '</div>';
    }
  };

  window.KBComponents = KBComponents;
})();

/**
 * KBPagination — Client-side pagination component.
 * Usage: KBPagination.render(containerId, { currentPage, totalPages, onPageChange });
 */
(function() {
  'use strict';

  var KBPagination = {
    paginate: function(items, page, perPage) {
      if (!perPage) perPage = 25;
      var start = (page - 1) * perPage;
      return {
        items: items.slice(start, start + perPage),
        currentPage: page,
        totalPages: Math.ceil(items.length / perPage),
        totalItems: items.length
      };
    },

    render: function(containerId, opts) {
      var container = document.getElementById(containerId);
      if (!container) return;

      var current = opts.currentPage || 1;
      var total = opts.totalPages || 1;
      var onPageChange = opts.onPageChange;

      if (total <= 1) {
        container.innerHTML = '';
        return;
      }

      var pages = [];
      var start = Math.max(1, current - 2);
      var end = Math.min(total, current + 2);

      if (start > 1) pages.push(1);
      if (start > 2) pages.push('...');
      for (var i = start; i <= end; i++) pages.push(i);
      if (end < total - 1) pages.push('...');
      if (end < total) pages.push(total);

      var html = '<nav><ul class="pagination pagination-sm justify-content-center">';
      html += '<li class="page-item' + (current === 1 ? ' disabled' : '') + '">' +
        '<a class="page-link" href="#" data-page="' + (current - 1) + '">&laquo;</a></li>';

      pages.forEach(function(p) {
        if (p === '...') {
          html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        } else {
          html += '<li class="page-item' + (p === current ? ' active' : '') + '">' +
            '<a class="page-link" href="#" data-page="' + p + '">' + p + '</a></li>';
        }
      });

      html += '<li class="page-item' + (current === total ? ' disabled' : '') + '">' +
        '<a class="page-link" href="#" data-page="' + (current + 1) + '">&raquo;</a></li>';
      html += '</ul></nav>';

      container.innerHTML = html;

      if (onPageChange) {
        container.querySelectorAll('[data-page]').forEach(function(el) {
          el.addEventListener('click', function(e) {
            e.preventDefault();
            var page = parseInt(this.getAttribute('data-page'));
            if (page >= 1 && page <= total && page !== current) {
              onPageChange(page);
            }
          });
        });
      }
    }
  };

  window.KBPagination = KBPagination;
})();

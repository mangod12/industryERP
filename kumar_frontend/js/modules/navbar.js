/**
 * KBNavbar — Dynamic navbar replacing 23 hardcoded navbars.
 * Usage: KBNavbar.render('navbar-container', 'dashboard');
 */
(function() {
  'use strict';

  const NAV_ITEMS = [
    { id: 'dashboard', label: 'Dashboard', href: 'index.html', icon: 'bi-speedometer2' },
    { id: 'customers', label: 'Customers', href: 'customers.html', icon: 'bi-people' },
    { id: 'tracking', label: 'Tracking', href: 'tracking_v2.html', icon: 'bi-clipboard-check' },
    { id: 'bom', label: 'BOM', href: 'bom.html', icon: 'bi-diagram-3' },
    { id: 'materials', label: 'Materials', href: 'materials.html', icon: 'bi-box-seam' },
    { id: 'stock', label: 'Stock', href: 'stock.html', icon: 'bi-boxes' },
    { id: 'grn', label: 'GRN', href: 'grn.html', icon: 'bi-truck' },
    { id: 'dispatch', label: 'Dispatch', href: 'dispatch.html', icon: 'bi-send' },
    { id: 'inventory', label: 'Inventory', href: 'raw_material.html', icon: 'bi-database' },
    { id: 'scrap', label: 'Scrap', href: 'scrap.html', icon: 'bi-trash' },
    { id: 'reusable', label: 'Reusable', href: 'reusable.html', icon: 'bi-recycle' },
    { id: 'queries', label: 'Queries', href: 'queries.html', icon: 'bi-question-circle' },
    { id: 'settings', label: 'Settings', href: 'settings.html', icon: 'bi-gear', roles: ['Boss', 'Software Supervisor'] },
  ];

  const KBNavbar = {
    render(containerId, activePage) {
      const container = document.getElementById(containerId);
      if (!container) return;

      const role = (window.KBAuth && KBAuth.getRole()) || 'User';
      const user = (window.KBAuth && KBAuth.getUser()) || {};
      const displayName = user.full_name || user.username || role;

      const visibleItems = NAV_ITEMS.filter(item => {
        if (item.roles && !item.roles.includes(role)) return false;
        return true;
      });

      const navLinksHtml = visibleItems.map(item => {
        const isActive = item.id === activePage ? ' active' : '';
        return '<li class="nav-item">' +
          '<a class="nav-link' + isActive + '" href="' + item.href + '">' +
          '<i class="bi ' + item.icon + ' me-1"></i>' + item.label +
          '</a></li>';
      }).join('');

      container.innerHTML =
        '<nav class="navbar navbar-expand-lg navbar-dark bg-dark">' +
          '<div class="container-fluid">' +
            '<a class="navbar-brand" href="index.html">' +
              '<strong>KB</strong>Steel ERP' +
            '</a>' +
            '<button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#mainNav">' +
              '<span class="navbar-toggler-icon"></span>' +
            '</button>' +
            '<div class="collapse navbar-collapse" id="mainNav">' +
              '<ul class="navbar-nav me-auto">' + navLinksHtml + '</ul>' +
              '<div class="navbar-nav">' +
                '<span class="nav-link text-light">' +
                  '<i class="bi bi-person-circle me-1"></i>' +
                  '<span id="current-user">' + displayName + '</span>' +
                  ' <span class="badge bg-secondary" id="current-role">' + role + '</span>' +
                '</span>' +
                '<a class="nav-link" href="#" onclick="KBAuth.clearAuth();window.location.href=\'login.html\'">' +
                  '<i class="bi bi-box-arrow-right"></i> Logout' +
                '</a>' +
              '</div>' +
            '</div>' +
          '</div>' +
        '</nav>';
    }
  };

  window.KBNavbar = KBNavbar;
})();

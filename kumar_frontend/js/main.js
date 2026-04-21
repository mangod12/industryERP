/**
 * KumarBrothers Steel ERP - Main JavaScript
 * Handles UI components, API integration, and page functionality
 */

(function () {
  // ==========================================================================
  // GLOBAL UI COMPONENTS (Loader, Toast)
  // ==========================================================================

  function createGlobals() {
    if (document.getElementById('globalLoader')) return;

    // Create loader
    const loader = document.createElement('div');
    loader.id = 'globalLoader';
    loader.className = 'position-fixed top-0 start-0 w-100 h-100 d-none justify-content-center align-items-center';
    loader.style.background = 'rgba(255,255,255,0.6)';
    loader.style.zIndex = '2000';
    loader.innerHTML = `<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>`;
    document.body.appendChild(loader);

    // Create toast container
    const tc = document.createElement('div');
    tc.id = 'toastContainer';
    tc.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(tc);
  }

  function showLoader() {
    const el = document.getElementById('globalLoader');
    if (el) { el.classList.remove('d-none'); el.classList.add('d-flex'); }
  }

  function hideLoader() {
    const el = document.getElementById('globalLoader');
    if (el) { el.classList.add('d-none'); el.classList.remove('d-flex'); }
  }

  function showToast(message, type = 'success') {
    createGlobals();
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toastEl = document.createElement('div');
    toastEl.className = `toast align-items-center text-bg-${type} border-0`;
    toastEl.setAttribute('role', 'alert');
    toastEl.innerHTML = `
      <div class="d-flex">
        <div class="toast-body">${message}</div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
      </div>
    `;
    container.appendChild(toastEl);
    try {
      const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
      toast.show();
      toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    } catch (e) {
      // Bootstrap may not be available; fallback
      setTimeout(() => toastEl.remove(), 3000);
    }
  }

  // Expose globally
  window.showLoader = showLoader;
  window.hideLoader = hideLoader;
  window.showToast = showToast;

  // Ensure elements exist when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      createGlobals();
      if (typeof KBUI !== 'undefined') KBUI.initRoleBasedUI();
    });
  } else {
    createGlobals();
    if (typeof KBUI !== 'undefined') KBUI.initRoleBasedUI();
  }

  // ==========================================================================
  // ENHANCED FETCH WRAPPER (with auth and error handling)
  // ==========================================================================

  const _fetch = window.fetch.bind(window);
  window.fetch = async function (...args) {
    const url = args[0];
    const opts = args[1] || {};
    const method = (opts.method || 'GET').toUpperCase();

    // Skip auth injection for login endpoint
    const isLoginEndpoint = typeof url === 'string' && url.includes('/auth/login');

    // Add auth token to all API requests (unless it's login)
    if (!isLoginEndpoint && typeof KBAuth !== 'undefined') {
      const token = KBAuth.getToken();
      if (token) {
        opts.headers = opts.headers || {};
        if (!opts.headers['Authorization']) {
          opts.headers['Authorization'] = `Bearer ${token}`;
        }
      }
    }

    args[1] = opts;
    showLoader();

    try {
      const res = await _fetch(...args);

      // Handle 401 - session expired
      if (res.status === 401 && typeof KBAuth !== 'undefined') {
        KBAuth.clearAuth();
        if (!window.location.pathname.includes('login.html')) {
          showToast('Session expired. Redirecting to login...', 'warning');
          setTimeout(() => { window.location.href = 'login.html'; }, 1500);
        }
      }

      if (!res.ok) {
        let msg = `Request failed (${res.status})`;
        try {
          const j = await res.clone().json().catch(() => null);
          if (j && j.detail) {
            msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail);
          }
        } catch (e) { }
        showToast(msg, 'danger');
      } else {
        if (method !== 'GET') showToast('Operation successful', 'success');
      }
      return res;
    } catch (err) {
      showToast(`Network error: ${err.message}`, 'danger');
      throw err;
    } finally {
      hideLoader();
    }
  };
})();

// ==========================================================================
// MAIN APPLICATION INITIALIZATION
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {

  // --------------------------------------------------------------------------
  // AUTH CHECK - Redirect to login if not authenticated (except login page)
  // Note: register.html now requires authentication.
  // --------------------------------------------------------------------------
  const publicPages = ['login.html'];
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';

  if (!publicPages.includes(currentPage)) {
    if (typeof KBAuth !== 'undefined' && !KBAuth.isAuthenticated()) {
      window.location.href = 'login.html';
      return;
    }
  }

  // --------------------------------------------------------------------------
  // ROLE-BASED UI INITIALIZATION
  // --------------------------------------------------------------------------
  if (typeof KBUI !== 'undefined') {
    KBUI.initRoleBasedUI();
  }

  // Get current role from stored auth and display it
  const currentRole = (typeof KBAuth !== 'undefined') ? KBAuth.getRole() : 'User';
  const roleDisplay = document.getElementById('current-role');
  if (roleDisplay) {
    roleDisplay.textContent = currentRole;
  }

  // --------------------------------------------------------------------------
  // LOGOUT HANDLER
  // --------------------------------------------------------------------------
  document.querySelectorAll('.kb-logout').forEach(el => {
    el.addEventListener('click', (e) => {
      e.preventDefault();
      if (typeof KBAuth !== 'undefined') {
        KBAuth.clearAuth();
      } else {
        localStorage.removeItem('kb_token');
        localStorage.removeItem('kb_role');
      }
      window.location.href = 'login.html';
    });
  });

  // --------------------------------------------------------------------------
  // NOTIFICATION BELL + POPUP SYSTEM
  // --------------------------------------------------------------------------
  if (!publicPages.includes(currentPage)) {
    (function initNotifications() {
      const API_BASE_N = (typeof KBConfig !== 'undefined' && KBConfig.API_BASE)
        ? KBConfig.API_BASE
        : (window.API_BASE || window.location.origin || 'http://127.0.0.1:8000');

      function authHdrs() {
        const t = (typeof KBAuth !== 'undefined') ? KBAuth.getToken() : localStorage.getItem('kb_token');
        return t ? { 'Authorization': `Bearer ${t}` } : {};
      }

      // --- Inject CSS ---
      const style = document.createElement('style');
      style.textContent = `
        .notif-bell-wrap { position: relative; cursor: pointer; margin-right: 8px; }
        .notif-bell-wrap .bi-bell-fill { font-size: 1.3rem; color: #fff; }
        .notif-badge { position: absolute; top: -4px; right: -6px; background: #ff4444; color: #fff;
          font-size: 0.65rem; font-weight: 700; padding: 1px 5px; border-radius: 10px; min-width: 16px;
          text-align: center; line-height: 1.3; display: none; }
        .notif-dropdown { position: absolute; top: 36px; right: 0; width: 340px; max-height: 400px;
          overflow-y: auto; background: #fff; border-radius: 10px; box-shadow: 0 8px 32px rgba(0,0,0,0.18);
          z-index: 9999; display: none; border: 1px solid #e5e7eb; }
        .notif-dropdown.show { display: block; }
        .notif-header { padding: 12px 16px; border-bottom: 1px solid #eee; display: flex;
          justify-content: space-between; align-items: center; }
        .notif-header h6 { margin: 0; font-weight: 700; font-size: 0.95rem; }
        .notif-header button { font-size: 0.75rem; border: none; background: none; color: #0d6efd; cursor: pointer; }
        .notif-item { padding: 10px 16px; border-bottom: 1px solid #f5f5f5; cursor: pointer;
          transition: background 0.15s; }
        .notif-item:hover { background: #f8f9fa; }
        .notif-item.unread { background: #f0f7ff; border-left: 3px solid #0d6efd; }
        .notif-item .notif-msg { font-size: 0.85rem; color: #333; margin-bottom: 2px; }
        .notif-item .notif-time { font-size: 0.72rem; color: #999; }
        .notif-empty { padding: 24px; text-align: center; color: #aaa; font-size: 0.85rem; }
        .notif-toast-container { position: fixed; top: 70px; right: 20px; z-index: 10000;
          display: flex; flex-direction: column; gap: 8px; }
        .notif-toast { background: #fff; border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);
          padding: 12px 18px; min-width: 280px; max-width: 360px; animation: notifSlideIn 0.35s ease;
          border-left: 4px solid #0d6efd; display: flex; align-items: flex-start; gap: 10px; }
        .notif-toast .nt-icon { font-size: 1.2rem; flex-shrink: 0; }
        .notif-toast .nt-body { flex: 1; }
        .notif-toast .nt-msg { font-size: 0.85rem; color: #333; }
        .notif-toast .nt-time { font-size: 0.7rem; color: #999; }
        .notif-toast .nt-close { cursor: pointer; font-size: 1rem; color: #ccc; margin-left: 6px; flex-shrink: 0; }
        .notif-toast .nt-close:hover { color: #666; }
        @keyframes notifSlideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
      `;
      document.head.appendChild(style);

      // --- Inject toast container ---
      const toastContainer = document.createElement('div');
      toastContainer.className = 'notif-toast-container';
      document.body.appendChild(toastContainer);

      // --- Inject bell icon into navbar ---
      const navbar = document.querySelector('.kb-navbar');
      if (navbar) {
        const rightSection = navbar.querySelector('.d-flex.align-items-center.gap-3:last-child');
        if (rightSection) {
          const bellWrap = document.createElement('div');
          bellWrap.className = 'notif-bell-wrap';
          bellWrap.innerHTML = `
            <i class="bi bi-bell-fill"></i>
            <span class="notif-badge" id="notifBadge">0</span>
            <div class="notif-dropdown" id="notifDropdown">
              <div class="notif-header">
                <h6>Notifications</h6>
                <button id="markAllRead">Mark all read</button>
              </div>
              <div id="notifList"><div class="notif-empty">No notifications</div></div>
            </div>
          `;
          rightSection.insertBefore(bellWrap, rightSection.firstChild);

          // Toggle dropdown
          bellWrap.querySelector('.bi-bell-fill').addEventListener('click', (e) => {
            e.stopPropagation();
            document.getElementById('notifDropdown').classList.toggle('show');
          });

          // Close on outside click
          document.addEventListener('click', (e) => {
            const dd = document.getElementById('notifDropdown');
            if (dd && !bellWrap.contains(e.target)) dd.classList.remove('show');
          });

          // Mark all read
          document.getElementById('markAllRead').addEventListener('click', async (e) => {
            e.stopPropagation();
            const unreadIds = cachedNotifications.filter(n => !n.read).map(n => n.id);
            if (!unreadIds.length) return;
            try {
              await fetch(`${API_BASE_N}/notifications/mark-read`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...authHdrs() },
                body: JSON.stringify(unreadIds)
              });
              fetchNotifications();
            } catch (err) { console.error('Mark read failed:', err); }
          });
        }
      }

      // --- Notification Polling ---
      let cachedNotifications = [];
      let seenIds = new Set();
      let firstLoad = true;

      async function fetchNotifications() {
        try {
          const res = await fetch(`${API_BASE_N}/notifications/`, { headers: authHdrs() });
          if (!res.ok) return;
          const items = await res.json();
          cachedNotifications = items;

          // Update badge
          const unread = items.filter(n => !n.read).length;
          const badge = document.getElementById('notifBadge');
          if (badge) {
            badge.textContent = unread > 99 ? '99+' : unread;
            badge.style.display = unread > 0 ? 'block' : 'none';
          }

          // Show toast for NEW unread items (not on first load)
          if (!firstLoad) {
            items.forEach(n => {
              if (!n.read && !seenIds.has(n.id)) {
                showNotifToast(n);
              }
            });
          }

          // Track seen IDs
          items.forEach(n => seenIds.add(n.id));
          firstLoad = false;

          // Update dropdown list
          renderNotifDropdown(items);
        } catch (err) { console.error('Notification fetch error:', err); }
      }

      function renderNotifDropdown(items) {
        const list = document.getElementById('notifList');
        if (!list) return;

        if (!items.length) {
          list.innerHTML = '<div class="notif-empty">No notifications</div>';
          return;
        }

        // Show latest 20
        const shown = items.slice(0, 20);
        list.innerHTML = '';
        shown.forEach(n => {
          const div = document.createElement('div');
          div.className = 'notif-item' + (n.read ? '' : ' unread');
          const ago = timeAgo(n.created_at);
          div.innerHTML = `
            <div class="notif-msg">${escHtml(n.message)}</div>
            <div class="notif-time">${ago}</div>
          `;
          div.addEventListener('click', async () => {
            if (!n.read) {
              try {
                await fetch(`${API_BASE_N}/notifications/mark-read`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json', ...authHdrs() },
                  body: JSON.stringify([n.id])
                });
                n.read = true;
                div.classList.remove('unread');
                const unread = cachedNotifications.filter(x => !x.read).length;
                const badge = document.getElementById('notifBadge');
                if (badge) {
                  badge.textContent = unread > 99 ? '99+' : unread;
                  badge.style.display = unread > 0 ? 'block' : 'none';
                }
              } catch (err) { console.error(err); }
            }
          });
          list.appendChild(div);
        });
      }

      function showNotifToast(n) {
        const toast = document.createElement('div');
        toast.className = 'notif-toast';
        const icon = n.message.startsWith('📋') ? '📋' : n.message.startsWith('❓') ? '❓' : '🔔';
        toast.innerHTML = `
          <div class="nt-icon">${icon}</div>
          <div class="nt-body">
            <div class="nt-msg">${escHtml(n.message)}</div>
            <div class="nt-time">Just now</div>
          </div>
          <div class="nt-close">&times;</div>
        `;
        toast.querySelector('.nt-close').addEventListener('click', () => toast.remove());
        toastContainer.appendChild(toast);
        // Auto-dismiss after 6s
        setTimeout(() => {
          if (toast.parentNode) toast.remove();
        }, 6000);
      }

      function escHtml(s) {
        return String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
      }

      function timeAgo(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        const now = new Date();
        const diffMs = now - d;
        const mins = Math.floor(diffMs / 60000);
        if (mins < 1) return 'Just now';
        if (mins < 60) return `${mins}m ago`;
        const hrs = Math.floor(mins / 60);
        if (hrs < 24) return `${hrs}h ago`;
        const days = Math.floor(hrs / 24);
        return `${days}d ago`;
      }

      // Initial fetch + poll every 30 seconds
      fetchNotifications();
      setInterval(fetchNotifications, 30000);
    })();
  }

  // --------------------------------------------------------------------------
  // UTILITY FUNCTIONS
  // --------------------------------------------------------------------------
  function escapeHtml(s) {
    return String(s || '').replace(/[&<>\"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  function highlightLowStock() {
    document.querySelectorAll('.remaining-qty').forEach(td => {
      const val = parseFloat(td.dataset.qty || '0');
      const total = parseFloat(td.dataset.total || '0');
      if (total > 0 && val / total < 0.15) {
        td.classList.add('low-stock');
      }
    });
  }

  // --------------------------------------------------------------------------
  // API BASE URL
  // --------------------------------------------------------------------------
  const apiBase = (typeof KBConfig !== 'undefined') ? KBConfig.API_BASE : 'http://127.0.0.1:8000';

  // --------------------------------------------------------------------------
  // INSTRUCTIONS — handled by instructions.html inline script (API-connected)
  // --------------------------------------------------------------------------

  // --------------------------------------------------------------------------
  // EXCEL UPLOAD
  // --------------------------------------------------------------------------
  const excelForm = document.getElementById('excelUploadForm');
  if (excelForm) {
    excelForm.addEventListener('submit', async function (e) {
      e.preventDefault();
      const fileInput = this.querySelector("input[type='file']");
      const statusEl = document.getElementById('excelStatus');
      const previewEl = document.getElementById('excelPreview');
      if (previewEl) previewEl.innerHTML = '';

      if (!fileInput || !fileInput.files || !fileInput.files.length) {
        if (statusEl) statusEl.innerText = 'Please select an .xlsx file';
        return;
      }

      const file = fileInput.files[0];
      if (!file.name.toLowerCase().endsWith('.xlsx')) {
        if (statusEl) statusEl.innerText = 'Only .xlsx files are supported';
        return;
      }

      const formData = new FormData();
      formData.append('file', file);
      if (statusEl) statusEl.innerHTML = 'Uploading and processing...';

      try {
        const res = await fetch(`${apiBase}/excel/upload`, {
          method: 'POST',
          body: formData,
        });

        if (!res.ok) {
          const err = await res.json().catch(() => null);
          const msg = err && err.detail ? err.detail : `Upload failed (${res.status})`;
          if (statusEl) statusEl.innerHTML = `<span class='text-danger'>${msg}</span>`;
          return;
        }

        const data = await res.json();
        if (statusEl) statusEl.innerHTML = "<span class='text-success'>Excel processed successfully</span>";

        // Render tables
        if (data && Array.isArray(data.sheets) && previewEl) {
          data.sheets.forEach(sheet => {
            const h = document.createElement('h6');
            h.textContent = sheet.sheet_name;
            h.className = 'mt-3';
            previewEl.appendChild(h);

            const table = document.createElement('table');
            table.className = 'table table-sm';

            const thead = document.createElement('thead');
            const tr = document.createElement('tr');
            sheet.columns.forEach(col => {
              const th = document.createElement('th');
              th.textContent = col;
              tr.appendChild(th);
            });
            thead.appendChild(tr);
            table.appendChild(thead);

            const tbody = document.createElement('tbody');
            (sheet.rows || []).forEach(row => {
              const tr = document.createElement('tr');
              (row || []).forEach(cell => {
                const td = document.createElement('td');
                td.textContent = (cell === null || cell === undefined) ? '' : String(cell);
                tr.appendChild(td);
              });
              tbody.appendChild(tr);
            });
            table.appendChild(tbody);
            previewEl.appendChild(table);
          });
        }
      } catch (err) {
        if (statusEl) statusEl.innerHTML = `<span class='text-danger'>Upload error: ${err.message}</span>`;
      }
    });
  }

  // --------------------------------------------------------------------------
  // INVENTORY CRUD
  // --------------------------------------------------------------------------
  const inventoryApiBase = `${apiBase}/inventory/`;

  async function fetchInventory() {
    try {
      const form = document.getElementById('inventoryFilterForm');
      let url = inventoryApiBase;

      if (form) {
        const params = new URLSearchParams();
        const fields = {
          'fName': 'material_name',
          'fCode': 'material_code',
          'fSection': 'section',
          'fCategory': 'category',
          'fUnit': 'unit',
          'fQtyMin': 'quantity_min',
          'fQtyMax': 'quantity_max',
          'fDateFrom': 'date_from',
          'fDateTo': 'date_to'
        };

        Object.entries(fields).forEach(([elementId, paramName]) => {
          const el = document.getElementById(elementId);
          if (el && el.value.trim()) {
            params.append(paramName, el.value.trim());
          }
        });

        const qs = params.toString();
        if (qs) url = `${inventoryApiBase}?${qs}`;
      }

      const res = await fetch(url);
      if (!res.ok) return [];
      return await res.json();
    } catch (err) {
      console.error('Inventory fetch error', err);
      return [];
    }
  }

  function renderInventory(items) {
    const tbody = document.querySelector('#inventoryTable tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    items.forEach(it => {
      const remaining = (Number(it.total) - Number(it.used)).toFixed(2);
      const tr = document.createElement('tr');
      tr.dataset.id = it.id;
      tr.innerHTML = `
        <td class="inv-name">${escapeHtml(it.name)}</td>
        <td class="inv-unit">${escapeHtml(it.unit || '')}</td>
        <td class="inv-total">${Number(it.total).toFixed(2)}</td>
        <td class="inv-used">${Number(it.used).toFixed(2)}</td>
        <td class="remaining-qty" data-qty="${remaining}" data-total="${it.total}">${remaining}</td>
        <td class="text-end">
          <button class="btn btn-sm btn-kb edit-btn" data-permission="inventory:update">Edit</button>
          <button class="btn btn-sm btn-danger delete-btn" data-permission="inventory:delete">Delete</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll('.edit-btn').forEach(btn => btn.addEventListener('click', onInventoryEdit));
    tbody.querySelectorAll('.delete-btn').forEach(btn => btn.addEventListener('click', onInventoryDelete));
    highlightLowStock();

    // Apply permission-based visibility to new elements
    if (typeof KBUI !== 'undefined') {
      KBUI.initRoleBasedUI();
    }
  }

  function onInventoryEdit(e) {
    const tr = e.currentTarget.closest('tr');
    if (!tr) return;
    const id = tr.dataset.id;

    const name = tr.querySelector('.inv-name').innerText;
    const unit = tr.querySelector('.inv-unit').innerText;
    const total = tr.querySelector('.inv-total').innerText;
    const used = tr.querySelector('.inv-used').innerText;

    tr.querySelector('.inv-name').innerHTML = `<input class="form-control form-control-sm edit-name" value="${escapeHtml(name)}">`;
    tr.querySelector('.inv-unit').innerHTML = `<input class="form-control form-control-sm edit-unit" value="${escapeHtml(unit)}">`;
    tr.querySelector('.inv-total').innerHTML = `<input type="number" step="0.01" class="form-control form-control-sm edit-total" value="${total}">`;
    tr.querySelector('.inv-used').innerHTML = `<input type="number" step="0.01" class="form-control form-control-sm edit-used" value="${used}">`;

    const actions = tr.querySelector('td.text-end');
    actions.innerHTML = `<button class="btn btn-sm btn-kb save-btn">Save</button> <button class="btn btn-sm btn-secondary cancel-btn">Cancel</button>`;
    actions.querySelector('.save-btn').addEventListener('click', () => onInventorySave(id, tr));
    actions.querySelector('.cancel-btn').addEventListener('click', () => refreshInventory());
  }

  async function onInventorySave(id, tr) {
    const payload = {
      id,
      name: tr.querySelector('.edit-name').value,
      unit: tr.querySelector('.edit-unit').value,
      total: Number(tr.querySelector('.edit-total').value) || 0,
      used: Number(tr.querySelector('.edit-used').value) || 0,
    };
    try {
      const res = await fetch(`${inventoryApiBase}/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error('Save failed');
      await refreshInventory();
    } catch (err) {
      alert('Failed to save item');
      console.error(err);
    }
  }

  async function onInventoryDelete(e) {
    const tr = e.currentTarget.closest('tr');
    if (!tr) return;
    const id = tr.dataset.id;
    if (!confirm('Delete this item?')) return;
    try {
      const res = await fetch(`${inventoryApiBase}/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Delete failed');
      await refreshInventory();
    } catch (err) {
      alert('Failed to delete item');
      console.error(err);
    }
  }

  async function addNewInventoryItem() {
    const name = document.getElementById('newName')?.value.trim();
    const unit = document.getElementById('newUnit')?.value.trim();
    const total = Number(document.getElementById('newTotal')?.value) || 0;
    const used = Number(document.getElementById('newUsed')?.value) || 0;

    if (!name) return alert('Enter material name');

    const payload = { name, unit, total, used };
    try {
      const res = await fetch(inventoryApiBase, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Add failed');

      // Clear form
      ['newName', 'newUnit', 'newTotal', 'newUsed'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
      });

      await refreshInventory();
    } catch (err) {
      alert('Failed to add item');
      console.error(err);
    }
  }

  async function refreshInventory() {
    const items = await fetchInventory();
    renderInventory(items || []);
  }

  // NOTE: Redundant addItemBtn listener removed to prevent double creation.
  // Page-specific scripts (like raw_material.html) handle this now.

  const filterSearchBtn = document.getElementById('filterSearchBtn');
  const filterResetBtn = document.getElementById('filterResetBtn');
  if (filterSearchBtn) filterSearchBtn.addEventListener('click', refreshInventory);
  if (filterResetBtn) filterResetBtn.addEventListener('click', async () => {
    ['fName', 'fCode', 'fSection', 'fCategory', 'fUnit', 'fQtyMin', 'fQtyMax', 'fDateFrom', 'fDateTo'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
    await refreshInventory();
  });

  // Initial inventory load
  if (document.getElementById('inventoryTable')) {
    refreshInventory();
  }

  // --------------------------------------------------------------------------
  // TRACKING / CUSTOMERS
  // --------------------------------------------------------------------------
  const trackingApiBase = `${apiBase}/tracking`;

  async function fetchTrackingCustomers() {
    try {
      const params = new URLSearchParams();
      const search = document.getElementById('custSearch');
      const status = document.getElementById('custStatus');

      if (search && search.value.trim()) params.append('name', search.value.trim());
      if (status && status.value) params.append('status', status.value);

      const qs = params.toString();
      const url = qs ? `${trackingApiBase}/customers?${qs}` : `${trackingApiBase}/customers`;
      const res = await fetch(url);
      if (!res.ok) return [];
      return await res.json();
    } catch (err) {
      console.error('Tracking fetch error', err);
      return [];
    }
  }

  async function renderCustomersList() {
    const rows = document.querySelector('#customersTable tbody');
    if (!rows) return;

    const items = await fetchTrackingCustomers();
    rows.innerHTML = '';

    items.forEach(c => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(c.name)}</td>
        <td>${escapeHtml(c.current_stage || 'Pending')}</td>
        <td><a class="btn btn-sm btn-kb" href="customer_details.html?id=${c.id}">View</a></td>
      `;
      rows.appendChild(tr);
    });
  }

  async function updateDashboardTracking() {
    const items = await fetchTrackingCustomers();

    const fab = items.filter(i => i.current_stage === 'Fabrication').length;
    const paint = items.filter(i => i.current_stage === 'Painting').length;
    const disp = items.filter(i => i.current_stage === 'Dispatch').length;

    const elF = document.getElementById('stageFabrication');
    if (elF) elF.innerText = `${fab} Jobs`;
    const elP = document.getElementById('stagePainting');
    if (elP) elP.innerText = `${paint} Jobs`;
    const elD = document.getElementById('stageDispatch');
    if (elD) elD.innerText = `${disp} Jobs`;

    const tbl = document.querySelector('#customerStatusTable tbody');
    if (tbl) {
      tbl.innerHTML = '';
      items.forEach(c => {
        const tr = document.createElement('tr');
        const status = (c.current_stage === 'Completed')
          ? `<span class="badge-status status-completed">Completed</span>`
          : `<span class="badge-status status-inprogress">${escapeHtml(c.current_stage || 'Pending')}</span>`;
        tr.innerHTML = `<td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.current_stage || 'Pending')}</td><td>${status}</td>`;
        tbl.appendChild(tr);
      });
    }
  }

  // --------------------------------------------------------------------------
  // CUSTOMER DETAILS PAGE
  // --------------------------------------------------------------------------
  async function loadCustomerDetails() {
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    if (!id) return;

    try {
      const res = await fetch(`${trackingApiBase}/customers/${id}`);
      if (!res.ok) return;
      const c = await res.json();

      const custName = document.getElementById('custName');
      const custProject = document.getElementById('custProject');
      const custStage = document.getElementById('custStage');

      if (custName) custName.innerText = c.name;
      if (custProject) custProject.innerText = c.project || '';
      if (custStage) custStage.innerText = c.current_stage || 'Pending';

      // Stage tracker visualization
      document.querySelectorAll('#stageTracker .stage').forEach(el => {
        const s = el.dataset.stage;
        el.classList.remove('completed', 'in-progress', 'pending');
        if (c.current_stage === s) {
          el.classList.add('in-progress');
        } else {
          const order = ['Fabrication', 'Painting', 'Dispatch'];
          const csIdx = order.indexOf(c.current_stage);
          const sIdx = order.indexOf(s);
          if (csIdx > sIdx) el.classList.add('completed');
          else el.classList.add('pending');
        }
      });

      // Action buttons (role-based)
      const act = document.getElementById('actionButtons');
      if (act) {
        act.innerHTML = '';
        const canUpdate = (typeof KBAuth !== 'undefined')
          ? KBAuth.hasPermission('production:update')
          : true;

        if (canUpdate) {
          const cur = c.current_stage;
          if (cur && cur !== 'Completed') {
            const startBtn = document.createElement('button');
            startBtn.className = 'btn btn-kb me-2';
            startBtn.innerText = `Start ${cur}`;
            startBtn.addEventListener('click', () => updateStage(id, cur, 'started'));

            const compBtn = document.createElement('button');
            compBtn.className = 'btn btn-kb';
            compBtn.innerText = `Mark ${cur} Completed`;
            compBtn.addEventListener('click', () => updateStage(id, cur, 'completed'));

            act.appendChild(startBtn);
            act.appendChild(compBtn);
          }
        }
      }

      // Material usage section
      const muCard = document.getElementById('materialUsageCard');
      if (muCard) {
        muCard.style.display = (c.current_stage === 'Fabrication') ? '' : 'none';
      }

      // Usage log
      const ul = document.getElementById('usageLog');
      if (ul) {
        ul.innerHTML = '';
        (c.material_usage || []).forEach(u => {
          const d = document.createElement('div');
          d.className = 'mb-1';
          d.innerText = `${u.ts} — ${u.name} ${u.qty} ${u.unit} by ${u.by || 'unknown'}`;
          ul.appendChild(d);
        });
      }

      // Stage history
      const sh = document.getElementById('stageHistory');
      if (sh) {
        sh.innerHTML = '';
        (c.stage_history || []).forEach(e => {
          const d = document.createElement('div');
          d.className = 'mb-1';
          d.innerText = `${e.ts} — ${e.stage} ${e.action} by ${e.by || 'unknown'}`;
          sh.appendChild(d);
        });
      }

      // Wire material usage add button
      const muAdd = document.getElementById('muAddBtn');
      if (muAdd) {
        muAdd.onclick = async () => {
          const name = document.getElementById('muMaterial')?.value.trim();
          const qty = Number(document.getElementById('muQty')?.value) || 0;
          if (!name || qty <= 0) return alert('Enter material and qty');

          try {
            const res = await fetch(`${trackingApiBase}/customers/${id}/material-usage`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ name, unit: 'kg', qty, by: currentRole })
            });
            if (!res.ok) throw new Error('fail');
            loadCustomerDetails();
          } catch (err) {
            alert('Failed to log usage');
          }
        };
      }

    } catch (err) {
      console.error(err);
    }
  }

  async function updateStage(id, stage, action) {
    try {
      const res = await fetch(`${trackingApiBase}/customers/${id}/stage`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stage, action, by: currentRole })
      });
      if (!res.ok) throw new Error('fail');
      await loadCustomerDetails();
      await updateDashboardTracking();
    } catch (err) {
      alert('Failed to update stage');
    }
  }

  // Initialize tracking pages
  if (document.getElementById('customersTable')) {
    renderCustomersList();
  }
  if (document.getElementById('customerStatusTable')) {
    updateDashboardTracking();
  }
  if (document.getElementById('custName')) {
    loadCustomerDetails();
  }

  // Wire customers filter buttons
  const custFilterBtn = document.getElementById('custFilterBtn');
  const custResetBtn = document.getElementById('custResetBtn');
  if (custFilterBtn) custFilterBtn.addEventListener('click', async () => {
    await renderCustomersList();
    await updateDashboardTracking();
  });
  if (custResetBtn) custResetBtn.addEventListener('click', async () => {
    const s = document.getElementById('custSearch');
    const st = document.getElementById('custStatus');
    if (s) s.value = '';
    if (st) st.value = '';
    await renderCustomersList();
    await updateDashboardTracking();
  });

  highlightLowStock();
});

// ==========================================================================
// NOTIFICATIONS MODULE
// ==========================================================================

document.addEventListener('DOMContentLoaded', () => {
  const notifBtn = document.getElementById('kb-notifications-btn');
  const notifList = document.getElementById('kbNotificationsList');
  const notifSettingsEl = document.getElementById('kbNotificationSettings');
  const markReadBtn = document.getElementById('kbMarkReadBtn');

  const API_BASE = (typeof KBConfig !== 'undefined') ? KBConfig.API_BASE : 'http://127.0.0.1:8000';

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>\"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  async function apiFetch(path, opts = {}) {
    const token = (typeof KBAuth !== 'undefined') ? KBAuth.getToken() : localStorage.getItem('kb_token');
    opts.headers = opts.headers || {};
    if (token) opts.headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(path.startsWith('http') ? path : API_BASE + path, opts);
    if (!res.ok) {
      try {
        const j = await res.json().catch(() => null);
        if (j && j.detail) showToast(j.detail, 'danger');
        else showToast(`Request failed (${res.status})`, 'danger');
      } catch (e) {
        showToast(`Request failed (${res.status})`, 'danger');
      }
    }
    return res;
  }

  async function loadNotifications() {
    if (!notifList) return;
    notifList.innerHTML = 'Loading...';

    try {
      const res = await apiFetch('/notifications/');
      if (!res.ok) {
        notifList.innerHTML = '<div class="text-danger">Failed to load</div>';
        return;
      }

      const items = await res.json();
      if (!items.length) {
        notifList.innerHTML = '<div class="small-muted">No notifications</div>';
        return;
      }

      const wrap = document.createElement('div');
      items.forEach(n => {
        const id = n.id;
        const div = document.createElement('div');
        div.className = `p-2 mb-2 border ${n.read ? '' : 'bg-light'}`;
        div.innerHTML = `
          <div class='form-check'>
            <input class='form-check-input notif-check' type='checkbox' value='${id}' id='notif-${id}'>
          </div>
          <div class='ms-2'>
            <strong>[${escapeHtml(n.level)}]</strong> ${escapeHtml(n.message)} 
            <div class='small text-muted'>${new Date(n.created_at).toLocaleString()}</div>
          </div>
        `;
        wrap.appendChild(div);
      });
      notifList.innerHTML = '';
      notifList.appendChild(wrap);
    } catch (err) {
      notifList.innerHTML = `<div class='text-danger'>Error: ${err.message}</div>`;
    }
  }

  async function loadNotificationSettings() {
    if (!notifSettingsEl) return;
    notifSettingsEl.innerHTML = 'Loading...';

    try {
      const res = await apiFetch('/notifications/settings');
      if (!res.ok) {
        notifSettingsEl.innerHTML = '<div class="text-danger">Failed to load settings</div>';
        return;
      }

      const s = await res.json();
      const html = `
        <div class='form-check'>
          <input id='ns-inapp' class='form-check-input' type='checkbox' ${s.in_app ? 'checked' : ''}>
          <label class='form-check-label ms-2'>In-app notifications</label>
        </div>
        <div class='form-check'>
          <input id='ns-email' class='form-check-input' type='checkbox' ${s.email ? 'checked' : ''}>
          <label class='form-check-label ms-2'>Email notifications</label>
        </div>
        <div class='form-check'>
          <input id='ns-push' class='form-check-input' type='checkbox' ${s.push ? 'checked' : ''}>
          <label class='form-check-label ms-2'>Push notifications</label>
        </div>
        <div class='mt-2'>
          <button id='ns-save' class='btn btn-sm btn-kb'>Save settings</button>
        </div>
      `;
      notifSettingsEl.innerHTML = html;

      document.getElementById('ns-save').addEventListener('click', async () => {
        const payload = {
          in_app: document.getElementById('ns-inapp').checked,
          email: document.getElementById('ns-email').checked,
          push: document.getElementById('ns-push').checked
        };
        const r = await apiFetch('/notifications/settings', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        if (!r.ok) {
          showToast('Failed to save settings', 'danger');
          return;
        }
        showToast('Notification settings saved', 'success');
        loadNotificationSettings();
      });
    } catch (err) {
      notifSettingsEl.innerHTML = `<div class='text-danger'>Error: ${err.message}</div>`;
    }
  }

  if (notifBtn) {
    notifBtn.addEventListener('click', () => {
      setTimeout(() => {
        loadNotifications();
        loadNotificationSettings();
      }, 200);
    });
  }

  if (markReadBtn) {
    markReadBtn.addEventListener('click', async () => {
      const checks = Array.from(document.querySelectorAll('.notif-check:checked')).map(i => Number(i.value));
      if (!checks.length) return showToast('Select notifications to mark read', 'warning');

      const r = await apiFetch('/notifications/mark-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(checks)
      });
      if (!r.ok) return showToast('Failed to mark read', 'danger');

      const j = await r.json();
      showToast(`Marked ${j.updated} notifications`, 'success');
      loadNotifications();
    });
  }
});

// ============================================================================
// Customer deletion helpers (Soft / Hard)
// ============================================================================

/**
 * Soft delete a customer (archival). Refreshes customers and dashboard.
 */
async function softDeleteCustomer(id, name) {
  if (!confirm(`Delete customer '${name}'? This is a soft-delete and can be restored by admin.`)) return;
  try {
    const res = await fetch(`${API_BASE}/customers/${id}`, { method: 'DELETE' });
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      alert(err && err.detail ? err.detail : `Failed to delete customer (${res.status})`);
      return;
    }
    showToast(`Customer '${name}' deleted`, 'success');
    if (typeof applyCustomerFilters === 'function') applyCustomerFilters();
    if (typeof refreshDashboard === 'function') refreshDashboard();
    if (typeof loadTrackingData === 'function') loadTrackingData();
  } catch (e) { console.error(e); alert('Failed to delete customer'); }
}

/**
 * Confirmation modal before hard delete
 */
function confirmHardDelete(id, name) {
  if (!confirm("⚠️ This will permanently delete customer and ALL production data. Continue?")) return;
  hardDeleteCustomer(id, name);
}

/**
 * Hard delete (permanent) – calls backend with ?hard=true and refreshes UI.
 */
async function hardDeleteCustomer(id, name) {
  try {
    const res = await fetch(`${API_BASE}/customers/${id}?hard=true`, { method: 'DELETE' });
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      alert((data && (data.detail || data.message)) || `Delete failed (${res.status})`);
      return;
    }
    alert((data && (data.message || 'Customer permanently deleted')) || 'Customer permanently deleted');
    if (typeof applyCustomerFilters === 'function') applyCustomerFilters();
    if (typeof refreshDashboard === 'function') refreshDashboard();
    if (typeof loadTrackingData === 'function') loadTrackingData();
  } catch (err) { console.error(err); alert('Hard delete failed'); }
}

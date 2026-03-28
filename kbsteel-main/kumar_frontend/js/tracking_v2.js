// Pagination helper for tracking_v2.html
const trackingV2 = (function () {
  const API_BASE = (typeof KBConfig !== 'undefined') ? KBConfig.API_BASE : (window.location.origin || 'http://127.0.0.1:8000');

  // Pagination state
  let currentPage = 1;
  let pageSize = 50;
  let totalItems = 0;

  function getToken() {
    if (typeof KBAuth !== 'undefined' && KBAuth.getToken) return KBAuth.getToken();
    return localStorage.getItem('kb_token') || localStorage.getItem('access_token');
  }

  async function loadTracking(companyId = null, page = currentPage) {
    currentPage = page;
    const url = new URL(`${API_BASE}/tracking/all-items`);
    url.searchParams.set('page', currentPage);
    url.searchParams.set('page_size', pageSize);
    if (companyId) url.searchParams.set('company_id', companyId);

    const headers = {};
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const res = await fetch(url.toString(), { headers });
    if (!res.ok) throw new Error(`Failed to fetch tracking: ${res.status}`);

    const data = await res.json();
    totalItems = data.total || 0;
    currentPage = data.page || currentPage;

    if (typeof window.renderTable === 'function') {
      window.renderTable(data.items || []);
    }

    renderPagination(currentPage, pageSize, totalItems);
    return data;
  }

  function renderPagination(p, ps, t) {
    // Ensure numbers
    p = parseInt(p, 10) || 1;
    ps = parseInt(ps, 10) || 50;
    t = parseInt(t, 10) || 0;

    // Update internal state
    currentPage = p;
    pageSize = ps;
    totalItems = t;

    const totalPages = Math.max(1, Math.ceil(t / ps));
    console.log(`[Pagination Debug] Page: ${p}, Size: ${ps}, Total: ${t}, Pages: ${totalPages}`);

    const el = document.getElementById('pagination');
    if (!el) return;

    el.innerHTML = `
      <div class="d-flex align-items-center">
        <button class="btn btn-sm btn-outline-secondary me-2" ${p <= 1 ? 'disabled' : ''} id="kb-first">First</button>
        <button class="btn btn-sm btn-outline-secondary me-2" ${p <= 1 ? 'disabled' : ''} id="kb-prev">Prev</button>
        <div class="small-muted">Page ${p} of ${totalPages}</div>
        <button class="btn btn-sm btn-outline-secondary ms-2" ${p >= totalPages ? 'disabled' : ''} id="kb-next">Next</button>
        <button class="btn btn-sm btn-outline-secondary ms-2" ${p >= totalPages ? 'disabled' : ''} id="kb-last">Last</button>
        <div class="ms-3">
          <label class="small-muted" style="margin-right:6px;">Size:</label>
          <select id="kb-page-size" class="form-select form-select-sm" style="width:70px;display:inline-block;vertical-align:middle;">
             <option value="10" ${ps === 10 ? 'selected' : ''}>10</option>
             <option value="25" ${ps === 25 ? 'selected' : ''}>25</option>
             <option value="50" ${ps === 50 ? 'selected' : ''}>50</option>
             <option value="100" ${ps === 100 ? 'selected' : ''}>100</option>
          </select>
        </div>
      </div>
    `;

    // Re-attach listeners explicitly
    const first = document.getElementById('kb-first');
    const prev = document.getElementById('kb-prev');
    const next = document.getElementById('kb-next');
    const last = document.getElementById('kb-last');
    const pageSizeEl = document.getElementById('kb-page-size');

    if (first) first.onclick = firstPage;
    if (prev) prev.onclick = prevPage;
    if (next) next.onclick = nextPage;
    if (last) last.onclick = lastPage;
    if (pageSizeEl) pageSizeEl.onchange = onPageSizeChange;
  }

  function nextPage() {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    if (currentPage < totalPages) {
      triggerLoad(currentPage + 1);
    }
  }

  function prevPage() {
    if (currentPage > 1) {
      triggerLoad(currentPage - 1);
    }
  }

  function firstPage() {
    triggerLoad(1);
  }

  function lastPage() {
    const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
    triggerLoad(totalPages);
  }

  function onPageSizeChange(e) {
    const v = parseInt(e.target.value, 10) || 50;
    pageSize = v;
    // Reset to page 1
    triggerLoad(1);
  }

  function triggerLoad(page) {
    if (typeof window.loadTrackingData === 'function') {
      // tracking_v2.html logic reads from DOM element "kb-page-size" usually,
      // but to ensure it picks up the NEW page size immediately, we might need to 
      // ensure the DOM is updated or pass it? 
      // loadTrackingData(page) in html reads the element.
      // If we fired this from onPageSizeChange, the element value is already updated by user input.
      console.log(`[Pagination] Triggering load for page ${page}`);
      window.loadTrackingData(page);
    } else {
      loadTracking(null, page);
    }
  }

  return {
    loadTracking,
    renderPagination,
    nextPage,
    prevPage,
    getState: () => ({ currentPage, pageSize, totalItems })
  };
})();

// Attach to window for legacy inline callers
window.trackingV2 = trackingV2;

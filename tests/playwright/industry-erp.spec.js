const fs = require('fs');
const path = require('path');
const { test, expect } = require('@playwright/test');

const USERNAME = process.env.E2E_USERNAME || 'admin';
const PASSWORD = process.env.E2E_PASSWORD || 'Boss1234!'; // pragma: allowlist secret
const screenshotDir = path.resolve(__dirname, '../../docs/screenshots');

const AUTHENTICATED_PAGES = [
  ['index.html', 'Dashboard'],
  ['raw_material.html', 'Raw Materials Inventory'],
  ['materials.html', 'Materials Master'],
  ['stock.html', 'Stock Overview'],
  ['grn.html', 'Goods Receipt Notes'],
  ['dispatch.html', 'Dispatch Notes'],
  ['tracking_v2.html', 'Production Tracking'],
  ['drawings.html', 'Drawings'],
  ['customers.html', 'Customers'],
  ['customer_add.html', 'Add Customer'],
  ['scrap.html', 'Scrap Inventory'],
  ['reusable.html', 'Reusable Stock'],
  ['queries.html', 'Queries'],
  ['instructions.html', 'Instructions'],
  ['instructions_edit.html', 'Edit Instructions'],
  ['settings.html', 'Settings'],
  ['account-settings.html', 'My Profile'],
  ['notification-settings.html', 'Notification Settings'],
  ['system-settings.html', 'System Settings'],
  ['register.html', 'Create New User']
];

async function login(page) {
  await page.goto('/login.html');
  await page.locator('#email-username').fill(USERNAME);
  await page.locator('#password').fill(PASSWORD);
  await page.getByRole('button', { name: /^login$/i }).click();
  await page.waitForURL(/index\.html|\/$/, { timeout: 15_000 });
  await expect(page.locator('main')).toContainText('Dashboard');
}

async function waitForApp(page) {
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(800);
}

async function capture(page, name) {
  await waitForApp(page);
  await page.screenshot({
    path: path.join(screenshotDir, `${name}.png`),
    fullPage: false
  });
}

test.beforeAll(() => {
  fs.mkdirSync(screenshotDir, { recursive: true });
});

test.describe('KumarBrothers Steel ERP production smoke', () => {
  test('authenticated API surfaces return seeded data', async ({ request, baseURL }) => {
    const loginRes = await request.post(`${baseURL}/auth/login`, {
      data: { username: USERNAME, password: PASSWORD }
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token } = await loginRes.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    const checks = [
      ['/healthz', null],
      ['/inventory/', 'ISMB 200 Beam'],
      ['/api/v2/grn/', 'GRN/FY26/00017'],
      ['/api/v2/dispatch/', 'DSP/FY26/00009'],
      ['/api/v2/settings/company', 'Kumar Brothers Steel'],
      ['/api/v2/reports/', 'reports']
    ];

    for (const [url, expectedText] of checks) {
      const res = await request.get(`${baseURL}${url}`, { headers });
      expect(res.ok(), `${url} should return 2xx`).toBeTruthy();
      if (expectedText) {
        expect(await res.text()).toContain(expectedText);
      }
    }
  });

  test('major workflows render and screenshots are captured', async ({ page }) => {
    const consoleErrors = [];
    page.on('pageerror', error => consoleErrors.push(error.message));
    page.on('console', message => {
      if (message.type() === 'error' && !message.text().includes('Failed to load resource')) {
        consoleErrors.push(message.text());
      }
    });

    await login(page);
    await capture(page, '01-dashboard');

    const pages = [
      ['raw_material.html', 'Raw Materials Inventory', '02-raw-materials'],
      ['materials.html', 'Materials Master', '03-materials-master'],
      ['stock.html', 'Stock Overview', '04-stock-overview'],
      ['grn.html', 'Goods Receipt', '05-goods-receipt'],
      ['dispatch.html', 'Dispatch', '06-dispatch'],
      ['tracking_v2.html', 'Production Tracking', '07-production-tracking'],
      ['drawings.html', 'Drawings', '08-drawings'],
      ['customers.html', 'Customers', '09-customers'],
      ['scrap.html', 'Scrap', '10-scrap'],
      ['reusable.html', 'Reusable', '11-reusable'],
      ['queries.html', 'Queries', '12-queries'],
      ['instructions.html', 'Instructions', '13-instructions'],
      ['settings.html', 'Settings', '14-settings']
    ];

    for (const [url, expected, screenshotName] of pages) {
      await page.goto(`/${url}`);
      await waitForApp(page);
      await expect(page.locator('body'), `${url} should render ${expected}`).toContainText(expected);
      await capture(page, screenshotName);
    }

    expect(consoleErrors).toEqual([]);
  });

  test('factory pages expose named controls without invalid display values', async ({ page }) => {
    await login(page);

    const firstCustomerId = await page.evaluate(async () => {
      const base = (typeof KBConfig !== 'undefined') ? KBConfig.API_BASE : window.location.origin;
      const res = await fetch(`${base}/customers`);
      if (!res.ok) return null;
      const customers = await res.json();
      return customers[0] && customers[0].id;
    });
    expect(firstCustomerId, 'seeded customer is required for edit/detail page coverage').toBeTruthy();

    const pages = [
      ...AUTHENTICATED_PAGES,
      [`customer_edit.html?id=${firstCustomerId}`, 'Edit Customer'],
      [`customer_details.html?id=${firstCustomerId}`, null]
    ];

    for (const [url, expected] of pages) {
      await page.goto(`/${url}`);
      await waitForApp(page);
      if (expected) {
        await expect(page.locator('body'), `${url} should render ${expected}`).toContainText(expected);
      }
      await expect(page.locator('h1').first(), `${url} should expose a page heading`).toBeVisible();
      await expect(page.locator('.kb-topbar'), `${url} should keep the shared top bar`).toBeVisible();
      await expect(page.locator('.kb-sidebar'), `${url} should keep the shared sidebar`).toBeVisible();

      const unnamedButtons = await page.locator('button:visible').evaluateAll(buttons =>
        buttons
          .filter(button => !button.innerText.trim() && !button.getAttribute('aria-label') && !button.getAttribute('title'))
          .map(button => button.outerHTML.slice(0, 160))
      );
      expect(unnamedButtons, `${url} has unnamed visible controls`).toEqual([]);
      await expect(page.locator('body'), `${url} should not show Invalid Date`).not.toContainText('Invalid Date');
      await expect(page.locator('body'), `${url} should not show NaN`).not.toContainText('NaN');
      await expect(page.locator('body'), `${url} should not show undefined`).not.toContainText(/\bundefined\b/i);
      await expect(page.locator('body'), `${url} should not show null`).not.toContainText(/\bnull\b/i);
      const hasPageOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
      expect(hasPageOverflow, `${url} should not create page-level horizontal overflow`).toBeFalsy();
    }
  });

  test('login page is consistent before authentication', async ({ page }) => {
    await page.goto('/login.html');
    await page.evaluate(() => {
      localStorage.removeItem('kb_token');
      localStorage.removeItem('kb_role');
      localStorage.removeItem('kb_user');
    });
    await page.reload();
    await waitForApp(page);
    await expect(page.locator('body')).toContainText('KumarBrothers Steel');
    await expect(page.getByRole('button', { name: /^login$/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /show password/i })).toBeVisible();
    const unnamedButtons = await page.locator('button:visible').evaluateAll(buttons =>
      buttons
        .filter(button => !button.innerText.trim() && !button.getAttribute('aria-label') && !button.getAttribute('title'))
        .map(button => button.outerHTML.slice(0, 160))
    );
    expect(unnamedButtons, 'login.html has unnamed visible controls').toEqual([]);
    await expect(page.locator('body')).not.toContainText('Invalid Date');
    await expect(page.locator('body')).not.toContainText('NaN');
  });

  test('GRN and dispatch lifecycle controls are wired and state-gated', async ({ page }) => {
    await login(page);

    await page.goto('/grn.html');
    await waitForApp(page);
    await page.getByRole('button', { name: 'Search' }).click();
    await page.getByRole('button', { name: 'Clear' }).click();
    await page.locator('.view-grn').first().click();
    await expect(page.locator('#grnDetailModal.show')).toBeVisible();
    await expect(page.locator('#btnSubmitGRN')).toHaveAttribute('title', /Draft|line item|Submit/i);
    await expect(page.locator('#btnApproveGRN')).toHaveAttribute('title', /Submitted|QA|Approve/i);
    const qaApprove = page.locator('.qa-approve').first();
    if (await qaApprove.count()) {
      await expect(qaApprove).toContainText('Approve');
    }
    await page.locator('#grnDetailModal .btn-close').click();
    await expect(page.locator('#grnDetailModal')).not.toHaveClass(/show/);

    await page.goto('/dispatch.html');
    await waitForApp(page);
    await page.getByRole('button', { name: 'Search' }).click();
    await page.getByRole('button', { name: 'Clear' }).click();
    await page.locator('.view-dispatch').first().click();
    await expect(page.locator('#dispatchDetailModal.show')).toBeVisible();
    await expect(page.locator('#btnSubmitDispatch')).toHaveText('Submit for Approval');
    await expect(page.locator('#btnApproveDispatch')).toHaveText('Confirm Dispatch');
    await expect(page.locator('#btnOpenPickStock')).toHaveAttribute('title', /Pick|locked/i);
  });

  test('fabrication completion opens material deduction confirmation before stage advance', async ({ page, request, baseURL }) => {
    let stageAdvanceRequests = 0;
    let tempCustomerId = null;
    const runId = Date.now();

    const loginRes = await request.post(`${baseURL}/auth/login`, {
      data: { username: USERNAME, password: PASSWORD }
    });
    expect(loginRes.ok()).toBeTruthy();
    const { access_token } = await loginRes.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    await page.route('**/api/tracking/*', async route => {
      const request = route.request();
      if (request.method() === 'PUT') {
        const body = request.postData() || '';
        if (body.includes('"stage"')) {
          stageAdvanceRequests += 1;
        }
      }
      await route.continue();
    });

    try {
      const customerRes = await request.post(`${baseURL}/customers`, {
        headers,
        data: { name: `PW Fabrication ${runId}`, project_details: 'Playwright modal gate' }
      });
      expect(customerRes.ok()).toBeTruthy();
      tempCustomerId = (await customerRes.json()).id;

      const itemCode = `PW-FAB-${runId}`;
      const itemRes = await request.post(`${baseURL}/customers/${tempCustomerId}/items`, {
        headers,
        data: {
          item_code: itemCode,
          item_name: 'Modal Gate Test Beam',
          section: 'ISMB 200',
          length_mm: 1200,
          quantity: 1,
          unit: 'pcs',
          weight_per_unit: 12.5,
          material_requirements: JSON.stringify([{ inventory_name: 'ISMB 200 Beam', profile: 'ISMB 200', qty: 12.5 }]),
          checklist: '[]'
        }
      });
      expect(itemRes.ok()).toBeTruthy();

      await login(page);
      await page.goto('/tracking_v2.html');
      await waitForApp(page);
      await page.locator('#searchInput').fill(itemCode);
      await page.getByRole('button', { name: 'Search' }).click();
      await waitForApp(page);

      const fabricationButton = page.locator('button.complete-btn.fabrication:not([disabled])').first();
      await expect(fabricationButton).toBeVisible();
      await fabricationButton.click();
      await expect(page.locator('#deductionModal.show')).toBeVisible();
      await expect(page.locator('#deductionPreview')).toContainText('ISMB 200');
      expect(stageAdvanceRequests).toBe(0);
      await page.locator('#deductionModal .btn-close').click();
    } finally {
      if (tempCustomerId) {
        await request.delete(`${baseURL}/customers/${tempCustomerId}?hard=true`, { headers });
      }
    }
  });

  test('raw material resets require typed confirmation and do not use native dialogs', async ({ page }) => {
    page.on('dialog', dialog => {
      throw new Error(`Unexpected native dialog: ${dialog.message()}`);
    });

    await login(page);
    await page.goto('/raw_material.html');
    await waitForApp(page);

    await page.getByRole('button', { name: 'Reset Total Stock' }).click();
    await expect(page.locator('#kbConfirmModal.show')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reset Total Stock' }).last()).toBeDisabled();
    await page.locator('#kbConfirmTypedInput').fill('RESET');
    await expect(page.getByRole('button', { name: 'Reset Total Stock' }).last()).toBeDisabled();
    await page.locator('#kbConfirmTypedInput').fill('RESET STOCK');
    await expect(page.getByRole('button', { name: 'Reset Total Stock' }).last()).toBeEnabled();
    await page.locator('#kbConfirmModal .btn-close').click();
  });

  test('customer actions are permission-filtered and safe for apostrophes', async ({ page }) => {
    await login(page);
    await page.goto('/customers.html');
    await waitForApp(page);

    await page.evaluate(() => {
      localStorage.setItem('kb_role', 'User');
      renderCustomers([
        {
          id: 98765,
          name: "O'Brien Steel",
          project_details: "Handrail trial",
          total_items: 1,
          current_stage: 'fabrication'
        }
      ]);
    });

    await expect(page.getByText("O'Brien Steel")).toBeVisible();
    await expect(page.getByText('Soft Delete')).not.toBeVisible();
    await expect(page.getByText('Hard Delete')).not.toBeVisible();
    await page.getByRole('button', { name: 'Upload' }).click();
    await expect(page.locator('#uploadExcelModal.show')).toBeVisible();
  });

  test('upload modals expose templates and scrap preview does not import early', async ({ page }) => {
    await login(page);

    await page.goto('/customers.html');
    await waitForApp(page);
    await page.locator('.upload-customer-btn').first().click();
    await expect(page.locator('#uploadExcelModal.show')).toBeVisible();
    await expect(page.locator('#trackingTemplateGuidance')).toContainText('Production Tracking Upload');
    await expect(page.locator('#trackingTemplateGuidance')).toContainText('Required');
    await expect(page.locator('#trackingTemplateGuidance').getByRole('link', { name: /Download Template/i })).toHaveAttribute(
      'href',
      /production_tracking_tcil_template\.csv/
    );
    await page.locator('#uploadExcelModal .btn-close').click();

    await page.goto('/scrap.html');
    await waitForApp(page);
    const countBeforePreview = await page.evaluate(async () => {
      const base = (typeof KBConfig !== 'undefined') ? KBConfig.API_BASE : window.location.origin;
      const res = await fetch(`${base}/scrap/records`);
      return (await res.json()).length;
    });

    await page.getByRole('button', { name: /Upload Scrap CSV/i }).click();
    await expect(page.locator('#uploadScrapModal.show')).toBeVisible();
    await expect(page.locator('#scrapTemplateGuidance')).toContainText('Scrap Import');
    await expect(page.locator('#scrapTemplateGuidance').getByRole('link', { name: /Download Template/i })).toHaveAttribute(
      'href',
      /scrap_import_template\.csv/
    );

    await page.setInputFiles('#scrapFileInput', {
      name: 'scrap-preview.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(
        'material_name,weight_kg,reason_code,dimensions,quantity\n' +
        'Playwright Scrap,12.5,leftover,1200mm offcut,1\n'
      )
    });
    await expect(page.locator('#uploadPreview')).toBeVisible();
    await expect(page.locator('#scrapUploadStatus')).toContainText('Preview ready');
    await expect(page.locator('#confirmUploadBtn')).toBeEnabled();

    const countAfterPreview = await page.evaluate(async () => {
      const base = (typeof KBConfig !== 'undefined') ? KBConfig.API_BASE : window.location.origin;
      const res = await fetch(`${base}/scrap/records`);
      return (await res.json()).length;
    });
    expect(countAfterPreview).toBe(countBeforePreview);
  });

  test('stock lot controls are explicit and CSV export is wired', async ({ page }) => {
    await login(page);
    await page.goto('/stock.html');
    await waitForApp(page);

    const viewButton = page.locator('.view-lot').first();
    test.skip(await viewButton.count() === 0, 'No stock lots in seeded data');
    await viewButton.click();
    await expect(page.locator('#stockDetailModal.show')).toBeVisible();
    await expect(page.locator('#btnHoldStock')).toBeDisabled();
    await expect(page.locator('#btnHoldStock')).toHaveAttribute('title', /GRN QA inspection/i);
    await expect(page.locator('#movementHistory')).not.toContainText('Movement history unavailable');
    await page.locator('#stockDetailModal .btn-close').click();

    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Export CSV' }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/^stock-lots-\d{4}-\d{2}-\d{2}\.csv$/);
  });

  test('role creation options and password toggles are operator-safe', async ({ page }) => {
    await login(page);
    await page.goto('/register.html');
    await waitForApp(page);

    const roleOptions = await page.locator('#roleSelect option').evaluateAll(options =>
      options.map(option => option.value).filter(Boolean)
    );
    expect(roleOptions).toEqual([
      'Boss',
      'Software Supervisor',
      'Store Keeper',
      'QA Inspector',
      'Dispatch Operator',
      'Fabricator',
      'Painter',
      'User'
    ]);

    await page.evaluate(() => localStorage.setItem('kb_role', 'Software Supervisor'));
    await page.goto('/register.html');
    await waitForApp(page);
    const supervisorRoleOptions = await page.locator('#roleSelect option').evaluateAll(options =>
      options.map(option => option.value).filter(Boolean)
    );
    expect(supervisorRoleOptions).toEqual([
      'Store Keeper',
      'QA Inspector',
      'Dispatch Operator',
      'Fabricator',
      'Painter',
      'User'
    ]);
    expect(supervisorRoleOptions).not.toContain('Boss');
    expect(supervisorRoleOptions).not.toContain('Software Supervisor');

    await page.evaluate(() => localStorage.setItem('kb_role', 'User'));
    await page.goto('/register.html');
    await page.waitForURL(/index\.html|\/$/, { timeout: 15_000 });
    await expect(page.locator('main')).toContainText('Dashboard');

    await page.evaluate(() => {
      localStorage.removeItem('kb_token');
      localStorage.removeItem('kb_role');
      localStorage.removeItem('kb_user');
    });
    await page.goto('/login.html');
    const toggle = page.getByRole('button', { name: /show password/i });
    await toggle.focus();
    await page.keyboard.press('Enter');
    await expect(page.getByRole('button', { name: /hide password/i })).toHaveAttribute('aria-pressed', 'true');
  });

  test('tablet viewport keeps operator pages reachable without page-level overflow', async ({ page }) => {
    await page.setViewportSize({ width: 1024, height: 768 });
    await login(page);

    for (const url of ['raw_material.html', 'tracking_v2.html', 'stock.html', 'customers.html']) {
      await page.goto(`/${url}`);
      await waitForApp(page);
      await expect(page.locator('h1').first()).toBeVisible();
      const hasPageOverflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
      expect(hasPageOverflow, `${url} should not create tablet page-level horizontal overflow`).toBeFalsy();
    }
  });

  test('operational pages do not register disruptive auto-refresh intervals', async ({ page }) => {
    await login(page);
    await page.addInitScript(() => {
      const originalSetInterval = window.setInterval;
      window.__kbRegisteredIntervals = [];
      window.setInterval = function (handler, timeout, ...args) {
        const source = typeof handler === 'function'
          ? Function.prototype.toString.call(handler)
          : String(handler);
        window.__kbRegisteredIntervals.push({ source, timeout });
        return originalSetInterval.call(this, handler, timeout, ...args);
      };
    });

    for (const url of ['drawings.html', 'scrap.html', 'reusable.html']) {
      await page.goto(`/${url}`);
      await waitForApp(page);
      const disruptiveIntervals = await page.evaluate(() =>
        window.__kbRegisteredIntervals
          .filter(item => /refreshPage|refreshScrap|refreshReusable/.test(item.source))
          .map(item => ({
            timeout: item.timeout,
            source: item.source.slice(0, 120)
          }))
      );
      expect(disruptiveIntervals, `${url} should use manual refresh for operator data`).toEqual([]);
    }
  });

  test('background dashboard refreshes do not show global loader or generic toasts', async ({ page }) => {
    await login(page);
    await page.addInitScript(() => {
      window.__kbRequestUiEvents = [];
      window.addEventListener('kb:request-ui', event => {
        window.__kbRequestUiEvents.push(event.detail);
      });
    });

    await page.goto('/index.html');
    await waitForApp(page);

    const backgroundEvents = await page.evaluate(() =>
      (window.__kbRequestUiEvents || []).filter(event => event.mode === 'background')
    );
    expect(backgroundEvents.length, 'dashboard should mark polling reads as background requests').toBeGreaterThan(0);
    expect(
      backgroundEvents.filter(event => event.showLoader || event.toastErrors || event.toastSuccess),
      'background requests should not trigger global loader or generic toast behavior'
    ).toEqual([]);
    await expect(page.locator('#globalLoader')).toHaveClass(/d-none/);
    await expect(page.locator('#toastContainer')).not.toContainText('Operation successful');
  });
});

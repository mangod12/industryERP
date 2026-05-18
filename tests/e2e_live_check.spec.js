// @ts-check
const { test, expect } = require('@playwright/test');

const BASE = 'https://kbsteel-backend-498310931350.asia-south1.run.app';
const FRONTEND = BASE; // same origin serves frontend

test.describe('KBSteel Live Deployment Check', () => {

  test('API /version returns app info', async ({ request }) => {
    const res = await request.get(`${BASE}/version`);
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.app).toBe('KBSteel ERP');
    expect(json.version).toBeTruthy();
  });

  test('API /docs (Swagger) loads', async ({ request }) => {
    const res = await request.get(`${BASE}/docs`);
    expect(res.ok()).toBeTruthy();
    const html = await res.text();
    expect(html).toContain('swagger-ui');
  });

  test('Login page loads', async ({ page }) => {
    await page.goto(`${FRONTEND}/login.html`);
    await expect(page).toHaveTitle(/KBSteel|Kumar|Login/i);
    await expect(page.locator('input[type="text"], input[name="username"], #username')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('Login with admin credentials', async ({ request }) => {
    const res = await request.post(`${BASE}/auth/login`, {
      data: { username: 'admin', password: 'AdminTest2026Kbs' }
    });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.access_token).toBeTruthy();
    expect(json.token_type).toBe('bearer');
  });

  test('Authenticated: enhanced dashboard returns 6 cards', async ({ request }) => {
    const login = await request.post(`${BASE}/auth/login`, {
      data: { username: 'admin', password: 'AdminTest2026Kbs' }
    });
    const { access_token } = await login.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/dashboard/enhanced-summary`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.number_cards).toHaveLength(6);
    expect(json.number_cards[0].label).toBe('Total Stock Value');
  });

  test('Authenticated: reports list returns 8 reports', async ({ request }) => {
    const login = await request.post(`${BASE}/auth/login`, {
      data: { username: 'admin', password: 'AdminTest2026Kbs' }
    });
    const { access_token } = await login.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/reports/`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.data.reports).toHaveLength(8);
  });

  test('Authenticated: stock-balance report has correct structure', async ({ request }) => {
    const login = await request.post(`${BASE}/auth/login`, {
      data: { username: 'admin', password: 'AdminTest2026Kbs' }
    });
    const { access_token } = await login.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/reports/stock-balance`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.data).toHaveProperty('columns');
    expect(json.data).toHaveProperty('data');
    expect(json.data).toHaveProperty('summary');
  });

  test('Authenticated: company settings accessible', async ({ request }) => {
    const login = await request.post(`${BASE}/auth/login`, {
      data: { username: 'admin', password: 'AdminTest2026Kbs' }
    });
    const { access_token } = await login.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/settings/company`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json).toHaveProperty('company_name');
    expect(json).toHaveProperty('company_gstin');
  });

  test('Authenticated: print format returns 404 for nonexistent GRN', async ({ request }) => {
    const login = await request.post(`${BASE}/auth/login`, {
      data: { username: 'admin', password: 'AdminTest2026Kbs' }
    });
    const { access_token } = await login.json();
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/print/grn/99999`, { headers });
    expect(res.status()).toBe(404);
  });

  test('Unauthenticated requests return 401', async ({ request }) => {
    const endpoints = [
      '/dashboard/enhanced-summary',
      '/api/v2/reports/',
      '/api/v2/settings/company',
      '/api/v2/print/grn/1',
    ];
    for (const ep of endpoints) {
      const res = await request.get(`${BASE}${ep}`);
      expect(res.status()).toBe(401);
    }
  });

  test('Dashboard page loads after login', async ({ page }) => {
    // Login via UI
    await page.goto(`${FRONTEND}/login.html`);
    await page.fill('input[type="text"], input[name="username"], #username', 'admin');
    await page.fill('input[type="password"]', 'AdminTest2026Kbs');
    await page.click('button[type="submit"], .btn-primary, #loginBtn');

    // Wait for redirect to dashboard
    await page.waitForURL(/index\.html|\/$/i, { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2000);

    // Check dashboard loaded
    const url = page.url();
    expect(url).toMatch(/index\.html|\/$/i);
  });

  test('System settings page loads', async ({ page }) => {
    // Login first
    await page.goto(`${FRONTEND}/login.html`);
    await page.fill('input[type="text"], input[name="username"], #username', 'admin');
    await page.fill('input[type="password"]', 'AdminTest2026Kbs');
    await page.click('button[type="submit"], .btn-primary, #loginBtn');
    await page.waitForTimeout(2000);

    // Navigate to system settings
    await page.goto(`${FRONTEND}/system-settings.html`);
    await page.waitForTimeout(2000);

    // Check tabs exist
    await expect(page.getByRole('tab', { name: 'Company Profile' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Naming Series' })).toBeVisible();
  });
});

// @ts-check
const { test, expect } = require('@playwright/test');

const BASE = process.env.E2E_BASE_URL || 'http://127.0.0.1:8000';
const FRONTEND = process.env.E2E_FRONTEND_URL || BASE; // same origin serves frontend by default
const USERNAME = process.env.E2E_USERNAME;
const PASSWORD = process.env.E2E_PASSWORD;

async function login(request) {
  test.skip(!USERNAME || !PASSWORD, 'E2E_USERNAME and E2E_PASSWORD are required for authenticated checks');
  const res = await request.post(`${BASE}/auth/login`, {
    data: { username: USERNAME, password: PASSWORD }
  });
  expect(res.ok()).toBeTruthy();
  const json = await res.json();
  expect(json.access_token).toBeTruthy();
  expect(json.token_type).toBe('bearer');
  return json.access_token;
}

async function loginViaUi(page) {
  test.skip(!USERNAME || !PASSWORD, 'E2E_USERNAME and E2E_PASSWORD are required for authenticated checks');
  await page.goto(`${FRONTEND}/login.html`);
  await page.fill('input[type="text"], input[name="username"], #username', USERNAME);
  await page.fill('input[type="password"]', PASSWORD);
  await page.click('button[type="submit"], .btn-primary, #loginBtn');
}

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
    await login(request);
  });

  test('Authenticated: enhanced dashboard returns 6 cards', async ({ request }) => {
    const access_token = await login(request);
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/dashboard/enhanced-summary`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.number_cards).toHaveLength(6);
    expect(json.number_cards[0].label).toBe('Total Stock Value');
  });

  test('Authenticated: reports list returns 8 reports', async ({ request }) => {
    const access_token = await login(request);
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/reports/`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.data.reports).toHaveLength(8);
  });

  test('Authenticated: stock-balance report has correct structure', async ({ request }) => {
    const access_token = await login(request);
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/reports/stock-balance`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json.data).toHaveProperty('columns');
    expect(json.data).toHaveProperty('data');
    expect(json.data).toHaveProperty('summary');
  });

  test('Authenticated: company settings accessible', async ({ request }) => {
    const access_token = await login(request);
    const headers = { Authorization: `Bearer ${access_token}` };

    const res = await request.get(`${BASE}/api/v2/settings/company`, { headers });
    expect(res.ok()).toBeTruthy();
    const json = await res.json();
    expect(json).toHaveProperty('company_name');
    expect(json).toHaveProperty('company_gstin');
  });

  test('Authenticated: print format returns 404 for nonexistent GRN', async ({ request }) => {
    const access_token = await login(request);
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
    await loginViaUi(page);

    // Wait for redirect to dashboard
    await page.waitForURL(/index\.html|\/$/i, { timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(2000);

    // Check dashboard loaded
    const url = page.url();
    expect(url).toMatch(/index\.html|\/$/i);
  });

  test('System settings page loads', async ({ page }) => {
    await loginViaUi(page);
    await page.waitForTimeout(2000);

    // Navigate to system settings
    await page.goto(`${FRONTEND}/system-settings.html`);
    await page.waitForTimeout(2000);

    // Check tabs exist
    await expect(page.getByRole('tab', { name: 'Company Profile' })).toBeVisible();
    await expect(page.getByRole('tab', { name: 'Naming Series' })).toBeVisible();
  });
});

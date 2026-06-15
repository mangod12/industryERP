const fs = require('fs');
const path = require('path');
const { test, expect } = require('@playwright/test');

const USERNAME = process.env.E2E_USERNAME || 'admin';
const PASSWORD = process.env.E2E_PASSWORD || 'Boss1234!'; // pragma: allowlist secret
const screenshotDir = path.resolve(__dirname, '../../docs/screenshots');

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

    const pages = [
      'raw_material.html',
      'materials.html',
      'stock.html',
      'grn.html',
      'dispatch.html',
      'tracking_v2.html',
      'drawings.html',
      'customers.html',
      'scrap.html',
      'reusable.html',
      'queries.html',
      'instructions.html',
      'settings.html'
    ];

    for (const url of pages) {
      await page.goto(`/${url}`);
      await waitForApp(page);

      const unnamedButtons = await page.locator('button:visible').evaluateAll(buttons =>
        buttons
          .filter(button => !button.innerText.trim() && !button.getAttribute('aria-label') && !button.getAttribute('title'))
          .map(button => button.outerHTML.slice(0, 160))
      );
      expect(unnamedButtons, `${url} has unnamed visible controls`).toEqual([]);
      await expect(page.locator('body'), `${url} should not show Invalid Date`).not.toContainText('Invalid Date');
      await expect(page.locator('body'), `${url} should not show NaN`).not.toContainText('NaN');
    }
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
});

import { expect, test } from '@playwright/test';

test('app shell mounts', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.app-shell')).toBeVisible();
  await expect(page.locator('.mode-selector')).toBeVisible();
});

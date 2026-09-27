import { expect, test } from '@playwright/test';

test('reduced motion keeps usable shell', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('.ghost-canvas, canvas').first()).toBeVisible({ timeout: 90_000 });
  await expect(page.locator('.mode-selector')).toBeVisible();
});

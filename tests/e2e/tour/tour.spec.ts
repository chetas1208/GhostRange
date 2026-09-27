import { expect, test } from '@playwright/test';

test.describe('GhostRange product tour', () => {
  test('welcome offers tour and skip', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('ghostrange.tour.completed'));
    await page.reload();
    await expect(page.getByRole('dialog', { name: /Investigate systems/i })).toBeVisible();
    await page.getByRole('button', { name: /Explore on my own/i }).click();
    await expect(page.getByRole('dialog', { name: /Investigate systems/i })).toHaveCount(0);
  });

  test('guided tour starts and shows controlled replay', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('ghostrange.tour.completed'));
    await page.reload();
    await page.getByRole('button', { name: /4-minute tour/i }).click();
    await expect(page.locator('.tour-input-panel')).toBeVisible();
    await expect(page.getByText('CONTROLLED REPLAY')).toBeVisible();
    await page.getByTestId('tour-build').click();
    await expect(page.locator('.tour-callout')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: 'Skip tour' }).click();
  });

  test('keyboard opens command tour action', async ({ page }) => {
    await page.goto('/');
    await page.keyboard.press('Control+KeyK');
    await expect(page.getByTestId('cmd-tour-guided')).toBeVisible();
  });
});

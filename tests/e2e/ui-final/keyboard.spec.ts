import { expect, test } from '@playwright/test';
import { startM20Campaign } from './helpers';

test('keyboard: CommandSurface, Escape, mode tabs', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Control+KeyK');
  await expect(page.getByRole('dialog', { name: 'Command surface' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: 'Command surface' })).toHaveCount(0);

  await startM20Campaign(page);

  const nav = page.getByRole('navigation', { name: 'Primary modes' });
  await nav.locator('button.mode-pill', { hasText: 'EXECUTION' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.mode-selector button.mode-pill.active')).toContainText('EXECUTION');

  await nav.locator('button.mode-pill', { hasText: 'EVIDENCE' }).focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('.mode-selector button.mode-pill.active')).toContainText('EVIDENCE');
});

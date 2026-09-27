import { test, expect } from '@playwright/test';

test.describe('Tactical UI', () => {
  test('three tabs and cost label semantics', async ({ page }) => {
    await page.goto('/?tab=multiverse');
    await expect(page.getByRole('navigation', { name: 'Primary modes' })).toContainText('MULTIVERSE');
    await expect(page.getByRole('navigation', { name: 'Primary modes' })).toContainText('EXECUTION');
    await expect(page.getByRole('navigation', { name: 'Primary modes' })).toContainText('EVIDENCE');
    await page.getByRole('button', { name: 'EXECUTION' }).click();
    await expect(page).toHaveURL(/tab=execution/);
    const cost = page.locator('.cost-indicator');
    await expect(cost).toBeVisible();
    const text = await cost.textContent();
    expect(text).toMatch(/ACCRUED EST\.|SIM EST\.|COST UNKNOWN|ESTIMATE/);
  });
});

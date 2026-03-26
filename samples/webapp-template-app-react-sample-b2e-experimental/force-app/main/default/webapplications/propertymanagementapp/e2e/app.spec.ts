import { test, expect } from '@playwright/test';

test.describe('base-react-app', () => {
  test('home page loads and shows welcome content', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByRole('heading', { name: 'Home' })).toBeVisible();
    await expect(
      page.getByText('Welcome to your React application.')
    ).toBeVisible();
  });

  test('not found route shows 404', async ({ page }) => {
    await page.goto('/non-existent-route');
    await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
    await expect(page.getByText('Page not found')).toBeVisible();
  });
});

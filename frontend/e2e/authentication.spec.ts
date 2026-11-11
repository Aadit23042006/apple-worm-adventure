import { test, expect } from '@playwright/test';

test('registers a player and opens level selection', async ({ page }) => {
  test.setTimeout(60000);

  const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const username = `awa_e2e_${suffix}`;
  const email = `awa.e2e.${suffix}@example.com`;
  const password = 'AwaE2ETest@2026';

  await page.goto('/');

  await page.getByRole('main').getByRole('button', { name: 'Start Adventure' }).click();

  await expect(
    page.getByRole('heading', { name: 'Start your adventure.' })
  ).toBeVisible();

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);

  const registrationPromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/register/') &&
    response.request().method() === 'POST'
  );

  const levelsPromise = page.waitForResponse(response =>
    response.url().includes('/api/levels/') &&
    response.request().method() === 'GET' &&
    response.status() === 200
  );

  await page.getByRole('button', { name: 'Create account' }).click();

  const registration = await registrationPromise;

  expect(registration.status()).toBe(201);

  const registrationData = await registration.json();

  expect(registrationData.token).toBeTruthy();
  expect(registrationData.user.email_verified).toBe(true);

  const levelsResponse = await levelsPromise;
  const levelsBody = await levelsResponse.text();
  expect(
    levelsResponse.status(),
    `GET /api/levels/ returned ${levelsResponse.status()}: ${levelsBody}`
  ).toBe(200);
  const levelsData = JSON.parse(levelsBody);

  expect(Array.isArray(levelsData.levels)).toBe(true);
  expect(levelsData.levels.length).toBeGreaterThan(0);

  expect(
    levelsData.levels.some(
      level => level.number === 1 && level.unlocked === true
    )
  ).toBe(true);

  await expect(
    page.getByRole('heading', { name: 'Choose a level' })
  ).toBeVisible();

  const storedToken = await page.evaluate(
    () => localStorage.getItem('veloop_auth_token')
  );

  expect(storedToken).toBeTruthy();
  expect(storedToken).toBe(registrationData.token);
});


test('restores session, refreshes an invalid access token, logs out, and logs back in', async ({ page }) => {
  test.setTimeout(90000);

  const suffix = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const username = `awa_lifecycle_${suffix}`;
  const email = `awa.lifecycle.${suffix}@example.com`;
  const password = 'AwaLifecycle@2026';

  await page.goto('/');
  await page.getByRole('main').getByRole('button', { name: 'Start Adventure' }).click();

  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);

  const registrationPromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/register/') &&
    response.request().method() === 'POST'
  );

  await page.getByRole('button', { name: 'Create account' }).click();

  const registration = await registrationPromise;
  expect(registration.status()).toBe(201);

  const registrationData = await registration.json();
  expect(registrationData.token).toBeTruthy();
  expect(registrationData.refresh_token).toBeTruthy();

  await expect(
    page.getByRole('heading', { name: 'Choose a level' })
  ).toBeVisible();

  // 1. Reload and verify the existing session is restored.
  const restoreMePromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/me/') &&
    response.request().method() === 'GET' &&
    response.status() === 200
  );

  await page.reload();
  const restoreMe = await restoreMePromise;
  expect(restoreMe.status()).toBe(200);

  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
  await page.getByRole('button', { name: 'Levels' }).click();

  await expect(
    page.getByRole('heading', { name: 'Choose a level' })
  ).toBeVisible();

  // 2. Corrupt only the access token; preserve the valid refresh token.
  await page.evaluate(() => {
    localStorage.setItem('veloop_auth_token', 'invalid-e2e-access-token');
  });

  const refreshPromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/refresh/') &&
    response.request().method() === 'POST'
  );

  const refreshedMePromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/me/') &&
    response.request().method() === 'GET' &&
    response.status() === 200
  );

  await page.reload();

  const refreshResponse = await refreshPromise;
  expect(refreshResponse.status()).toBe(200);

  const refreshedMe = await refreshedMePromise;
  expect(refreshedMe.status()).toBe(200);

  await expect(page.getByRole('button', { name: 'Sign out' })).toBeVisible();
  await page.getByRole('button', { name: 'Levels' }).click();

  await expect(
    page.getByRole('heading', { name: 'Choose a level' })
  ).toBeVisible();

  const refreshedStorage = await page.evaluate(() => ({
    access: localStorage.getItem('veloop_auth_token'),
    refresh: localStorage.getItem('veloop_refresh_token'),
  }));

  expect(refreshedStorage.access).toBeTruthy();
  expect(refreshedStorage.access).not.toBe('invalid-e2e-access-token');
  expect(refreshedStorage.refresh).toBeTruthy();

  await expect(
    page.getByRole('heading', { name: 'Choose a level' })
  ).toBeVisible();

  // 3. Sign out and verify both tokens are cleared.
  await page.getByRole('button', { name: 'Sign out' }).click();

  await expect(
    page.getByRole('button', { name: 'Login' })
  ).toBeVisible();

  const afterLogout = await page.evaluate(() => ({
    access: localStorage.getItem('veloop_auth_token'),
    refresh: localStorage.getItem('veloop_refresh_token'),
  }));

  expect(afterLogout.access).toBeNull();
  expect(afterLogout.refresh).toBeNull();

  // 4. Log in again using the same account.
  await page.getByRole('button', { name: 'Login' }).click();

  await expect(
    page.getByRole('heading', { name: 'Welcome back.' })
  ).toBeVisible();

  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);

  const loginPromise = page.waitForResponse(response =>
    response.url().includes('/api/auth/login/') &&
    response.request().method() === 'POST'
  );

  await page.getByRole('button', { name: 'Log in' }).click();

  const loginResponse = await loginPromise;
  expect(loginResponse.status()).toBe(200);

  await expect(
    page.getByRole('heading', { name: 'Choose a level' })
  ).toBeVisible();

  const loggedInStorage = await page.evaluate(() => ({
    access: localStorage.getItem('veloop_auth_token'),
    refresh: localStorage.getItem('veloop_refresh_token'),
  }));

  expect(loggedInStorage.access).toBeTruthy();
  expect(loggedInStorage.refresh).toBeTruthy();
});

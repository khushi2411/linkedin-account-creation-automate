const fs = require('fs');
const { chromium } = require('playwright');
require('dotenv').config();


(async () => {
  // Launch browser
  const browser = await chromium.launch({ headless: false }); // Set headless to false to see the browser
  const userDataDir = 'data';
  const context = await chromium.launchPersistentContext(userDataDir, {headless: false});

  // Open new page
  const page = await context.newPage();

  // Go to LinkedIn login page
  await page.goto('https://www.linkedin.com/login');

  // Fill in email and password
  await page.fill('#username', process.env.LINKEDIN_EMAIL);
  await page.fill('#password', process.env.LINKEDIN_PASSWORD);

  // Click sign in button
  await page.click('button[type="submit"]');

  // Wait for navigation to complete (optional)
  await page.waitForNavigation();

  // Print the title of the page
  console.log(`Page title is: ${await page.title()}`);

  // Close browser
  // await browser.close();
})();
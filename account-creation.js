const { chromium } = require('playwright');

async function fillLinkedInAdForm() {
  // Launch the browser
  const userDataDir = "data";
  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
  });
  
  // Function to fill out the form in a page
  async function processForm(page, accountNumber) {
    try {
      // Generate dynamic account name
      const accountName = `Account ${accountNumber}`;
      
      // Navigate to LinkedIn - you'll need to modify this URL to the actual form page
      await page.goto("https://www.linkedin.com/campaignmanager/accounts?shouldShowNotificationPanelOnRender=true"      );
      console.log('Navigated to LinkedIn Campaign Manager');
      
      // Click on the dismiss button using a more robust selector
      await page.waitForSelector('button[type="button"] span:has-text("Dismiss")');
      await page.click('button[type="button"] span:has-text("Dismiss")');
      console.log('Dismissed initial popup');
      
   // // create account button
   await page.waitForSelector("#ember32");
   await page.click("#ember32");
      
      // Fill out the account name with dynamic number
      await page.fill('#account-name', accountName);
      console.log(`Filled account name: ${accountName}`);
      
      // Select currency (example: USD)
      await page.selectOption("#account-currency", "INR");
      
      // Associate with LinkedIn Page
      // Click on the input field to focus it
      await page.click("#account-reference");
      await page.fill("#account-reference", "Canvas homes");
      await page.waitForSelector(".company-typeahead--result-item-wrapper");
      await page.click("text=Canvas Homes");
      
      // Check the agreement checkbox
      await page.check('#legal-terms-of-service-disclaimer-checkbox');
      
      // Click the Save button
      await page.click('button[form="account-form"][type="submit"]');
      
      // Wait for navigation to complete
      await page.waitForTimeout(3000);
      
      // Get the current URL
      const currentUrl = page.url();
      
      // Check if we're on the campaign groups page and redirect if needed
      if (currentUrl.includes('/campaign-groups')) {
        // Extract the account ID from the URL
        const accountId = currentUrl.match(/\/accounts\/(\d+)\/campaign-groups/)[1];
        
        // Navigate to the billing page
        await page.goto(`https://www.linkedin.com/campaignmanager/accounts/${accountId}/billing`);
        
        // Wait for the billing page to load
        await page.waitForLoadState('networkidle');
        
        console.log(`Successfully redirected to billing page for account ${accountId}`);
      }
      
      // Wait for the "Add payment details" button to be visible
      await page.waitForSelector('button[aria-label="Add payment details"]');
      
      // Click on the "Add payment details" button
      await page.waitForSelector('button[aria-label="Add payment details"]');
      await page.click('button[aria-label="Add payment details"]');
    
      // billing form STEP: 1
      // Wait for the business information form to appear and load completely
      await page.waitForSelector('h2:has-text("Business information")');
      await page.waitForTimeout(1000); // Give the form a moment to fully render
    
      // await page.waitForSelector('label:has-text("Business name") + input');
      // await page.fill('label:has-text("Business name") + input', 'Canvas Homes');
      // console.log('Filled Business name');
    
      await page.selectOption(
        '[data-test-address-ui__field="country"] select',
        "IN"
      );
      console.log("Selected Country: India");
    
      // Wait a moment for any country-dependent fields to update
      // await page.waitForTimeout(1000);
    
      // Fill Address line 1 using data-test attributes
      await page.fill('[data-test-address-ui__field="line1"] input', "HSR Layout");
      console.log("Filled Address line 1");
    
      // Fill City using data-test attributes
      await page.fill('[data-test-address-ui__field="city"] input', "Bengaluru");
      console.log("Filled City");
    
      // Select State - now we know Karnataka is a direct option
      await page.selectOption(
        '[data-test-address-ui__field="geographicArea"] select',
        "Karnataka"
      );
      console.log("Selected State: Karnataka");
    
      // Fill ZIP code using data-test attributes
      await page.fill('[data-test-address-ui__field="postalCode"] input', "560102");
      console.log("Filled ZIP code");
    
      await page.waitForSelector(
        '[data-test-customer-verification-onboarding-field-set__business-typeahead=""] input[role="combobox"]'
      );
      await page.fill(
        '[data-test-customer-verification-onboarding-field-set__business-typeahead=""] input[role="combobox"]',
        "Canvas Homes"
      );
      console.log("Filled Business name");
    
      // Click Save and continue button
      await page.click('button:has-text("Save and continue")');
     
      
      // Wait for the payment details form to appear
      await page.waitForSelector('.credit-card-panel__form');
      await page.waitForTimeout(1000); // Wait for the form to fully load
      
      // Fill First Name using data-test attributes
      await page.fill('[data-test-name="FIRST_NAME"] input', 'Amit');
      console.log('Filled First name');
      
      // Fill Last Name using data-test attributes
      await page.fill('[data-test-name="LAST_NAME"] input', 'Daga');
      console.log('Filled Last name');
      
      // Select Country
      await page.selectOption('#COUNTRY_CODE', 'IN');
      console.log('Selected Country: India for billing');
      
      // Fill Postal Code
      await page.fill('[data-test-name="POSTAL_CODE"] input', '560102');
      console.log('Filled Postal code');
      
      console.log('Credit card form has been filled (except for the secure credit card fields)');
      console.log(`Please manually enter credit card details for ${accountName}`);
      
      // Wait for 20 seconds to allow manual intervention
      await page.waitForTimeout(20000);
      console.log(`Process completed for ${accountName}`);
      
      return true;
    } catch (error) {
      console.error(`Error during form filling process for account ${accountNumber}:`, error);
      
      // Capture a screenshot on error for debugging
      await page.screenshot({ path: `error-screenshot-account${accountNumber}-${Date.now()}.png` });
      console.log(`Screenshot saved as error-screenshot-account${accountNumber}-${Date.now()}.png`);
      
      return false;
    }
  }
  
  try {
    // Start account number from 15
    let accountNumber = 15;
    const maxAccounts = 20; // Process accounts 15 through 20
    
    while (accountNumber <= maxAccounts) {
      console.log(`Starting process for Account ${accountNumber}`);
      
      // Create a new page
      const page = await context.newPage();
      
      // Process the form on this page with the current account number
      await processForm(page, accountNumber);
      
      // Close the page when done
      await page.close();
      console.log(`Closed page for Account ${accountNumber}`);
      
      // Increment account number for next iteration
      accountNumber++;
      
      // If we've reached the maximum, break out of the loop
      if (accountNumber > maxAccounts) {
        console.log('Reached maximum number of accounts to process');
        break;
      }
      
      console.log('Creating new page to repeat the process for the next account...');
    }
  } catch (error) {
    console.error('Error in main process:', error);
  } finally {
    // Close the browser
    await browser.close();
    console.log('Browser closed');
  }
}

// Run the script
fillLinkedInAdForm();
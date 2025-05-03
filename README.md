# LinkedIn Automation Project

This project contains two main scripts:

- `linkedin_login.js`: This script automates the login process to LinkedIn using Playwright. It reads the LinkedIn email and password from the `.env` file.
- `account-creation.js`: This script automates the creation of ad accounts in LinkedIn Campaign Manager. It navigates to the campaign manager, fills out the account creation form, and adds billing details.

## Prerequisites

- Node.js and npm installed
- Playwright installed (`npm install playwright`)
- `.env` file with `LINKEDIN_EMAIL` and `LINKEDIN_PASSWORD` environment variables set
- A "data" directory for storing browser session data

## Setup

1.  Install dependencies:

    ```bash
    npm install playwright dotenv
    npx playwright install
    ```
2.  Create a `.env` file in the project root with your LinkedIn credentials:

    ```
    LINKEDIN_EMAIL=your_email@example.com
    LINKEDIN_PASSWORD=your_password
    ```
3.  Create a "data" directory in the project root. This directory will be used to store browser session data.

## Usage

1.  Run `linkedin_login.js` to log in to LinkedIn:

    ```bash
    node linkedin_login.js
    ```
2.  Run `account-creation.js` to create ad accounts:

    ```bash
    node account-creation.js
    ```

    **Note:** The `account-creation.js` script requires manual intervention to fill in the credit card details. The script will pause for 20 seconds to allow you to manually enter the details.

## Details

The `account-creation.js` script creates multiple ad accounts, starting from account number 15 up to 20. It fills in the business information and billing details, but requires manual input for the credit card information due to security reasons.

The `linkedin_login.js` script logs into LinkedIn using the provided credentials from the `.env` file.

## Disclaimer

Use these scripts at your own risk. Automating LinkedIn processes may violate LinkedIn's terms of service.
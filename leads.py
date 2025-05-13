import os
import csv
import time
import json
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from dotenv import load_dotenv

# Load environment variables from the specific path
ENV_PATH = r"C:\Users\khush\linkedin-account-creation-automate\.env"
load_dotenv(ENV_PATH)

# LinkedIn credentials directly from .env file
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")          # yashika@truestate.in
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")    # TruEstate@01

# Define the path for persistent user data
USER_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "linkedin_user_data")

# Output files
ACCOUNT_IDS_FILE = "linkedin_account_ids.csv"
DOWNLOADS_DIR    = "downloads"
COMBINED_CSV_FILE = "all_leads.csv"  # New file for combined leads

# Timeout settings
PAGE_LOAD_TIMEOUT  = 60_000   # 60 s
NAVIGATION_TIMEOUT = 60_000
ELEMENT_TIMEOUT    = 15_000

# ──────────────────────────────────────────────────────────────
async def main():
    # Create folders if they don't exist
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    os.makedirs(USER_DATA_DIR, exist_ok=True)

    async with async_playwright() as p:
        print(f"Using persistent browser context at: {USER_DATA_DIR}")
        try:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,                 # set True in prod
                accept_downloads=True,
                viewport={'width': 1280, 'height': 800},
                timeout=PAGE_LOAD_TIMEOUT
            )
            context.set_default_navigation_timeout(NAVIGATION_TIMEOUT)

            page = await context.new_page()

            # ── open Campaign Manager
            print("Navigating to LinkedIn...")
            await page.goto("https://www.linkedin.com/campaignmanager/accounts",
                            timeout=PAGE_LOAD_TIMEOUT)
            print(f"Current URL after navigation: {page.url}")

            # ── login if needed
            if "/login" in page.url:
                print("Not logged in. Performing login process…")
                await login_to_linkedin(page)
                print("Navigating to Campaign Manager accounts page…")
                await page.goto("https://www.linkedin.com/campaignmanager/accounts",
                                timeout=PAGE_LOAD_TIMEOUT)
            else:
                print("Already logged in, using existing session")

            # let DOM settle
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10_000)
                await asyncio.sleep(3)
            except PlaywrightTimeoutError:
                print("Warning: DOMContentLoaded timed-out, continuing")

            # ── scrape account IDs
            print("Extracting account IDs…")
            account_ids = await extract_account_ids(page)
            print(f"Saving {len(account_ids)} IDs to {ACCOUNT_IDS_FILE}…")
            save_account_ids_to_csv(account_ids, ACCOUNT_IDS_FILE)

            # ── process each account
            print("Processing lead-gen forms for each account…")
            
            # Create/reset the combined CSV file with headers and JSON file
            initialize_combined_csv()
            
            for account_id in account_ids:
                await process_account_leadgen_forms(page, account_id)
                
            print(f"All lead data has been consolidated in {COMBINED_CSV_FILE} and {JSON_OUTPUT_FILE}")
            await context.close()

        except Exception as e:
            print(f"Failed: {e}")

    print("Script execution completed.")

# ──────────────────────────────────────────────────────────────
async def login_to_linkedin(page):
    """Log in to LinkedIn with credentials from .env file"""
    await page.goto("https://www.linkedin.com/login", timeout=PAGE_LOAD_TIMEOUT)
    await page.wait_for_selector("#username", state="visible", timeout=ELEMENT_TIMEOUT)
    await page.fill("#username", LINKEDIN_EMAIL)
    await page.fill("#password", LINKEDIN_PASSWORD)
    print("Filled login form, attempting to log in…")
    await page.click("button[type='submit']")

    try:
        await page.wait_for_load_state("domcontentloaded", timeout=ELEMENT_TIMEOUT)
        await asyncio.sleep(3)
    except PlaywrightTimeoutError:
        print("Warning: post-login load timeout, continuing")

    # security checkpoint?
    if "checkpoint" in page.url:
        print("Security verification required — complete it manually.")
        start = time.time()
        while "checkpoint" in page.url and time.time() - start < 300:
            await asyncio.sleep(10)
        if "checkpoint" in page.url:
            raise RuntimeError("Security verification timed-out.")

    print("Login completed.")

# ──────────────────────────────────────────────────────────────
async def extract_account_ids(page):
    """Extract all account IDs from Campaign Manager accounts page using improved pagination"""
    account_ids, page_no = [], 1
    
    while True:
        print(f"Processing page {page_no}…")
        try:
            # Try multiple selectors to find account IDs
            selectors = [
                "div.u-layout__display-table.mt1.reporting-table__status-simplification-item-id",
                "div[class*='status-simplification-item-id']",
                "div[class*='account-id']",
                "div:contains('Account ID:')"
            ]
            
            # Try each selector until one works
            element_found = False
            for selector in selectors:
                try:
                    await page.wait_for_selector(selector, timeout=10_000)
                    print(f"Found account ID elements using selector: {selector}")
                    element_found = True
                    
                    # Get all account ID elements
                    elements = await page.query_selector_all(selector)
                    
                    if elements:
                        for el in elements:
                            txt = await el.inner_text()
                            if "Account ID:" in txt:
                                account_id = txt.split("Account ID:")[-1].strip()
                                if account_id not in account_ids:  # Avoid duplicates
                                    account_ids.append(account_id)
                                    print(f"Found Account ID: {account_id}")
                    
                    break  # Break out of selector loop if one worked
                except PlaywrightTimeoutError:
                    continue
                except Exception as e:
                    print(f"Error with selector {selector}: {e}")
                    continue
            
            if not element_found:
                # Alternative approach: extract all text and find account IDs
                print("Could not find account ID elements with selectors, trying text extraction...")
                try:
                    page_text = await page.evaluate('() => document.body.innerText')
                    import re
                    id_matches = re.findall(r"Account ID:\s*(\d+)", page_text)
                    if id_matches:
                        for account_id in id_matches:
                            if account_id not in account_ids:  # Avoid duplicates
                                account_ids.append(account_id)
                                print(f"Found Account ID from text: {account_id}")
                except Exception as e:
                    print(f"Error extracting text: {e}")
            
            # Look for next page button - try multiple selectors
            next_btn_selectors = [
                "button.ember-view:has-text('Next'):not([disabled])",
                "button:has-text('Next'):not([disabled])",
                "li.pagination__next-button:not(.disabled) button",
                "[aria-label='Next page']:not([disabled])"
            ]
            
            next_btn = None
            for selector in next_btn_selectors:
                try:
                    next_btn = await page.query_selector(selector)
                    if next_btn:
                        print(f"Found next button with selector: {selector}")
                        break
                except Exception:
                    continue
            
            if not next_btn:
                print("No more pages to process.")
                break
                
            # Wait to see if the button is clickable
            try:
                await next_btn.wait_for_element_state("stable", timeout=5000)
                await next_btn.click()
                print(f"Clicked next button, moving to page {page_no + 1}")
                await page.wait_for_load_state("domcontentloaded", timeout=ELEMENT_TIMEOUT)
                await asyncio.sleep(3)  # Give the page time to update
                page_no += 1
            except Exception as e:
                print(f"Error navigating to next page: {e}")
                break

        except Exception as e:
            print(f"Error on page {page_no}: {e}")
            break

    print(f"Total account IDs found: {len(account_ids)}")
    return account_ids

# ──────────────────────────────────────────────────────────────
def save_account_ids_to_csv(ids, fname):
    with open(fname, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Account ID"])
        writer.writerows([[i] for i in ids])
    print(f"Account IDs saved to {fname}")

# ──────────────────────────────────────────────────────────────
# Define JSON output file
JSON_OUTPUT_FILE = "leads.json"

def initialize_combined_csv():
    """Create the combined CSV file with headers"""
    # We'll populate with headers when we append the first file
    if os.path.exists(COMBINED_CSV_FILE):
        os.remove(COMBINED_CSV_FILE)
    print(f"Initialized combined CSV file: {COMBINED_CSV_FILE}")
    
    # Initialize JSON file
    if os.path.exists(JSON_OUTPUT_FILE):
        os.remove(JSON_OUTPUT_FILE)
    with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('[]')  # Empty JSON array
    print(f"Initialized JSON output file: {JSON_OUTPUT_FILE}")

# ──────────────────────────────────────────────────────────────
def append_csv_to_combined(source_file, account_id):
    """Append a downloaded CSV file to the combined CSV and update JSON"""
    if not os.path.exists(source_file):
        print(f"Warning: Source file {source_file} does not exist!")
        return
    
    try:
        # Read source file
        with open(source_file, 'r', newline='', encoding='utf-8') as src_file:
            reader = csv.reader(src_file)
            headers = next(reader)  # Get headers
            rows = list(reader)     # Get data rows
        
        # Add account ID column if not already present
        if 'Account ID' not in headers:
            headers.append('Account ID')
        account_id_col_index = headers.index('Account ID')
        
        # Add account ID to each row
        for row in rows:
            # Extend row if needed
            while len(row) <= account_id_col_index:
                row.append('')
            row[account_id_col_index] = account_id
        
        # Check if combined file exists and has headers
        combined_file_exists = os.path.exists(COMBINED_CSV_FILE) and os.path.getsize(COMBINED_CSV_FILE) > 0
        
        # Write to combined file
        with open(COMBINED_CSV_FILE, 'a', newline='', encoding='utf-8') as dest_file:
            writer = csv.writer(dest_file)
            
            # Write headers if this is the first file
            if not combined_file_exists:
                writer.writerow(headers)
            
            # Write data rows
            writer.writerows(rows)
        
        # Also update the JSON file with the new data
        update_json_with_leads(headers, rows, account_id)
        
        print(f"Appended {len(rows)} leads from account {account_id} to combined CSV and JSON")
    except Exception as e:
        print(f"Error appending data to files: {e}")

# ──────────────────────────────────────────────────────────────
def update_json_with_leads(headers, rows, account_id):
    """Update the JSON file with new leads data using the desired format"""
    try:
        # Read existing JSON data
        with open(JSON_OUTPUT_FILE, 'r', encoding='utf-8') as f:
            json_data = []
            try:
                file_content = f.read().strip()
                if file_content:  # If file is not empty
                    json_data = json.loads(file_content)
            except json.JSONDecodeError:
                print("Warning: JSON file was empty or invalid, starting with empty list")
                json_data = []
        
        # Convert each row to a JSON object with the specific format
        for row in rows:
            # Create a dict from CSV headers and values
            csv_data = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    csv_data[header] = row[i]
                else:
                    csv_data[header] = ""
            
            # Generate a unique ID
            unique_id = f"{account_id}_{int(time.time())}_{len(json_data)}"
            
            # Current timestamp
            current_time = int(time.time())
            
            phone_number = ""
            for possible_phone in ["Phone number", "Phone Number", "phone", "phoneNumber", "Mobile", "mobile"]:
                if possible_phone in csv_data and csv_data[possible_phone]:
                    phone_number = csv_data[possible_phone].strip().replace(" ", "")
                    break
                
            project_name = ""
            for possible_form in ["form_name", "Form Name", "Lead Gen Form", "Campaign Name", "campaign_name"]:
                if possible_form in csv_data and csv_data[possible_form]:
                    project_name = csv_data[possible_form].strip()
                    break
            
            # Create lead object with the desired format
            lead_data = {
                "id": unique_id,
                "projectName":project_name,
                "subSource": "LinkedIn",
                "added": current_time,
                "phonenumber": phone_number,
                "source": "Social Media",
                "mode": "Online",
                "customerType": "Premium",
                "tag": "Fresh",
                "email": csv_data.get("Email address", ""),
                "truestateTag": False,
                "stage": "Unqualified",
                "name": f"{csv_data.get('First name', '')} {csv_data.get('Last name', '')}".strip(),
                "location": csv_data.get("City", ""),
                "status": "Customer",
                "tasks": [
                    {
                        "actionType": "Call",
                        "schedule": current_time + 86400,  # Schedule for tomorrow
                        "agent": "yashika@truestate.in",
                        "taskName": "Call",
                        "type": "Customer",
                        "timestamp": current_time,
                        "objectID": f"{current_time}-{unique_id[:4]}",
                    }
                ],
                "currentAgent": "yashika@truestate.in",
                "lastModified": current_time
            }
            
            # Add any campaign or form specific data
            if "Campaign Name" in csv_data and csv_data["Campaign Name"]:
                lead_data["projectName"] = csv_data["Campaign Name"]
                
            if "Lead Gen Form" in csv_data and csv_data["Lead Gen Form"]:
                lead_data["leadGenForm"] = csv_data["Lead Gen Form"]
                
            # Add the LinkedIn Account ID
            lead_data["linkedinAccountId"] = account_id
            
            # Store the original CSV data as a nested object if needed
            # lead_data["originalData"] = csv_data
            
            json_data.append(lead_data)
        
        # Write back to JSON file
        with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2)
            
        print(f"Updated JSON file with {len(rows)} new leads in the desired format")
    except Exception as e:
        print(f"Error updating JSON file: {e}")

# ──────────────────────────────────────────────────────────────
async def process_account_leadgen_forms(page, account_id):
    """Open the lead-gen forms page, tick 'select-all', download leads CSV."""
    try:
        print(f"\n── Processing Account {account_id}")
        leadgen_url = f"https://www.linkedin.com/campaignmanager/accounts/{account_id}/leadgen-forms"
        await page.goto(leadgen_url, timeout=PAGE_LOAD_TIMEOUT)
        await page.wait_for_load_state("domcontentloaded", timeout=ELEMENT_TIMEOUT)
        await asyncio.sleep(3)

        # Try to click the "Select all" checkbox
        checkbox_clicked = False
        try:
            # 1️⃣ Use iframe if the table is embedded in one
            ctx = page
            for fr in page.frames:
                if "leadgen-forms" in fr.url:
                    ctx = fr
                    break

            # 2️⃣ The <label> is the visible, clickable element
            await ctx.wait_for_selector("label[for^='select-all-']", timeout=10_000)
            lbl = ctx.locator("label[for^='select-all-']")
            await lbl.scroll_into_view_if_needed()
            await lbl.click()
            checkbox_clicked = True
            print("✓  Select-all label clicked")

            # 3️⃣ Ensure the hidden checkbox is checked
            chk = ctx.locator("input[id^='select-all-']")
            if not await chk.is_checked():
                await chk.check(force=True)

        except PlaywrightTimeoutError:
            print("⚠️  Select-all label not found in time.")
        except Exception as e:
            print(f"⚠️  Error clicking Select-all: {e}")

        if not checkbox_clicked:
            print("❌  Could not click 'Select all' — skipping download.")
            return

        await asyncio.sleep(2)  # let UI update

        # Download button selectors
        download_btn_selectors = [
            "button[data-test-forms-management-download]",
            "button[data-test-forms-management__forms-management-download-button]",
            "button:has-text('Download leads')"
        ]
        
        download_clicked = False
        for sel in download_btn_selectors:
            try:
                print(f"Trying download button selector: {sel}")
                btn = await ctx.wait_for_selector(sel, timeout=5_000, state="visible")
                
                if await btn.get_attribute("disabled"):
                    print("Button disabled – maybe no leads.")
                    return
                
                await btn.click()
                print("Initial download button clicked")
                download_clicked = True
                break
            except PlaywrightTimeoutError:
                print(f"Selector not found: {sel}")
                continue
            except Exception as e:
                print(f"Error with selector {sel}: {e}")
                continue
        
        if not download_clicked:
            print("Could not click initial download button")
            return
        
        # Wait for the second download button in the dialog
        await asyncio.sleep(2)  # Wait for dialog to appear
        
        # Try multiple selectors for the second download button
        second_btn_selectors = [
            "button[data-test-download-leads__download-button]",
            "button.ember-view.button:has-text('Download')",
            "button:has-text('Download'):not([disabled])"
        ]
        
        second_download_clicked = False
        for sel in second_btn_selectors:
            try:
                print(f"Trying second download button selector: {sel}")
                second_btn = await page.wait_for_selector(sel, timeout=10_000, state="visible")
                
                async with page.expect_download() as dl_wait:
                    await second_btn.click()
                    print("Second download button clicked")
                
                # Wait for download to complete
                download = await asyncio.wait_for(dl_wait.value, 60.0)
                temp_path = os.path.join(DOWNLOADS_DIR, f"leads_{account_id}.csv")
                await download.save_as(temp_path)
                print(f"📥  Saved to {temp_path}")
                
                # Append to combined CSV
                append_csv_to_combined(temp_path, account_id)
                
                second_download_clicked = True
                break
            
            except PlaywrightTimeoutError:
                print(f"Second download button selector not found: {sel}")
                continue
            except Exception as e:
                print(f"Error with second download button {sel}: {e}")
                continue
        
        if not second_download_clicked:
            print("Could not complete download process")
        
        await asyncio.sleep(5)  # polite delay

    except Exception as e:
        print(f"Error processing account {account_id}: {e}")

# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(main())
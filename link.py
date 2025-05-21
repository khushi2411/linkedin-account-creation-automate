import json, os, re
from datetime import datetime

# -------------------------------------------------
# 1. PATHS
# -------------------------------------------------
BASE_DIR   = r"C:\Users\khush\Linkedn-account-2"
COMBINED   = os.path.join(BASE_DIR, "combined-leads.json")
NEW_USERS  = os.path.join(BASE_DIR, "new_users.json")
UNIQUE_OUT = os.path.join(BASE_DIR, "unique_leads.json")   # <- NEW

# -------------------------------------------------
# 2. Util – normalise phone to last 10 digits
# -------------------------------------------------
def norm(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    return digits[-10:]          # "" if <10 digits

# -------------------------------------------------
# 3. Load files
# -------------------------------------------------
with open(COMBINED,  "r", encoding="utf-8") as f:
    combined_data = json.load(f)

with open(NEW_USERS, "r", encoding="utf-8") as f:
    new_users_data = json.load(f)

# if unique file already exists, load it so we append instead of overwrite
if os.path.exists(UNIQUE_OUT):
    with open(UNIQUE_OUT, "r", encoding="utf-8") as f:
        unique_data = json.load(f)
else:
    unique_data = []

# -------------------------------------------------
# 4. Index phones already present in *either* file
# -------------------------------------------------
existing_phones = {norm(u.get("phonenumber", "")) for u in new_users_data}
existing_phones |= {norm(u.get("phonenumber", "")) for u in unique_data}

# -------------------------------------------------
# 5. Collect brand-new leads
# -------------------------------------------------
fresh = []
for lead in combined_data:
    phone_norm = norm(lead.get("phonenumber", ""))
    if not phone_norm:
        continue
    if phone_norm in existing_phones:
        continue
    fresh.append(lead)
    existing_phones.add(phone_norm)

print(f"✅  {len(fresh)} unique LinkedIn leads identified")

if not fresh:
    print("Nothing new to write. All done!")
    quit()

# -------------------------------------------------
# 6. Append to unique_leads.json (create if needed)
# -------------------------------------------------
unique_data.extend(fresh)

with open(UNIQUE_OUT, "w", encoding="utf-8") as f:
    json.dump(unique_data, f, indent=2, ensure_ascii=False)

print(f"📄  unique leads written → {UNIQUE_OUT} (total now {len(unique_data)})")

# -------------------------------------------------
# 7. (Optional) backup new_users.json for safety – but DO NOT modify it
# -------------------------------------------------
ts = datetime.now().strftime("%Y%m%d-%H%M%S")
backup_path = f"{NEW_USERS}.{ts}.bak"
os.rename(NEW_USERS, backup_path)
print(f"🗃️  Backup of new_users.json saved → {backup_path}")

# restore the original file name without changes
with open(backup_path, "r", encoding="utf-8") as src, \
     open(NEW_USERS, "w", encoding="utf-8") as dst:
    dst.write(src.read())

print("🎉  Script finished. new_users.json left unchanged.")

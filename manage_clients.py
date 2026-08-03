import csv
import os

from get_matrix import geocode_address, build_matrices

CLIENTS_FILE = "generator_clients.csv"
EDITABLE_FIELDS = ["Phone", "Address", "Plan", "Size", "Type", "Model", "Serial"]
# Home is used as the fixed route start/end point elsewhere in the codebase.
PROTECTED_NAMES = {"Home"}

# Contract tiers, in the order the CSV should be grouped by.
VALID_PLANS = ("Platinum", "Gold", "Silver", "no")
PLAN_ORDER = {plan: i for i, plan in enumerate(VALID_PLANS)}


def normalize_plan(value):
    """Validate a plan against VALID_PLANS, title-cased except for 'no'."""
    value = value.strip()
    if not value:
        return None
    if value.lower() == "no":
        return "no"
    titled = value.title()
    return titled if titled in VALID_PLANS[:-1] else None


def prompt_plan(current=""):
    while True:
        value = prompt(f"Plan ({', '.join(VALID_PLANS)})", current)
        normalized = normalize_plan(value)
        if normalized:
            return normalized
        print(f"  Plan must be one of: {', '.join(VALID_PLANS)}")


def plan_sort_key(row):
    plan = (row.get('Plan') or '').strip()
    return (PLAN_ORDER.get(plan, len(PLAN_ORDER)), row.get('Name', '').strip().lower())


def load_clients():
    with open(CLIENTS_FILE, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def save_clients(fieldnames, rows):
    rows.sort(key=plan_sort_key)
    with open(CLIENTS_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def prompt(label, default=""):
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value if value else default


def find_by_name(rows, name):
    for row in rows:
        if row['Name'].strip().lower() == name.strip().lower():
            return row
    return None


def geocode_with_feedback(address):
    print("  Looking up coordinates...")
    result = geocode_address(address)
    if result:
        lat, lon = result
        print(f"  Found: {lat}, {lon}")
        return str(lat), str(lon)

    print("  Could not automatically find coordinates for that address.")
    print("  In Google Maps, right-click the location and click the lat/long shown at the top of")
    print("  the menu - that copies it to your clipboard.")
    manual = input("  Paste the coordinates here, or press Enter to leave blank: ").strip()
    if manual and manual.count(",") == 1:
        lat_str, lon_str = (part.strip() for part in manual.split(","))
        try:
            float(lat_str)
            float(lon_str)
            return lat_str, lon_str
        except ValueError:
            pass
        print("  Could not read that as coordinates.")
    print("  Leaving coordinates blank - run get_matrix.py to retry automatically.")
    return "", ""


def update_matrices(output_dir='.'):
    print("Updating distance and duration matrices...")
    try:
        build_matrices(CLIENTS_FILE, output_dir=output_dir)
        print("Matrices updated.\n")
    except Exception as e:
        print(f"Could not update the matrices automatically ({e}). Run get_matrix.py manually.\n")


def list_clients(rows):
    if not rows:
        print("\nNo clients found.\n")
        return
    print(f"\n{'#':<4}{'Name':<28}{'Plan':<12}{'Address'}")
    print("-" * 90)
    for i, row in enumerate(rows, start=1):
        print(f"{i:<4}{row['Name'][:26]:<28}{(row.get('Plan') or ''):<12}{row['Address']}")
    print()


def select_client(rows, action):
    list_clients(rows)
    if not rows:
        return None
    choice = input(f"Enter the # of the client to {action} (or press Enter to cancel): ").strip()
    if not choice:
        print("Cancelled.\n")
        return None
    if not choice.isdigit() or not (1 <= int(choice) <= len(rows)):
        print("Invalid selection.\n")
        return None
    return rows[int(choice) - 1]


def add_client(fieldnames, rows):
    print("\n-- Add Client --")
    name = input("Name: ").strip()
    if not name:
        print("Name is required. Cancelled.\n")
        return
    if find_by_name(rows, name):
        print(f"A client named '{name}' already exists. Cancelled.\n")
        return

    row = {field: "" for field in fieldnames}
    row['Name'] = name
    row['Phone'] = prompt("Phone")
    row['Address'] = prompt("Address")
    row['Plan'] = prompt_plan()
    row['Size'] = prompt("Generator size")
    row['Type'] = prompt("Generator type")
    row['Model'] = prompt("Model")
    row['Serial'] = prompt("Serial")

    if row['Address']:
        row['Latitude'], row['Longitude'] = geocode_with_feedback(row['Address'])

    rows.append(row)
    save_clients(fieldnames, rows)
    print(f"Added {name}.\n")
    update_matrices()


def edit_client(fieldnames, rows):
    print("\n-- Edit Client --")
    row = select_client(rows, "edit")
    if row is None:
        return

    print(f"Editing {row['Name']} - press Enter to keep the current value.\n")

    old_name = row['Name']
    new_name = prompt("Name", old_name)
    if new_name != old_name:
        if find_by_name([r for r in rows if r is not row], new_name):
            print(f"A client named '{new_name}' already exists. Cancelled.\n")
            return
        if old_name in PROTECTED_NAMES:
            confirm = input(
                f"'{old_name}' is used as a route start/end point elsewhere in the app. "
                f"Renaming it will break routing unless main.py is updated too. Continue? (y/n): "
            ).strip().lower()
            if confirm != 'y':
                print("Cancelled.\n")
                return
    row['Name'] = new_name

    old_address = row['Address']
    for field in EDITABLE_FIELDS:
        if field == "Plan":
            row[field] = prompt_plan(row.get(field, ''))
        else:
            row[field] = prompt(field, row.get(field, ''))

    if row['Address'] != old_address:
        row['Latitude'], row['Longitude'] = geocode_with_feedback(row['Address'])

    save_clients(fieldnames, rows)
    print(f"Saved changes to {row['Name']}.\n")
    update_matrices()


def remove_client(fieldnames, rows):
    print("\n-- Remove Client --")
    row = select_client(rows, "remove")
    if row is None:
        return

    if row['Name'] in PROTECTED_NAMES:
        confirm = input(
            f"'{row['Name']}' is used as a route start/end point elsewhere in the app. "
            f"Removing it will break routing. Type the name again to confirm removal: "
        ).strip()
        if confirm != row['Name']:
            print("Cancelled.\n")
            return

    confirm = input(f"Remove {row['Name']} ({row['Address']})? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.\n")
        return

    rows.remove(row)
    save_clients(fieldnames, rows)
    print(f"Removed {row['Name']}.\n")
    update_matrices()


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)) or ".")
    fieldnames, rows = load_clients()

    while True:
        print("=" * 40)
        print("Generator Client Manager")
        print("=" * 40)
        print("1. List clients")
        print("2. Add client")
        print("3. Edit client")
        print("4. Remove client")
        print("5. Exit")
        choice = input("Choose an option (1-5): ").strip()

        if choice == "1":
            list_clients(rows)
        elif choice == "2":
            add_client(fieldnames, rows)
        elif choice == "3":
            edit_client(fieldnames, rows)
        elif choice == "4":
            remove_client(fieldnames, rows)
        elif choice == "5":
            print("Goodbye.")
            break
        else:
            print("Invalid option.\n")


if __name__ == "__main__":
    main()

import csv
import os
import requests

CENSUS_GEOCODER_URL = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"


def geocode_address(address):
    """Look up (latitude, longitude) for a US address via the free Census geocoder."""
    try:
        response = requests.get(CENSUS_GEOCODER_URL, params={
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        }, timeout=10)
        response.raise_for_status()
        matches = response.json().get("result", {}).get("addressMatches", [])
    except (requests.RequestException, ValueError):
        return None
    if not matches:
        return None
    coords = matches[0]["coordinates"]
    return coords["y"], coords["x"]  # (latitude, longitude)


def fill_missing_coordinates(file_path):
    """Geocode any row missing Latitude/Longitude and write the results back to the CSV."""
    with open(file_path, mode='r', encoding='utf-8', newline='') as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames
        rows = list(reader)

    updated = False
    for row in rows:
        if row.get('Address') and not (row.get('Latitude') and row.get('Longitude')):
            result = geocode_address(row['Address'])
            if result:
                row['Latitude'], row['Longitude'] = result
                updated = True
                print(f"Geocoded {row['Name']}: {result[0]}, {result[1]}")
            else:
                print(f"Could not geocode {row['Name']!r} ({row['Address']!r}) - add Latitude/Longitude manually.")

    if updated:
        with open(file_path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)


def get_matrix(coordinates, type="distance", timeout=15): # duration or distance
    # Convert coordinates to OSRM API format
    coordinates_str = ';'.join([f"{lon},{lat}" for lon, lat in coordinates])

    # Construct the OSRM API request URL
    url = f"http://router.project-osrm.org/table/v1/driving/{coordinates_str}?annotations={type}"

    # Make the request to OSRM
    response = requests.get(url, timeout=timeout)
    data = response.json()

    # Extract the distance matrix
    return data.get(f"{type}s", [])

def read_csv(file_path):
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        coordinates = []
        addresses = []
        for row in reader:
            if row['Longitude'] and row['Latitude']:
                coordinates.append((float(row['Longitude']), float(row['Latitude'])))
                addresses.append(row['Address'])
        return coordinates, addresses

def write_matrix_to_csv(matrix, addresses, file_path):
    with open(file_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['From/To'] + addresses)
        for address, row in zip(addresses, matrix):
            writer.writerow([address] + row)

def build_matrices(input_file_path='generator_clients.csv', output_dir='.', timeout=15):
    """Geocode any missing coordinates, then rebuild distance_matrix.csv and duration_matrix.csv."""
    # Fill in any missing Latitude/Longitude by geocoding the Address
    fill_missing_coordinates(input_file_path)

    # Read coordinates and addresses from the CSV file
    coordinates, addresses = read_csv(input_file_path)

    for type in ["distance", "duration"]:
        output_file_path = os.path.join(output_dir, f'{type}_matrix.csv')

        # Get the matrix
        matrix = get_matrix(coordinates, type=type, timeout=timeout)

        # Write the matrix to a CSV file
        write_matrix_to_csv(matrix, addresses, output_file_path)


def main():
    build_matrices()
    print("Finished")

if __name__ == "__main__":
    main()

import csv
import requests

def get_matrix(coordinates, type="distance"): # duration or distance
    # Convert coordinates to OSRM API format
    coordinates_str = ';'.join([f"{lon},{lat}" for lon, lat in coordinates])

    # Construct the OSRM API request URL
    url = f"http://router.project-osrm.org/table/v1/driving/{coordinates_str}?annotations={type}"

    # Make the request to OSRM
    response = requests.get(url)
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

def main():
    input_file_path = 'generator_clients.csv'

    # Read coordinates and addresses from the CSV file
    coordinates, addresses = read_csv(input_file_path)

    for type in ["distance", "duration"]:
        output_file_path = f'{type}_matrix.csv'
        
        # Get the matrix
        matrix = get_matrix(coordinates, type=type)
        
        # Write the matrix to a CSV file
        write_matrix_to_csv(matrix, addresses, output_file_path)

    print("Finished")
    
if __name__ == "__main__":
    main()

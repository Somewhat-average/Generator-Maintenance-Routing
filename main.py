import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)

from math import isnan, sqrt, sin, cos, atan2, pi
import os
import inspect
import uuid
import pandas as pd
from statistics import fmean
from itertools import combinations
from beautiful_date import *
from gcsa.event import Event
from gcsa.google_calendar import GoogleCalendar

clients_file = "generator_clients.csv"

with open("calendar_id.txt") as file:
    google_calendar_id = file.read().splitlines()[0]

username = os.getenv("USERNAME")
clear_screen = True

def format_number(value):
    if isinstance(value, float):
        if isnan(value):
            return ''
        return int(value)
    else:
        return value

# Loop until valid input is received
while True:
    matrix_type = input("Optimize for:\n1. Distance\n2. Duration\nEnter your choice (1 or 2): ")
    if matrix_type == "1":
        matrix_file = "distance_matrix.csv"
        break
    elif matrix_type == "2":
        matrix_file = "duration_matrix.csv"
        break
    else:
        print("Invalid choice. Please enter '1' for Distance or '2' for Duration.")

if clear_screen:
    os.system('cls')

while True:
    start = input("Start route at:\n1. Work\n2. Home\nEnter your choice (1 or 2): ")
    if start == "1":
        start = "Work"
        break
    elif start == "2":
        start = "Home"
        break
    else:
        print("Invalid choice. Please enter '1' for Work or '2' for Home.")

if clear_screen:
    os.system('cls')

while True:
    end = input("End route at:\n1. Work\n2. Home\nEnter your choice (1 or 2): ")
    if end == "1":
        end = "Work"
        break
    elif end == "2":
        end = "Home"
        break
    else:
        print("Invalid choice. Please enter '1' for Work or '2' for Home.")

split = None
extra = None
if start == end:
    while True:
        split = input("Split route (y/n)? ").strip().lower()
        
        if split == "y":
            split = True
            extra = "Work" if start == "Home" else "Home"
            break  # Exit the loop once valid input is received
        elif split == "n":
            split = False
            extra = None
            break  # Exit the loop once valid input is received
        else:
            print("Please enter 'y' or 'n'.")


if clear_screen:
    os.system('cls')

clients = pd.read_csv(clients_file)
matrix = pd.read_csv(matrix_file, index_col="From/To")


def calculate_total_distance(path, matrix):
    total_distance = 0

    for i in range(len(path) - 1):
        distance = matrix.loc[path[i], path[i + 1]]
        try:
            total_distance += distance.iat[1]
        except AttributeError:
            total_distance += distance
    # total_distance += matrix.loc[path[-1], path[0]]  # Close the loop
    return total_distance


def two_opt_swap(path, i, k):
    new_path = path[0:i]
    new_path.extend(reversed(path[i:k + 1]))
    new_path.extend(path[k + 1:])
    return new_path


def two_opt(path, matrix):
    improvement = True
    while improvement:
        improvement = False
        best_distance = calculate_total_distance(path, matrix)
        for i in range(1, len(path) - 2):
            for k in range(i + 1, len(path) - 1):
                new_path = two_opt_swap(path, i, k)
                new_distance = calculate_total_distance(new_path, matrix)
                if new_distance < best_distance:
                    path = new_path
                    best_distance = new_distance
                    improvement = True
    return path


# Modify the solve_tsp function
def solve_tsp_two_opt(sub_matrix):
    # Create an initial path - could be Nearest Neighbor or any other method
    start_address = sub_matrix.index[0]
    end_address = sub_matrix.index[-1]
    # print(f"{start_address=}, {end_address=}")
    initial_path = [start_address] + sub_matrix.index[1:-1].tolist() + [end_address]

    # Apply 2-opt to the initial path
    optimized_path = two_opt(initial_path, sub_matrix)
    return optimized_path


# Solving TSP using Nearest Neighbor Algorithm
def solve_tsp_nearest_neighbor(sub_matrix):
    start_address = sub_matrix.index[0]
    end_address = sub_matrix.index[-1]
    path = [start_address]
    while len(path) < len(sub_matrix.index):
        last_visited = path[-1]
        # Find the nearest neighbor
        remaining = sub_matrix.loc[last_visited].drop(path)
        nearest = remaining.idxmin()
        path.append(nearest)
    path.append(end_address)  # Return to the starting point
    return path


# Group clients by plan
def group_clients_by_plan(clients):
    grouped_clients = {}
    for _, client in clients.iterrows():
        plan = client['Plan']
        if not pd.isna(plan):
            if plan not in grouped_clients:
                grouped_clients[plan] = []
            grouped_clients[plan].append(client)
    return grouped_clients


def select_clients(grouped_clients, select_platinum=True):
    selected_clients = []
    selected_client_names = set()  # Set to track selected client names
    
    if not clear_screen:
        print('\n')

    print("List of clients grouped by plan:")
    for plan, clients in grouped_clients.items():
        print(f"\nClients with {plan} plan:")
        for index, client in enumerate(clients, start=1):
            print(f"{index}. {client['Name']}")

        # Automatically select all clients if the plan is Platinum and the flag is True
        if plan == "Platinum" and select_platinum:
            for client in clients:
                if client['Name'] not in selected_client_names:
                    selected_client_names.add(client['Name'])
                    selected_clients.append(client)
            print(f"All {plan} plan clients have been automatically selected.")
            continue  # Skip manual selection for Platinum plan

        while True:
            try:
                selected_indices = input(f"Select {plan} Plan clients (e.g., 1 3 5): ").split()
                selected_indices = [int(index) for index in selected_indices]
                
                for index in selected_indices:
                    if 0 < index <= len(clients):
                        client = clients[index - 1]
                        if client['Name'] not in selected_client_names:
                            selected_client_names.add(client['Name'])
                            selected_clients.append(client)

                break
            except ValueError:
                print("Invalid input, please enter valid indices.")
            except IndexError:
                print("Index out of range, please select clients from the list.")
    

    return selected_clients


def format_address(address):
    return address.replace(' ', '+')


def unformat_address(address):
    return address.replace('+', ' ')


def shorten_url(origin, end, addresses, latitude, longitude, length):
    url_base = "https://www.google.com/maps/dir/"
    formatted_route = '/'.join([origin] + addresses + [end])
    zoom = round((12.88 - 5.5 * length) * 4) / 4 # fitted model on 2 data to nearest 0.25
    return f"{url_base}{formatted_route}/@{latitude},{longitude},{zoom}z?entry=ttu" # 11z = 11 zoom


def make_url(origin, end, addresses, latitude, longitude, length):
    formatted_addresses = [format_address(address) for address in addresses]
    return shorten_url(origin, end, formatted_addresses, latitude, longitude, length)

def decode_url(origin, end, url, clients, selected_clients, latitude, longitude, length, return_link=False, split=False, extra=None):
    print()
    output = ''

    # Extract addresses from URL and remove the first and last item ('Work')
    addresses = url.split('/')[6:-2]
    addresses = addresses[1:-1]  # remove first and last address
    shortened_url = shorten_url(origin, end, addresses, latitude, longitude, length)

    if return_link:
        return shortened_url

    for i in range(len(addresses)):
        addresses[i] = unformat_address(addresses[i])

    index = 1
    for i, address in enumerate(addresses, 1):
        matched_clients = [client for _, client in clients.iterrows() if address in client['Address']]
        
        if matched_clients:
            client = matched_clients[0]
            
            # Handle the split scenario
            if split and extra is not None and client['Name'] == extra:
                print(f"\n-- Splitting route at {extra} --\n")
                output += f"\n-- Splitting route at {extra} --\n"
                index = 1  # Reset the index after the split
                continue  # Skip the rest of this loop and continue processing

            selected_clients[i-1] = client
            print(f"{index}. {client['Name']} ({client['Plan']})")
            output += f"{index}. {client['Name']} ({client['Plan']})\n"
            index += 1
        else:
            print(f"{i}. Address not found in client list.")
            output += f"{i}. Address not found in client list.\n"
            index += 1

    print(f"\nlink: {shortened_url}")
    output += f"\nlink: {shortened_url}"
    
    return output


# Create submatrix for selected addresses
def make_sub_matrix(matrix, selected_addresses):
    return matrix.loc[selected_addresses, selected_addresses]

def mean_coordinates(clients):
    longitudes = [client['Longitude'] for client in clients]
    latitudes = [client['Latitude'] for client in clients]
    return (fmean(longitudes), fmean(latitudes))


def greatest_distance(clients, scaled_down=False):
    longest = 0
    longitudes = [client['Longitude'] for client in clients]
    latitudes = [client['Latitude'] for client in clients]
    coordinates = zip(longitudes, latitudes)
    pairs = list(combinations(coordinates, 2))
    for pair in pairs:
        dist, dir = to_polar_vector(pair[0], pair[1])
        if scaled_down:
            dist = dist / (sin(dir) + cos(dir)) # scale down to x-1 from circle
        if dist > longest:
            longest = dist

    return longest


def to_polar_vector(p, q):
    magnitude = sqrt((p[0] - q[0])**2 + (p[1] - q[1])**2)
    direction = atan2((p[1]- q[1]), (p[0] - q[0])) # in radians [-pi, pi]
    # make between 0 and pi/2
    direction = abs(direction)
    direction = 0.5*pi - abs(0.5*pi - direction)

    return (magnitude, direction)


ALGORITHM = "two_opt" # Options: "two_opt", "nearest_neighbor", "christofides"


def main():
    # Group clients by plan, excluding those with NaN plans
    grouped_clients = group_clients_by_plan(clients)

    # Prompt the user for client selection by plan
    selected_clients = select_clients(grouped_clients, select_platinum=False)

    # Extract addresses from selected clients
    selected_addresses = [client['Address'] for client in selected_clients]

    # Directly add the start address to the selected addresses
    start_address = clients[clients['Name'] == start]['Address'].iloc[0]
    end_address = clients[clients['Name'] == end]['Address'].iloc[0]
    formatted_start_address = format_address(start_address)
    formatted_end_address = format_address(end_address)

    selected_addresses.insert(0, start_address)
    selected_addresses.append(end_address)

    if split:
        extra_client = clients[clients['Name'] == extra]
        extra_address = extra_client['Address'].iloc[0]
        selected_clients.append(extra_client)
        selected_addresses.insert(1, extra_address)

    # Generate submatrix for selected addresses
    sub_matrix = make_sub_matrix(matrix, selected_addresses)

    if ALGORITHM == "christofides":
        from christofides import solve_tsp_christofides, create_graph
        tsp_path = solve_tsp_christofides(sub_matrix)
        tsp_path = two_opt(tsp_path, sub_matrix)  # Optimize with 2-opt
    elif ALGORITHM == "two_opt":
        tsp_path = solve_tsp_two_opt(sub_matrix)
    elif ALGORITHM == "nearest_neighbor":
        tsp_path = solve_tsp_nearest_neighbor(sub_matrix)
    else:
        raise ValueError("Invalid algorithm selection")

    if clear_screen:
        os.system('cls')

    # Calculate and print stats of the path
    if matrix_type == "1":
        distance = calculate_total_distance(tsp_path, sub_matrix)
        # Based on emperical data
        estimated_time = distance*0.00103989801767 + 21.5290060028
        standard_deviation = 9.98231810177 # for future use; n=19
        upper_limit = estimated_time + 1*standard_deviation
        lower_limit = estimated_time - 1*standard_deviation

        stops = len(selected_clients)
        upper_limit /= (stops + 1)
        lower_limit /= (stops + 1)

        print("Efficiency of route:")
        print(f"Estimated drive time per stop: {lower_limit:.0f}-{upper_limit:.0f} minutes")

    # view location
    lon, lat = mean_coordinates(selected_clients)
    longest_distance = greatest_distance(selected_clients, scaled_down=True)
    # print(f"{longest_distance=}")
    
    # Generate and print the Google Maps URL for the TSP path
    tsp_addresses = [unformat_address(addr) for addr in tsp_path]  # Unformat addresses for URL
    google_maps_url = make_url(formatted_start_address, formatted_end_address, tsp_addresses, lat, lon, longest_distance)
    # print("Google Maps URL for TSP path:", google_maps_url)
    
    # Decode the URL to show the client details in the TSP order
    decode_url(formatted_start_address, formatted_end_address, google_maps_url, clients, selected_clients, lat, lon, longest_distance, return_link=False, split=split, extra=extra)

    if split:
        print("Run again with clients from each leg for urls")

    # Calendar implementation
    verified_macs = [
            'FC:B0:DE:17:F9:5A', # matthew's laptop
            '90:B1:1C:5D:02:06', # front office
            '34:17:EB:BF:D5:FD' # back office
            ]
    current_mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff).upper() for ele in range(0,8*6,8)][::-1])
    # print(current_mac)
    add_to_calendar = None


    while True:
        # disabled MAC address verification
        # if current_mac not in verified_macs:
        #    break

        add_to_calendar = input("\nAdd to Google Calendar? [yes/no]: ").strip().lower()
        if add_to_calendar == 'yes':
            add_to_calendar = True
            break
        elif add_to_calendar == 'no':
            add_to_calendar = False
            print("Exiting Program.")
            break
        else:
            print("Please enter 'yes' or 'no'.")

    if add_to_calendar:
        # Team MR Gen tech Calendar
        try:
            calendar = GoogleCalendar(google_calendar_id)
        except Exception as e:
            os.remove(f"C:\\Users\\{username}\\.credentials\\token.pickle")
            calendar = GoogleCalendar(google_calendar_id)

        # Next specified day
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        for index, day in enumerate(weekdays, 1):
            print(f"{index}: {day}")
        while True:
            selected_day = input("Select day: ")
            if selected_day == "1":
                selected_day = D.today() + MO
                break
            if selected_day == "2":
                selected_day = D.today() + TU
                break
            if selected_day == "3":
                selected_day = D.today() + WE
                break
            if selected_day == "4":
                selected_day = D.today() + TH
                break
            if selected_day == "5":
                selected_day = D.today() + FR
                break
            if selected_day == "6":
                selected_day = D.today() + SA
                break
            if selected_day == "7":
                selected_day = D.today() + SU
                break
            print("Invalid input")

        start_time = selected_day[7:00]
        time_increment = 1 * hours

        if len(selected_clients) > 8:
            time_increment = 0.5 * hours
        for client in selected_clients:
            event = Event(
                f"{client['Name']} ({client['Plan']})".replace(' (no)', ''),
                start=start_time,
                end=start_time + time_increment,
                location=client['Address'],
                description=inspect.cleandoc(f"""
                Phone: {client['Phone']}
                Generator: {client['Size']} {client['Type']}
                Model: {format_number(client['Model'])}
                Serial: {format_number(client['Serial'])}"""
                .replace("nan", ""))
            )

            calendar.add_event(event)
            start_time += time_increment

        # add route url to calendar
        link = decode_url(formatted_start_address, formatted_end_address, google_maps_url, clients, selected_clients, lat, lon, longest_distance, True)
        event = Event(
                "Generator Route",
                start=selected_day,
                description=f'<a href="{link}">Google Maps Route</a>'
        )
        calendar.add_event(event)


if __name__ == "__main__":
    main()


# Generator-Maintenance-Routing
A simple CLI tool to route a technician between many customers efficiently, with Google Calendar and OneStep integration

## GUI
Double-click `Generator Maintenance Tool.bat` (or run `python gui_app.py`) for a single window with both "Manage Clients" and "Generate Route" tabs - no terminal typing required. It's a thin wrapper around the same logic the CLI scripts below use, so behavior (geocoding, matrix rebuilding, TSP solving, Google Calendar events) is identical either way. The original `.bat` files and CLI scripts still work unchanged if you prefer the terminal.

## CSV Files
generator_clients.csv
| Name       | Phone          | Address                           | Plan | Size | Type       | Model    | Serial     | Latitude           | Longitude          |
| ---------- | -------------- | --------------------------------- | ---- | ---- | ---------- | -------- | ---------- | ------------------ | ------------------ |
| John Smith | (111) 222-3333 | 1234 NE Brick Rd, Tampa, FL 33613 | Gold | 24kW | Air Cooled | G0072099 | 1111111111 | 28.062757985228004 | -82.41318894541786 |

## Managing Clients
Double-click `Manage Clients.bat` (or run `python manage_clients.py`) to add, edit, or remove clients through a simple menu - no need to edit `generator_clients.csv` by hand.

- **Coordinates are automatic.** When you add a client or change an address, the tool looks up its Latitude/Longitude for you (via the free US Census geocoder). You only get asked for coordinates if that lookup fails - in that case, right-click the address in Google Maps, click the lat/long shown at the top of the menu to copy it, then paste it in when prompted.
- **The routing matrices stay in sync.** Every add, edit, or removal automatically rebuilds `distance_matrix.csv` and `duration_matrix.csv`, so `Generator Route.bat` always has up-to-date data. (If that step fails, e.g. no internet connection, run `get_matrix.py` manually once you're back online.)
- **`Home`** is a reserved name used as the route's fixed start/end point - the tool will warn you before letting you rename or remove it.



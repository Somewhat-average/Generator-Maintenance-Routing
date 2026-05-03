import numpy as np
import pandas as pd

clients_file = "../generator_clients.csv"
clients = pd.read_csv(clients_file)

# remove home and work
clients = clients.drop([0, 1])

# Open a file for writing
with open("zones.csv", "w") as f:
    # Write the header to the file
    f.write("name,color,area,vertices,zone_group,zone_group_color,label_color,visible,label_visible,area_visible\n")

    for _, client in clients.iterrows():
        latitude = client["Latitude"]
        longitude = client["Longitude"]

        radius = 0.05  # miles
        points = 15  # number of points on the circle

        rotate = 180 // points # make flat side on bottom # only integer values
        # scaling approximates circle much better with the shape, given the same area
        # deciding not to scale so that the vehicle is always at or closer than the radius
        # so that there is no ambiguity on whether is is further out or not
        # radius *= np.sqrt((2 * np.pi) / (points * np.sin((2 * np.pi) / points))) # make area constant regardless of shape

        earth_radius = 3958.8
        latitude_conversion = 180 / (np.pi * earth_radius) # miles to degrees
        longitude_conversion = 180 / (np.pi * earth_radius * np.cos(np.radians(latitude))) # miles to degrees

        # Generate vertices for an n sided regular polygon
        vertices = [
            (
                latitude + radius * latitude_conversion * np.sin(np.radians(angle)),
                longitude + radius * longitude_conversion * np.cos(np.radians(angle))
            )
            for angle in range(0 + rotate, 365 + rotate, 360 // points)
        ]

        # Format vertices as a string
        vertices_str = ",".join(f"{lat:.6f},{lon:.6f}" for lat, lon in vertices)

        # Write the formatted line to the file
        f.write(f'"{client["Name"]}",#FF0000,0,"{vertices_str}",Generators,#2950CA,zone_group,true,true,false\n')


import openrouteservice
from openrouteservice import convert
import gpxpy
import gpxpy.gpx
import folium
import os
import logging
from dotenv import load_dotenv

from src.base.itinerary import Itinerary


class RoutePlanner():
    def __init__(self, ors_api_key):
        self.ors = openrouteservice.Client(key=ors_api_key)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def _geocode_itinerary(self, itinerary):
        #TODO: better geocoding ex: avoid outliers (calculate distance )
        coords = []
        total_itinerary = [itinerary.start] + itinerary.waypoints + [itinerary.end]
        for place in total_itinerary:
            res = self.ors.pelias_search(text=place, size=1)
            if res['features']:
                lon, lat = res['features'][0]['geometry']['coordinates']
                coords.append((lon, lat))
            else:
                # TODO: handle geocoding failure more gracefully
                self.logger.error(f"Could not geocode location: {place}")
                raise ValueError(f"Could not geocode location: {place}")
            
        return coords


    def _request_route(self, coords):
        try:
            route_params = {
                'coordinates': coords,
                'profile': 'foot-walking',
                'format': 'geojson',
                'instructions': False,

            }
            data = self.ors.directions(**route_params)
        except Exception as e:
            self.logger.error(f"Error requesting route: {e}")
            raise e
        return data

    def create_route(self, itinerary):
        if not itinerary.feasible:
            raise ValueError("Cannot create route for unfeasible itinerary")
        
        self.logger.info(f"Creating route for itinerary: {itinerary}")
        coords = self._geocode_itinerary(itinerary)

        self.logger.info(f"Geocoded coordinates: {coords}")
        data = self._request_route(coords)


        line = data['features'][0]['geometry']['coordinates']

        # Build GPX
        gpx = gpxpy.gpx.GPX()
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        for lon, lat in line:
            gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))

        with open("out/itinerary_route.gpx", "w") as f:
            f.write(gpx.to_xml())
        return





        

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)    

    load_dotenv()

    api_key = os.getenv("ORS_API_KEY")
    planner = RoutePlanner(ors_api_key=api_key)

    itinerary = Itinerary(
        start="Sheraton Grand Krakow, Krakow",
        end="Sheraton Grand Krakow, Krakow",
        waypoints=[
            'Grodzka Street, Krakow',
            'Main Market Square (Rynek Główny), Krakow',
            'Floriańska Street, Krakow',
            "St. Florian's Gate, Krakow",
            'Barbican, Krakow',
            'Pijarska Street, Krakow',
            'Uniwersytet Jagielloński, Krakow',
            'Main Market Square (Rynek Główny), Krakow',
            'Grodzka Street, Krakow'
        ],
        itinerary=None
    )

    route = planner.create_route(itinerary)
    print(route)

    # visualize the GPX data (optional)
    gpx_file = open('itinerary_route.gpx', 'r')
    gpx = gpxpy.parse(gpx_file)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append(tuple([point.latitude, point.longitude]))

    # 3. Create a Folium map centered on the starting point
    if points:
        start_point = points[0]
        my_map = folium.Map(location=start_point, zoom_start=14)

        # Add the route as a line to the map
        folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(my_map)

        # Save the map as an HTML file
        my_map.save("route_map.html")
        print("Map 'route_map.html' has been created successfully.")
    else:
        print("No points found in the GPX file.")
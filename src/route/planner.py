import openrouteservice
from openrouteservice import convert

import folium
import os
import logging
from dotenv import load_dotenv
import sys
from pathlib import Path

# import

current_dir = Path(__file__).resolve().parent.parent
utilities_dir = current_dir.parent / "src"
sys.path.append(str(utilities_dir.parent))

from src.base.itinerary import Itinerary
from src.base.route import Route

class RoutePlanner():
    def __init__(self, ors_api_key):
        self.ors = openrouteservice.Client(key=ors_api_key)
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
    
    def _haversine_km(self, coord_a, coord_b):
        """Compute great-circle distance in kilometers between two (lon, lat) tuples."""
        from math import radians, sin, cos, asin, sqrt
        lon1, lat1 = coord_a
        lon2, lat2 = coord_b
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        earth_radius_km = 6371.0088
        return earth_radius_km * c

    def _median(self, values):
        if not values:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        mid = n // 2
        if n % 2 == 0:
            return (sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0
        return sorted_vals[mid]

    def _detect_outliers_mad(self, coords, z_threshold=3.5):
        """
        Detect outliers based on the median of pairwise distances per point and MAD.
        Returns a set of indices considered outliers.
        """
        n = len(coords)
        if n < 3:
            return set()
    
        # For each point, compute distances to others and take median distance
        median_dists = []
        for i in range(n):
            dists = []
            for j in range(n):
                if i == j:
                    continue
                dists.append(self._haversine_km(coords[i], coords[j]))
            median_dists.append(self._median(dists))
            
        overall_median = self._median(median_dists)
        abs_dev = [abs(x - overall_median) for x in median_dists]
        mad = self._median(abs_dev)
        if mad == 0:
            m = overall_median
            if m == 0:
                # Cluster is essentially at a point; anything >1.5 km is an outlier
                return {i for i, x in enumerate(median_dists) if x > 1.5}
            factor = 3.5
            abs_km = 2.0
            thresh = max(m * factor, m + abs_km)
            return {i for i, x in enumerate(median_dists) if x > thresh}

        # Modified Z-Score using 0.6745
        outliers = set()
        for idx, x in enumerate(median_dists):
            mz = 0.6745 * abs(x - overall_median) / mad
            if mz > z_threshold:
                outliers.add(idx)
        return outliers

    def _choose_best_candidate(self, candidates, fixed_coords):
        """
        Given candidate coordinates for a point and the list of other fixed coordinates,
        choose the candidate minimizing median distance to fixed points.
        """
        if not candidates:
            return None
        best = None
        best_score = float("inf")
        for cand in candidates:
            dists = [self._haversine_km(cand, other) for other in fixed_coords] or [float("inf")]
            score = self._median(dists)
            if score < best_score:
                best_score = score
                best = cand
        return best
    
    def _get_bounding_box(self, coords):
        """Calculate bounding box from list of (lon, lat) coordinates"""
        if not coords:
            return None
        lons, lats = zip(*coords)
        return {
            'min_lon': min(lons),
            'max_lon': max(lons),
            'min_lat': min(lats),
            'max_lat': max(lats)
        }

    def _geocode_itinerary(self, itinerary, detect_outliers=False):
        coords = []
        places = [itinerary.start] + itinerary.waypoints + [itinerary.end]
        for place in places:
            res = self.ors.pelias_search(text=place, size=1)
            if res.get('features'):
                lon, lat = res['features'][0]['geometry']['coordinates']
                coords.append((lon, lat))
            else:
                self.logger.error(f"Could not geocode location: {place}")
                raise ValueError(f"Could not geocode location: {place}")

        if detect_outliers:
            outliers = self._detect_outliers_mad(coords)
            if outliers:
                self.logger.info(f"Outlier indices detected in geocoding: {sorted(list(outliers))}")
                
                # Get bounding box from non-outlier points
                non_outlier_coords = [coords[i] for i in range(len(coords)) if i not in outliers]
                bbox = self._get_bounding_box(non_outlier_coords)
                
                # Add some padding to the bounding box (20%)
                if bbox:
                    pad_lon = (bbox['max_lon'] - bbox['min_lon']) * 0.2
                    pad_lat = (bbox['max_lat'] - bbox['min_lat']) * 0.2
                    bbox = {
                        'min_lon': bbox['min_lon'] - pad_lon,
                        'max_lon': bbox['max_lon'] + pad_lon,
                        'min_lat': bbox['min_lat'] - pad_lat,
                        'max_lat': bbox['max_lat'] + pad_lat
                    }
                    
                for idx in outliers:
                    place = places[idx]
                    try:
                        
                        search_params = {
                            'text': place,
                            'size': 5
                        }
                        if bbox:
                            search_params.update({
                                'rect_min_x': bbox['min_lon'],
                                'rect_max_x': bbox['max_lon'],
                                'rect_min_y': bbox['min_lat'],
                                'rect_max_y': bbox['max_lat']
                            })
                        res = self.ors.pelias_search(**search_params)
                    except Exception as e:
                        self.logger.warning(f"Re-query failed for '{place}': {e}")
                        continue
                    cand_coords = []
                    for feat in res.get('features', []):
                        try:
                            lon, lat = feat['geometry']['coordinates']
                            cand_coords.append((lon, lat))
                        except Exception:
                            continue
                    fixed = [coords[j] for j in range(len(coords)) if j != idx]
                    best = self._choose_best_candidate(cand_coords, fixed)
                    if best is not None:
                        coords[idx] = best

                # check again if there are outliers
                outliers = self._detect_outliers_mad(coords)
                if outliers:
                    self.logger.info(f"Still outlier indices detected in geocoding: {sorted(list(outliers))}")
        return coords


    def _request_route(self, coords):
        try:
            route_params = {
                'coordinates': coords,
                'profile': 'foot-walking',
                'units':'m',
                'format': 'geojson',
                'instructions': False,
                'preference': 'recommended',
                'options': { 'avoid_features': ['ferries']},
                'elevation': True,
                'extra_info':['steepness', 'suitability', 'surface', 'green', 'noise', 'shadow'] 
                # Add traildifficulty to include trail running
                # check ors documentation if you want to add cycling
                # TODO: ask for instructions for llm to describe after as tourist guide
                # TODO: try out weightings (given by llm?)
            }
            data = self.ors.directions(**route_params)
        except Exception as e:
            self.logger.error(f"Error requesting route: {e}")
            raise e
        return data

    def create_route(self, itinerary, save_gpx=True, filename="out/itinerary.gpx"):
        if not itinerary.feasible:
            raise ValueError("Cannot create route for unfeasible itinerary")
        
        
        coords = self._geocode_itinerary(itinerary, detect_outliers=True)

        self.logger.info(f"Geocoded coordinates: {coords}")
        data = self._request_route(coords)

        route = Route(data["features"][0])
        
        if save_gpx:
            route.save_gpx(filename)
        
        return route





        

if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)    

    load_dotenv()

    api_key = os.getenv("ORS_API_KEY")
    planner = RoutePlanner(ors_api_key=api_key)

    itinerary = Itinerary(
        start="Wawel Castle, Krakow",
        end="Wawel Castle, Krakow",
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

    # # visualize the GPX data (optional)
    # gpx_file = open('out/itinerary_route.gpx', 'r')
    # gpx = gpxpy.parse(gpx_file)
    # points = []
    # for track in gpx.tracks:
    #     for segment in track.segments:
    #         for point in segment.points:
    #             points.append(tuple([point.latitude, point.longitude]))

    # # 3. Create a Folium map centered on the starting point
    # if points:
    #     start_point = points[0]
    #     my_map = folium.Map(location=start_point, zoom_start=14)

    #     # Add the route as a line to the map
    #     folium.PolyLine(points, color="blue", weight=2.5, opacity=1).add_to(my_map)

    #     # Save the map as an HTML file
    #     my_map.save("out/route_map.html")
    #     print("Map 'route_map.html' has been created successfully.")
    # else:
    #     print("No points found in the GPX file.")
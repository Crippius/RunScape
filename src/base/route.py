
from src.base.route_features import Surface, Steepness, Greenness, Noisiness, Shadowness

import gpxpy
import gpxpy.gpx

class Route():

    def __init__(self, json_data):
        self._parse_json(json_data)


    
    def _parse_json(self, json_data):


        # TODO: complexer class?
        self.route_coords = json_data['geometry']['coordinates'] 
        if len(self.route_coords) == 0:
            raise ValueError("Coords not present")
        if len(self.route_coords[0]) == 2: # No elevation
            self._3d = 0
        elif len(self.route_coords[0]) == 3: # Elevation present
            self._3d = 1
        else:
            raise ValueError
        
        self.bbox = json_data["bbox"] # To plot on map

        self.distance = json_data["properties"]["summary"]["distance"]
        # Duration calculated for walking 5km/h -> not correct for running 
        # self.duration = json_data["properties"]["summary"]["duration"]
        if self._3d:
            self.total_ascent = json_data["properties"]["ascent"]
            self.total_descent = json_data["properties"]["descent"]

        # Gauge type 0-10
        self.greenness = None
        if "green" in json_data["properties"]["extras"].keys():
            self.greenness = Greenness(json_data["properties"]["extras"]["green"])
        
        # Gauge type 0-10
        self.noisiness = None
        if "noise" in json_data["properties"]["extras"].keys():
            self.noisiness = Noisiness(json_data["properties"]["extras"]["noise"])

        # Gauge type 0-10
        self.shadowness = None
        if "shadow" in json_data["properties"]["extras"].keys():
            self.shadowness = Shadowness(json_data["properties"]["extras"]["shadow"])

        self.surface = None
        if "surface" in json_data["properties"]["extras"].keys():
            self.surface = Surface(json_data["properties"]["extras"]["surface"])

        self.surface
        if "steepness" in json_data["properties"]["extras"].keys():
            self.steepness = Steepness(json_data["properties"]["extras"]["steepness"])

        # traildifficulty not used yet (expansion for trail-running / cycling)

        # instructions?

    def get_greenness(self):
        if self.greenness == None:
            return None
        return self.greenness.get_grenness()
    
    def get_noisiness(self):
        if self.noisiness == None:
            return None
        return self.noisiness.get_noisiness()
    
    def get_shadowness(self):
        if self.shadowness == None:
            return None
        return self.shadowness.get_shadowness()
    

    def save_gpx(self, filename="out/itinerary.gpx"):

        gpx = gpxpy.gpx.GPX()
        gpx_track = gpxpy.gpx.GPXTrack()
        gpx.tracks.append(gpx_track)
        gpx_segment = gpxpy.gpx.GPXTrackSegment()
        gpx_track.segments.append(gpx_segment)

        if not self._3d:
            for lon, lat in self.route_coords:
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon))

        if self._3d:
            for lon, lat, elevation in self.route_coords:
                gpx_segment.points.append(gpxpy.gpx.GPXTrackPoint(lat, lon, elevation=elevation))

        with open(filename, "w") as f:
            f.write(gpx.to_xml())







        
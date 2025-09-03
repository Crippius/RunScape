import folium
from src.base.route import Route
from typing import Optional
from pathlib import Path

class RouteVisualizer:
    
    def __init__(self, route: Route):
        self.route = route
        self._map = None
        
    def create_map(self, zoom_start: int = 14) -> folium.Map:

        if not self.route.route_coords:
            raise ValueError("Route has no coordinates")
            
        # Convert [lon, lat] to [lat, lon] for folium
        points = [[lat, lon] for lon, lat, *_ in self.route.route_coords]
        
        # Center map on first point
        self._map = folium.Map(
            location=points[0],
            zoom_start=zoom_start
        )
        
        # Add the route line
        folium.PolyLine(
            points,
            color="blue",
            weight=2.5,
            opacity=1,
            popup=f"Distance: {self.route.distance/1000:.2f} km"
        ).add_to(self._map)
        
        # Add start/end markers
        folium.Marker(
            points[0],
            popup="Start",
            icon=folium.Icon(color='green', icon='info-sign')
        ).add_to(self._map)
        
        folium.Marker(
            points[-1],
            popup="End",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(self._map)
        
        self.add_features()

        return self._map
    
    def add_features(self) -> None:
        """Adds route features like greenness, noise levels etc. as map overlays"""
        if not self._map:
            raise ValueError("Create map first using create_map()")
            
        features = {
            'Greenness': self.route.get_greenness(),
            'Noise Level': self.route.get_noisiness(),
            'Shadow': self.route.get_shadowness()
        }
        
        # Add feature information
        feature_html = "<br>".join(
            f"{k}: {v:.1f}/10" for k, v in features.items() if v != None
            if v is not None
        )
        
        if feature_html:
            folium.Rectangle(
                bounds=[[self.route.bbox[1], self.route.bbox[0]], 
                       [self.route.bbox[3], self.route.bbox[2]]],
                popup=feature_html,
                color="#ff7800",
                weight=1,
                fill=False,
            ).add_to(self._map)
    
    def save(self, filename: Optional[str] = "out/map.html") -> None:

        if not self._map:
            raise ValueError("Create map first using create_map()")
            

        # Save map
        self._map.save(filename)
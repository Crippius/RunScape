
from enum import Enum
from abc import ABC


class SurfaceType(Enum):
    UNKNOWN = 0
    PAVED = 1
    UNPAVED = 2
    ASPHALT = 3
    CONCRETE = 4
    COBBLESTONE = 5
    METAL = 6
    WOOD = 7
    COMPACTED_GRAVEL = 8
    FINE_GRAVEL = 9
    GRAVEL = 10
    DIRT = 11
    GROUND = 12
    ICE = 13
    PAVING_STONES = 14
    SAND = 15
    WOODCHIPS = 16
    GRASS = 17
    GRASS_PAVER = 18

    def __str__(self):
        return f"{self.name.replace("_", " ").title()}"


class SteepnessType(Enum):
    VERY_STEEP_DECLINE = -5
    STEEP_DECLINE = -4
    MODERATE_DECLINE = -3
    SLIGHT_DECLINE = -2
    VERY_SLIGHT_DECLINE = -1
    FLAT = 0
    VERY_SLIGHT_INCLINE = 1
    SLIGHT_INCLINE = 2
    MODERATE_INCLINE = 3
    STEEP_INCLINE = 4
    VERY_STEEP_INCLINE = 5

    @property
    def range_str(self):
        ranges = {
            -5: ">16%",
            -4: "12-15%",
            -3: "7-11%",
            -2: "4-6%",
            -1: "1-3%",
            0: "0%",
            1: "1-3%",
            2: "4-6%",
            3: "7-11%",
            4: "12-15%",
            5: ">16%"
        }
        return ranges[self.value]
    
    def __str__(self):
        return f"{self.name.replace('_', ' ').title()} ({self.range_str})"


class TopographicFeature(ABC):    
    
    feature = Enum

    
    def __init__(self, json_data, detailed=True):
        self.detailed = detailed
        self.summary = {}
        self.data = []
        self.start = 0
        self.end = 0
        
        
        self._parse_json(json_data)
        
    def _parse_json(self, json_data):
        if self.detailed:
            for start, end, feature_value in json_data.get("values", []):
                self.data.append((start, end, self.feature(feature_value)))
            
            if self.data:
                self.start = self.data[0][0]
                self.end = self.data[-1][1]
        
        for summary_item in json_data.get("summary", []):
            self.summary[self.feature(summary_item["value"])] = {
                "distance": summary_item["distance"],
                "percent": summary_item["amount"]
            }

    def get_feature(self, point):

        if not self.detailed:
            raise ValueError("Detailed representation not available")
        if not (self.start <= point < self.end):
            raise ValueError("Point outside of range")
        
        low = 0
        high = len(self.data) - 1
        result_index = -1
        
        while low <= high:
            mid = (low + high) // 2
            start_point = self.data[mid][0]
            
            if start_point <= point:
                result_index = mid
                low = mid + 1
            else:
                high = mid - 1
        
        if result_index == -1:
            raise ValueError("Point outside of range")
            
        start, end, feature_type = self.data[result_index]
        
        if start <= point < end:
            return feature_type
        else:
            raise ValueError("Point outside of range")
        

    def get_summary(self):
        # TODO:
        pass
        
class SimplifiedTopographicFeature(TopographicFeature):

    feature = int

    def __init__(self, json_data, detailed=False):   
        self.detailed = detailed
        self.summary = {}
        self.data = []
        self.start = 0
        self.end = 0
        
        self._parse_json(json_data)

        self.average = 0
        for value in self.summary:
            self.average += value * self.summary[value]["percent"]
        self.average = round(self.average, 2)

 
    def get_feature(self, point=None):
        return self.average
    
    def get_summary(self):
        # TODO:
        pass


class Surface(TopographicFeature):

    feature = SurfaceType

    def __init__(self, json_data, detailed=True):
        super().__init__(json_data, detailed)

    def get_surface(self, point):
        return self.get_feature(point)

class Steepness(TopographicFeature):

    feature = SteepnessType

    def __init__(self, json_data, detailed=True):
        super().__init__(json_data, detailed)

    def get_steepness(self, point):
        return self.get_feature(point)

class Greenness(SimplifiedTopographicFeature):

    def __init__(self, json_data, detailed=False):
        super().__init__(json_data, detailed)
    
    def get_grenness(self):
        return self.get_feature()
    
class Noisiness(SimplifiedTopographicFeature):

    def __init__(self, json_data, detailed=False):
        super().__init__(json_data, detailed)
    
    def get_noisiness(self):
        return self.get_feature()
    
class Shadowness(SimplifiedTopographicFeature):

    def __init__(self, json_data, detailed=False):
        super().__init__(json_data, detailed)
    
    def get_shadowness(self):
        return self.get_feature()
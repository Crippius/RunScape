class Itinerary():

    def __init__(self, start, end, waypoints, itinerary):
        self.start = start
        self.end = end
        self.waypoints = waypoints
        self.itinerary = itinerary
        self.feasible = True
    
    def __repr__(self):
        return f"Itinerary(start={self.start}, end={self.end}, waypoints={self.waypoints}"
    
    def __str__(self):
        return f"Itinerary from {self.start} to {self.end} via {self.waypoints}\nItinerary: {self.itinerary}"

class UnfeasibleItinerary(Itinerary):
    def __init__(self, updated_request):
        super().__init__(None, None, None)
        self.feasible = False
        self.updated_request = updated_request

    def __repr__(self):
        return f"UnfeasibleItinerary(updated_request={self.updated_request})"
    
    def __str__(self):
        return f"Unfeasible Itinerary. Suggested update to request: {self.updated_request}"



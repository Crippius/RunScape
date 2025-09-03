from src.base.itinerary import Itinerary
from src.route.planner import RoutePlanner
from src.agent.builder import ItineraryBuilder
from src.visualize.visualizer import RouteVisualizer
import logging
from dotenv import load_dotenv
import gpxpy
import gpxpy.gpx
import folium
import os



if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    agent = ItineraryBuilder(api_key=api_key, model="gemini-2.5-flash", temperature=0, debug=False)

    query = "I want to do a nice 5km run in Krakow, starting from the castle going through the old town and the university district, and ending back at the castle. I prefer scenic routes with some historical landmarks along the way."
    # query = "I want to do a nice 10km run in Milan, starting from Arco della Pace going through Parco Sempione, Castello Sforzesco, and Brera district, and ending back at Arco della Pace. I prefer scenic routes with some historical landmarks along the way."
    
    suggested_itinerary = agent.request_running_itinerary(query)

    if suggested_itinerary.feasible is False:
        logger.error("The provided running plan is not feasible.")
        logger.info(f"Suggested update to request: {suggested_itinerary.updated_request}")
        exit(1)
    
    print(suggested_itinerary)

    ors_key = os.getenv("ORS_API_KEY")
    planner = RoutePlanner(ors_api_key=ors_key)
    
    route = planner.create_route(suggested_itinerary)

    visualizer = RouteVisualizer(route)

    visualizer.create_map()

    visualizer.save()
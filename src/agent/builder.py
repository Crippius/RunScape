
import os
import logging

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from time import time

from src.agent.templates import ValidationTemplate, ItinearyDesignTemplate, MappingTemplate
from src.base.itinerary import Itinerary
from src.base.itinerary import Itinerary, UnfeasibleItinerary




class ItineraryBuilder(object):
    def __init__(self, api_key, model, temperature=0, debug=True):
        
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        if "gemini" in model:
            self.logger.info("using Google Gemini Model")
            self.chat_model = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=temperature
                # TODO: tune other parameters
            )
        # TODO: add other models (openAI, palm2, etc)
        else:
            raise ValueError("Model not supported")
        
        self.api_key = api_key

        self.validation_prompt = ValidationTemplate()
        self.itinerary_prompt = ItinearyDesignTemplate()
        self.mapping_prompt = MappingTemplate()
    
    def request_running_itinerary(self, query):
        # TODO add starting point as input parameter

        self.logger.info("Requesting running itinerary")

        self.logger.info("Validating user input")
        t1 = time()
        validation_messages = self.validation_prompt().format_messages(
            query=query,
            format_instructions=self.validation_prompt.parser.get_format_instructions(),
        )
        validation_response = self.chat_model.invoke(validation_messages)
        validation_text = getattr(validation_response, "content", str(validation_response))
        validation_test = self.validation_prompt.parser.parse(validation_text)
        t2 = time()
        self.logger.info("Time to validate request: {}".format(round(t2 - t1, 2)))

        if validation_test.plan_is_valid.lower() == "no":
            self.logger.warning("User request was not valid!")
            print("\n######\n Travel plan is not valid \n######\n")
            return UnfeasibleItinerary(updated_request=validation_test.updated_request)

        # if we reach here, the plan is valid
        # TODO: RAG system to avoid hallucinations
        self.logger.info("User request is valid, generating itinerary")
        t1 = time()
        # Step 1: Produce narrated itinerary suggestion
        itinerary_messages = self.itinerary_prompt().format_messages(query=query)
        itinerary_response = self.chat_model.invoke(itinerary_messages)
        agent_suggestion = getattr(itinerary_response, "content", str(itinerary_response))

        # Step 2: Map narrated itinerary to structured start/end/waypoints JSON
        mapping_messages = self.mapping_prompt().format_messages(
            agent_suggestion=agent_suggestion,
            format_instructions=self.mapping_prompt.parser.get_format_instructions(),
        )
        mapping_response = self.chat_model.invoke(mapping_messages)
        mapping_text = getattr(mapping_response, "content", str(mapping_response))
        t2 = time()
        self.logger.info("Time to generate itinerary: {}".format(round(t2 - t1, 2)))

        mapping_data = self.mapping_prompt.parser.parse(mapping_text)
        
        suggested_itinerary = Itinerary(
            start=mapping_data.start,
            end=mapping_data.end,
            waypoints=mapping_data.waypoints,
            itinerary=agent_suggestion
        )


            
        return suggested_itinerary
        

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    agent = ItineraryBuilder(api_key=api_key, model="gemini-2.5-flash", temperature=0, debug=True)

    query = "I want to do a nice 5km run in Krakow, starting from the castle going through the old town and the university district, and ending back at the castle. I prefer scenic routes with some historical landmarks along the way."
    suggested_itinerary = agent.request_running_itinerary(query)

    if suggested_itinerary.feasible is False:
        logger.error("The provided running plan is not feasible.")
        logger.info(f"Suggested update to request: {suggested_itinerary.updated_request}")
        exit(1)
    

    print(suggested_itinerary)



import os
import logging

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain.chains import LLMChain, SequentialChain
from time import time

from src.plan.templates import ValidationTemplate, ItinearyDesignTemplate, MappingTemplate
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

        self.validation_chain = self._setup_validation_chain(debug)
        self.agent_chain = self._setup_agent_chain(debug)

    def _setup_validation_chain(self, debug):
        
        validation_agent = LLMChain(
            llm=self.chat_model,
            prompt=self.validation_prompt(),
            output_key="validation_output",
            verbose=debug
        )
        
        overall_chain = SequentialChain(
            chains=[validation_agent],
            input_variables=["query", "format_instructions"],
            output_variables=["validation_output"],
            verbose=debug,
        )

        return overall_chain

    def _setup_agent_chain(self, debug):
        
        itinerary_agent = LLMChain(
            llm=self.chat_model,
            prompt=self.itinerary_prompt(),
            verbose=debug,
            output_key="agent_suggestion",
        )

        mapping_agent = LLMChain(
            llm=self.chat_model,
            prompt=self.mapping_prompt(),
            verbose=debug,
            output_key="mapping_json",
        )

        overall_chain = SequentialChain(
            chains=[itinerary_agent, mapping_agent],
            input_variables=["query", "format_instructions"],
            output_variables=["agent_suggestion", "mapping_json"],
            verbose=debug,
        )

        return overall_chain
    
    def request_running_itinerary(self, query):
        # TODO add starting point as input parameter

        self.logger.info("Requesting running itinerary")

        self.logger.info("Validating user input")
        t1 = time()
        validation_result = self.validation_chain(
            {
                "query": query,
                "format_instructions": self.validation_prompt.parser.get_format_instructions()
            }
        )
        validation_test = self.validation_prompt.parser.parse(validation_result["validation_output"])
        t2 = time()
        self.logger.info("Time to validate request: {}".format(round(t2 - t1, 2)))

        if validation_test.plan_is_valid.lower() == "no":
            self.logger.warning("User request was not valid!")
            print("\n######\n Travel plan is not valid \n######\n")
            return UnfeasibleItinerary(updated_request=validation_test.updated_request)

        # if we reach here, the plan is valid
        self.logger.info("User request is valid, generating itinerary")
        t1 = time()
        agent_result = self.agent_chain(
                {
                    "query": query,
                    "format_instructions": self.mapping_prompt.parser.get_format_instructions(),
                }
            )
        t2 = time()
        self.logger.info("Time to generate itinerary: {}".format(round(t2 - t1, 2)))
        

        mapping_data = self.mapping_prompt.parser.parse(agent_result["mapping_json"])
        
        suggested_itinerary = Itinerary(
            start=mapping_data.start,
            end=mapping_data.end,
            waypoints=mapping_data.waypoints,
            itinerary=agent_result["agent_suggestion"]
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


from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,    
    HumanMessagePromptTemplate, 
)   

from langchain.output_parsers import PydanticOutputParser

from pydantic import BaseModel, Field
from typing import List


class ItineraryPlanSchema(BaseModel):
    start: str = Field(description="start location of itinerary")
    end: str = Field(description="end location of itinerary")
    waypoints: List[str] = Field(description="list of waypoints")

class PlanValidationSchema(BaseModel):
    plan_is_valid: str = Field(
        description="This field is 'yes' if the plan is feasible, 'no' otherwise"
    )
    updated_request: str = Field(description="Your update to the plan")

class ValidationTemplate(object):
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=PlanValidationSchema)
        
        system_template = """You are a running coach and who helps users create their running route.

The user's request will be denoted by four hashtags. Determine if the user's request is reasonable and achievable within the constraints they set.

A valid request should contain the following:
- A start and end location
- A running duration that is reasonable given the start and end location
- A running distance that is reasonable given that it is being run on foot

Any request that contains potentially harmful activities is not valid, regardless of what other details are provided.

If the requested distance is too short given the requested locations, add new locations to the itinerary to make the distance reasonable.

If the end location is not specified, assume the user wants to return to the start location.

If the request is not valid, set plan_is_valid = "no" and use your travel expertise to update the request to make it valid, keeping your revised request shorter than 100 words.

If the request seems reasonable, then set plan_is_valid = "yes" and don't revise the request.

{format_instructions}"""

        human_template = """####${query}####"""

        system_message_prompt = SystemMessagePromptTemplate.from_template(
            system_template,
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            },
        )
        human_message_prompt = HumanMessagePromptTemplate.from_template(
            human_template,
            input_variables=["query"]
        )

        self.chat_prompt = ChatPromptTemplate.from_messages(
            [system_message_prompt, human_message_prompt]
        )
        
    def __call__(self):
        return self.chat_prompt

class ItinearyDesignTemplate(object):
    def __init__(self):
        system_template = """
You are a running coach who designs enjoyable narrated running routes.  

The user's request will be between four hashtags. Convert it into a flowing narrative itinerary that guides the runner through interesting streets, landmarks, and parks.  

Rules:
- Write directions as a series of bullet points.
- Write in a natural, descriptive style (like giving a guided tour).  
- Highlight atmosphere (e.g., “quiet street,” “historic square,” “green park”).  
- Include specific streets, squares, or park entrances.  
- Each bullet point should specify a clear street or landmark.
- Avoid generic directions like “head north” or “turn left.”  
- Always mark the beginning and end of the run.  
- If the user mentions a specific distance, design the route to match it as closely as possible.
- If the user does not specify an end location, assume they want to return to the start.

Example:
####
6 km easy run in Milan, starting at Arco della Pace
####

Output:
- Begin your run at the iconic **Arco della Pace** in Piazza Sempione, a popular gathering spot for runners.  
- Head down **Corso Sempione** until you reach **Via Melzi d'Eril**, where you'll find the entrance to Parco Sempione.  
- Enter the park through **Viale Elvezia** and enjoy the green paths as you pass by the **Civic Aquarium of Milan**.  
- Continue toward the majestic **Castello Sforzesco**, crossing **Piazza Castello**.  
- Make your way onto **Via Legnano**, a quieter street that brings you back toward the starting area.  
- Finish strong as you return to **Arco della Pace** in Piazza Sempione.
"""

        self.human_template = """####${query}####"""

        self.system_message_prompt = SystemMessagePromptTemplate.from_template(
            system_template
        )
        self.human_message_prompt = HumanMessagePromptTemplate.from_template(
            self.human_template,
            input_variables=["query"]
        )

        self.chat_prompt = ChatPromptTemplate.from_messages(
            [self.system_message_prompt, self.human_message_prompt]
        )
        
    def __call__(self):
        return self.chat_prompt
    

class MappingTemplate(object):
    def __init__(self):
        self.system_template = """
You are an agent that converts a narrated running itinerary into a fully geocodable list of locations.

The itinerary will be denoted by four hashtags.  
Your task:  
- Extract the **Start**, **End**, and **Waypoints** in order.  
- Each waypoint must be a **single, precise location**: include street/intersection/landmark, city, country, and postcode if available.  
- If a landmark has multiple entrances, pick the most common/main entrance.  
- Always include both **Start** and **End**.  
- Limit the total number of waypoints to 20.  
- Return the output strictly in this format:

Example:
####  
- Begin your run at the iconic **Arco della Pace**, Piazza Sempione. Enjoy the surrounding park and monuments.  
- Run along **Corso Sempione** towards **Via Melzi d'Eril**, a quieter street perfect for jogging.  
- Enter **Parco Sempione** at the Viale Elvezia entrance, enjoy the paths past the **Civic Aquarium of Milan**.  
- Continue toward the majestic **Castello Sforzesco**, crossing **Piazza Castello**.  
- Take **Via Legnano** back towards the starting area.  
- Finish at **Arco della Pace**, Piazza Sempione.
####

Output:
Start: Arco della Pace, Piazza Sempione, Milan, Italy, 20154  
End: Arco della Pace, Piazza Sempione, Milan, Italy, 20154  
Waypoints: [
    "Intersection of Corso Sempione and Via Melzi d'Eril, Milan, Italy, 20154",
    "Entrance of Parco Sempione at Viale Elvezia, Milan, Italy, 20154",
    "Civic Aquarium of Milan, Viale Gadio 2, Milan, Italy, 20154",
    "Castello Sforzesco, Piazza Castello, Milan, Italy, 20121",
    "Via Legnano, Milan, Italy, 20145"
]

{format_instructions}
"""

        self.human_template = """
      ####{agent_suggestion}####
    """

        self.parser = PydanticOutputParser(pydantic_object=ItineraryPlanSchema)

        self.system_message_prompt = SystemMessagePromptTemplate.from_template(
            self.system_template,
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()
            },
        )
        self.human_message_prompt = HumanMessagePromptTemplate.from_template(
            self.human_template, input_variables=["agent_suggestion"]
        )

        self.chat_prompt = ChatPromptTemplate.from_messages(
            [self.system_message_prompt, self.human_message_prompt]
        )
    
    def __call__(self):
        return self.chat_prompt
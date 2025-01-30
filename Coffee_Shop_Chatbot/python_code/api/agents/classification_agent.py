from dotenv import load_dotenv
import os
import json
from copy import deepcopy
from .utils import get_chatbot_response, double_check_json_output
from openai import OpenAI
load_dotenv()

class ClassificationAgent():
    def __init__(self):
        try:
            self.client = OpenAI(
                api_key=os.getenv("RUNPOD_TOKEN"),
                base_url=os.getenv("RUNPOD_CHATBOT_URL"),
                http_client=None  # Prevent runpod from injecting its own http client
            )
        except TypeError as e:
            # Fallback initialization if the above fails
            self.client = OpenAI(
                api_key=os.getenv("RUNPOD_TOKEN"),
                base_url=os.getenv("RUNPOD_CHATBOT_URL")
            )
        self.model_name = os.getenv("MODEL_NAME")
    
    def get_response(self,messages):
        messages = deepcopy(messages)

        system_prompt = """You are a helpful AI assistant for a coffee shop application.
Your task is to determine what agent should handle the user input. You have 3 agents to choose from:

1. details_agent: This agent handles:
   * Questions about the coffee shop (location, hours, etc.)
   * Questions about menu items and their details
   * Questions about prices (e.g., "How much is a latte?")
   * General inquiries about what we offer

2. order_taking_agent: This agent handles:
   * Taking new orders
   * Adding items to existing orders
   * When users want to purchase something
   * Explicit ordering intent (e.g., "I want", "I'll have", "Can I get")

3. recommendation_agent: This agent handles:
   * Requests for suggestions
   * "What do you recommend?"
   * Best seller inquiries
   * Pairing suggestions

IMPORTANT: Your response must be a valid JSON object with no extra characters, whitespace, or formatting. The decision MUST be one of these exact values: "details_agent", "order_taking_agent", or "recommendation_agent". No other values are allowed.

Follow this exact format:
{"chain_of_thought":"your analysis of which agent is most appropriate","decision":"details_agent OR order_taking_agent OR recommendation_agent","message":""}

Examples of valid responses:
{"chain_of_thought":"User is asking about menu items","decision":"details_agent","message":""}
{"chain_of_thought":"User is asking about prices","decision":"details_agent","message":""}
{"chain_of_thought":"User wants to purchase items","decision":"order_taking_agent","message":""}
{"chain_of_thought":"User is asking for suggestions","decision":"recommendation_agent","message":""}

Key rules:
* Price inquiries go to details_agent (e.g., "How much is X?", "What's the price of Y?")
* Actual orders go to order_taking_agent (e.g., "I'll have X", "Can I get Y?")
* Recommendation requests go to recommendation_agent (e.g., "What do you recommend?")"""
        
        input_messages = [
            {"role": "system", "content": system_prompt},
        ]

        input_messages += messages[-3:]

        chatbot_output = get_chatbot_response(self.client,self.model_name,input_messages)
        chatbot_output = double_check_json_output(self.client,self.model_name,chatbot_output)
        output = self.postprocess(chatbot_output)
        return output

    def postprocess(self,output):
        print("Raw output:", repr(output))  # Show exact string including whitespace
        try:
            output = json.loads(output)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {str(e)}")
            return self._get_fallback_response()

        # Validate decision value
        valid_decisions = ["details_agent", "order_taking_agent", "recommendation_agent"]
        if 'decision' not in output or output['decision'] not in valid_decisions:
            print(f"Invalid decision value: {output.get('decision', 'missing')}")
            return self._get_fallback_response()

        dict_output = {
            "role": "assistant",
            "content": output.get('message', ''),
            "memory": {
                "agent": "classification_agent",
                "classification_decision": output['decision']
            }
        }
        return dict_output

    def _get_fallback_response(self):
        return {
            "role": "assistant",
            "content": "I apologize, but I encountered an error. Please try again.",
            "memory": {
                "agent": "classification_agent",
                "classification_decision": "order_taking_agent"  # Default to order taking since that's most common
            }
        }

from dotenv import load_dotenv
import os
import json
from copy import deepcopy
from .utils import get_chatbot_response, double_check_json_output
from openai import OpenAI
load_dotenv()

class GuardAgent():
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

        system_prompt = """You are a helpful AI assistant for a coffee shop application which serves drinks and pastries.
Your task is to determine whether the user is asking something relevant to the coffee shop or not.

The user is allowed to:
1. Ask questions about the coffee shop, like location, working hours, menu items and coffee shop related questions.
2. Ask questions about menu items, they can ask for ingredients in an item and more details about the item.
3. Make an order or add items to their order.
4. Ask about recommendations of what to buy.

The user is NOT allowed to:
1. Ask questions about anything else other than our coffee shop.
2. Ask questions about the staff or how to make a certain menu item.

IMPORTANT: Your response MUST be a valid JSON object with EXACTLY these fields:
{
    "chain_of_thought": "your analysis of whether the input is allowed",
    "decision": "allowed" or "not_allowed" (ONLY these two values are valid),
    "message": "error message if not allowed, empty string if allowed"
}

Examples of valid responses:
{"chain_of_thought":"User is asking about menu items","decision":"allowed","message":""}
{"chain_of_thought":"User is placing an order","decision":"allowed","message":""}
{"chain_of_thought":"User is asking about staff","decision":"not_allowed","message":"I apologize, but I cannot provide information about our staff."}

DO NOT include any order details, prices, or calculations in your response. Your only job is to determine if the user's request is allowed."""
        
        input_messages = [{"role": "system", "content": system_prompt}] + messages[-3:]

        chatbot_output = get_chatbot_response(self.client,self.model_name,input_messages)
        chatbot_output = double_check_json_output(self.client,self.model_name,chatbot_output)
        output = self.postprocess(chatbot_output)
        
        return output

    def postprocess(self,output):
        print("Raw output:", repr(output))  # Show exact string including whitespace
        try:
            output = json.loads(output)
            
            # Validate required fields
            required_fields = ["chain_of_thought", "decision", "message"]
            for field in required_fields:
                if field not in output:
                    print(f"Missing required field: {field}")
                    return self._get_fallback_response()
            
            # Validate decision value
            if output["decision"] not in ["allowed", "not_allowed"]:
                print(f"Invalid decision value: {output['decision']}")
                return self._get_fallback_response()

            dict_output = {
                "role": "assistant",
                "content": output['message'] if output['decision'] == "not_allowed" else "",
                "memory": {
                    "agent": "guard_agent",
                    "guard_decision": output['decision']
                }
            }
            return dict_output

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error processing output: {str(e)}")
            return self._get_fallback_response()

    def _get_fallback_response(self):
        return {
            "role": "assistant",
            "content": "",
            "memory": {
                "agent": "guard_agent",
                "guard_decision": "allowed"  # Default to allowed to let other agents handle it
            }
        }

import os
import json
from .utils import get_chatbot_response,double_check_json_output
from openai import OpenAI
from copy import deepcopy
from dotenv import load_dotenv
load_dotenv()


class OrderTakingAgent():
    # Define menu prices as a class variable
    menu_prices = {
        "Cappuccino": 4.50,
        "Jumbo Savory Scone": 3.25,
        "Latte": 4.75,
        "Chocolate Chip Biscotti": 2.50,
        "Espresso shot": 2.00,
        "Hazelnut Biscotti": 2.75,
        "Chocolate Croissant": 3.75,
        "Dark chocolate (Drinking Chocolate)": 5.00,
        "Cranberry Scone": 3.50,
        "Croissant": 3.25,
        "Almond Croissant": 4.00,
        "Ginger Biscotti": 2.50,
        "Oatmeal Scone": 3.25,
        "Ginger Scone": 3.50,
        "Chocolate syrup": 1.50,
        "Hazelnut syrup": 1.50,
        "Caramel syrup": 1.50,
        "Sugar Free Vanilla syrup": 1.50,
        "Dark chocolate (Packaged Chocolate)": 3.00
    }

    def __init__(self, recommendation_agent):
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

        self.recommendation_agent = recommendation_agent
    
    def get_response(self,messages):
        messages = deepcopy(messages)
        system_prompt = """
            You are a customer support Bot for a coffee shop called "Merry's way"

            Here is the menu for this coffee shop:
            Cappuccino - $4.50
            Jumbo Savory Scone - $3.25
            Latte - $4.75
            Chocolate Chip Biscotti - $2.50
            Espresso shot - $2.00
            Hazelnut Biscotti - $2.75
            Chocolate Croissant - $3.75
            Dark chocolate (Drinking Chocolate) - $5.00
            Cranberry Scone - $3.50
            Croissant - $3.25
            Almond Croissant - $4.00
            Ginger Biscotti - $2.50
            Oatmeal Scone - $3.25
            Ginger Scone - $3.50
            Chocolate syrup - $1.50
            Hazelnut syrup - $1.50
            Caramel syrup - $1.50
            Sugar Free Vanilla syrup - $1.50
            Dark chocolate (Packaged Chocolate) - $3.00

            Special Instructions:
            * When a user orders syrups, treat them as separate items in the order array
            * For example, if they order "2 caramel syrup", add it as {"item": "Caramel syrup", "quantity": 2, "price": 1.50}
            * Keep track of all items separately in the order array, don't combine or merge items

            Things to NOT DO:
            * DON'T ask how to pay by cash or Card
            * Don't tell the user to go to the counter
            * Don't tell the user to go to place to get the order

            Your task is as follows:
            1. Take the User's Order
            2. Validate that all their items are in the menu
            3. If an item is not in the menu let the user know and repeat back the remaining valid order
            4. Ask them if they need anything else
            5. If they do then repeat starting from step 3
            6. If they say "no" to recommendations or additional items:
                1. List down all the items and their prices
                2. Calculate the total
                3. Thank the user for the order and close the conversation with no more questions
            7. Do not ask if they want anything else after they say "no"

            The user message will contain a section called memory with "order" and "step number".
            Use this information to determine the next step in the process.
            
            IMPORTANT: Your response MUST be a valid JSON object with ALL of these fields:
            {
                "chain_of_thought": "Your analysis of the current step and how to respond",
                "step_number": "Current step number (1-7)",
                "order": [
                    {
                        "item": "Exact item name from menu",
                        "quantity": number,
                        "price": number
                    }
                ],
                "response": "Your response to the user"
            }

            Example of valid responses:
            {
                "chain_of_thought": "User ordered 2 lattes, need to ask if they want anything else",
                "step_number": "4",
                "order": [{"item": "Latte", "quantity": 2, "price": 4.75}],
                "response": "I've added 2 lattes to your order. Would you like anything else?"
            }

            {
                "chain_of_thought": "User ordered 2 caramel syrups to add to their order",
                "step_number": "4",
                "order": [
                    {"item": "Latte", "quantity": 2, "price": 4.75},
                    {"item": "Caramel syrup", "quantity": 2, "price": 1.50}
                ],
                "response": "I've added 2 caramel syrups to your order. Would you like anything else?"
            }

            IMPORTANT: When calculating totals, multiply each item's price by its quantity and sum all items.
            For example, with the order above:
            - 2 Lattes: 2 × $4.75 = $9.50
            - 2 Caramel syrups: 2 × $1.50 = $3.00
            Total: $12.50

            Always maintain the current order items in the order array, don't lose previous items when adding new ones.
        """

        last_order_taking_status = ""
        asked_recommendation_before = False
        for message_index in range(len(messages)-1,0,-1):
            message = messages[message_index]
            
            agent_name = message.get("memory",{}).get("agent","")
            if message["role"] == "assistant" and agent_name == "order_taking_agent":
                step_number = message["memory"]["step number"]
                order = message["memory"]["order"]
                asked_recommendation_before = message["memory"]["asked_recommendation_before"]
                last_order_taking_status = f"""
                step number: {step_number}
                order: {order}
                """
                break

        messages[-1]['content'] = last_order_taking_status + " \n "+ messages[-1]['content']

        input_messages = [{"role": "system", "content": system_prompt}] + messages        

        chatbot_output = get_chatbot_response(self.client,self.model_name,input_messages)

        # double check json 
        chatbot_output = double_check_json_output(self.client,self.model_name,chatbot_output)

        output = self.postprocess(chatbot_output,messages,asked_recommendation_before)

        return output

    def postprocess(self,output,messages,asked_recommendation_before):
        try:
            if isinstance(output, str):
                output = json.loads(output)

            # Validate required fields
            required_fields = ["chain_of_thought", "step_number", "order", "response"]
            for field in required_fields:
                if field not in output:
                    print(f"Missing required field: {field}")
                    return self._get_fallback_response(messages, asked_recommendation_before)

            # Ensure order is a list
            if isinstance(output["order"], str):
                output["order"] = json.loads(output["order"])
            if not isinstance(output["order"], list):
                print("Order field must be a list")
                return self._get_fallback_response(messages, asked_recommendation_before)

            # Validate each order item
            for item in output["order"]:
                required_item_fields = ["item", "quantity", "price"]
                for field in required_item_fields:
                    normalized_field = "quantity" if field == "quanitity" else field
                    if field not in item and normalized_field not in item:
                        print(f"Order item missing field: {field}")
                        return self._get_fallback_response(messages, asked_recommendation_before)

            response = output['response']
            last_user_message = messages[-1]["content"].lower().strip()
            
            if last_user_message == "no":
                # Calculate total and format order summary
                total = 0
                order_summary = "Here's your order summary:\n\n"
                
                for item in output["order"]:
                    quantity = item.get("quantity", item.get("quanitity", 0))  # Handle both spellings
                    # Use menu price instead of item price to ensure accuracy
                    if item["item"] in self.menu_prices:
                        price = self.menu_prices[item["item"]]
                        item_total = price * quantity
                        total += item_total
                        order_summary += f"{item['item']} x{quantity} - ${item_total:.2f}\n"
                    else:
                        print(f"Warning: Item not found in menu: {item['item']}")
                
                order_summary += f"\nTotal: ${total:.2f}\n\nThank you for your order!"
                response = order_summary
                asked_recommendation_before = True
                output["step_number"] = "6"  # Use consistent field name
            elif not asked_recommendation_before and len(output["order"]) > 0:
                # Get recommendations but keep them separate from the order
                recommendation_output = self.recommendation_agent.get_recommendations_from_order(messages, output['order'])
                
                # Calculate current order total first
                total = 0
                order_summary = "Here's your current order:\n\n"
                for item in output["order"]:
                    quantity = item.get("quantity", item.get("quanitity", 0))
                    if item["item"] in self.menu_prices:
                        price = self.menu_prices[item["item"]]
                        item_total = price * quantity
                        total += item_total
                        order_summary += f"{item['item']} x{quantity} - ${item_total:.2f}\n"
                
                order_summary += f"\nTotal: ${total:.2f}\n\n"
                order_summary += "Recommendations based on your order:\n"
                order_summary += recommendation_output['content']
                order_summary += "\nWould you like to add any of these items to your order?"
                
                response = order_summary
                asked_recommendation_before = True

            dict_output = {
                "role": "assistant",
                "content": response,
                "memory": {
                    "agent": "order_taking_agent",
                    "step number": output["step_number"],  # Use the normalized field name
                    "order": output["order"],
                    "asked_recommendation_before": asked_recommendation_before
                }
            }
            return dict_output

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"Error processing output: {str(e)}")
            return self._get_fallback_response(messages, asked_recommendation_before)

    def _get_fallback_response(self, messages, asked_recommendation_before):
        # Try to preserve existing order if available
        existing_order = []
        for message in reversed(messages):
            if message.get("memory", {}).get("agent") == "order_taking_agent":
                existing_order = message["memory"].get("order", [])
                break

        return {
            "role": "assistant",
            "content": "I apologize, but I'm having trouble processing your order. Could you please repeat your last request?",
            "memory": {
                "agent": "order_taking_agent",
                "step number": "1",  # Reset to initial step
                "order": existing_order,  # Preserve existing order
                "asked_recommendation_before": asked_recommendation_before
            }
        }

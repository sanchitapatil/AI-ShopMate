from dotenv import load_dotenv
import os
from .utils import get_chatbot_response,get_embedding
from openai import OpenAI
from copy import deepcopy
from pinecone import Pinecone
load_dotenv()

class DetailsAgent():
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

        try:
            self.embedding_client = OpenAI(
                api_key=os.getenv("RUNPOD_TOKEN"),
                base_url=os.getenv("RUNPOD_EMBEDDING_URL"),
                http_client=None  # Prevent runpod from injecting its own http client
            )
        except TypeError as e:
            # Fallback initialization if the above fails
            self.embedding_client = OpenAI(
                api_key=os.getenv("RUNPOD_TOKEN"),
                base_url=os.getenv("RUNPOD_EMBEDDING_URL")
            )
        self.model_name = os.getenv("MODEL_NAME")
        self.pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index_name = os.getenv("PINECONE_INDEX_NAME")
    
    def get_closest_results(self,index_name,input_embeddings,top_k=2):
        index = self.pc.Index(index_name)
        
        results = index.query(
            namespace="ns1",
            vector=input_embeddings,
            top_k=top_k,
            include_values=False,
            include_metadata=True
        )

        return results

    def get_response(self,messages):
        messages = deepcopy(messages)

        user_message = messages[-1]['content']
        embedding = get_embedding(self.embedding_client,self.model_name,user_message)[0]
        result = self.get_closest_results(self.index_name,embedding)
        source_knowledge = "\n".join([x['metadata']['text'].strip()+'\n' for x in result['matches'] ])

        prompt = f"""
        Using the contexts below, answer the query.

        Contexts:
        {source_knowledge}

        Query: {user_message}
        """

        system_prompt = """You are a customer support agent for a coffee shop called "Merry's way".

        Here is our menu with prices:
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

        Your tasks:
        1. Answer questions about menu items, including prices
        2. Provide information about ingredients and item details
        3. Answer questions about the coffee shop
        4. Be friendly and helpful, like a knowledgeable waiter

        When asked about prices:
        * Always provide the exact price from the menu
        * Be clear and direct about the price
        * You can suggest complementary items but don't be pushy

        Example responses:
        Q: How much is a croissant?
        A: A croissant is $3.25. It's one of our freshly baked pastries.

        Q: What's the price of a latte?
        A: A latte costs $4.75. You can also add any of our flavored syrups for $1.50 each if you'd like."""
        messages[-1]['content'] = prompt
        input_messages = [{"role": "system", "content": system_prompt}] + messages[-3:]

        chatbot_output =get_chatbot_response(self.client,self.model_name,input_messages)
        output = self.postprocess(chatbot_output)
        return output

    def postprocess(self,output):
        output = {
            "role": "assistant",
            "content": output,
            "memory": {"agent":"details_agent"
                      }
        }
        return output

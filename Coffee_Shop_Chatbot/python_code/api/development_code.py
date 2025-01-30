from agents import (GuardAgent,
                    ClassificationAgent,
                    DetailsAgent,
                    OrderTakingAgent,
                    RecommendationAgent,
                    AgentProtocol
                    )
from typing import Dict
import os
import pathlib
folder_path = pathlib.Path(__file__).parent.resolve()


def main():
    guard_agent = GuardAgent()
    classification_agent = ClassificationAgent()  
    recommendation_agent =  RecommendationAgent(
        os.path.join(folder_path,'recommendation_objects/apriori_recommendations.json'),
        os.path.join(folder_path,'recommendation_objects/popularity_recommendation.csv'))
    
    # print(recommendation_agent.get_apriori_recommendation(['Latte']))
    agent_dict: Dict[str, AgentProtocol] = {
        "details_agent": DetailsAgent(),
        "recommendation_agent": recommendation_agent,
        "order_taking_agent": OrderTakingAgent(recommendation_agent)                                                                               
    }
    
    messages = []
    while True:
        # Display the chat history
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("\n\nPrint Messages ...............")
        for message in messages:
            print(f"{message['role'].capitalize()}: {message['content']}")

        # Get user input
        prompt = input("User: ")
        messages.append({"role": "user", "content": prompt})

        # Get GuardAgent's response
        guard_agent_response = guard_agent.get_response(messages)
        if guard_agent_response["memory"]["guard_decision"] == "not_allowed":
            messages.append(guard_agent_response)
            continue

        # Get Classification Agent's Response
        classification_agent_response = classification_agent.get_response(messages)
        chosen_agent = classification_agent_response["memory"]["classification_decision"]

        #Get the choosen Agents Response
        agent = agent_dict[chosen_agent]
        response = agent.get_response(messages)
        messages.append(response)

if __name__ == "__main__":
    main()

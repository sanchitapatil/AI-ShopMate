import json

def get_chatbot_response(client,model_name,messages,temperature=0):
    input_messages = []
    for message in messages:
        # Validate message object
        if not message or not isinstance(message, dict):
            print(f"Invalid message object: {message}")
            continue
            
        # Get role and content with defaults
        role = message.get("role", "user")
        content = message.get("content", "")
        
        if not content:
            print(f"Empty content in message: {message}")
            continue
            
        input_messages.append({"role": role, "content": content})
    
    # Ensure we have at least one valid message
    if not input_messages:
        print("No valid messages found")
        return '{"error": "No valid messages found"}'

    response = client.chat.completions.create(
        model=model_name,
        messages=input_messages,
        temperature=temperature,
        top_p=0.8,
        max_tokens=2000,
    ).choices[0].message.content
    
    return response

def get_embedding(embedding_client,model_name,text_input):
    output = embedding_client.embeddings.create(input = text_input,model=model_name)
    
    embedings = []
    for embedding_object in output.data:
        embedings.append(embedding_object.embedding)

    return embedings

def double_check_json_output(client,model_name,json_string):
    prompt = f"""Fix this JSON string if needed and return ONLY the valid JSON with no extra characters or whitespace. 
If it's already valid, return it exactly as is. The output must be parseable by json.loads().

Rules:
1. Remove any leading/trailing whitespace
2. Ensure proper quote usage (double quotes for keys and string values)
3. No comments or extra text allowed
4. No formatting or pretty printing
5. Must be a single line

Input JSON string to validate:
{json_string}"""

    messages = [{"role": "user", "content": prompt}]
    response = get_chatbot_response(client,model_name,messages)
    
    # Try to parse the response to verify it's valid JSON
    try:
        json.loads(response.strip())
        return response.strip()
    except json.JSONDecodeError:
        # If parsing fails, try to extract JSON from response
        try:
            # Look for content between first { and last }
            start = response.find('{')
            end = response.rfind('}') + 1
            if start >= 0 and end > start:
                extracted = response[start:end]
                json.loads(extracted)  # Validate it's valid JSON
                return extracted
        except (json.JSONDecodeError, ValueError):
            pass
        
        # If all attempts fail, return a minimal valid JSON
        return '{"chain of thought":"Error processing input","decision":"order_taking_agent","message":""}'

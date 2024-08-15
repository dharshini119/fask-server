import json
import random
import asyncio
import aiohttp
from flask import Flask, request, jsonify
import time
import google.generativeai as genai
from flask_cors import CORS
from functools import lru_cache
app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Define your API key for Gemini
API_KEY = 'AIzaSyDPqZG3lgE9Z0VTlsFqPHOB6a4mtUjeN28'

def get_input_and_send_to_gemini(query):
    # List of known items for 
    if query:
        user_input = query
    else:
        user_input = 'plastic spoon' 

    genai.configure(api_key=API_KEY)

    # Create the model
    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "application/json",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    chat_session = model.start_chat(
        history=[
            {
                "role": "user",
                "parts": [
                    "Please provide a JSON-formatted list of up to three eco-friendly alternatives for the following plastic product:\n\n**Plastic Item**: [Specify one plastic item here, e.g., \"plastic spoon\"]\n\nThe JSON object should follow this format:\n\n{\n  \"plastic item\": [\"eco_alternative1\", \"eco_alternative2\", \"eco_alternative3\"]\n}\n\nEnsure the list contains exactly three elements if possible. If fewer alternatives are relevant, include as many as applicable.\n\nIf the specified plastic item is \"plastic spoon\", the output should look like this:\n\n{\n  \"plastic spoon\": [\"biodegradable spoon\", \"compostable spoon\", \"wooden spoon\"]\n}\n",
                ],
            },
            {
                "role": "model",
                "parts": [
                    "```json\n{\"plastic spoon\": [\"biodegradable spoon\", \"compostable spoon\", \"wooden spoon\"]}\n\n```",
                ],
            },
            {
                "role": "user",
                "parts": [
                    "format :\n\n{ name : [ 'eco_alternative1','eco_alternative2',''eco_alternative3'] }\n",
                ],
            },
            {
                "role": "model",
                "parts": [
                    "```json\n{\"plastic bag\": [\"reusable tote bag\", \"mesh produce bag\", \"paper bag\"]}\n\n```",
                ],
            },
        ]
    )

    response = chat_session.send_message(f'''Please provide a JSON-formatted list of up to three eco-friendly alternatives for the following plastic product:

    **Plastic Item:** {user_input}

    The JSON object should follow this format:

    {{
      "result": ["eco_alternative1", "eco_alternative2", "eco_alternative3"]
    }}

    Ensure the list contains exactly three elements if possible. If fewer alternatives are relevant, include as many as applicable.

    If the specified plastic item is "plastic spoon", the output should look like this:

    {{
      "result": ["biodegradable spoon", "compostable spoon", "wooden spoon"]
    }}
    ''')
    return response.text

async def fetch_amazon_data(session, search_term):
    payload = {
        'source': 'amazon_search',
        'domain': 'in',
        'query': search_term,
        'start_page': 1,
        'pages': 1,
        'parse': True,
    }

    async with session.post(
        'https://realtime.oxylabs.io/v1/queries',
        auth=aiohttp.BasicAuth('sparkathon_Im4mr', 'spark24+PITIT'),
        json=payload
    ) as response:
        data = await response.json()
        return data

async def get_response_from_amazon(search_term):
    async with aiohttp.ClientSession() as session:
        data = await fetch_amazon_data(session, search_term)
        
        filtered_dict = dict(data)['results'][0]['content']['results']['organic'][:10]

        rating_list = [i.get('rating', 0) for i in filtered_dict]

        def find_max_with_index(rating_list):
            if not rating_list:
                return None

            max_value = rating_list[0]
            max_index = 0

            for index, value in enumerate(rating_list):
                if value > max_value:
                    max_value = value
                    max_index = index

            return max_index

        def get_details_for_the_given_index(index):
            item = filtered_dict[index]
            url = item.get('url', '')
            title = item.get('title', 'No Title')
            img_url = item.get('url_image', '')
            price = item.get('price', 'No Price')
            return url, title, img_url, price

        max_index = find_max_with_index(rating_list)

        if max_index is not None:
            url, title, img_url, price = get_details_for_the_given_index(max_index)
            return {'image': img_url, 'price': price, 'url': url, 'title': title }
        else:
            return {}

@app.route('/')
def get_alternative_titles():
    query = request.args.get('query', default=None, type=str)

    @lru_cache(maxsize=None)
    async def main(query):
        start_time = time.time()

        response_data = get_input_and_send_to_gemini(query)
        response_data = json.loads(response_data)
        response_data1 = response_data.get('result', [])
        final_list = list(response_data1)

        tasks = [get_response_from_amazon(eco_alternative) for eco_alternative in final_list]
        responses = await asyncio.gather(*tasks)

        final_values = [response for response in responses if response]

        json_data = json.dumps(final_values)
        end_time = time.time()

        execution_time = end_time - start_time
        print(f"Execution time: {execution_time} seconds")
        print(f"Final data to return: {json_data}")
        return json_data

    return asyncio.run(main(query))

if __name__ == '__main__':
    app.run(debug=True)

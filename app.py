from dotenv import load_dotenv
import chainlit as cl
from dotenv import load_dotenv
from movie_function import get_now_playing_movies, get_reviews, get_showtimes
import json

load_dotenv()

# Note: If switching to LangSmith, uncomment the following, and replace @observe with @traceable
# from langsmith.wrappers import wrap_openai
# from langsmith import traceable
# client = wrap_openai(openai.AsyncClient())

from langfuse.decorators import observe
from langfuse.openai import AsyncOpenAI
 
client = AsyncOpenAI()

gen_kwargs = {
    "model": "gpt-4o",
    "temperature": 0.2,
    "max_tokens": 500
}

SYSTEM_PROMPT = """\
You are a movie booking assistant. You are provided with the following tools:
- get_now_playing_movies: Returns a list of movies currently playing in theaters.
- get_showtimes: Returns the showtimes for a given movie in a given location.
You can use these tools to answer user questions about movies.
If a user is asking about movies currently playing, use get_now_playing_movies().
If a user is asking about showtimes for a movie, use get_showtimes(title, location).
When using a function, respond in this format:
{ "function_call": { "name": "function_name", "arguments": "arguments" } }
"""

@observe
@cl.on_chat_start
def on_chat_start():    
    message_history = [{"role": "system", "content": SYSTEM_PROMPT}]
    cl.user_session.set("message_history", message_history)

@observe
async def generate_response(client, message_history, gen_kwargs):
    response_message = cl.Message(content="")
    await response_message.send()

    stream = await client.chat.completions.create(messages=message_history, stream=True, **gen_kwargs)
    async for part in stream:
        if token := part.choices[0].delta.content or "":
            await response_message.stream_token(token)
    
    await response_message.update()

    return response_message

@cl.on_message
@observe
async def on_message(message: cl.Message):
    message_history = cl.user_session.get("message_history", [])
    message_history.append({"role": "user", "content": message.content})
    
    response_message = await generate_response(client, message_history, gen_kwargs)
    
    while "function_call" in response_message.content:
        response_content = json.loads(response_message.content)
        function_name = response_content["function_call"]["name"]
        arguments = response_content["function_call"]["arguments"]
        
        # Call the appropriate function
        if function_name == "get_now_playing_movies":
            result = get_now_playing_movies()
        elif function_name == "get_showtimes":
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            title = arguments.get("title")
            location = arguments.get("location")
            result = get_showtimes(title, location)
        elif function_name == "buy_ticket":
            confirm_ticket_purchase(theater, movie, showtime)
        else:
            result = f"Error: Unknown function '{function_name}'"
        
        # Add the function result to the message history
        message_history.append({"role": "function", "name": function_name, "content": result})
        
        # Generate a new response based on the function result
        response_message = await generate_response(client, message_history, gen_kwargs)

    # Check if the response is a function call
    message_history.append({"role": "assistant", "content": response_message.content})
    cl.user_session.set("message_history", message_history)

def confirm_ticket_purchase(theater, movie, showtime):
    return 
    

if __name__ == "__main__":
    cl.main()

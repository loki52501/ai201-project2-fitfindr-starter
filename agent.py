import json
import os
from dotenv import load_dotenv
from groq import Groq
from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = (
    "You are FitFindr, a friendly thrift shopping assistant. Help users find secondhand clothing "
    "and style it with their wardrobe. When a user asks about finding something, use search_listings "
    "first, then suggest_outfit with the best match, then create_fit_card to present the result. "
    "Always use all three tools in sequence for a complete recommendation."
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "search_listings",
            "description": "Search secondhand listings by style/description keywords, size, and max price",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "Style keywords, item type, aesthetic"},
                    "size": {"type": "string", "description": "Size filter (optional)"},
                    "max_price": {"type": "number", "description": "Maximum price filter (optional)"},
                },
                "required": ["description"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "suggest_outfit",
            "description": "Suggest an outfit pairing a new thrifted item with pieces from the user's wardrobe",
            "parameters": {
                "type": "object",
                "properties": {
                    "new_item": {
                        "type": "object",
                        "description": "The new thrifted item to style (a listing dict with keys like title, price, size, etc.)",
                    },
                },
                "required": ["new_item"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_fit_card",
            "description": "Generate a formatted markdown fit card summarizing the outfit recommendation",
            "parameters": {
                "type": "object",
                "properties": {
                    "outfit": {
                        "type": "object",
                        "description": "Outfit dict with outfit_pieces and styling_notes keys",
                    },
                    "new_item": {
                        "type": "object",
                        "description": "The new thrifted item being featured",
                    },
                },
                "required": ["outfit", "new_item"],
            },
        },
    },
]


def run_agent(user_query: str, wardrobe: dict = None) -> str:
    """
    Run the FitFindr agent for a single user query.
    Returns the final response string (usually a fit card or error message).
    """
    if wardrobe is None:
        from utils.data_loader import get_example_wardrobe
        wardrobe = get_example_wardrobe()

    tool_map = {
        "search_listings": search_listings,
        "suggest_outfit": lambda **kwargs: suggest_outfit(kwargs["new_item"], wardrobe),
        "create_fit_card": create_fit_card,
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    for _ in range(6):
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )

        choice = response.choices[0]
        messages.append(choice.message)

        if not choice.message.tool_calls:
            return choice.message.content

        for tool_call in choice.message.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            result = tool_map[name](**args)

            # Surface empty search results explicitly so the LLM can respond helpfully
            if name == "search_listings" and isinstance(result, list) and len(result) == 0:
                result = "No listings found"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return response.choices[0].message.content or "Unable to complete recommendation after maximum iterations."


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe
    wardrobe = get_example_wardrobe()
    query = input("What are you looking for? ")
    print(run_agent(query, wardrobe))
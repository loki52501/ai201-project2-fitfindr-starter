import os
from dotenv import load_dotenv
from groq import Groq
from utils.data_loader import load_listings

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def search_listings(description: str, size: str = None, max_price: float = None) -> list[dict]:
    try:
        listings = load_listings()
    except Exception:
        return []

    query_words = description.lower().split()

    def count_matches(listing):
        searchable = " ".join([
            listing.get("title", ""),
            listing.get("description", ""),
            " ".join(listing.get("style_tags", [])),
            listing.get("category", ""),
            " ".join(listing.get("colors", [])),
        ]).lower()
        return sum(1 for word in query_words if word in searchable)

    results = []
    for listing in listings:
        if count_matches(listing) == 0:
            continue

        if size is not None:
            listing_size = listing.get("size", "").lower()
            size_lower = size.lower()
            if size_lower not in listing_size and listing_size not in size_lower:
                continue

        if max_price is not None:
            if listing.get("price", float("inf")) > max_price:
                continue

        results.append((count_matches(listing), listing))

    results.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in results[:5]]


def suggest_outfit(new_item: dict, wardrobe: dict) -> dict:
    items = wardrobe.get("items", [])
    if not items:
        return {"outfit_pieces": [], "styling_notes": "No wardrobe items available to suggest an outfit."}

    item_names = [item.get("name", str(item)) for item in items]
    wardrobe_list = "\n".join(f"- {name}" for name in item_names)

    prompt = f"""You are a fashion stylist. A thrifter just found this item:
Title: {new_item.get('title', 'Unknown')}
Category: {new_item.get('category', 'Unknown')}
Style Tags: {', '.join(new_item.get('style_tags', []))}
Colors: {', '.join(new_item.get('colors', []))}

Their current wardrobe includes:
{wardrobe_list}

Select 2-4 wardrobe pieces that pair well with the new item to create a cohesive outfit. Explain why they work together.

Respond in this exact format:
OUTFIT PIECES: <comma-separated list of wardrobe item names>
STYLING NOTES: <one paragraph explanation>"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content.strip()

        outfit_pieces = []
        styling_notes = ""

        for line in text.splitlines():
            if line.startswith("OUTFIT PIECES:"):
                raw = line.replace("OUTFIT PIECES:", "").strip()
                outfit_pieces = [p.strip() for p in raw.split(",") if p.strip()]
            elif line.startswith("STYLING NOTES:"):
                styling_notes = line.replace("STYLING NOTES:", "").strip()

        if not styling_notes:
            styling_notes = text

        return {"outfit_pieces": outfit_pieces, "styling_notes": styling_notes}
    except Exception:
        return {"outfit_pieces": [], "styling_notes": "Could not generate outfit suggestion."}


def create_fit_card(outfit: dict, new_item: dict) -> str:
    outfit_pieces = outfit.get("outfit_pieces", [])
    styling_notes = outfit.get("styling_notes", "")

    fallback = f"""# 🛍️ {new_item.get('title', 'Thrift Find')}

**💰 Price:** ${new_item.get('price', 'N/A')}
**📦 Platform:** {new_item.get('platform', 'N/A')}
**🏷️ Category:** {new_item.get('category', 'N/A')}
**🎨 Colors:** {', '.join(new_item.get('colors', []))}
**✨ Style Tags:** {', '.join(new_item.get('style_tags', []))}
"""

    if not outfit_pieces and not styling_notes:
        return fallback

    prompt = f"""You are a fashion content creator. Create a compelling fit card in markdown for this thrift find:

Item: {new_item.get('title', 'Unknown')}
Price: ${new_item.get('price', 'N/A')}
Platform: {new_item.get('platform', 'N/A')}
Colors: {', '.join(new_item.get('colors', []))}
Style Tags: {', '.join(new_item.get('style_tags', []))}
Category: {new_item.get('category', 'N/A')}

Outfit Pieces to pair with it:
{chr(10).join(f'- {p}' for p in outfit_pieces)}

Styling Notes: {styling_notes}

Write a clean markdown fit card with emoji headers that includes:
- The item name and price
- The platform it's from
- The outfit pieces to pair with it
- The styling notes
- A short vibe/aesthetic description

Keep it fun, concise, and stylish."""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return fallback

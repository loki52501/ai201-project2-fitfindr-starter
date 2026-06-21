# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Tool Inventory

| Tool | Inputs | Return value |
|------|--------|--------------|
| `search_listings` | `description: str`, `size: str = None`, `max_price: float = None` | `list[dict]` — up to 5 matching listings, each with: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, `platform`. Empty list if no matches. |
| `suggest_outfit` | `new_item: dict`, `wardrobe: dict` | `dict` with keys: `outfit_pieces` (list of wardrobe item name strings), `styling_notes` (str explaining the pairing). |
| `create_fit_card` | `outfit: dict`, `new_item: dict` | `str` — a markdown-formatted fit card with the item info, outfit pieces, styling notes, and a vibe description. |

---

## Interaction Walkthrough

**User query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers."

**Step 1 — Tool called:**
- Tool: `search_listings`
- Input: `description="vintage graphic tee"`, `max_price=30.0`
- Why this tool: The user named an item type and a price ceiling — search_listings filters the dataset by both keyword match and price before any LLM call is made.
- Output: `[{"id": "lst_002", "title": "Y2K Baby Tee — Butterfly Print", "price": 18.0, "style_tags": ["y2k", "vintage", "graphic tee", "cottagecore"], "colors": ["white", "pink", "purple"], "platform": "depop", ...}, ...]`

**Step 2 — Tool called:**
- Tool: `suggest_outfit`
- Input: `new_item={"title": "Y2K Baby Tee — Butterfly Print", "style_tags": ["y2k", "vintage", "graphic tee"], "colors": ["white", "pink", "purple"], "category": "tops", ...}`, `wardrobe=<example_wardrobe>`
- Why this tool: The agent has a candidate item and needs to connect it to the user's existing clothes. suggest_outfit sends both to the LLM and asks it to pick complementary wardrobe pieces.
- Output: `{"outfit_pieces": ["Baggy straight-leg jeans, dark wash", "Chunky white sneakers"], "styling_notes": "Tuck the baby tee into the high-waisted jeans for a classic Y2K silhouette. The chunky sneakers keep it casual and grounded."}`

**Step 3 — Tool called:**
- Tool: `create_fit_card`
- Input: `outfit={"outfit_pieces": [...], "styling_notes": "..."}`, `new_item={"title": "Y2K Baby Tee...", "price": 18.0, "platform": "depop", ...}`
- Why this tool: The agent now has everything it needs to produce the final user-facing output — create_fit_card formats all of it into a styled markdown card.
- Output: A markdown fit card (see Final output below).

**Final output to user:**
```
# 👗 Y2K Baby Tee — Butterfly Print

**💰 Price:** $18.00 · **📦 Platform:** Depop · **🏷️ Condition:** Excellent

## ✨ The Fit
- Baggy straight-leg jeans, dark wash
- Chunky white sneakers

## 💬 Styling Notes
Tuck the baby tee into the high-waisted jeans for a classic Y2K silhouette.
The chunky sneakers keep it casual and grounded.

## 🎨 Vibe
Nostalgic Y2K energy — effortless, fun, and perfectly throwback.
```

---

## Error Handling and Fail Points

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the query keywords, size, or price filter | Returns an empty list; the agent surfaces `"No listings found"` to the LLM, which tells the user no matches were found and suggests broadening the search (remove size filter, raise price, or try different keywords). |
| `suggest_outfit` | Wardrobe is empty (`wardrobe.get("items", [])` is `[]`) or Groq API call fails | Returns `{"outfit_pieces": [], "styling_notes": "No wardrobe items available..."}` or `{"outfit_pieces": [], "styling_notes": "Could not generate outfit suggestion."}` — the agent passes this to `create_fit_card`, which falls back to a minimal item-only card. |
| `create_fit_card` | Outfit dict has no pieces/notes, or Groq API call raises an exception | Falls back to a hardcoded markdown card built from listing fields only (title, price, platform, category, colors, style tags), so the user always receives a formatted response. |

---

## Spec Reflection

**One way planning.md helped during implementation:**

Defining the exact return shape of `suggest_outfit` in planning.md — specifically that it returns a dict with `outfit_pieces` (list) and `styling_notes` (str) — made it straightforward to write `create_fit_card` independently. Without that contract written down first, the two functions would have required coordination mid-implementation. The planning doc acted as the interface agreement between tools, so each could be built and tested in isolation.

**One divergence from your spec, and why:**

The spec described the planning loop as having a human-in-the-loop pause after `search_listings` (the agent presents the top 3 results and asks the user to pick one before calling `suggest_outfit`). In the final implementation, the LLM automatically selects the best match from the returned list and proceeds without asking. This kept the interaction snappier for a chat UI context — requiring a selection step would have added friction and made the Gradio demo feel slow. The tradeoff is that the user doesn't explicitly choose, but the fit card still reflects a well-matched item.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

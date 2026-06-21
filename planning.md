# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Searches the mock secondhand listings dataset (data/listings.json) by matching the user's description against each listing's title, description, and style_tags fields. Optionally filters results by exact size match and by maximum price.

**Input parameters:**
- `description` (str): A natural-language string of style keywords extracted from the user's query (e.g., "vintage graphic tee"). Matched case-insensitively against listing title, description, and style_tags.
- `size` (str): Optional. The clothing size to filter by (e.g., "M", "L", "XS"). If provided, only listings whose `size` field matches are returned.
- `max_price` (float): Optional. The upper price limit in dollars. If provided, only listings whose `price` field is less than or equal to this value are returned.

**What it returns:**
A list of matching listing dicts. Each dict contains: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list of str), `size` (str), `condition` (str), `price` (float), `colors` (list of str), `brand` (str), and `platform` (str). Returns an empty list if nothing matches.

**What happens if it fails or returns nothing:**
If the list is empty, the agent does not call any further tools. Instead it tells the user that no listings matched their description and price/size constraints, then prompts them to try broader keywords, remove the size filter, or raise the maximum price. The agent loops back to await a revised query.

---

### Tool 2: suggest_outfit

**What it does:**
Uses the Groq LLM to select wardrobe items from the user's existing wardrobe (data/wardrobe_schema.json) that pair well with a chosen thrift listing. It sends both the new item's details and the full wardrobe to the model and asks it to compose a cohesive outfit.

**Input parameters:**
- `new_item` (dict): The full listing dict chosen by the user (same structure returned by search_listings), including title, description, style_tags, colors, and category.
- `wardrobe` (dict): The user's wardrobe loaded from data/wardrobe_schema.json. Contains a list of items, each with a name, category, colors, and style descriptors.

**What it returns:**
A dict with two keys:
- `"outfit_pieces"` (list of str): Names of wardrobe items selected by the LLM to pair with the new listing (e.g., `["Baggy straight-leg jeans, dark wash", "Chunky white sneakers"]`).
- `"styling_notes"` (str): A short paragraph from the LLM describing how to wear the outfit together, including tuck, layer, or accessory suggestions.

**What happens if it fails or returns nothing:**
If the wardrobe is empty or the LLM returns a malformed response, the agent catches the error and returns a fallback outfit dict with an empty `outfit_pieces` list and a `styling_notes` string stating "No wardrobe items available — try adding items to your wardrobe to get styling suggestions." The agent still proceeds to create_fit_card with this fallback so the user at least sees the item details.

---

### Tool 3: create_fit_card

**What it does:**
Uses the Groq LLM to generate a formatted Markdown fit card that summarizes the chosen thrift item, the selected outfit pieces, and the styling notes in a visually structured output ready to display to the user.

**Input parameters:**
- `outfit` (dict): The dict returned by suggest_outfit, containing `"outfit_pieces"` (list of str) and `"styling_notes"` (str).
- `new_item` (dict): The full listing dict for the chosen thrift find, including title, brand, price, condition, size, colors, and platform.

**What it returns:**
A Markdown-formatted string (str) containing a complete fit card. The card includes: a header with the item name, a section listing item details (brand, price, condition, size, platform), a section listing the outfit pieces, and a section with the LLM-generated styling notes.

**What happens if it fails or returns nothing:**
If `outfit` is missing keys or `new_item` is incomplete, the agent catches the KeyError or LLM error and returns a minimal Markdown string that shows only the available item title and price, with a note that full styling details could not be generated. The partial card is still shown to the user so they have the listing information.

---

### Additional Tools (if any)

No additional tools beyond the required three are planned for the core implementation. A stretch-goal `save_fit_card(fit_card: str, filename: str) -> str` tool could be added to persist cards to disk, but it is not part of the base spec.

---

## Planning Loop

**How does your agent decide which tool to call next?**

The planning loop runs inside a Groq-powered agent that maintains a session state dict. On each turn it follows this decision sequence:

1. **Parse the user message.** The agent extracts style keywords (everything that describes the garment or aesthetic), a size token if present (e.g., "size M", "medium"), and a price ceiling if present (e.g., "under $30", "max $25"). These become the arguments for the first tool call.

2. **Call search_listings.** Always the first tool called on a new query. The agent passes the extracted keywords, size, and max_price. If the result list is empty it terminates the tool chain, messages the user, and waits for a new query. If results exist it stores them in session state under `"candidates"`.

3. **Present top 3 results to the user.** The agent formats a short numbered list of the top 3 matches (title, price, condition, size) and asks the user to pick one. It then waits for user input — this is the only human-in-the-loop pause mid-loop.

4. **Call suggest_outfit.** Once the user selects an item, the agent retrieves the full listing dict from `"candidates"` and loads the wardrobe from `data/wardrobe_schema.json`. It calls suggest_outfit with both. The result is stored in session state under `"outfit"`.

5. **Call create_fit_card.** Immediately after suggest_outfit succeeds, the agent calls create_fit_card with the outfit dict and the selected listing dict. No user input is needed between these two steps.

6. **Return the fit card.** The agent sends the Markdown fit card string to the user as the final message of the loop. The session state is cleared and the agent waits for a new query.

The loop knows it is done when create_fit_card returns a non-empty string and that string has been delivered to the user. It does not loop back unless the user sends a new message.

---

## State Management

**How does information from one tool get passed to the next?**

A session-level Python dict called `session_state` persists across tool calls within a single user interaction. It is initialized empty at the start of each new top-level query and contains the following keys as the interaction progresses:

- `"query"` (str): The raw user query, stored on arrival so it can be referenced in error messages.
- `"parsed"` (dict): The extracted keywords, size, and max_price after parsing the query.
- `"candidates"` (list of dict): The full list returned by search_listings, indexed so the user's numeric choice can map back to a specific listing dict.
- `"selected_item"` (dict): The listing dict the user chose from the candidates list. Populated after the user replies with a number.
- `"outfit"` (dict): The dict returned by suggest_outfit, containing outfit_pieces and styling_notes. Passed directly to create_fit_card.

The wardrobe is loaded once from `data/wardrobe_schema.json` at startup and held in a module-level variable; it does not need to be stored in session_state because it does not change during a session. All tool calls receive their inputs directly from session_state keys, ensuring no data is reconstructed from the LLM's text output.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Agent skips suggest_outfit and create_fit_card entirely. It replies: "I couldn't find any listings matching '[description]' under $[max_price]. Try broader keywords, a different size, or a higher price limit." Then waits for a revised query. |
| suggest_outfit | Wardrobe is empty | Agent catches the empty-wardrobe case before calling the LLM and returns the fallback dict with an empty outfit_pieces list and a message instructing the user to add wardrobe items. It still proceeds to create_fit_card so the thrift find details are shown. |
| create_fit_card | Outfit input is missing or incomplete | Agent catches KeyError or LLM failure, constructs a minimal fallback Markdown card from the new_item dict alone (title, price, brand, platform), appends a note "Styling details unavailable," and returns it to the user rather than silently failing. |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER (Gradio UI)                           │
│  Input: "vintage graphic tee under $30, baggy jeans + chunky shoes" │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ raw query
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    GROQ PLANNING LOOP (agent.py)                    │
│                                                                     │
│  1. Parse query → keywords, size, max_price                         │
│  2. Decide: call search_listings                                     │
│  3. Receive candidates → store in session_state["candidates"]       │
│  4. Present top 3 → await user selection                            │
│  5. Decide: call suggest_outfit                                      │
│  6. Receive outfit → store in session_state["outfit"]               │
│  7. Decide: call create_fit_card                                     │
│  8. Receive fit card → return to user                               │
└──┬──────────────┬──────────────────────┬────────────────────────────┘
   │              │                      │
   ▼              ▼                      ▼
┌──────────┐  ┌────────────────┐  ┌─────────────────┐
│ search_  │  │ suggest_outfit │  │ create_fit_card  │
│ listings │  │                │  │                  │
│          │  │  Groq LLM      │  │  Groq LLM        │
│ Reads    │  │  picks wardrobe│  │  formats Markdown│
│ data/    │  │  items that    │  │  fit card from   │
│ listings │  │  pair with new │  │  outfit + item   │
│ .json    │  │  item          │  │  details         │
└──┬───────┘  └──────┬─────────┘  └────────┬─────────┘
   │                 │                      │
   │  list[dict]     │  {outfit_pieces,     │  markdown str
   │  or []          │   styling_notes}     │
   │                 │                      │
   ▼                 ▼                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     session_state (Python dict)                     │
│  "query" | "parsed" | "candidates" | "selected_item" | "outfit"    │
└─────────────────────────────────────────────────────────────────────┘
                                │
           ┌────────────────────┤
           │  ERROR PATHS       │
           │                    │
           │  search → []       │ → tell user, await new query
           │  outfit → empty WD │ → fallback dict, continue
           │  fit card → fail   │ → minimal card, continue
           └────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     USER sees final Fit Card                        │
└─────────────────────────────────────────────────────────────────────┘
```

Data files referenced:
- `data/listings.json` — read by search_listings
- `data/wardrobe_schema.json` — loaded at startup, passed to suggest_outfit

---

## AI Tool Plan

**Milestone 3 — Individual tool implementations:**

I will use Claude Code for all three tool implementations. For each tool I will paste the corresponding section of this planning.md (the "What it does," "Input parameters," "What it returns," and "What happens if it fails" fields) as the prompt context, along with the relevant JSON schema from data/listings.json and data/wardrobe_schema.json.

- **search_listings:** Give Claude the Tool 1 spec plus a sample listings.json entry. Ask it to implement the function using Python's built-in string matching (case-insensitive `in` check across title, description, and style_tags). Verify by running 3 manual test queries: (1) "vintage graphic tee" with max_price=30 expecting at least 1 result, (2) "silk blouse" with size="XS" expecting filtered results, (3) "zxqfoo" expecting an empty list.

- **suggest_outfit:** Give Claude the Tool 2 spec plus the wardrobe_schema.json structure and a sample new_item dict. Ask it to construct a Groq chat completion prompt that lists the wardrobe items and asks the model to select pairing pieces and write styling notes. Verify by running the function with the Y2K Baby Tee item and the sample wardrobe; confirm the return dict has both required keys and outfit_pieces contains recognizable wardrobe item names.

- **create_fit_card:** Give Claude the Tool 3 spec plus a sample outfit dict and new_item dict. Ask it to construct a Groq prompt that produces a Markdown fit card with clearly labeled sections. Verify by inspecting the output string for the required sections: item header, item details, outfit pieces, and styling notes. Confirm the string renders correctly in a Markdown viewer.

**Milestone 4 — Planning loop and state management:**

I will use Claude Code with the Architecture diagram and the Planning Loop section of this document as the prompt. I will also include the State Management section so the agent understands which keys to read and write at each step. I will ask Claude to implement the planning loop as a function that accepts a user message string and the current session_state dict, calls the correct tool based on the current state, updates session_state, and returns the agent's reply string.

Verification: walk through the complete interaction example below manually step by step, checking that session_state contains the expected keys after each tool call and that the final output is a non-empty Markdown string. Also verify the error path by passing an unmatchable query and confirming the loop returns the "no results" message without calling suggest_outfit or create_fit_card.

**Milestone 5 — Gradio UI:**

I will use Claude Code with the Gradio documentation (fetched via context7) as reference. I will give Claude the final agent function signature and ask it to wrap it in a Gradio ChatInterface component. Verify by launching locally and submitting the example query below; confirm the fit card renders in the chat window and no Python exceptions appear in the terminal.

---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The agent parses the query and extracts: description = "vintage graphic tee", max_price = 30.0, size = None (not mentioned). It calls `search_listings("vintage graphic tee", max_price=30.0)`. The function scans all 40 listings and returns matching items including the Y2K Butterfly Baby Tee ($18) and other listings whose title, description, or style_tags contain "vintage," "graphic," or "tee." The returned list is stored in `session_state["candidates"]`. The agent presents the top 3 results as a numbered list to the user and asks which one they want to style.

**Step 2:**
The user replies "1" (selecting the Y2K Butterfly Baby Tee). The agent maps the choice to `session_state["candidates"][0]`, stores it as `session_state["selected_item"]`, and calls `suggest_outfit({"id": "...", "title": "Y2K Butterfly Baby Tee", "price": 18.0, "style_tags": ["y2k", "vintage", "butterfly", "babytee"], ...}, wardrobe)`. The Groq LLM reviews the wardrobe items and returns: `{"outfit_pieces": ["Baggy straight-leg jeans, dark wash", "Chunky white sneakers"], "styling_notes": "Tuck the tee into the jeans for a classic Y2K silhouette. Keep accessories minimal — a thin silver belt and small hoop earrings complete the look without competing with the print. The chunky sneakers ground the outfit and echo the early-2000s energy of the tee."}`. This is stored in `session_state["outfit"]`.

**Step 3:**
Immediately after receiving the outfit dict, the agent calls `create_fit_card(session_state["outfit"], session_state["selected_item"])`. The Groq LLM receives both dicts and formats a Markdown fit card string. The function returns the completed card and the agent sends it to the user as the final reply. Session state is then cleared in preparation for the next query.

**Final output to user:**

```
## Your Fit Card

### Thrift Find: Y2K Butterfly Baby Tee
| Detail | Info |
|--------|------|
| Brand | No Boundaries |
| Price | $18.00 |
| Condition | Good |
| Size | S |
| Platform | Depop |

### Outfit Pieces
- Baggy straight-leg jeans, dark wash
- Chunky white sneakers

### Styling Notes
Tuck the tee into the jeans for a classic Y2K silhouette. Keep accessories
minimal — a thin silver belt and small hoop earrings complete the look without
competing with the print. The chunky sneakers ground the outfit and echo the
early-2000s energy of the tee.
```
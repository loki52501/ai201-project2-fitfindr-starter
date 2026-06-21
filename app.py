import gradio as gr
from dotenv import load_dotenv
from utils.data_loader import get_example_wardrobe
from agent import run_agent

load_dotenv()

wardrobe = get_example_wardrobe()


def chat(message: str, history: list) -> str:
    return run_agent(message, wardrobe)


def format_wardrobe(wardrobe: dict) -> str:
    lines = []
    for item in wardrobe.get("items", []):
        name = item.get("name", "Unknown")
        category = item.get("category", "")
        colors = item.get("colors", [])
        lines.append(f"- **{name}** ({category}) — {', '.join(colors)}")
    return "\n".join(lines)


wardrobe_md = format_wardrobe(wardrobe)

examples = [
    "Find me a vintage graphic tee under $30. I wear baggy jeans and chunky sneakers.",
    "Looking for a grunge outerwear piece, size M, under $50.",
    "Any Y2K accessories under $20? I have mostly streetwear basics.",
]

with gr.Blocks(title="FitFindr") as demo:
    gr.Markdown("# 👗 FitFindr — Your Thrift Shopping Assistant")
    gr.Markdown("Describe what you're looking for and I'll search secondhand listings and style it with your wardrobe.")

    with gr.Row():
        with gr.Column(scale=3):
            gr.ChatInterface(
                fn=chat,
                examples=examples,
                type="messages",
            )
        with gr.Column(scale=1):
            with gr.Accordion("Your Wardrobe", open=True):
                gr.Markdown(wardrobe_md)

if __name__ == "__main__":
    demo.launch()

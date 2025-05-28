# from langchain_openai.chat_models import ChatOpenAI
from langchain_openai import ChatOpenAI
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.schema import AIMessage
from langgraph.prebuilt import create_react_agent
import streamlit as st
from PIL import Image
import logging
import os
from dotenv import load_dotenv
import asyncio

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")  # noqa: E501
logger = logging.getLogger(__name__)

load_dotenv()
openai_api_key = os.getenv('openai_key')
model = ChatOpenAI(temperature=0.7, api_key=openai_api_key)


async def generate_response(input_data):
    async with MultiServerMCPClient() as client:
        await client.connect_to_server(
            "todoist",
            command="python",
            args=["/workspaces/osn2025/mcp-app/todoist-server.py"],
            transport="stdio"
        )
        await client.connect_to_server(
            "firewall",
            command="python",
            args=["/workspaces/osn2025/mcp-app/firewall-server.py"],
            transport="stdio"
        )

        agent = create_react_agent(model, client.get_tools())
        answer = await agent.ainvoke(input={"messages": input_data})
        logger.info(f"Raw answer from agent: {answer}")  # Log the raw answer

        r = parse_ai_messages(answer)
        st.info(r)


def parse_ai_messages(data):
    messages = dict(data).get('messages', [])
    logger.info(f"Extracted messages: {messages}")
    formatted_message = ""

    # Iterate through all messages and prioritize the last valid AIMessage
    for message in messages:
        if isinstance(message, AIMessage):
            logger.info(f"Processing AIMessage: {message.content}")
            if message.content.strip():
                # Check if content is not empty or whitespace
                formatted_message = message.content

    if not formatted_message:
        logger.warning("No valid AIMessage content found.")
        return "No valid AI message content found"

    return formatted_message


icon_path = "images/pete-3d.png"
icon_image = Image.open(icon_path)
col1, col2 = st.columns([1, 5])  # Adjust the proportions as needed

# Place the icon in the first column and the title in the second column
with col1:
    st.image(icon_image, width=100)  # Adjust the width as needed
with col2:
    st.title("MCP Demo")
with st.form("my_form"):
    text = st.text_area(
        "Enter text:",
        "What is your question?",
    )
    submitted = st.form_submit_button("Submit")
    if not openai_api_key.startswith("sk-"):
        st.warning("Please enter your OpenAI API key!", icon="⚠")
    if submitted and openai_api_key.startswith("sk-"):
        asyncio.run(generate_response(text))

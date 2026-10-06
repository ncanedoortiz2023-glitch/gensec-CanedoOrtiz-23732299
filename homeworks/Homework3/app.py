"""Run a basic LangChain agent with the course's Google Gemini model."""

import os

from langchain.agents import create_agent
from langchain_experimental.tools import PythonREPLTool
from langchain_google_genai import ChatGoogleGenerativeAI


def create_homework_agent():
    """Create a tool-free LangChain agent using environment configuration."""
    api_key = os.getenv("GOOGLE_API_KEY")
    model_name = os.getenv("GOOGLE_MODEL")
    if not api_key:
        raise RuntimeError("Set GOOGLE_API_KEY in the environment before running.")
    if not model_name:
        raise RuntimeError("Set GOOGLE_MODEL in the environment before running.")

    model = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
    )
    return create_agent(model=model, tools=[PythonREPLTool()])


def main():
    """Read one prompt, invoke the agent, and print its response."""
    agent = create_homework_agent()
    prompt = input("Prompt: ").strip()
    if not prompt:
        print("Please enter a prompt.")
        return

    result = agent.invoke({"messages": [{"role": "user", "content": prompt}]})
    print(result["messages"][-1].text)


if __name__ == "__main__":
    main()

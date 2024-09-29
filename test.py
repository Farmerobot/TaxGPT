import os
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, StateGraph, START
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import operator
from typing import Annotated, Sequence
from typing_extensions import TypedDict
from langchain_core.messages import AIMessage
from typing import Literal
from langchain_core.tools import tool

client = AzureChatOpenAI(azure_endpoint=os.getenv("AZURE_OPENAI_API_BASE"),
                     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                     api_version="2023-03-15-preview")

# Load environment variables from .env file
load_dotenv()
app = Flask(__name__)
# In-memory storage for chat messages
messs = []


# Configure Azure OpenAI with environment variables
# Replace with the API version you're using

def create_agent(llm, tools, system_message: str):
    """Create an agent."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Jesteś asystentem podatkowym AI wspomagający użytkowników w procesie wypełniania deklaracji podatkowej."+
                "Pomagasz rozmówcy.",
            ),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )
    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
    return prompt | llm.bind_tools(tools)


@tool
def test_tool():
    """do not use this tool ever"""
    return "{elo: 1}"


# This defines the object that is passed between each node
# in the graph. We will create different nodes for each agent and tool
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    sender: str


import functools


# Helper function to create a node for a given agent
def agent_node(state, agent, name):
    result = agent.invoke(state)
    # We convert the agent output into a format that is suitable to append to the global state
    if isinstance(result, ToolMessage):
        pass
    else:
        result = AIMessage(**result.dict(exclude={"type", "name"}), name=name)
    return {
        "messages": [result],
        # Since we have a strict workflow, we can
        # track the sender so we know who to pass to next.
        "sender": name,
    }


llm = client

# Research agent and node
research_agent = create_agent(
    llm,
    [test_tool],
    system_message="Mówisz OK. Twoim odwiecznym zadaniem jest mówienie OK.",
)
research_node = functools.partial(agent_node, agent=research_agent, name="Researcher")

# chart_generator
chart_agent = create_agent(
    llm,
    [test_tool],
    system_message="Mówisz FUJ. Twoim odwiecznym zadaniem jest mówienie FUJ.",
)
from langgraph.prebuilt import ToolNode

tools = [test_tool]
tool_node = ToolNode(tools)
chart_node = functools.partial(agent_node, agent=chart_agent, name="chart_generator")


# Either agent can decide to end


workflow = StateGraph(AgentState)

workflow.add_node("Researcher", research_node)
workflow.add_node("chart_generator", chart_node)
# workflow.add_node("call_tool", tool_node)
workflow.add_edge(START, "Researcher")
workflow.add_edge("Researcher", "chart_generator")
workflow.add_edge("chart_generator", END)
# workflow.add_edge("call_tool", END)
graph = workflow.compile()

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/get_messages', methods=['GET'])
def get_messages():
    return jsonify(messs)


@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.get_json()
    user_message = data['text']

    # Add user's message to messages
    messs.append({"text": user_message, "sender": "user"})

    for output in graph.stream(
            {"messages": [HumanMessage(content=user_message)]},
            config={"configurable": {"thread_id": str("876reytdfy")}}, stream_mode="updates"
    ):
        last_message = next(iter(output.values()))["messages"][-1]
        messs.append({"text": last_message.content, "sender": "bot"})

    return jsonify(success=True)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)

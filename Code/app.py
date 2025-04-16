# D:\CRS-Taager-Task\Code\app.py
import os
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
# from langchain_core.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv('var.env')

# Validate environment variables
required_vars = ['OPENAI_API_KEY', 'PINECONE_API_KEY', 'PINECONE_INDEX_NAME']
missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

# Initialize components
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstore = PineconeVectorStore(
    index_name=os.getenv("PINECONE_INDEX_NAME"),
    embedding=embeddings
)
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Create conversation analysis tool
retriever_tool = create_retriever_tool(
    retriever,
    name="conversation_analyzer",
    description="Search historical customer conversations to identify successful confirmation strategies, rejection patterns, and optimal responses."
)

# State definition
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]

# Enhanced prompt template
from prompt import prompt_template
ANALYSIS_PROMPT = prompt_template

# Define nodes with debug logging
def agent_node(state: AgentState):
    """Decision node with tool binding"""
    # For API integration, we can make debug prints conditional
    # print("\n[DEBUG] Agent node triggered")
    llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools([retriever_tool])
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def retrieve_node(state: AgentState):
    """Retrieval node with error handling"""
    try:
        # print("\n[DEBUG] Retrieval node triggered")
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""
        
        if hasattr(last_message, 'tool_calls'):
            query = last_message.tool_calls[0]['args']['query']
            
        # print(f"[DEBUG] Retrieving for: {query}")
        docs = retriever.invoke(query)
        # print(f"[DEBUG] Retrieved {len(docs)} documents")
        
        context = "\n\n".join([
            f"### Conversation {i+1}\n{doc.page_content}" 
            for i, doc in enumerate(docs[:3])  # Show top 3
        ])
        return {"messages": [HumanMessage(content=context)]}
    except Exception as e:
        # print(f"[ERROR] Retrieval failed: {str(e)}")
        return {"messages": [HumanMessage(content="No relevant conversations found")]}

def analyze_node(state: AgentState):
    """Analysis node with structured output"""
    # print("\n[DEBUG] Analysis node triggered")
    chain = ANALYSIS_PROMPT | ChatOpenAI(model="gpt-4-turbo") | StrOutputParser()
    
    query = next(m.content for m in state["messages"] if isinstance(m, HumanMessage))
    context = state["messages"][-1].content
    
    analysis = chain.invoke({"context": context, "query": query})
    return {"messages": [HumanMessage(content=analysis)]}

# Build workflow
workflow = StateGraph(AgentState)
workflow.add_node("agent", agent_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("analyze", analyze_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges(
    "agent",
    lambda state: "retrieve" if any(
        hasattr(msg, 'tool_calls') 
        for msg in state["messages"] 
        if isinstance(msg, AIMessage)
    ) else END,
    {"retrieve": "retrieve", END: END}
)
workflow.add_edge("retrieve", "analyze")
workflow.add_edge("analyze", END)

app = workflow.compile()

# Interactive test loop - only runs when script is executed directly
# if __name__ == "__main__":
#     print("\n" + "="*50)
#     print("Customer Service Optimization Analyzer")
#     print("Type 'exit' to quit\n")
    
#     while True:
#         user_input = input("Enter customer query or conversation snippet: ").strip()
        
#         if user_input.lower() in ['exit', 'quit']:
#             print("\nExiting analyzer...")
#             break
            
#         if not user_input:
#             print("Please enter a valid query\n")
#             continue
            
#         print("\n" + "-"*50)
#         print("Analyzing conversation...\n")
        
#         test_input = {
#             "messages": [
#                 HumanMessage(content=user_input)
#             ]
#         }
        
#         try:
#             for output in app.stream(test_input):
#                 for key, value in output.items():
#                     if key == "analyze":
#                         print("\n" + value["messages"][-1].content + "\n")
                        
#         except Exception as e:
#             print(f"\n[ERROR] Processing failed: {str(e)}\n")
            
#         print("-"*50 + "\n")
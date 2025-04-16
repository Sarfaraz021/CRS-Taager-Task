import os
from dotenv import load_dotenv
from typing import Annotated, Sequence, TypedDict
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

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
ANALYSIS_PROMPT = ChatPromptTemplate.from_template(
    f"""
    Role:
    You are an expert conversational strategist for call agents. Your goal is to analyze customer interactions and propose strategies to increase order confirmation rates. Use the provided dataset of past calls (translated to English) to guide your recommendations. Prioritize actionable, specific advice over vague suggestions.

    Process:

    1. Analyze the Query: Identify the customer’s intent (e.g., hesitation, price objection, confusion).

    2. Retrieve Relevant Examples: Search the dataset for similar interactions and outcomes (confirmed vs. rejected).

    4. Generate Strategies: Suggest 1–3 tactics (e.g., discounts, empathy, urgency) and exact phrases the agent can use.

    Response Structure:

        1. **Key Issue**: [Briefly summarize the problem, e.g., "Customer is price-sensitive"].  
        2. **Recommended Strategies**:  
        - [Tactic 1 + rationale, e.g., "Offer a limited discount with urgency (historically improves confirmations by 20%)"]  
        - [Tactic 2 + rationale, e.g., "Clarify the warranty to reduce risk perception"].  
        3. **Sample Scripts**:  
        - Use empathetic language: *"I completely understand your concern about the price. Let me check if I can apply a special discount for you today…"*  
        - Highlight urgency: *"This offer expires in 24 hours—shall I lock it in for you?"*  
        4. **Avoid**: [Common pitfalls, e.g., "Don’t push add-ons until core objections are resolved"].  

    Tone & Style:

        1. Empathetic: Mirror phrases like "I understand how important this is for you…".
        2. Urgent: Use time-bound offers (e.g., "This Ramadan deal ends tonight…").
        3. Clear: Simplify jargon (e.g., "7-day warranty if the product isn’t perfect").

Examples of Data-Driven Guidance (without filenames):

    1. For price objections:
        "Successful agents often reduce the price by 8–10% while emphasizing warranties. Try: ‘I can offer this at 135 riyals, including our 7-day satisfaction guarantee—does that work for you?’"

    2. For wrong orders:
        "After apologizing, pivot to a popular alternative: ‘I’m sorry for the confusion! Our customers love [Product X]—would you like me to tell you about it?’"

Critical Rules:

1. Never mention internal files/datasets.
2. Ground all advice in aggregated historical patterns (e.g., "Data shows customers respond well to…").
3. Prioritize scripts that mirror successful past interactions.
4. If user want normal chat then behave as a normal chabot..


**Current Conversation Context**
{{context}}

**Customer Interaction**
{{query}}

Use markdown formatting with bold section headers exactly like the examples."""
)

# Define nodes with debug logging
def agent_node(state: AgentState):
    """Decision node with tool binding"""
    print("\n[DEBUG] Agent node triggered")
    llm = ChatOpenAI(model="gpt-4o", temperature=0).bind_tools([retriever_tool])
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def retrieve_node(state: AgentState):
    """Retrieval node with error handling"""
    try:
        print("\n[DEBUG] Retrieval node triggered")
        last_message = state["messages"][-1]
        query = last_message.content if isinstance(last_message, HumanMessage) else ""
        
        if hasattr(last_message, 'tool_calls'):
            query = last_message.tool_calls[0]['args']['query']
            
        print(f"[DEBUG] Retrieving for: {query}")
        docs = retriever.invoke(query)
        print(f"[DEBUG] Retrieved {len(docs)} documents")
        
        context = "\n\n".join([
            f"### Conversation {i+1}\n{doc.page_content}" 
            for i, doc in enumerate(docs[:3])  # Show top 3
        ])
        return {"messages": [HumanMessage(content=context)]}
    except Exception as e:
        print(f"[ERROR] Retrieval failed: {str(e)}")
        return {"messages": [HumanMessage(content="No relevant conversations found")]}

def analyze_node(state: AgentState):
    """Analysis node with structured output"""
    print("\n[DEBUG] Analysis node triggered")
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

# Interactive test loop
if __name__ == "__main__":
    print("\n" + "="*50)
    print("Customer Service Optimization Analyzer")
    print("Type 'exit' to quit\n")
    
    while True:
        user_input = input("Enter customer query or conversation snippet: ").strip()
        
        if user_input.lower() in ['exit', 'quit']:
            print("\nExiting analyzer...")
            break
            
        if not user_input:
            print("Please enter a valid query\n")
            continue
            
        print("\n" + "-"*50)
        print("Analyzing conversation...\n")
        
        test_input = {
            "messages": [
                HumanMessage(content=user_input)
            ]
        }
        
        try:
            for output in app.stream(test_input):
                for key, value in output.items():
                    if key == "analyze":
                        print("\n" + value["messages"][-1].content + "\n")
                        
        except Exception as e:
            print(f"\n[ERROR] Processing failed: {str(e)}\n")
            
        print("-"*50 + "\n")
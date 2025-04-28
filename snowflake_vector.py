# Snowflake RAG Similarity Search Agent
# This script creates a LangChain agent that interfaces with Snowflake vector database
# to perform similarity searches on vector embeddings.

import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain.vectorstores import SnowflakeVector
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import OpenAIEmbeddings
from langchain_openai import ChatOpenAI
from langchain.agents import create_openai_functions_agent
from langchain.agents import AgentExecutor
from langchain.tools import tool

# Environment setup (replace with your actual credentials)
os.environ["OPENAI_API_KEY"] = "your-openai-api-key"
os.environ["SNOWFLAKE_ACCOUNT"] = "your-snowflake-account"
os.environ["SNOWFLAKE_USER"] = "your-snowflake-username"
os.environ["SNOWFLAKE_PASSWORD"] = "your-snowflake-password"
os.environ["SNOWFLAKE_DATABASE"] = "your-database-name"
os.environ["SNOWFLAKE_SCHEMA"] = "your-schema-name"

# Snowflake connection parameters
snowflake_connection_params = {
    "account": os.environ.get("SNOWFLAKE_ACCOUNT"),
    "user": os.environ.get("SNOWFLAKE_USER"),
    "password": os.environ.get("SNOWFLAKE_PASSWORD"),
    "database": os.environ.get("SNOWFLAKE_DATABASE"),
    "schema": os.environ.get("SNOWFLAKE_SCHEMA"),
}

# Initialize the embedding model
embeddings = OpenAIEmbeddings()

# Initialize the Snowflake vector store (adjust table parameters as needed)
vector_store = SnowflakeVector(
    connection_params=snowflake_connection_params,
    embedding=embeddings,
    table_name="YOUR_VECTOR_TABLE",  # Replace with your vector table name
    content_column="DOCUMENT_CONTENT",  # Column containing the text/document content
    embedding_column="EMBEDDINGS",  # Column containing the vector embeddings
    metadata_columns=["METADATA_COL1", "METADATA_COL2"]  # Optional metadata columns
)

# Create tools for our agent
@tool
def similarity_search(query: str, k: int = 5):
    """
    Perform a similarity search on the Snowflake vector table.
    query: The text to search for similar documents
    k: Number of results to return (default: 5)
    """
    results = vector_store.similarity_search(query, k=k)
    formatted_results = []
    
    for i, doc in enumerate(results):
        formatted_results.append(
            f"Result {i+1}:\n"
            f"Content: {doc.page_content}\n"
            f"Metadata: {doc.metadata}\n"
        )
    
    return "\n".join(formatted_results)

@tool
def similarity_search_with_score(query: str, k: int = 5):
    """
    Perform a similarity search on the Snowflake vector table with relevance scores.
    query: The text to search for similar documents
    k: Number of results to return (default: 5)
    """
    results = vector_store.similarity_search_with_score(query, k=k)
    formatted_results = []
    
    for i, (doc, score) in enumerate(results):
        formatted_results.append(
            f"Result {i+1} (Score: {score}):\n"
            f"Content: {doc.page_content}\n"
            f"Metadata: {doc.metadata}\n"
        )
    
    return "\n".join(formatted_results)

@tool
def mmr_search(query: str, k: int = 5, fetch_k: int = 20, lambda_mult: float = 0.5):
    """
    Perform a Maximum Marginal Relevance (MMR) search on the Snowflake vector table.
    This balances relevance with diversity in results.
    
    query: The text to search for similar documents
    k: Number of results to return (default: 5)
    fetch_k: Number of initial results to fetch before reranking (default: 20)
    lambda_mult: Diversity factor, 0-1 (0 = max diversity, 1 = max relevance, default: 0.5)
    """
    results = vector_store.max_marginal_relevance_search(
        query, k=k, fetch_k=fetch_k, lambda_mult=lambda_mult
    )
    formatted_results = []
    
    for i, doc in enumerate(results):
        formatted_results.append(
            f"Result {i+1}:\n"
            f"Content: {doc.page_content}\n"
            f"Metadata: {doc.metadata}\n"
        )
    
    return "\n".join(formatted_results)

# Define the tools our agent will use
tools = [similarity_search, similarity_search_with_score, mmr_search]

# Initialize the LLM
llm = ChatOpenAI(model="gpt-4")

# Define the agent prompt
prompt = ChatPromptTemplate.from_messages([
    ("system", """You are an AI assistant specializing in vector similarity searches on a Snowflake database.
    Your job is to help users perform semantic searches on their document embeddings.
    
    When the user asks for a similarity search, use the appropriate tool to search the vector database.
    
    Be sure to ask for clarification if the query is ambiguous, and explain your search approach.
    """),
    ("human", "{input}"),
])

# Create the agent
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Example usage function
def run_rag_agent(query):
    """
    Function to run the RAG agent with a user query
    """
    return agent_executor.invoke({"input": query})

# Example usage - uncomment to test
# query = "Find documents similar to 'machine learning for natural language processing'"
# result = run_rag_agent(query)
# print(result['output'])

# Interactive CLI (for testing)
if __name__ == "__main__":
    print("Snowflake RAG Similarity Search Agent")
    print("Enter 'exit' to quit")
    
    while True:
        user_input = input("\nEnter your query: ")
        if user_input.lower() in ["exit", "quit"]:
            break
            
        try:
            result = run_rag_agent(user_input)
            print("\nAgent Response:")
            print(result['output'])
        except Exception as e:
            print(f"Error: {str(e)}")
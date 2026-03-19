from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen3:14b",
    base_url="http://localhost:11434"
)
response = llm.invoke("Tu es un assistant PLU. Dis bonjour.")
print(response.content)
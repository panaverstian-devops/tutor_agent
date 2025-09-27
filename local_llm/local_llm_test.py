from ollama import chat, AsyncClient
from ollama import Client

# Synchronous
response = chat(
    model="llama3.1",
    messages=[{"role": "user", "content": "Hello, how are you?"}],
)
print(response["message"]["content"])

# Asynchronous client
async def example_async():
    client = AsyncClient(host="http://127.0.0.1:11434")
    resp = await client.chat(
        model="llama3.1",
        messages=[{"role": "user", "content": "What is 5 + 3?"}],
    )
    print(resp.message.content)

# To do streaming:
for chunk in chat(
    model="llama3.1",
    messages=[{"role": "user", "content": "Tell me a story"}],
    stream=True,
):
    print(chunk["message"]["content"], end="", flush=True)


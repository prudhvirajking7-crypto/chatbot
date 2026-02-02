import os
from dotenv import load_dotenv
from rag_engine import RAGChatbot

load_dotenv()

def test_response():
    api_key = os.getenv("GOOGLE_API_KEY")
    bot = RAGChatbot(api_key)
    
    print("Testing response...")
    try:
        query = "What documents are uploaded?"
        answer, sources = bot.get_response(query)
        print("--- ANSWER ---")
        print(answer)
        print("--- SOURCES ---")
        print(len(sources))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_response()

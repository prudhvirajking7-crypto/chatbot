try:
    import langchain
    print(f"langchain: {langchain.__version__}")
except ImportError as e:
    print(f"langchain error: {e}")

try:
    from langchain.chains import RetrievalQA
    print("langchain.chains.RetrievalQA found")
except ImportError as e:
    print(f"langchain.chains error: {e}")

try:
    from langchain.prompts import PromptTemplate
    print("langchain.prompts.PromptTemplate found")
except ImportError as e:
    print(f"langchain.prompts error: {e}")

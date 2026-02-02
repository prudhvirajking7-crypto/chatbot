try:
    import langchain_core
    print(f"langchain_core: {langchain_core.__version__}")
    from langchain_core.prompts import PromptTemplate
    print("PromptTemplate found in langchain_core")
except ImportError as e:
    print(f"langchain_core error: {e}")

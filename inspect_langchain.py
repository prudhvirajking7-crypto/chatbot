import langchain
print(f"Version: {langchain.__version__}")
print(f"Dir: {dir(langchain)}")
try:
    import langchain.chains
    print("langchain.chains exists")
    print(dir(langchain.chains))
except ImportError as e:
    print(f"ImportError: {e}")

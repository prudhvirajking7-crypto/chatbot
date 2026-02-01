# RAG Chatbot with Google Gemini

This is a Retrieval-Augmented Generation (RAG) chatbot application built with Python, Streamlit, and Google's Gemini Pro model. It allows you to upload documents (PDF, TXT) and ask questions about them.

## Features

-   **Free LLM**: Uses Google's Gemini Pro (free tier available).
-   **RAG Technology**: Retrieves relevant context from your uploaded documents to answer questions accurately.
-   **Document Support**: Supports PDF and TXT files.
-   **Modern UI**: Built with Streamlit with a custom dark-themed design.
-   **Source Citations**: Shows exactly which parts of the documents were used to generate the answer.

## Prerequisites

-   Python 3.10 or higher
-   A Google Cloud API Key with Gemini API access (Get it [here](https://makersuite.google.com/app/apikey))

## Installation

1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Run the Application**:
    ```bash
    python -m streamlit run app.py
    ```

2.  **Configure**:
    -   Enter your Google Gemini API Key in the sidebar.
    -   Upload your PDF or Text documents.
    -   Click "Process Documents".

3.  **Chat**:
    -   Once processed, ask any question about the documents in the chat interface.

## Project Structure

-   `app.py`: The main Streamlit application and UI logic.
-   `rag_engine.py`: Handles document processing, embedding generation, and the RAG chain.
-   `requirements.txt`: List of Python dependencies.

# Deploying to Streamlit Community Cloud (Free)

This guide will help you deploy your RAG Chatbot to the internet for free using Streamlit Community Cloud.

## Prerequisites
- A [GitHub Account](https://github.com/)
- A [Streamlit Community Cloud Account](https://share.streamlit.io/) (Sign in with GitHub)

## Step 1: Push Code to GitHub

1.  **Create a New Repository** on GitHub (e.g., `gemini-rag-chatbot`).
2.  **Upload your files**:
    -   `app.py`
    -   `rag_engine.py`
    -   `requirements.txt`
    -   (Do NOT upload `.env` or `chroma_db` folder - these should be kept local or generated at runtime)
3.  If using the command line:
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin https://github.com/YOUR_USERNAME/gemini-rag-chatbot.git
    git push -u origin main
    ```
    *Note: You can also use the "Upload files" button on the GitHub website if you prefer.*

## Step 2: Deploy on Streamlit Cloud

1.  Go to [share.streamlit.io](https://share.streamlit.io/).
2.  Click **"New app"**.
3.  Select your repository (`gemini-rag-chatbot`) and branch (`main`).
4.  Set "Main file path" to `app.py`.
5.  Click **"Deploy!"**.

## Step 3: Configure Secrets (API Key)

Since we didn't upload the `.env` file (for security), we need to give Streamlit the API key safely.

1.  Once the app is deploying/deployed, click the **Settings menu** (three dots) in the top-right corner of your app.
2.  Select **Settings**.
3.  Go to **Secrets**.
4.  Paste your API key in the following format:
    ```toml
    GOOGLE_API_KEY = "AIzaSy..."
    ```
5.  Click **Save**.

## Step 4: Done!

Your app should now be live! You can share the URL with anyone.

### Note on Persistence
Streamlit Cloud apps are "ephemeral", meaning they restart occasionally. The documents you upload are processed into the `chroma_db` folder. On the cloud, this folder will reset if the app goes to sleep. You will simply need to re-upload documents when you start a new session, which is standard for free hosting.

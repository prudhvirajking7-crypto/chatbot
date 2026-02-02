# MongoDB Atlas Setup Guide

Follow these steps to create a free MongoDB cluster for persistent document storage.

## Step 1: Create MongoDB Atlas Account

1. Go to **https://www.mongodb.com/cloud/atlas/register**
2. Sign up with:
   - Email address
   - Or use Google/GitHub to sign up
3. Complete the registration

## Step 2: Create a Free Cluster

1. After logging in, you'll see "Deploy a cloud database"
2. Click **"Create"** or **"Build a Database"**
3. Choose deployment option:
   - Select **"M0 FREE"** (Shared cluster)
   - Provider: **AWS** or **Google Cloud** (your choice)
   - Region: Choose the closest to you (e.g., `Mumbai` or `Singapore` for India)
4. Cluster Name: Keep default or name it `ChatbotCluster`
5. Click **"Create Deployment"** or **"Create Cluster"**

## Step 3: Create Database User

You'll see a security quickstart:

1. **Authentication Method**: Username and Password
2. Create credentials:
   - Username: `chatbot_user` (or any name you prefer)
   - Password: Click **"Autogenerate Secure Password"** 
   - ⚠️ **COPY THIS PASSWORD** - you'll need it!
3. Click **"Create User"**

## Step 4: Add IP Address Access

1. Under "Where would you like to connect from?":
   - Click **"Add My Current IP Address"** (for local development)
   - **For Streamlit Cloud**: Click **"Add IP Address"**
     - IP Address: `0.0.0.0/0` (allows access from anywhere)
     - Description: `Streamlit Cloud`
   - Click **"Add Entry"**
2. Click **"Finish and Close"**

## Step 5: Get Connection String

1. Click **"Connect"** on your cluster
2. Choose **"Drivers"**
3. Select:
   - Driver: **Python**
   - Version: **3.12 or later**
4. Copy the connection string (looks like):
   ```
   mongodb+srv://chatbot_user:<password>@chatbotcluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
5. **Replace `<password>`** with the password you copied earlier

## Step 6: Your Final Connection String

Your connection string should look like:
```
mongodb+srv://chatbot_user:YOUR_ACTUAL_PASSWORD@chatbotcluster.xxxxx.mongodb.net/?retryWrites=true&w=majority
```

## Next Steps

Once you have your connection string, let me know and I will:
1. Update the code to use MongoDB for persistent storage
2. Add it to your Streamlit secrets
3. Deploy the updated version

---

**Important Notes:**
- ✅ Free tier: 512MB storage (plenty for documents)
- ✅ Automatic backups
- ✅ Vector search for RAG (we'll use this!)
- ⚠️ Never commit your connection string to GitHub - we'll use Streamlit Secrets

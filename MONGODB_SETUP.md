# MongoDB Setup

1. Create a MongoDB Atlas cluster.
2. Create a database user with read/write access.
3. Allow your app IP in **Network Access**.
4. Copy your connection string and set in `.env`:

```env
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
```

5. Start the app:

```bash
uvicorn app:app --reload
```

The app will automatically create required collections and indexes:
- `users`
- `sessions`
- `conversations`
- `messages`
- `documents`

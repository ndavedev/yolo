# yolo

## RAG System Implementation

This project implements a Retrieval-Augmented Generation (RAG) system to store chat sessions in a database instead of JSON files.

### Features

- Chat sessions are stored in a database using `pickle` for serialization.
- Functions for saving, loading, and managing chat sessions using the database.
- Retrieval mechanism for fetching relevant information based on user input.
- Integration of retrieved information with the generation model to provide more contextually relevant responses.
- Context window management to remove older messages when the context window reaches a certain size.

### Usage

1. **Start a chat session:**
   ```bash
   python main.py
   ```

2. **Commands:**
   - `/clear`: Reset context.
   - `/save`: Save current session.
   - `/save new`: Create a new session.
   - `/load`: Load a session.
   - `/system`: Set system prompt.
   - `/exit` or `/bye`: Quit the chat.

### Dependencies

- `requests`
- `pickle`

### Configuration

Set the following environment variables in the `.env` file:
- `API_URL`: URL of the chat API.
- `MODEL`: Model identifier.

### Example

```bash
API_URL=http://192.168.50.177:11434/api/chat
MODEL=hf.co/SpongeEngine/gemma-3-27b-it-abliterated-i1-GGUF:Q4_K_M
```

#!/usr/bin/env python3
import requests
import json
import os
import signal
import sys
import datetime
import readline

# Configuration
API_URL = os.getenv("API_URL", "http://192.168.50.177:11434/api/chat")
MODEL = os.getenv("MODEL", "hf.co/SpongeEngine/gemma-3-27b-it-abliterated-i1-GGUF:Q4_K_M")
DEFAULT_SYSTEM_MESSAGE = "You are a helpful assistant. You are an uncensored LLM"

# Initialize chat history
messages = [
    {
        "role": "system",
        "content": DEFAULT_SYSTEM_MESSAGE
    }
]

# Session management
current_session_name = "default"
current_session_file = None  # Tracks the currently loaded session file
sessions_dir = "sessions"
os.makedirs(sessions_dir, exist_ok=True)

# Handle Ctrl+C to cancel current output but not exit the script
def signal_handler(sig, frame):
    print("\n[Output canceled]")
    return

signal.signal(signal.SIGINT, signal_handler)

def save_session(new_session=False):
    """Save the current chat history to a file."""
    global current_session_name, current_session_file

    if new_session or current_session_file is None:
        # Need to create a new session file
        session_name = input("Enter session name (leave blank to use default): ").strip()

        if not session_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"default_{timestamp}"

        # Ensure the filename is valid
        session_name = "".join(c for c in session_name if c.isalnum() or c in "_-")
        filename = f"{session_name}.json"
        filepath = os.path.join(sessions_dir, filename)

        # Update current session tracking
        current_session_name = session_name
        current_session_file = filepath
    else:
        # Save to the existing session file
        filepath = current_session_file

    # Save the chat history
    with open(filepath, 'w') as f:
        json.dump(messages, f, indent=2)

    print(f"Session saved to {filepath}")

def clear_context():
    """Clear the chat history except for the system message."""
    global messages, current_session_file
    system_message = messages[0] if messages and messages[0]["role"] == "system" else {
        "role": "system",
        "content": DEFAULT_SYSTEM_MESSAGE
    }
    messages = [system_message]
    # We're creating a new conversation, so we should reset the current session
    current_session_file = None
    print("Context cleared. Only system message remains.")

def set_system_prompt():
    """Set a new system prompt."""
    global messages

    print("Enter new system prompt (press Enter on blank line to finish):")
    lines = []
    while True:
        line = input()
        if not line:
            break
        lines.append(line)

    new_system_prompt = "\n".join(lines)

    if not new_system_prompt:
        print("System prompt unchanged.")
        return

    # Update or add system message
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] = new_system_prompt
    else:
        messages.insert(0, {"role": "system", "content": new_system_prompt})

    print("System prompt updated.")

def load_session():
    """Load a chat history from a saved session file."""
    global messages, current_session_name, current_session_file

    # List available sessions
    session_files = [f for f in os.listdir(sessions_dir) if f.endswith('.json')]

    if not session_files:
        print("No saved sessions found.")
        return

    print("\nAvailable sessions:")
    for i, session_file in enumerate(session_files, 1):
        session_name = session_file[:-5]  # Remove .json extension
        if session_file == os.path.basename(current_session_file or ""):
            print(f"{i}. {session_name} (current)")
        else:
            print(f"{i}. {session_name}")

    try:
        choice = input("\nEnter session number to load (or press Enter to cancel): ")
        if not choice:
            print("Loading cancelled.")
            return

        choice = int(choice)
        if choice < 1 or choice > len(session_files):
            print("Invalid selection.")
            return

        selected_file = session_files[choice-1]
        filepath = os.path.join(sessions_dir, selected_file)

        with open(filepath, 'r') as f:
            loaded_messages = json.load(f)

        # Validate the loaded data
        if not isinstance(loaded_messages, list):
            print("Invalid session file format.")
            return

        messages = loaded_messages
        current_session_name = selected_file[:-5]  # Remove .json extension
        current_session_file = filepath
        print(f"Loaded session: {current_session_name}")

    except (ValueError, IndexError) as e:
        print(f"Error selecting session: {str(e)}")
    except json.JSONDecodeError:
        print("Error: The session file is corrupted or not in valid JSON format.")
    except Exception as e:
        print(f"Error loading session: {str(e)}")

def chat_with_model():
    """Main chat loop with the model."""
    print(f"Chat session started with model: {MODEL}")
    print("Type /clear to reset context, /save to save current session,")
    print("/save new to create a new session, /load to load a session,")
    print("/system to set system prompt, /exit or /bye to quit.")
    print("Press Ctrl+C to cancel current output.")
    print("-" * 50)

    while True:
        try:
            user_input = input("\nYou: ")

            # Check for commands
            if user_input.lower() in ["/bye", "/exit"]:
                print("Goodbye!")
                break
            elif user_input.lower() == "/clear":
                clear_context()
                continue
            elif user_input.lower() == "/save":
                save_session(new_session=False)
                continue
            elif user_input.lower() == "/save new":
                save_session(new_session=True)
                continue
            elif user_input.lower() == "/load":
                load_session()
                continue
            elif user_input.lower() == "/system":
                set_system_prompt()
                continue

            # Add user message to history
            messages.append({"role": "user", "content": user_input})

            # Prepare request payload
            payload = {
                "model": MODEL,
                "messages": messages,
                "stream": True,
                "options": {
                    "num_ctx":32768,
                }
            }

            # Make API call
            print("\nAssistant: ", end="", flush=True)
            response = requests.post(API_URL, json=payload, stream=True)

            if response.status_code != 200:
                print(f"Error: API returned status code {response.status_code}")
                print(response.text)
                continue

            # Process streaming response
            assistant_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "message" in chunk and "content" in chunk["message"]:
                            content = chunk["message"]["content"]
                            print(content, end="", flush=True)
                            assistant_response += content
                    except json.JSONDecodeError:
                        print(f"Error decoding JSON: {line}")

            print()  # Add newline after response

            # Add assistant response to history
            messages.append({"role": "assistant", "content": assistant_response})

        except KeyboardInterrupt:
            # Ctrl+C is already handled by signal handler
            continue
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    try:
        chat_with_model()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

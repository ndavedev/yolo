#!/usr/bin/env python3
import requests
import os
import signal
import sys
import datetime
import readline
import pickle
import json

# Load configuration from config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)

API_URL = config["API_URL"]
MODEL = config["MODEL"]
DEFAULT_SYSTEM_MESSAGE = config["DEFAULT_SYSTEM_MESSAGE"]
DATABASE_FILE = config["DATABASE_FILE"]
CONTEXT_WINDOW_SIZE = config["CONTEXT_WINDOW_SIZE"]

# Initialize chat history
messages = [
    {
        "role": "system",
        "content": DEFAULT_SYSTEM_MESSAGE
    }
]

# Session management
current_session_name = "default"
current_session_data = None  # Tracks the currently loaded session data

# Handle Ctrl+C to cancel current output but not exit the script
def signal_handler(sig, frame):
    print("\n[Output canceled]")
    return

signal.signal(signal.SIGINT, signal_handler)

def save_session(new_session=False):
    """Save the current chat history to the database."""
    global current_session_name, current_session_data

    if new_session or current_session_data is None:
        # Need to create a new session
        session_name = input("Enter session name (leave blank to use default): ").strip()

        if not session_name:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            session_name = f"default_{timestamp}"

        # Ensure the session name is valid
        session_name = "".join(c for c in session_name if c.isalnum() or c in "_-")

        # Update current session tracking
        current_session_name = session_name
        current_session_data = messages
    else:
        # Save to the existing session
        current_session_data = messages

    # Save the chat history to the database
    try:
        with open(DATABASE_FILE, 'rb') as f:
            database = pickle.load(f)
    except FileNotFoundError:
        database = {}

    database[current_session_name] = current_session_data

    with open(DATABASE_FILE, 'wb') as f:
        pickle.dump(database, f)

    print(f"Session saved to database with name: {current_session_name}")

def clear_context():
    """Clear the chat history except for the system message."""
    global messages, current_session_data
    system_message = messages[0] if messages and messages[0]["role"] == "system" else {
        "role": "system",
        "content": DEFAULT_SYSTEM_MESSAGE
    }
    messages = [system_message]
    # We're creating a new conversation, so we should reset the current session
    current_session_data = None
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
    """Load a chat history from the database."""
    global messages, current_session_name, current_session_data

    try:
        with open(DATABASE_FILE, 'rb') as f:
            database = pickle.load(f)
    except FileNotFoundError:
        print("No saved sessions found.")
        return

    if not database:
        print("No saved sessions found.")
        return

    print("\nAvailable sessions:")
    for i, session_name in enumerate(database.keys(), 1):
        if session_name == current_session_name:
            print(f"{i}. {session_name} (current)")
        else:
            print(f"{i}. {session_name}")

    try:
        choice = input("\nEnter session number to load (or press Enter to cancel): ")
        if not choice:
            print("Loading cancelled.")
            return

        choice = int(choice)
        if choice < 1 or choice > len(database):
            print("Invalid selection.")
            return

        selected_session_name = list(database.keys())[choice-1]
        messages = database[selected_session_name]
        current_session_name = selected_session_name
        current_session_data = messages
        print(f"Loaded session: {current_session_name}")

    except (ValueError, IndexError) as e:
        print(f"Error selecting session: {str(e)}")
    except Exception as e:
        print(f"Error loading session: {str(e)}")

def retrieve_relevant_information(user_input):
    """Retrieve relevant information from the database based on user input."""
    try:
        with open(DATABASE_FILE, 'rb') as f:
            database = pickle.load(f)
    except FileNotFoundError:
        return []

    relevant_info = []
    for session_name, session_data in database.items():
        for message in session_data:
            if user_input.lower() in message["content"].lower():
                relevant_info.append(message["content"])

    return relevant_info

def manage_context_window():
    """Manage the context window by removing older messages when it reaches a certain size."""
    global messages
    if len(messages) > CONTEXT_WINDOW_SIZE:
        messages = messages[-CONTEXT_WINDOW_SIZE:]

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

            # Retrieve relevant information
            relevant_info = retrieve_relevant_information(user_input)
            for info in relevant_info:
                messages.append({"role": "retrieved", "content": info})

            # Manage context window
            manage_context_window()

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

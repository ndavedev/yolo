import requests
import json
import os
import pickle
import readline
import sys

def get_story(prompt):
    url = "http://192.168.50.177:11434/api/chat"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "model": "hf.co/mradermacher/Pantheon-RP-1.8-24b-Small-3.1-i1-GGUF:Q4_K_M",
        "prompt": prompt
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        return response.json().get("story", "")
    else:
        return "Error: Unable to fetch story."

def save_session(session, name):
    if not os.path.exists("sessions"):
        os.makedirs("sessions")
    with open(f"sessions/{name}.pkl", "wb") as f:
        pickle.dump(session, f)

def load_session(name):
    try:
        with open(f"sessions/{name}.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None

def main():
    session = []
    history = []
    while True:
        try:
            user_input = input("You: ")
            if user_input in ["/bye", "/quit", "/exit"]:
                print("Goodbye!")
                break
            elif user_input.startswith("/save"):
                _, name = user_input.split(maxsplit=1)
                save_session(session, name)
                print(f"Session saved as {name}.")
            elif user_input.startswith("/load"):
                _, name = user_input.split(maxsplit=1)
                loaded_session = load_session(name)
                if loaded_session is not None:
                    session = loaded_session
                    print(f"Session {name} loaded.")
                else:
                    print(f"No session found with the name {name}.")
            else:
                story = get_story(user_input)
                print(f"Story: {story}")
                session.append((user_input, story))
                history.append(user_input)
        except KeyboardInterrupt:
            print("\nUse /bye, /quit, or /exit to exit.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()

def test_get_story():
    prompt = "Once upon a time"
    story = get_story(prompt)
    assert isinstance(story, str)

def test_save_session():
    session = [("Hello", "Hi there!")]
    save_session(session, "test_session")
    assert os.path.exists("sessions/test_session.pkl")

def test_load_session():
    session = load_session("test_session")
    assert session == [("Hello", "Hi there!")]

def test_main():
    # This is a placeholder for testing the main function.
    # Testing interactive functions can be complex and may require tools like `unittest.mock` or `pytest`.
    pass

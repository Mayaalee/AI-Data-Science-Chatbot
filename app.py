import streamlit as st
import time
import json
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
import os
import datetime
import requests
from dotenv import load_dotenv
from requests.exceptions import ConnectionError, Timeout

# ✅ Streamlit Page Config
st.set_page_config(page_title="AI Data Science Tutor", page_icon="🤖", layout="wide")

# ✅ Step 1: Ask User for Google API Key
st.sidebar.title("🔑 Enter Google Gemini API Key")
if "api_key" not in st.session_state:
    st.session_state.api_key = ""

api_key = st.sidebar.text_input("API Key:", type="password")

def validate_api_key(api_key):
    try:
        genai.configure(api_key=api_key)
        test_model = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=api_key)
        test_model.invoke("Hello")  # Test API Call
        return True
    except Exception:
        return False

if st.sidebar.button("Submit API Key"):
    if validate_api_key(api_key):
        st.session_state.api_key = api_key
        st.sidebar.success("✅ API Key is valid! Proceeding...")
        st.rerun()
    else:
        st.sidebar.error("❌ Invalid API Key! Please try again.")

# ✅ Stop execution if API key is missing
if not st.session_state.api_key:
    st.warning("⚠️ Please enter a valid Google API Key to continue.")
    st.stop()

# ✅ Configure AI Model
genai.configure(api_key=st.session_state.api_key)
chat_model = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash", google_api_key=st.session_state.api_key
)  # Initialize the model once

# ✅ Profanity Detection List
PROFANITY_LIST = ["badword1", "badword2", "offensivephrase"]  # Add more words

# ✅ IP Auto-Banning System
BANNED_IPS_FILE = "banned_ips.json"


def get_user_ip():
    try:
        response = requests.get("https://api64.ipify.org?format=json", timeout=2)  # Add a timeout
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()["ip"]
    except (ConnectionError, Timeout) as e:
        st.error(f"Error fetching IP address: {e}.  Please check your network connection.")
        return "Unknown"
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching IP address: {e}")
        return "Unknown"



def load_banned_ips():
    try:
        with open(BANNED_IPS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_banned_ips(banned_ips):
    try:
        with open(BANNED_IPS_FILE, "w") as f:
            json.dump(banned_ips, f, indent=4)
    except Exception as e:
        st.error(f"Error saving banned IPs: {e}")



# ✅ Check & Ban IP if Profanity Detected
user_ip = get_user_ip()
banned_ips = load_banned_ips()

if user_ip in banned_ips:
    st.error("🚫 Your IP has been banned for inappropriate language.")
    st.stop()

# ✅ Chat Management Functions
CHAT_DIR = "chat_sessions"
os.makedirs(CHAT_DIR, exist_ok=True)


def get_chat_history(chat_name):
    chat_file = os.path.join(CHAT_DIR, f"{chat_name}.json")
    try:
        with open(chat_file, "r") as hfile:
            return json.load(hfile)
    except (FileNotFoundError, json.JSONDecodeError):
        return []



def save_chat_history(chat_name, chat_data):
    chat_file = os.path.join(CHAT_DIR, f"{chat_name}.json")
    with open(chat_file, "w") as hfile:
        json.dump(chat_data, hfile, indent=4)



# ✅ Authentication System
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔑 Login to AI Data Science Tutor")
    username = st.text_input("Enter your username:")

    if st.button("Login"):
        if not username:
            st.error("Please enter a username.")
        else:
            st.session_state.username = username
            st.session_state.logged_in = True
            st.session_state.current_chat = f"Chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
            save_chat_history(st.session_state.current_chat, [])
            st.rerun()
    st.stop()

username = st.session_state.username
st.sidebar.write(f"👋 Welcome, {username}!")

# ✅ Multi-Chat System
if "current_chat" not in st.session_state:
    st.session_state.current_chat = f"Chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

st.sidebar.subheader("📂 Chat Sessions")
chat_names = [f.replace(".json", "") for f in os.listdir(CHAT_DIR) if f.endswith(".json")]

if chat_names:
    selected_chat = st.sidebar.radio("Select Chat", chat_names, index=0)
    st.session_state.current_chat = selected_chat

if st.sidebar.button("➕ New Chat"):
    new_chat = f"Chat_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    st.session_state.current_chat = new_chat
    save_chat_history(new_chat, [])
    st.rerun()

if st.sidebar.button("🗑 Delete Current Chat"):
    chat_path = os.path.join(CHAT_DIR, f"{st.session_state.current_chat}.json")
    if os.path.exists(chat_path):
        os.remove(chat_path)
        st.success("Chat deleted successfully!")
        st.rerun()


# ✅ Chat Interface
st.title("🧠 AI Data Science Tutor")

# ✅ Display Chat History (Sorted by Date)
chat_history = get_chat_history(st.session_state.current_chat)
sorted_chats = {}

for entry in chat_history:
    date = entry["timestamp"].split()[0]
    if date not in sorted_chats:
        sorted_chats[date] = []
    sorted_chats[date].append(entry)

for date, messages in sorted_chats.items():
    st.subheader(f"📅 {date}")
    for chat in messages:
        role_icon = "👤" if chat["role"] == "user" else "🤖"
        with st.chat_message(chat["role"]):
            st.markdown(f"**{role_icon} {chat['role'].title()}**\n\n{chat['message']}")



# ✅ AI Response Handling
def contains_profanity(text):
    return any(word in text.lower() for word in PROFANITY_LIST)


user_input = st.chat_input("Ask a Data Science question...")

if user_input:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if contains_profanity(user_input):
        banned_ips.append(user_ip)
        save_banned_ips(banned_ips)
        st.error("🚫 Profanity detected! Your IP has been banned.")
        st.stop()

    chat_history.append({"role": "user", "message": user_input, "timestamp": timestamp})
    save_chat_history(st.session_state.current_chat, chat_history)

    with st.chat_message("assistant"):
        with st.spinner("Thinking... 🤔"):
            try:
                response = chat_model.invoke(user_input)
                chat_history.append(
                    {"role": "assistant", "message": response.content, "timestamp": timestamp}
                )
                save_chat_history(st.session_state.current_chat, chat_history)
                st.markdown(f"**🤖 AI:**\n\n{response.content}")
            except Exception as e:
                st.error(f"An error occurred: {e}")

    st.rerun()

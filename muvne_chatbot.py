# muvne_chatbot.py
import streamlit as st
import os
from pathlib import Path
import yaml
import logging
import uuid
from datetime import datetime
import anthropic
from dotenv import load_dotenv
import sqlite3
import re
import json
import pandas as pd

# Configure logging
logging.basicConfig(
    filename='muvne_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)

# Load environment variables
load_dotenv()

def set_page_style():
    """Set Streamlit page style for RTL and Hebrew"""
    st.markdown("""
    <style>
    .main { direction: rtl; }
    .stChatMessage { direction: rtl; text-align: right; }
    .stChatInput { direction: rtl; text-align: right; }
    .stMarkdown { direction: rtl; text-align: right; }
    .stButton button { direction: rtl; }
    .stSelectbox { direction: rtl; }
    table { direction: rtl; }
    th { text-align: right; }
    td { text-align: right; }
    </style>
    """, unsafe_allow_html=True)

class SalesChatBot:
    def __init__(self):
        """Initialize the chatbot with basic configuration"""
        self.base_dir = Path.cwd()
        self.config_dir = self.base_dir / "config"
        self.db_path = self.base_dir / "database" / "chat.db"
        self.yaml_configs = {}
        
        # Create necessary directories
        os.makedirs(self.db_path.parent, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Initialize components
        self.setup_database()
        self.load_configs()
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def load_configs(self):
        """Load all YAML configuration files"""
        config_files = [
            'company_info.yaml',
            'products.yaml',
            'legal.yaml',
            'sales_responses.yaml'
        ]
        
        for config_file in config_files:
            try:
                file_path = self.config_dir / config_file
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.yaml_configs[config_file] = yaml.safe_load(f)
                    logging.info(f"Loaded config: {config_file}")
            except Exception as e:
                logging.error(f"Error loading {config_file}: {str(e)}")

    def setup_database(self):
        """Enhanced database setup with lead tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create tables
            c.execute('''CREATE TABLE IF NOT EXISTS conversations
                        (conversation_id TEXT PRIMARY KEY,
                         lead_status TEXT DEFAULT 'new',
                         investor_type TEXT,
                         contact_info TEXT,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS messages
                        (message_id TEXT PRIMARY KEY,
                         conversation_id TEXT,
                         role TEXT,
                         content TEXT,
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id))''')
            
            c.execute('''CREATE TABLE IF NOT EXISTS leads
                        (lead_id TEXT PRIMARY KEY,
                         conversation_id TEXT,
                         name TEXT,
                         email TEXT,
                         phone TEXT,
                         investor_type TEXT,
                         interest_level TEXT,
                         notes TEXT,
                         status TEXT DEFAULT 'new',
                         timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                         FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id))''')
            
            conn.commit()
            conn.close()
            logging.info("Database setup complete")
        except Exception as e:
            logging.error(f"Database setup error: {str(e)}")
            raise

    def save_message(self, conversation_id: str, role: str, content: str):
        """Save message to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            # Create conversation if doesn't exist
            c.execute('INSERT OR IGNORE INTO conversations (conversation_id) VALUES (?)',
                     (conversation_id,))
            
            message_id = str(uuid.uuid4())
            c.execute('''INSERT INTO messages (message_id, conversation_id, role, content)
                        VALUES (?, ?, ?, ?)''',
                     (message_id, conversation_id, role, content))
            
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error saving message: {str(e)}")

    def get_response(self, query: str, conversation_id: str) -> str:
        """Generate response using Claude"""
        try:
            # Get conversation history
            history = self.get_conversation_history(conversation_id)
            history_text = "\n".join([f"{'לקוח' if msg[0] == 'user' else 'נציג'}: {msg[1]}" for msg in history])
            
            # Prepare system prompt
            system_prompt = f"""אתה נציג שיווק השקעות מקצועי ומנוסה של מובנה גלובל.

            היסטוריית השיחה האחרונה:
            {history_text}

            הנחיות:
            1. תן הסברים מקצועיים ומעמיקים, אבל בשפה ברורה
            2. אסור לציין אחוזי תשואה או ריבית ספציפיים
            3. הדגש את היתרונות הייחודיים של החברה
            4. השתמש בדוגמאות להמחשה כשצריך

            ענה בצורה טבעית ומקצועית."""

            # Get response from Claude
            response = self.client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=800,
                temperature=0.7,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": query
                }]
            )

            bot_response = response.content[0].text if response.content else "מצטער, לא הצלחתי להבין. אנא נסה שוב."
            return bot_response
            
        except Exception as e:
            logging.error(f"Error generating response: {str(e)}")
            return "מצטער, אירעה שגיאה. אנא נסה שוב."

    def get_conversation_history(self, conversation_id: str, limit: int = 5) -> list:
        """Get recent conversation history"""
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            
            c.execute('''SELECT role, content FROM messages
                        WHERE conversation_id = ?
                        ORDER BY timestamp DESC
                        LIMIT ?''', (conversation_id, limit))
            
            history = c.fetchall()
            conn.close()
            
            return [(msg[0], msg[1]) for msg in reversed(history)]
        except Exception as e:
            logging.error(f"Error getting conversation history: {str(e)}")
            return []

def main():
    """Main function to run the chatbot"""
    try:
        # Initialize bot
        bot = SalesChatBot()
        
        # Page setup
        st.set_page_config(page_title="מובנה גלובל - שיווק השקעות", layout="wide")
        set_page_style()
        
        # Header
        st.markdown("""
        <div style='text-align: right; direction: rtl;'>
        <h1>מובנה גלובל</h1>
        <h3>חברה לשיווק השקעות</h3>
        <p>בעלת רישיון משווק השקעות מטעם רשות ניירות ערך</p>
        </div>
        """, unsafe_allow_html=True)

        # Initialize session state
        if 'conversation_id' not in st.session_state:
            st.session_state.conversation_id = str(uuid.uuid4())
            
        if 'messages' not in st.session_state:
            st.session_state.messages = []

        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("איך אוכל לעזור לך היום?"):
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Save user message
            bot.save_message(st.session_state.conversation_id, "user", prompt)

            # Get and display bot response
            with st.chat_message("assistant"):
                response = bot.get_response(prompt, st.session_state.conversation_id)
                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Save bot response
                bot.save_message(st.session_state.conversation_id, "assistant", response)

    except Exception as e:
        st.error("אירעה שגיאה בטעינת המערכת. אנא רענן את הדף.")
        logging.error(f"System error: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()
import streamlit as st
import random
import time
import urllib.request
from streamlit_drawable_canvas import st_canvas

# --- 1. Word Loader (The Big Dictionary) ---
@st.cache_data
def load_words():
    # We fetch a list of 2,500+ common nouns to ensure variety but keep it 'drawable'
    # Fallback list in case internet fails
    default_words = ["Time", "Person", "Year", "Way", "Day", "Thing", "Man", "World", "Life", "Hand"]
    
    url = "https://raw.githubusercontent.com/taikuukaits/SimpleWordlists/master/Wordlist-Nouns-Common-Audited-Len-3-6.txt"
    
    try:
        with urllib.request.urlopen(url) as response:
            text = response.read().decode('utf-8')
            words = [w.strip() for w in text.splitlines() if w.strip()]
            return words if words else default_words
    except Exception as e:
        return default_words

# Load the dictionary once
DICTIONARY = load_words()

# --- 2. Shared Game State ---
@st.cache_resource
class GameState:
    def __init__(self):
        self.players = []
        self.scores = {}
        self.phase = "LOBBY" # LOBBY, PLAYING, ROUND_OVER, GAMEOVER
        
        # Match Data
        self.drawer_idx = 0
        self.current_word = None
        self.drawing_data = None 
        self.guesses_left = 3
        self.turn_start_time = 0
        self.last_update = time.time()
        self.last_outcome = ""

    def join_game(self, name):
        if name not in self.players and len(self.players) < 2:
            self.players.append(name)
            self.scores[name] = 0

    def start_round(self):
        if len(self.players) < 2:
            return False
        
        # Pick a random word from the massive dictionary
        self.current_word = random.choice(DICTIONARY)
        
        # Capitalize it nicely
        self.current_word = self.current_word.capitalize()
        
        self.drawing_data = None 
        self.guesses_left = 3
        self.turn_start_time = time.time()
        self.phase = "PLAYING"
        return True

    def update_drawing(self, json_data):
        self.drawing_data = json_data
        self.last_update = time.time()

    def make_guess(self, guesser_name, guess_text):
        if self.guesses_left <= 0:
            return False

        # Strict Check (Case Insensitive)
        if guess_text.strip().lower() == self.current_word.lower():
            self.scores[guesser_name] += 10
            self.phase = "ROUND_OVER"
            self.last_outcome = f"✅ Correct! {guesser_name} guessed '{self.current_word}'"
            return True
        else:
            self.guesses_left -= 1
            if self.guesses_left <= 0:
                self.phase = "ROUND_OVER"
                self.last_outcome = f"❌ Out of guesses! The word was '{self.current_word}'"
            return False

    def next_turn(self):
        self.drawer_idx = (self.drawer_idx + 1) % len(self.players)
        self.start_round()

    def reset_game(self):
        self.players = []
        self.scores = {}
        self.phase = "LOBBY"
        self.drawer_idx = 0

def get_game():
    return GameState()

# --- 3. App UI ---
st.set_page_config(page_title="Pictionary Live", page_icon="🎨", layout="wide")

st.markdown("""
    <style>
    div.stButton > button {
        width: 100%; height: 50px; font-size: 18px; font-weight: bold; border-radius: 8px;
    }
    .word-box {
        background-color: #FFF9C4; color: #FBC02D; padding: 20px;
        text-align: center; font-size: 30px; font-weight: bold;
        border-radius: 15px; border: 2px solid #FBC02D; margin-bottom: 20px;
    }
    .score-card {
        background-color: #f0f2f6; padding: 10px; border-radius: 10px;
        text-align: center; font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

game = get_game()

# --- 4. Login ---
if 'player_name' not in st.session_state:
    st.title("🎨 Pictionary Login")
    st.write(f"Dictionary Size: **{len(DICTIONARY)} words** loaded.")
    name = st.text_input("Enter your name:")
    if st.button("Join"):
        if name:
            game.join_game(name)
            st.session_state.player_name = name
            st.rerun()
    st.stop()

# --- 5. Sidebar ---
with st.sidebar:
    st.write(f"👤 **{st.session_state.player_name}**")
    st.write("### 🏆 Scores")
    for p, s in game.scores.items():
        st.write(f"{p}: {s}")
    st.write("---")
    if st.button("🔥 Reset Game"):
        game.reset_game()
        st.rerun()

# --- 6. Main Game Loop ---
@st.fragment(run_every=1)
def draw_game():
    me = st.session_state.player_name
    
    # === PHASE: LOBBY ===
    if game.phase == "LOBBY":
        st.title("Waiting Room")
        st.info("Need minimum 2 players.")
        
        cols = st.columns(4)
        for i, p in enumerate(game.players):
            cols[i%4].success(p)
            
        if len(game.players) >= 2:
            st.write("---")
            if st.button("START GAME"):
                game.start_round()
                st.rerun()

    # === PHASE: PLAYING ===
    elif game.phase == "PLAYING":
        drawer_name = game.players[game.drawer_idx]
        is_drawer = (me == drawer_name)
        
        st.subheader(f"🎨 Drawer: {drawer_name}")
        
        c1, c2 = st.columns([3, 1])
        
        with c1:
            if is_drawer:
                st.info(f"You are drawing: **{game.current_word}**")
                
                # Active Canvas
                canvas_result = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)",
                    stroke_width=3,
                    stroke_color="#000000",
                    background_color="#ffffff",
                    update_streamlit=True,
                    height=400,
                    width=600,
                    drawing_mode="freedraw",
                    key="canvas_drawer",
                )
                
                if canvas_result.json_data is not None:
                    if canvas_result.json_data != game.drawing_data:
                        game.update_drawing(canvas_result.json_data)
            
            else:
                st.write(f"Guess the word! ({game.guesses_left} tries left)")
                
                # Passive Canvas
                st_canvas(
                    initial_drawing=game.drawing_data,
                    stroke_width=3,
                    stroke_color="#000000",
                    background_color="#ffffff",
                    height=400,
                    width=600,
                    drawing_mode="transform",
                    key=f"canvas_guesser_{game.last_update}",
                )

        with c2:
            if not is_drawer:
                st.write("### Make a Guess")
                with st.form("guess_form"):
                    guess = st.text_input("Type here:")
                    submitted = st.form_submit_button("Submit")
                    if submitted and guess:
                        game.make_guess(me, guess)
                        st.rerun()
            else:
                st.markdown(f"""
                <div class="word-box">
                    SECRET WORD<br>{game.current_word}
                </div>
                """, unsafe_allow_html=True)
                st.warning("Don't write letters! Just draw.")

    # === PHASE: ROUND OVER ===
    elif game.phase == "ROUND_OVER":
        if game.last_outcome.startswith("✅"):
            st.balloons()
            st.success(game.last_outcome)
        else:
            st.error(game.last_outcome)
            
        st.write("---")
        
        # Show Final Drawing
        if game.drawing_data:
            st_canvas(
                initial_drawing=game.drawing_data, 
                stroke_width=3,
                stroke_color="#000000",
                background_color="#ffffff",
                drawing_mode="transform", 
                height=300, 
                width=500, 
                key="final_view"
            )

        if st.button("Start Next Round ➡️"):
            game.next_turn()
            st.rerun()

draw_game()

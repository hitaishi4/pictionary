import streamlit as st
import random
import time
from streamlit_drawable_canvas import st_canvas

# --- 1. The Pictionary Dictionary ---
# A curated list of things that are actually possible to draw
WORDS = [
    "Apple", "Bicycle", "Car", "Dog", "Elephant", "Flower", "Guitar", "House",
    "Ice Cream", "Jellyfish", "Kite", "Lion", "Moon", "Nose", "Owl", "Pizza",
    "Queen", "Rainbow", "Sun", "Tree", "Umbrella", "Violin", "Whale", "Xylophone",
    "Yacht", "Zebra", "Airplane", "Basketball", "Camera", "Dinosaur", "Ear",
    "Fish", "Grapes", "Helicopter", "Igloo", "Jacket", "Key", "Lamp", "Mouse",
    "Necklace", "Orange", "Pencil", "Robot", "Snake", "Train", "Unicorn", "Volcano",
    "Watch", "Yo-Yo", "Bee", "Cat", "Duck", "Frog", "Ghost", "Hat", "Island",
    "Jungle", "Kangaroo", "Leaf", "Mountain", "Nest", "Octopus", "Parrot", "Rabbit",
    "Spider", "Turtle", "Vase", "Window", "Butterfly", "Cloud", "Donut", "Eye",
    "Fire", "Glasses", "Hand", "Ice", "Jar", "Ladder", "Mroom", "Net", "Ocean",
    "Pen", "Ring", "Star", "Tent", "Van", "Water", "Box", "Cup", "Door"
]

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
        self.drawing_data = None # Stores the JSON strokes
        self.guesses_left = 3
        self.turn_start_time = 0
        self.last_update = time.time()

    def join_game(self, name):
        if name not in self.players and len(self.players) < 2:
            self.players.append(name)
            self.scores[name] = 0

    def start_round(self):
        if len(self.players) < 2:
            return False
        
        # Pick a word
        self.current_word = random.choice(WORDS)
        self.drawing_data = None # Clear board
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

        # Check Guess (Case insensitive)
        if guess_text.strip().lower() == self.current_word.lower():
            # Correct!
            self.scores[guesser_name] += 10
            self.phase = "ROUND_OVER"
            self.last_outcome = f"✅ Correct! {guesser_name} guessed '{self.current_word}'"
            return True
        else:
            # Wrong
            self.guesses_left -= 1
            if self.guesses_left <= 0:
                self.phase = "ROUND_OVER"
                self.last_outcome = f"❌ Out of guesses! The word was '{self.current_word}'"
            return False

    def next_turn(self):
        # Rotate Drawer
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
    name = st.text_input("Enter your name:")
    if st.button("Join"):
        if name:
            game.join_game(name)
            st.session_state.player_name = name
            st.rerun()
    st.stop()

# --- 5. Main Game Loop ---
@st.fragment(run_every=1)
def draw_game():
    me = st.session_state.player_name
    
    # Sidebar Scores
    with st.sidebar:
        st.write("### 🏆 Scores")
        for p, s in game.scores.items():
            st.write(f"{p}: {s}")
        st.write("---")
        if st.button("🔥 Reset Game"):
            game.reset_game()
            st.rerun()

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
            # --- CANVAS LOGIC ---
            if is_drawer:
                st.info(f"You are drawing: **{game.current_word}**")
                
                # Active Canvas for Drawer
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
                
                # Sync data to server
                if canvas_result.json_data is not None:
                    # Only update if changed to reduce lag
                    if canvas_result.json_data != game.drawing_data:
                        game.update_drawing(canvas_result.json_data)
            
            else:
                st.write(f"Guess the word! ({game.guesses_left} tries left)")
                
                # Passive Canvas for Guesser (Read-Only)
                # We feed the JSON data from the drawer into initial_drawing
                st_canvas(
                    initial_drawing=game.drawing_data,
                    stroke_width=3,
                    stroke_color="#000000",
                    background_color="#ffffff",
                    height=400,
                    width=600,
                    drawing_mode="transform", # Makes it read-only
                    key=f"canvas_guesser_{game.last_update}", # Unique key forces redraw
                )

        with c2:
            # --- GUESSING LOGIC ---
            if not is_drawer:
                st.write("### Make a Guess")
                
                # Using a form so Enter key works
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
                st.warning("Don't write the letters! Just draw.")

    # === PHASE: ROUND OVER ===
    elif game.phase == "ROUND_OVER":
        if game.last_outcome.startswith("✅"):
            st.balloons()
            st.success(game.last_outcome)
        else:
            st.error(game.last_outcome)
            
        st.write("---")
        
        # Show final drawing one last time
        if game.drawing_data:
            st_canvas(initial_drawing=game.drawing_data, drawing_mode="transform", height=300, width=500, key="final_view")

        if st.button("Start Next Round ➡️"):
            game.next_turn()
            st.rerun()

draw_game()

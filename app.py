import json
import random
import datetime as dt
import base64
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

try:
    import gspread
    from gspread.exceptions import WorksheetNotFound, APIError
    from google.oauth2.service_account import Credentials
except ImportError:
    gspread = None
    WorksheetNotFound = Exception
    APIError = Exception
    Credentials = None


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(
    page_title="StatGuessr",
    page_icon="📊",
    layout="centered",
)

APP_DIR = Path(__file__).parent
DATA_FILE = APP_DIR / "stats.json"
ASSETS_DIR = APP_DIR / "assets"
ONEPOLL_LOGO = ASSETS_DIR / "onepoll_logo.png"
ROUNDS_PER_GAME = 5
LEADERBOARD_WORKSHEET_NAME = "Leaderboard"


# -----------------------------
# Styling
# -----------------------------
st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 0.7rem;
        padding-bottom: 1.5rem;
        max-width: 820px;
    }

    .hero {
        text-align: center;
        margin-bottom: 0.35rem;
    }

    .compact-hero {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        margin-bottom: 0.4rem;
    }

    .onepoll-logo {
        height: 42px;
        width: auto;
        object-fit: contain;
    }

    .hero h1 {
        margin: 0;
        font-size: 2rem;
        line-height: 1.1;
    }

    .hero p {
        color: #6b7280;
        margin-top: 0.15rem;
        margin-bottom: 0;
        font-size: 0.88rem;
    }

    .panel {
        background: linear-gradient(180deg, #ffffff 0%, #fafafa 100%);
        border: 1px solid #ececec;
        border-radius: 16px;
        padding: 0.85rem 0.95rem;
        margin-bottom: 0.65rem;
        box-shadow: 0 6px 18px rgba(0,0,0,0.04);
    }

    .question-text {
        font-size: 1.04rem;
        font-weight: 750;
        line-height: 1.42;
        margin-bottom: 0.55rem;
    }

    .guess-display {
        text-align: center;
        font-size: 2.55rem;
        font-weight: 800;
        line-height: 1;
        margin: 0.2rem 0 0.45rem 0;
        color: #111827;
    }

    .guess-card {
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.65rem;
        background: #ffffff;
        margin-bottom: 0.55rem;
    }

    .result-card {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 0.8rem 0.95rem;
        margin-top: 0.55rem;
        margin-bottom: 0.65rem;
    }

    .leaderboard-row {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.65rem 0.85rem;
        margin-bottom: 0.45rem;
    }

    .mode-banner {
        background: linear-gradient(90deg, #eff6ff 0%, #f8fafc 100%);
        border: 1px solid #bfdbfe;
        border-radius: 14px;
        padding: 0.55rem 0.8rem;
        margin-bottom: 0.55rem;
        font-size: 0.9rem;
    }

    .mode-title {
        font-weight: 750;
        color: #1d4ed8;
        margin-bottom: 0.05rem;
    }

    .how-to-play {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 0.55rem 0.75rem;
        margin-bottom: 0.55rem;
        color: #374151;
        font-size: 0.88rem;
    }

    .muted {
        color: #6b7280;
        font-size: 0.9rem;
    }

    .pill {
        display: inline-block;
        padding: 0.28rem 0.58rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 650;
        margin-right: 0.3rem;
        margin-bottom: 0.25rem;
        background: #f3f4f6;
        color: #111827;
    }

    .pill-easy {
        background: #dcfce7;
        color: #166534;
    }

    .pill-medium {
        background: #fef3c7;
        color: #92400e;
    }

    .pill-hard {
        background: #fee2e2;
        color: #991b1b;
    }

    .share-box {
        background: #f9fafb;
        border: 1px dashed #d1d5db;
        border-radius: 14px;
        padding: 0.8rem 0.9rem;
        white-space: pre-wrap;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 0.9rem;
    }

    h2, h3 {
        margin-top: 0.45rem !important;
        margin-bottom: 0.45rem !important;
    }

    div[data-testid="stSlider"] {
        padding-top: 0rem;
        padding-bottom: 0.1rem;
    }

    div[data-testid="stProgress"] {
        margin-bottom: 0.25rem;
    }

    .block-container hr {
        margin-top: 0.85rem;
        margin-bottom: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Launch polish settings
# -----------------------------
SHORTENED_QUESTIONS = {
    "What percentage of UK parents with children aged 3–16 who subscribe to a streaming service say they always check age ratings?":
        "What percentage of streaming-service parents always check age ratings?",
    "What percentage of those parents recognised the age rating symbols shown to them?":
        "What percentage of streaming-service parents recognised the age rating symbols shown to them?",
    "What percentage of UK office workers say they would feel more positive about employer flexibility during major cultural or sporting events?":
        "What percentage of office workers would feel more positive about employer flexibility during major cultural or sporting events?",
    "What percentage of UK office workers say they would be more likely to go into the office if their employer showed a major match there?":
        "What percentage of office workers would be more likely to go in if their employer showed a major match there?",
    "What percentage of UK adults are more likely to host or attend a house party than go to a bar or club on New Year’s Eve?":
        "What percentage of UK adults are more likely to choose a house party than a bar or club on New Year’s Eve?",
    "What percentage of UK adults say they would worry about being taken advantage of if people knew they had won the lottery?":
        "What percentage of UK adults would worry about being taken advantage of after a lottery win?",
    "What percentage of UK adults say their biggest concern after winning the lottery would be being asked for money or loans?":
        "What percentage of UK adults say their biggest lottery-win concern would be being asked for money?",
    "What percentage of UK adults think New Year’s Eve food and drink price increases are unfair?":
        "What percentage of UK adults think New Year’s Eve food and drink price hikes are unfair?",
    "What percentage of UK adults are aware that bathroom products can come in refillable or reusable alternatives?":
        "What percentage of UK adults know bathroom products can come in refillable or reusable alternatives?"
}

PARKED_STAT_IDS = {
    "stat_025",
    "stat_026"
}


# -----------------------------
# Core data helpers
# -----------------------------
def load_stats():
    if not DATA_FILE.exists():
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def image_to_base64(path):
    if not path.exists():
        return None

    with open(path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()
    
def request_scroll_to_top():
    st.session_state.scroll_to_top = True


def perform_scroll_to_top_if_needed():
    if st.session_state.get("scroll_to_top", False):
        components.html(
            """
            <script>
            window.parent.scrollTo({ top: 0, behavior: "smooth" });
            </script>
            """,
            height=0,
        )
        st.session_state.scroll_to_top = False

def display_question(stat):
    original = stat.get("question", "")
    return SHORTENED_QUESTIONS.get(original, original)


def calculate_score(guess, actual):
    diff = abs(guess - actual)
    score = max(0, 5000 - diff * 100)
    return score


def infer_difficulty(stat):
    if stat.get("difficulty"):
        return stat["difficulty"]

    question = display_question(stat)
    category = stat.get("category", "")
    answer = stat.get("answer", 50)

    if len(question) > 125:
        return "Hard"

    if category in ["News / Media", "Streaming / Family", "Cycling / E-bikes", "Work / Sport"]:
        return "Medium"

    if answer <= 25 or answer >= 80:
        return "Hard"

    if 40 <= answer <= 70:
        return "Medium"

    return "Easy"


def difficulty_pill_class(difficulty):
    if difficulty == "Easy":
        return "pill pill-easy"
    if difficulty == "Hard":
        return "pill pill-hard"
    return "pill pill-medium"


def did_you_know_text(stat):
    if stat.get("fact"):
        return stat["fact"]

    answer = stat.get("answer")
    base_note = stat.get("base_note", "")

    if base_note:
        return f"The survey result was {answer}%. {base_note}."
    return f"The survey result was {answer}%."


def feedback_band(score):
    if score >= 4800:
        return "🎯 Almost perfect", "That is annoyingly accurate."
    if score >= 4200:
        return "👌 Very close", "Strong public-opinion instincts."
    if score >= 3000:
        return "🙂 Decent effort", "Pretty respectable guessing."
    if score >= 1800:
        return "😬 Bit off", "You were in the right area… spiritually."
    return "💀 Miles off", "A spectacularly brave guess."


def final_verdict(total_score, max_score):
    pct = total_score / max_score if max_score else 0

    if pct >= 0.90:
        return "🧠 Survey Wizard", "You clearly live inside survey tables."
    if pct >= 0.75:
        return "📊 Data Detective", "Very strong feel for what Britain thinks."
    if pct >= 0.60:
        return "🤔 Professional Guesser", "Solid instincts, with a few rogue moments."
    if pct >= 0.40:
        return "🎲 Lucky Punt Merchant", "Chaotic, but occasionally inspired."
    return "🍻 Pub Logic Champion", "The vibes were strong. The accuracy was optional."


def get_filtered_stats(use_quality_filter=True):
    stats = load_stats()

    if not use_quality_filter:
        return stats

    filtered = []
    for stat in stats:
        if stat.get("id") in PARKED_STAT_IDS:
            continue

        if not isinstance(stat.get("answer"), int):
            continue

        if stat.get("answer") < 0 or stat.get("answer") > 100:
            continue

        filtered.append(stat)

    return filtered


def get_seed_for_mode(mode, selected_date):
    if mode == "Daily Challenge":
        return int(selected_date.strftime("%Y%m%d"))
    return random.randint(1, 10_000_000)


def pick_rounds(stats, mode, selected_date):
    rounds_to_play = min(ROUNDS_PER_GAME, len(stats))

    if rounds_to_play == 0:
        return []

    if mode == "Daily Challenge":
        rng = random.Random(get_seed_for_mode(mode, selected_date))
        return rng.sample(stats, rounds_to_play)

    rng = random.Random()
    stats_copy = stats[:]
    rng.shuffle(stats_copy)
    return stats_copy[:rounds_to_play]


def build_game_key(mode, selected_date, quality_filter):
    if mode == "Daily Challenge":
        return f"daily_{selected_date.isoformat()}_filter_{quality_filter}"
    return f"practice_{st.session_state.get('practice_run_id', 1)}_filter_{quality_filter}"


def build_share_text():
    total = st.session_state.total_score
    total_rounds = len(st.session_state.rounds)
    max_score = total_rounds * 5000

    if st.session_state.mode == "Daily Challenge":
        headline = f"📊 StatGuessr — Daily Challenge ({st.session_state.selected_date.isoformat()})"
    else:
        headline = "📊 StatGuessr — Practice Mode"

    return f"""{headline}

I scored {total:,} / {max_score:,} on StatGuessr.

Can you beat me?
"""


# -----------------------------
# Google Sheets leaderboard helpers
# -----------------------------
def google_leaderboard_configured():
    if gspread is None or Credentials is None:
        return False

    try:
        return "google_sheet_id" in st.secrets and "gcp_service_account" in st.secrets
    except Exception:
        return False


@st.cache_resource
def get_sheets_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]

    service_account_info = dict(st.secrets["gcp_service_account"])

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes
    )

    return gspread.authorize(credentials)


def get_leaderboard_worksheet():
    if not google_leaderboard_configured():
        return None

    client = get_sheets_client()
    spreadsheet = client.open_by_key(st.secrets["google_sheet_id"])

    try:
        worksheet = spreadsheet.worksheet(LEADERBOARD_WORKSHEET_NAME)
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(
            title=LEADERBOARD_WORKSHEET_NAME,
            rows=1000,
            cols=10
        )
        worksheet.append_row(
            [
                challenge_id,
                player_name,
                int(score),
                int(max_score),
                pct,
                submitted_at
            ],
            value_input_option="USER_ENTERED"
        )

        load_leaderboard_entries_cached.clear()
        return True, "Score added to today's leaderboard."

    values = worksheet.get_all_values()

    if not values:
        worksheet.append_row(
            ["challenge_id", "player_name", "score", "max_score", "pct", "submitted_at"],
            value_input_option="USER_ENTERED"
        )

    return worksheet


def get_challenge_id():
    return st.session_state.selected_date.isoformat()


def clean_player_name(name):
    name = str(name).strip()

    if not name:
        return None

    return name[:24]


def safe_int(value, default=0):
    try:
        return int(float(value))
    except Exception:
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


@st.cache_data(ttl=60, show_spinner=False)
def load_leaderboard_entries_cached(challenge_id):
    """
    Cached Google Sheets read.
    This avoids hitting the Google Sheets API on every Streamlit rerun.
    Cache refreshes every 60 seconds.
    """
    try:
        worksheet = get_leaderboard_worksheet()

        if worksheet is None:
            return []

        return worksheet.get_all_records()

    except APIError as e:
        # 429 = quota exceeded / too many requests
        st.warning("Leaderboard is temporarily rate-limited. Try again in about a minute.")
        return []

    except Exception:
        return []


def get_daily_leaderboard(limit=10):
    challenge_id = get_challenge_id()

    entries = [
        entry for entry in load_leaderboard_entries_cached(challenge_id)
        if str(entry.get("challenge_id")) == challenge_id
    ]

    entries.sort(
        key=lambda x: (
            safe_int(x.get("score")),
            str(x.get("submitted_at", ""))
        ),
        reverse=True
    )

    return entries[:limit]


def add_leaderboard_entry(player_name, score, max_score):
    if not google_leaderboard_configured():
        return False, "Google Sheets leaderboard is not configured yet."

    worksheet = get_leaderboard_worksheet()

    if worksheet is None:
        return False, "Could not connect to the leaderboard sheet."

    player_name = clean_player_name(player_name)

    if not player_name:
        return False, "Please enter a display name."

    challenge_id = get_challenge_id()
    pct = round((score / max_score) * 100, 1) if max_score else 0
    submitted_at = dt.datetime.now().isoformat(timespec="seconds")

    rows = worksheet.get_all_values()

    for row_number, row in enumerate(rows[1:], start=2):
        existing_challenge_id = row[0] if len(row) > 0 else ""
        existing_player_name = row[1] if len(row) > 1 else ""
        existing_score = safe_int(row[2] if len(row) > 2 else 0)

        if (
            existing_challenge_id == challenge_id
            and existing_player_name.lower() == player_name.lower()
        ):
            if int(score) > existing_score:
                worksheet.update(
                    range_name=f"A{row_number}:F{row_number}",
                    values=[[
                        challenge_id,
                        player_name,
                        int(score),
                        int(max_score),
                        pct,
                        submitted_at
                    ]]
                )
                load_leaderboard_entries_cached.clear()
                return True, "Leaderboard updated with your new best score."

            return False, "You already have an equal or better score on today's leaderboard."

    worksheet.append_row(
        [
            challenge_id,
            player_name,
            int(score),
            int(max_score),
            pct,
            submitted_at
        ],
        value_input_option="USER_ENTERED"
    )

    load_leaderboard_entries_cached.clear()

    request_scroll_to_top()
    return True, "Score added to today's leaderboard."

def render_leaderboard(title="🏆 Today's leaderboard", limit=10):
    st.markdown(f"### {title}")

    if not google_leaderboard_configured():
        st.info("Leaderboard is not configured yet. Add Google Sheets secrets to enable it.")
        return

    entries = get_daily_leaderboard(limit=limit)

    if not entries:
        st.info("No scores yet. Be the first on today's leaderboard.")
        return

    for idx, entry in enumerate(entries, start=1):
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."

        player_name = entry.get("player_name", "Player")
        score = safe_int(entry.get("score"))
        max_score = safe_int(entry.get("max_score"))
        pct = safe_float(entry.get("pct"))

        st.markdown(
            f"""
            <div class="leaderboard-row">
                <strong>{medal} {player_name}</strong><br>
                Score: <strong>{score:,} / {max_score:,}</strong>
                <span class="muted">({pct}%)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )


# -----------------------------
# Game state helpers
# -----------------------------
def start_new_game(force=False):
    game_key = build_game_key(
        st.session_state.mode,
        st.session_state.selected_date,
        st.session_state.use_quality_filter
    )

    if force or st.session_state.get("game_key") != game_key:
        stats = get_filtered_stats(st.session_state.use_quality_filter)

        st.session_state.rounds = pick_rounds(
            stats,
            st.session_state.mode,
            st.session_state.selected_date,
        )
        st.session_state.round_index = 0
        st.session_state.total_score = 0
        st.session_state.revealed = False
        st.session_state.last_guess = None
        st.session_state.last_score = 0
        st.session_state.game_finished = False
        st.session_state.history = []
        st.session_state.game_key = game_key
        st.session_state.leaderboard_submitted = False


def reset_practice_mode():
    st.session_state.practice_run_id = st.session_state.get("practice_run_id", 1) + 1
    start_new_game(force=True)


def go_to_next_round():
    st.session_state.round_index += 1
    st.session_state.revealed = False
    st.session_state.last_guess = None
    st.session_state.last_score = 0
    request_scroll_to_top()

    if st.session_state.round_index >= len(st.session_state.rounds):
        st.session_state.game_finished = True


def submit_guess(stat, guess):
    actual = stat["answer"]
    round_score = calculate_score(guess, actual)

    st.session_state.last_guess = int(guess)
    st.session_state.last_score = round_score
    st.session_state.total_score += round_score
    st.session_state.revealed = True

    st.session_state.history.append(
        {
            "question": display_question(stat),
            "guess": int(guess),
            "actual": int(actual),
            "score": int(round_score),
            "category": stat.get("category", "General"),
            "difficulty": infer_difficulty(stat)
        }
    )


# -----------------------------
# State init
# -----------------------------
if "mode" not in st.session_state:
    st.session_state.mode = "Daily Challenge"

if "selected_date" not in st.session_state:
    st.session_state.selected_date = dt.date.today()

if "practice_run_id" not in st.session_state:
    st.session_state.practice_run_id = 1

if "game_key" not in st.session_state:
    st.session_state.game_key = None

if "history" not in st.session_state:
    st.session_state.history = []

if "use_quality_filter" not in st.session_state:
    st.session_state.use_quality_filter = True

if "player_name" not in st.session_state:
    st.session_state.player_name = ""

if "leaderboard_notice" not in st.session_state:
    st.session_state.leaderboard_notice = None

if "leaderboard_submitted" not in st.session_state:
    st.session_state.leaderboard_submitted = False

if "scroll_to_top" not in st.session_state:
    st.session_state.scroll_to_top = False

# -----------------------------
# Sidebar
# -----------------------------
with st.sidebar:
    st.markdown("## Game mode")

    chosen_mode = st.radio(
        "Choose mode",
        ["Daily Challenge", "Practice Mode"],
        index=0 if st.session_state.mode == "Daily Challenge" else 1,
    )

    if chosen_mode != st.session_state.mode:
        st.session_state.mode = chosen_mode

        if chosen_mode == "Practice Mode":
            reset_practice_mode()
        else:
            start_new_game(force=True)

        st.rerun()

    if st.session_state.mode == "Daily Challenge":
        chosen_date = st.date_input(
            "Challenge date",
            value=st.session_state.selected_date,
        )

        if chosen_date != st.session_state.selected_date:
            st.session_state.selected_date = chosen_date
            start_new_game(force=True)
            st.rerun()

        st.caption("Same date = same 5 stats, so scores are comparable.")
    else:
        st.caption("Practice Mode reshuffles the stat set.")

        if st.button("🔀 New practice run", use_container_width=True):
            reset_practice_mode()
            st.rerun()

    st.divider()

    use_filter = st.checkbox(
        "Use launch-quality filter",
        value=st.session_state.use_quality_filter,
        help="Hides a few niche or non-MVP questions for a cleaner first launch."
    )

    if use_filter != st.session_state.use_quality_filter:
        st.session_state.use_quality_filter = use_filter
        start_new_game(force=True)
        st.rerun()

    all_stats_count = len(load_stats())
    filtered_count = len(get_filtered_stats(st.session_state.use_quality_filter))

    st.caption(f"Stats available: {filtered_count} of {all_stats_count}")

    st.divider()

    if st.session_state.mode == "Daily Challenge":
        st.markdown("### 🏆 Today")

        if google_leaderboard_configured():
            try:
                sidebar_entries = get_daily_leaderboard(limit=5)

                if not sidebar_entries:
                    st.caption("No leaderboard scores yet.")
                else:
                    for idx, entry in enumerate(sidebar_entries, start=1):
                        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
                        st.caption(f"{medal} {entry.get('player_name', 'Player')} — {safe_int(entry.get('score')):,}")

            except Exception:
                st.caption("Leaderboard temporarily unavailable.")
        else:
            st.caption("Leaderboard not configured.")

    if st.button("♻️ Restart current game", use_container_width=True):
        start_new_game(force=True)
        st.rerun()


# Load game
start_new_game()


# -----------------------------
# Header
# -----------------------------
logo_b64 = image_to_base64(ONEPOLL_LOGO)

if logo_b64:
    st.markdown(
        f"""
        <div class="hero compact-hero">
            <img src="data:image/png;base64,{logo_b64}" class="onepoll-logo">
            <div>
                <h1>📊 StatGuessr</h1>
                <p>Powered by OnePoll-style survey stats</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="hero compact-hero">
            <div>
                <h1>📊 StatGuessr</h1>
                <p>Powered by OnePoll-style survey stats</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

if st.session_state.mode == "Daily Challenge":
    banner_text = f"Daily Challenge • {st.session_state.selected_date.strftime('%A %d %B %Y')}"
    banner_sub = "Everyone playing this date gets the same stat set."
else:
    banner_text = "Practice Mode"
    banner_sub = "Keep playing with reshuffled stats."

st.markdown(
    f"""
    <div class="mode-banner">
        <div class="mode-title">{banner_text}</div>
        <div class="muted">{banner_sub}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="how-to-play">
        <strong>How to play:</strong> Guess the percentage. The closer your guess is to the real survey result, the more points you score.
    </div>
    """,
    unsafe_allow_html=True,
)


# -----------------------------
# Main app
# -----------------------------
if len(st.session_state.rounds) == 0:
    st.error("No valid stats found. Check your stats.json file or turn off the launch-quality filter.")

elif st.session_state.game_finished:
    max_score = len(st.session_state.rounds) * 5000
    verdict, subtext = final_verdict(st.session_state.total_score, max_score)
    share_text = build_share_text()

    st.progress(100, text="Game complete")
    st.markdown("## Final Score")

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Your total", f"{st.session_state.total_score:,}", border=True)
    with c2:
        st.metric("Max possible", f"{max_score:,}", border=True)
    with c3:
        pct = round((st.session_state.total_score / max_score) * 100) if max_score else 0
        st.metric("Accuracy vibe", f"{pct}%", border=True)

    st.markdown(
        f"""
        <div class="result-card">
            <div style="font-weight: 750; font-size: 1.08rem; margin-bottom: 0.2rem;">{verdict}</div>
            <div class="muted">{subtext}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.total_score >= 20000:
        st.balloons()

    # -----------------------------
    # Leaderboard block - moved high up so it is easy to find
    # -----------------------------
    if st.session_state.mode == "Daily Challenge":
        st.markdown("## 🏆 Daily leaderboard")

        if st.session_state.leaderboard_notice:
            st.success(st.session_state.leaderboard_notice)
            st.session_state.leaderboard_notice = None

        if not google_leaderboard_configured():
            st.warning(
                "Leaderboard is not configured yet. Check your `.streamlit/secrets.toml`, "
                "Google Sheet ID, service account JSON, and that the sheet is shared with the service account email."
            )
        else:
            with st.form("leaderboard_submit_form"):
                player_name = st.text_input(
                    "Display name",
                    value=st.session_state.player_name,
                    placeholder="e.g. Louis",
                    max_chars=24
                )

                submit_score = st.form_submit_button(
                    "Submit score",
                    type="primary",
                    use_container_width=True,
                    disabled=st.session_state.leaderboard_submitted
                )

            if submit_score:
                st.session_state.player_name = player_name

                success, message = add_leaderboard_entry(
                    player_name=player_name,
                    score=st.session_state.total_score,
                    max_score=max_score
                )

                if success:
                    st.session_state.leaderboard_submitted = True
                    st.session_state.leaderboard_notice = message
                    st.rerun()
                else:
                    st.warning(message)

        render_leaderboard(limit=10)

    st.markdown("### Round recap")
    for i, row in enumerate(st.session_state.history, start=1):
        diff = row["guess"] - row["actual"]
        diff_text = "Exact" if diff == 0 else f"{abs(diff)} points {'too high' if diff > 0 else 'too low'}"

        st.markdown(
            f"""
            <div class="result-card">
                <strong>Round {i} — {row['category']} • {row['difficulty']}</strong><br>
                <span class="muted">{row['question']}</span><br><br>
                Your guess: <strong>{row['guess']}%</strong><br>
                Actual: <strong>{row['actual']}%</strong><br>
                Difference: <strong>{diff_text}</strong><br>
                Score: <strong>{row['score']:,}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("### Share text")
    st.markdown(
        f'<div class="share-box">{share_text}</div>',
        unsafe_allow_html=True,
    )

    st.download_button(
        "⬇️ Download share text",
        data=share_text,
        file_name="statguessr_share_text.txt",
        mime="text/plain",
        use_container_width=True,
    )

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔁 Play again", type="primary", use_container_width=True):
            if st.session_state.mode == "Practice Mode":
                reset_practice_mode()
            else:
                start_new_game(force=True)
            st.rerun()

    with col_b:
        if st.button("📊 Back to round 1", use_container_width=True):
            start_new_game(force=True)
            st.rerun()

else:
    current_round = st.session_state.round_index + 1
    total_rounds = len(st.session_state.rounds)
    stat = st.session_state.rounds[st.session_state.round_index]

    question = display_question(stat)
    category = stat.get("category", "General")
    difficulty = infer_difficulty(stat)
    difficulty_class = difficulty_pill_class(difficulty)

    progress_pct = int((current_round - 1) / total_rounds * 100)
    st.progress(progress_pct, text=f"Round {current_round} of {total_rounds}")

    st.markdown("### Today's stat")

    st.markdown(
        f"""
        <div class="panel">
            <div class="question-text">
                {question}
            </div>
            <span class="pill">📂 {category}</span>
            <span class="{difficulty_class}">🔥 {difficulty}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not st.session_state.revealed:
        guess = st.slider(
            "Your guess",
            min_value=0,
            max_value=100,
            value=50,
            step=1,
            label_visibility="collapsed"
        )

        st.markdown(
            f"""
            <div class="guess-card">
                <div class="muted" style="text-align:center;">Your guess</div>
                <div class="guess-display">{guess}%</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button("Submit guess", type="primary", use_container_width=True):
            submit_guess(stat, guess)
            st.rerun()

    else:
        actual = stat["answer"]
        guess = st.session_state.last_guess
        diff = guess - actual
        label, sublabel = feedback_band(st.session_state.last_score)

        st.markdown("### Result")

        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("Your guess", f"{guess}%", border=True)
        with m2:
            st.metric("Actual answer", f"{actual}%", border=True)
        with m3:
            st.metric("Round score", f"{st.session_state.last_score:,}", border=True)

        delta_label = (
            f"{abs(diff)} points too high"
            if diff > 0
            else f"{abs(diff)} points too low"
            if diff < 0
            else "Exact guess"
        )
        delta_color = "inverse" if diff > 0 else "normal" if diff < 0 else "off"

        r1, r2 = st.columns([1.2, 1])
        with r1:
            st.metric(
                "Difference",
                f"{abs(diff)} points" if diff != 0 else "0 points",
                delta=delta_label,
                delta_color=delta_color,
                border=True,
            )
        with r2:
            st.metric(
                "Running total",
                f"{st.session_state.total_score:,}",
                border=True,
            )

        if diff == 0:
            st.balloons()

        st.markdown(
            f"""
            <div class="result-card">
                <div style="font-weight: 750; font-size: 1.08rem; margin-bottom: 0.25rem;">{label}</div>
                <div class="muted">{sublabel}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div class="result-card">
                <div style="font-weight: 750; font-size: 1.05rem; margin-bottom: 0.25rem;">💡 Did you know?</div>
                <div>{did_you_know_text(stat)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if current_round < total_rounds:
            if st.button("Next round ➜", type="primary", use_container_width=True):
                go_to_next_round()
                st.rerun()
        else:
            if st.button("See final score ➜", type="primary", use_container_width=True):
                go_to_next_round()
                st.rerun()


st.divider()

with st.expander("How scoring works"):
    st.write(
        """
- Exact guess = **5000 points**
- Every percentage point away costs you **100 points**
- Daily Challenge gives everyone the same 5 stats for that chosen date
- Daily Challenge scores can be submitted to the leaderboard
- Practice Mode reshuffles the stat pool but does not submit leaderboard scores
- The launch-quality filter hides a few niche questions for a cleaner first version
"""
    )
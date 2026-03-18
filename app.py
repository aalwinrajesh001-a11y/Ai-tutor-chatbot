"""
LearnBot - AI-Powered Personalized Learning Chatbot
Main Flask application file
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3
import hashlib
import json
import os
import re
from datetime import date, datetime
import google.generativeai as genai

# ─────────────────────────────────────────────
# App Setup
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "learnbot_secret_2024"  # Used to encrypt session cookies

# Configure Gemini AI
GEMINI_API_KEY = "AIzaSyDYjv794dcJMu66XqB1qVSaBDbM3caGBWk"
genai.configure(api_key=GEMINI_API_KEY)

# ─────────────────────────────────────────────
# Database Setup
# ─────────────────────────────────────────────
DATABASE = "learnbot.db"

def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row  # Allows dict-like access to rows
    return conn

def init_db():
    """Create all database tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            subject TEXT DEFAULT 'Physics',
            learning_style TEXT DEFAULT 'detailed',
            level TEXT DEFAULT 'beginner',
            streak INTEGER DEFAULT 0,
            last_login TEXT DEFAULT '',
            created_at TEXT DEFAULT ''
        )
    """)

    # Chat history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Progress / completed topics table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            completed_at TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Quiz scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            topic TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            taken_at TEXT DEFAULT '',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────
def hash_password(password):
    """Hash password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def get_user(user_id):
    """Fetch a user by ID."""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user

def update_streak(user_id):
    """Update daily login streak for a user."""
    conn = get_db()
    user = conn.execute("SELECT last_login, streak FROM users WHERE id = ?", (user_id,)).fetchone()
    today = str(date.today())

    if user["last_login"] == today:
        # Already logged in today, no change
        conn.close()
        return

    yesterday = str(date.fromordinal(date.today().toordinal() - 1))
    if user["last_login"] == yesterday:
        new_streak = user["streak"] + 1  # Consecutive day
    else:
        new_streak = 1  # Streak reset

    conn.execute(
        "UPDATE users SET streak = ?, last_login = ? WHERE id = ?",
        (new_streak, today, user_id)
    )
    conn.commit()
    conn.close()

def build_system_prompt(user):
    """Build a personalized system prompt based on user preferences."""
    style_instructions = {
        "visual": "Use diagrams described in text, bullet points, and structured layouts. Use analogies with visual comparisons.",
        "detailed": "Give thorough, step-by-step explanations with full context and background information.",
        "short": "Be concise. Give brief, clear answers. Use minimal words without sacrificing accuracy.",
        "examples": "Always lead with practical real-world examples before explaining theory."
    }

    level_instructions = {
        "beginner": "Use very simple language. Avoid jargon. Explain all terms. Use everyday comparisons.",
        "intermediate": "Assume basic knowledge. Use some technical terms with brief explanations."
    }

    return f"""You are LearnBot, an expert AI tutor specializing in {user['subject']}.

Teaching Style: {style_instructions.get(user['learning_style'], 'Be clear and helpful.')}
Student Level: {level_instructions.get(user['level'], 'Adapt to the student.')}

Always:
- Stay focused on {user['subject']} topics
- Encourage the student
- End responses with a follow-up question or suggestion to keep learning
- Format responses with clear structure using markdown-like formatting

If asked about other subjects, gently redirect to {user['subject']}."""

# ─────────────────────────────────────────────
# Hardcoded Quiz Questions
# ─────────────────────────────────────────────
QUIZ_QUESTIONS = {
    "Physics": {
        "Motion": [
            {"q": "What is the SI unit of velocity?", "options": ["m/s", "m/s²", "kg", "N"], "answer": 0},
            {"q": "Which law states F = ma?", "options": ["Newton's 1st", "Newton's 2nd", "Newton's 3rd", "Hooke's"], "answer": 1},
            {"q": "What is acceleration due to gravity on Earth?", "options": ["9.8 m/s²", "8.9 m/s²", "10.8 m/s²", "6.7 m/s²"], "answer": 0},
            {"q": "A body at rest has which type of inertia?", "options": ["Inertia of motion", "Inertia of rest", "Inertia of direction", "No inertia"], "answer": 1},
            {"q": "Distance is a __ quantity.", "options": ["vector", "scalar", "tensor", "none"], "answer": 1},
        ],
        "Waves": [
            {"q": "Speed of light in vacuum?", "options": ["3×10⁸ m/s", "3×10⁶ m/s", "3×10¹⁰ m/s", "3×10⁴ m/s"], "answer": 0},
            {"q": "Sound is a __ wave.", "options": ["transverse", "longitudinal", "electromagnetic", "none"], "answer": 1},
            {"q": "Frequency unit is?", "options": ["Hertz", "Newton", "Joule", "Pascal"], "answer": 0},
            {"q": "Wavelength × Frequency = ?", "options": ["Amplitude", "Speed", "Period", "Energy"], "answer": 1},
            {"q": "Echoes are caused by?", "options": ["Refraction", "Reflection", "Diffraction", "Absorption"], "answer": 1},
        ]
    },
    "Chemistry": {
        "Atoms": [
            {"q": "Atomic number is number of?", "options": ["Neutrons", "Protons", "Electrons", "Nucleons"], "answer": 1},
            {"q": "Who proposed the nuclear model?", "options": ["Bohr", "Thomson", "Rutherford", "Dalton"], "answer": 2},
            {"q": "Valence electrons are in?", "options": ["Inner shell", "Nucleus", "Outermost shell", "All shells"], "answer": 2},
            {"q": "Isotopes have same?", "options": ["Mass number", "Neutrons", "Protons", "Nucleons"], "answer": 2},
            {"q": "Chemical symbol of Gold?", "options": ["Go", "Gd", "Au", "Ag"], "answer": 2},
        ],
        "Reactions": [
            {"q": "Acid + Base → ?", "options": ["Salt + Water", "Gas + Water", "Oxide + Water", "None"], "answer": 0},
            {"q": "pH of pure water?", "options": ["0", "7", "14", "5"], "answer": 1},
            {"q": "Rusting is a __ reaction.", "options": ["Decomposition", "Oxidation", "Reduction", "Neutralization"], "answer": 1},
            {"q": "Catalyst affects?", "options": ["Products", "Reactants", "Reaction rate", "Temperature"], "answer": 2},
            {"q": "Combustion requires?", "options": ["CO₂", "N₂", "O₂", "H₂"], "answer": 2},
        ]
    },
    "Maths": {
        "Algebra": [
            {"q": "If x + 5 = 12, then x = ?", "options": ["5", "7", "8", "17"], "answer": 1},
            {"q": "Quadratic formula solves?", "options": ["Linear eq", "Quadratic eq", "Cubic eq", "None"], "answer": 1},
            {"q": "Discriminant b²-4ac > 0 means?", "options": ["No real roots", "Two equal roots", "Two distinct roots", "Complex roots"], "answer": 2},
            {"q": "Slope formula is?", "options": ["(y2+y1)/(x2+x1)", "(y2-y1)/(x2-x1)", "(x2-x1)/(y2-y1)", "None"], "answer": 1},
            {"q": "(a+b)² = ?", "options": ["a²+b²", "a²+2ab+b²", "a²-2ab+b²", "2a+2b"], "answer": 1},
        ],
        "Geometry": [
            {"q": "Sum of angles in a triangle?", "options": ["90°", "180°", "270°", "360°"], "answer": 1},
            {"q": "Area of circle with radius r?", "options": ["2πr", "πr²", "πd", "4πr²"], "answer": 1},
            {"q": "Pythagoras: a²+b² = ?", "options": ["c", "c²", "2c", "c/2"], "answer": 1},
            {"q": "Perimeter of square with side s?", "options": ["s²", "2s", "4s", "8s"], "answer": 2},
            {"q": "Parallel lines never?", "options": ["Run side by side", "Have same slope", "Intersect", "Exist"], "answer": 2},
        ]
    }
}

# ─────────────────────────────────────────────
# Routes - Authentication
# ─────────────────────────────────────────────
@app.route("/")
def index():
    """Home page - redirect based on login status."""
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """User registration."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            return render_template("register.html", error="All fields are required.")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password, created_at) VALUES (?, ?, ?, ?)",
                (username, email, hash_password(password), str(datetime.now()))
            )
            conn.commit()
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            return render_template("register.html", error="Username or email already exists.")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """User login."""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, hash_password(password))
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            update_streak(user["id"])  # Update daily streak
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid username or password.")

    return render_template("login.html")

@app.route("/logout")
def logout():
    """Logout and clear session."""
    session.clear()
    return redirect(url_for("index"))

# ─────────────────────────────────────────────
# Routes - Dashboard
# ─────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    """Main dashboard showing progress and preferences."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user(session["user_id"])
    conn = get_db()

    # Get completed topics count
    completed = conn.execute(
        "SELECT COUNT(*) as cnt FROM progress WHERE user_id = ?",
        (user["id"],)
    ).fetchone()["cnt"]

    # Get quiz scores
    scores = conn.execute(
        "SELECT * FROM quiz_scores WHERE user_id = ? ORDER BY taken_at DESC LIMIT 5",
        (user["id"],)
    ).fetchall()

    # Get recent topics
    topics = conn.execute(
        "SELECT DISTINCT topic FROM progress WHERE user_id = ? ORDER BY completed_at DESC LIMIT 5",
        (user["id"],)
    ).fetchall()

    conn.close()

    # Calculate progress percentage (out of ~10 sample topics)
    progress_pct = min(int((completed / 10) * 100), 100)

    return render_template(
        "dashboard.html",
        user=user,
        completed=completed,
        scores=scores,
        topics=topics,
        progress_pct=progress_pct,
        quiz_topics=list(QUIZ_QUESTIONS.get(user["subject"], {}).keys())
    )

@app.route("/update_preferences", methods=["POST"])
def update_preferences():
    """Update user learning preferences."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    subject = request.form.get("subject")
    style = request.form.get("learning_style")
    level = request.form.get("level")

    conn = get_db()
    conn.execute(
        "UPDATE users SET subject = ?, learning_style = ?, level = ? WHERE id = ?",
        (subject, style, level, session["user_id"])
    )
    conn.commit()
    conn.close()

    return redirect(url_for("dashboard"))

# ─────────────────────────────────────────────
# Routes - Chat
# ─────────────────────────────────────────────
@app.route("/chat")
def chat():
    """Chat interface page."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user(session["user_id"])
    conn = get_db()
    history = conn.execute(
        "SELECT role, message FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT 20",
        (user["id"],)
    ).fetchall()
    conn.close()

    return render_template("chat.html", user=user, history=list(reversed(history)))

@app.route("/api/chat", methods=["POST"])
def api_chat():
    """API endpoint for chat messages."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    user = get_user(session["user_id"])
    conn = get_db()

    # Save user message to DB
    conn.execute(
        "INSERT INTO chat_history (user_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (user["id"], "user", user_message, str(datetime.now()))
    )

    # Build conversation history for Gemini
    history_rows = conn.execute(
        "SELECT role, message FROM chat_history WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (user["id"],)
    ).fetchall()
    history_rows = list(reversed(history_rows))

    try:
        # Use Gemini API
        model = genai.GenerativeModel("gemini-1.5-flash")
        system_prompt = build_system_prompt(user)

        # Build message history for Gemini
        gemini_history = []
        for row in history_rows[:-1]:  # All except last (current user msg)
            role = "user" if row["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [row["message"]]})

        chat_session = model.start_chat(history=gemini_history)
        full_prompt = f"{system_prompt}\n\nStudent: {user_message}"
        response = chat_session.send_message(full_prompt)
        bot_reply = response.text

        # Auto-detect topic for progress tracking
        topic_keywords = {
            "Physics": {"motion": "Motion", "wave": "Waves", "force": "Motion", "energy": "Energy", "light": "Optics"},
            "Chemistry": {"atom": "Atoms", "react": "Reactions", "acid": "Reactions", "bond": "Bonding", "element": "Atoms"},
            "Maths": {"algebra": "Algebra", "equation": "Algebra", "geometry": "Geometry", "triangle": "Geometry", "calculus": "Calculus"}
        }
        msg_lower = user_message.lower()
        subject_topics = topic_keywords.get(user["subject"], {})
        for keyword, topic in subject_topics.items():
            if keyword in msg_lower:
                # Mark topic as visited
                existing = conn.execute(
                    "SELECT id FROM progress WHERE user_id = ? AND topic = ?",
                    (user["id"], topic)
                ).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO progress (user_id, subject, topic, completed_at) VALUES (?, ?, ?, ?)",
                        (user["id"], user["subject"], topic, str(datetime.now()))
                    )
                break

    except Exception as e:
        bot_reply = f"⚠️ AI service error: {str(e)}\n\nPlease check your API key or try again later."

    # Save bot response
    conn.execute(
        "INSERT INTO chat_history (user_id, role, message, timestamp) VALUES (?, ?, ?, ?)",
        (user["id"], "bot", bot_reply, str(datetime.now()))
    )
    conn.commit()
    conn.close()

    return jsonify({"reply": bot_reply})

@app.route("/api/clear_chat", methods=["POST"])
def clear_chat():
    """Clear chat history for the current user."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    conn = get_db()
    conn.execute("DELETE FROM chat_history WHERE user_id = ?", (session["user_id"],))
    conn.commit()
    conn.close()
    return jsonify({"status": "cleared"})

# ─────────────────────────────────────────────
# Routes - Quiz
# ─────────────────────────────────────────────
@app.route("/quiz/<topic>")
def quiz(topic):
    """Quiz page for a given topic."""
    if "user_id" not in session:
        return redirect(url_for("login"))

    user = get_user(session["user_id"])
    subject = user["subject"]
    questions = QUIZ_QUESTIONS.get(subject, {}).get(topic, [])

    if not questions:
        return redirect(url_for("dashboard"))

    return render_template("quiz.html", user=user, topic=topic, questions=questions)

@app.route("/api/submit_quiz", methods=["POST"])
def submit_quiz():
    """Submit quiz answers and calculate score."""
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.get_json()
    topic = data.get("topic")
    answers = data.get("answers", [])

    user = get_user(session["user_id"])
    subject = user["subject"]
    questions = QUIZ_QUESTIONS.get(subject, {}).get(topic, [])

    if not questions:
        return jsonify({"error": "Topic not found"}), 404

    # Calculate score
    score = 0
    results = []
    for i, q in enumerate(questions):
        user_ans = answers[i] if i < len(answers) else -1
        correct = q["answer"]
        is_correct = (user_ans == correct)
        if is_correct:
            score += 1
        results.append({
            "question": q["q"],
            "options": q["options"],
            "correct": correct,
            "user_answer": user_ans,
            "is_correct": is_correct
        })

    # Save score to DB
    conn = get_db()
    conn.execute(
        "INSERT INTO quiz_scores (user_id, subject, topic, score, total, taken_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user["id"], subject, topic, score, len(questions), str(datetime.now()))
    )
    # Mark topic as completed in progress
    existing = conn.execute(
        "SELECT id FROM progress WHERE user_id = ? AND topic = ?",
        (user["id"], topic)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO progress (user_id, subject, topic, completed_at) VALUES (?, ?, ?, ?)",
            (user["id"], subject, topic, str(datetime.now()))
        )
    conn.commit()
    conn.close()

    return jsonify({"score": score, "total": len(questions), "results": results})

# ─────────────────────────────────────────────
# Run App
# ─────────────────────────────────────────────
# Add enumerate filter to Jinja2 (used in quiz.html template)
app.jinja_env.globals.update(enumerate=enumerate)

if __name__ == "__main__":
    init_db()  # Create tables if they don't exist
    print("🚀 LearnBot is running at http://localhost:5000")
    app.run(debug=True, port=5000)

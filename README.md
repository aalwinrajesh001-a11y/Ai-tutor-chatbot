# 🤖 LearnBot — AI Personalized Learning Chatbot

A fully featured AI-powered learning web app built with Flask + Gemini AI.

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the app
```bash
python app.py
```

### 3. Open in browser
```
http://localhost:5000
```

---

## 📁 Project Structure

```
learnbot/
├── app.py                  # Flask backend (all routes, AI, DB logic)
├── requirements.txt        # Python dependencies
├── learnbot.db             # SQLite database (auto-created on first run)
├── templates/
│   ├── index.html          # Landing page
│   ├── login.html          # Login page
│   ├── register.html       # Registration page
│   ├── dashboard.html      # Main dashboard
│   ├── chat.html           # AI chat interface
│   └── quiz.html           # Quiz page
└── static/
    ├── style.css           # All styles (green-black theme)
    └── script.js           # Chat, markdown, UI interactions
```

---

## ✨ Features

- **Auth** — Register / Login / Logout with password hashing
- **Preferences** — Choose Subject, Learning Style, Level
- **AI Chat** — Powered by Gemini 1.5 Flash, adapts to your preferences
- **Quizzes** — 5 MCQ quizzes per topic with instant scoring
- **Progress** — Track completed topics, quiz scores, progress bar
- **Streak** — Daily login streak counter
- **Green × Black** — Sleek dark theme throughout

---

## 🎨 Design Theme

- Primary: `#00e676` (neon green)  
- Background: `#050a06` (near black)  
- Font: Syne (headings) + Space Grotesk (body)

---

## 🔑 AI Configuration

The Gemini API key is set directly in `app.py`:
```python
GEMINI_API_KEY = "AIzaSyDYjv794dcJMu66XqB1qVSaBDbM3caGBWk"
```

---

## 📚 Available Subjects & Quiz Topics

| Subject    | Topics            |
|------------|-------------------|
| Physics    | Motion, Waves     |
| Chemistry  | Atoms, Reactions  |
| Maths      | Algebra, Geometry |

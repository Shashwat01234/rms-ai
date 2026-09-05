# RMS-AI — Residential & Academic Management System

<div align="center">

![RMS AI Banner](https://img.shields.io/badge/RMS_AI-v4.0-1f6feb?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyek0xMiAxNmMtMi4yMSAwLTQtMS43OS00LTRzMS43OS00IDQtNCA0IDEuNzkgNCA0LTEuNzkgNC00IDR6Ii8+PC9zdmc+)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.0_Flash-AI_Powered-8E44AD?style=for-the-badge&logo=google&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite_/_PostgreSQL-Dual_DB-003B57?style=for-the-badge&logo=sqlite&logoColor=white)

**An AI-powered campus management platform that handles hostel maintenance complaints, academic queries, and certificate verification — all in one system.**

[Live Demo →](https://rms-ai-yo3.onrender.com) &nbsp;·&nbsp; [Report Bug](https://github.com/Shashwat01234/rms-ai/issues) &nbsp;·&nbsp; [Feature Request](https://github.com/Shashwat01234/rms-ai/issues)

</div>

---

## What It Does

RMS-AI solves three distinct problems faced by hostel students at LPU (and similar universities):

| Problem | RMS-AI Solution |
|---------|----------------|
| Student reports "my fan not wrking" — who fixes it? | Multi-stage NLP engine understands the complaint, detects the appliance, and auto-assigns the right technician at the right time |
| Student needs to know how to apply for re-evaluation | Gemini 2.0 Flash gives step-by-step LPU-specific guidance with the correct department contact |
| Admin needs to verify if a submitted certificate is genuine | Gemini Vision analyzes the document for seals, signatures, watermarks, and tampering |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Frontend (HTML/CSS/JS)             │
│  Homepage → Login → Complaint → Academic → Certif.   │
│                 Admin Dashboard                       │
└────────────────────┬────────────────────────────────-┘
                     │ HTTP (Flask REST API)
┌────────────────────▼────────────────────────────────-┐
│                  server.py (Flask)                    │
│                                                       │
│  /submit_request → NLP Pipeline → DB                  │
│  /academic/ask   → Academic AI  → DB                  │
│  /certificate/verify → Vision AI → DB                 │
│  /api/nlp/analyze (real-time preview endpoint)        │
└──────┬──────────────┬──────────────┬─────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────────────┐
│ nlp_engine  │ │ academic   │ │ certificate        │
│ .py         │ │ _ai.py     │ │ _verifier.py       │
│             │ │            │ │                    │
│ • normalize │ │ • Gemini   │ │ • Gemini Vision    │
│ • intent    │ │   2.0 Flash│ │ • PDF→PNG convert  │
│ • entities  │ │ • caching  │ │ • 8-point checks   │
│ • role      │ │ • memory   │ │ • verdict + flags  │
│ • duplicate │ │ • fallback │ │                    │
└─────────────┘ └────────────┘ └────────────────────┘
       │
┌──────▼───────────────────────────┐
│  database.py (SQLite / PostgreSQL) │
│  Auto-switches based on env var    │
└────────────────────────────────────┘
```

---

## NLP Pipeline (Core Feature)

The `ai/nlp_engine.py` module is the heart of the complaint routing system. It runs a 5-stage pipeline on every complaint:

```
Raw Input: "my ac not cooling in room 302, free at 6pm please fix urgently"
     ↓
1. normalize_text()   →  spell correction, slang fix ("wrking"→"working", "urgnt"→"urgent")
     ↓
2. detect_intent()    →  maintenance (0.88 confidence)  [vs inquiry vs emergency]
     ↓
3. extract_entities() →  room=302, time=18h, urgency=high, objects=[air_conditioner]
     ↓
4. detect_role()      →  electrician (0.86 confidence)  [9 possible roles]
     ↓
5. build_human_response() →  "⚡ Urgent request received. Your complaint has been noted
                              and Ravi (Electrician) will visit your room to fix the
                              air conditioner at approximately 18:00 hrs..."
```

**10/10 test cases correctly classified** — including the tricky ones:
- `"how do i fix my fan"` → maintenance/electrician *(not academic AI)*
- `"how to check my cgpa on ums"` → Academic AI *(not IT support)*

---

## Features

### 🛠️ Hostel Complaint System
- **Smart NLP routing** — 9 technician roles (electrician, plumber, carpenter, painter, housekeeping, IT support, mess, laundry, security)
- **Live AI preview** — shows detected intent, role, room, time as you type
- **Time-aware scheduling** — matches student's free time with technician availability
- **Emergency detection** — flags fire/flood/electric shock with evacuation instructions
- **Duplicate detection** — Jaccard + sequence similarity prevents re-submission
- **Urgency classification** — low / medium / high / emergency

### 🎓 Academic AI Advisor (Aria)
- Powered by **Gemini 2.0 Flash** with an empathetic "Aria" persona
- Covers 11 LPU categories: Fee & Finance, Examinations, Results, UMS Portal, Documents, Admissions, Scholarships, Placement, Library, Hostel, Departments
- **Response caching** — same question answered instantly without API call
- **Conversation memory** — 4-turn history per student for follow-up questions
- **Rich fallback KB** — step-by-step guides when API unavailable

### 📜 Certificate Verifier
- **Gemini Vision** analyzes uploaded JPG/PNG/PDF certificates
- Checks: official seal, signature, watermark, letterhead, unique ID, typography, print quality, tampering
- Returns verdict: GENUINE / LIKELY GENUINE / SUSPICIOUS / REQUIRES MANUAL REVIEW
- Admin override capability for edge cases

### ⚙️ Admin Dashboard
- Real-time stats (total, pending, resolved, technician load)
- 4-tab interface: Hostel Requests, Academic Queries, Certificate Checks, Technicians
- Search & filter by status, student, technician
- Admin notes on academic queries

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, Flask 3.0, Flask-CORS |
| AI / NLP | Google Gemini 2.0 Flash, Custom NLP Engine, scikit-learn (TF-IDF + Logistic Regression) |
| Database | SQLite (local dev) / PostgreSQL (production) — auto-switched via `DATABASE_URL` |
| Frontend | Vanilla HTML/CSS/JS, Inter font, Glassmorphism dark theme |
| Deployment | Render (gunicorn), render.yaml config |
| PDF Processing | PyMuPDF (fitz) for PDF→image conversion |

---

## Quick Start

### Prerequisites
- Python 3.10+
- A [Google Gemini API key](https://aistudio.google.com/app/apikey) (free tier available)

### Setup

```bash
# 1. Clone
git clone https://github.com/Shashwat01234/rms-ai.git
cd rms-ai

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate    # Windows
# source venv/bin/activate  # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Train ML model
python train.py

# 6. Run
python server.py
```

Open `http://localhost:5000`

### Demo Credentials

| Role | Username | Password |
|------|----------|----------|
| Student | `12345` | `pass123` |
| Student | `12411793` | `pass234` |
| Technician | `Ravi` | `tech123` |
| Admin | *(set in env)* | *(set in env)* |

---

## Project Structure

```
rms-ai/
├── ai/
│   ├── nlp_engine.py          # Multi-stage NLP pipeline (core)
│   ├── academic_ai.py         # Gemini 2.0 academic advisor + caching
│   ├── certificate_verifier.py # Gemini Vision certificate checker
│   └── category_predictor.py  # Lightweight keyword predictor
├── frontend/
│   ├── homepage.html          # Landing page with portal cards
│   ├── login.html             # Student login
│   ├── complaint.html         # Complaint submission + live NLP preview
│   ├── academic.html          # Academic AI Q&A interface
│   ├── certificate.html       # Certificate upload & verification
│   ├── admin.html             # Admin dashboard (4 tabs)
│   ├── status.html            # Request status tracker
│   ├── history.html           # Student complaint history
│   └── style.css              # Shared dark glassmorphism design system
├── server.py                  # Flask REST API (all routes)
├── database.py                # Dual SQLite/PostgreSQL backend
├── train.py                   # ML model training script
├── queries.csv                # Training dataset (182 samples, 11 categories)
├── model.pkl                  # Trained logistic regression classifier
├── vectorizer.pkl             # TF-IDF vectorizer
├── render.yaml                # Render deployment config
└── requirements.txt
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/login` | Student authentication |
| POST | `/submit_request` | Submit complaint (NLP pipeline) |
| GET | `/get_status?id=<id>` | Track complaint status |
| GET | `/api/history/<student_id>` | Complaint history |
| POST | `/api/nlp/analyze` | **Real-time NLP preview** |
| POST | `/academic/ask` | Ask academic AI question |
| POST | `/certificate/verify` | Upload and verify certificate |
| POST | `/admin/login` | Admin authentication |
| GET | `/admin/stats` | Dashboard statistics |
| GET | `/admin/get_all_requests` | All hostel requests |
| POST | `/admin/update_status` | Update request status |

---

## Deployment

### Render (One-Click)

1. Fork this repository
2. Create a new **Web Service** on [render.com](https://render.com)
3. Connect your forked repo
4. Set environment variables on Render dashboard:
   - `GEMINI_API_KEY` — your Google AI Studio key
   - `ADMIN_PASSWORD` — choose a strong password
   - `DATABASE_URL` — auto-provided by Render PostgreSQL addon
5. Deploy — Render uses `render.yaml` automatically

> **Security Note:** All secrets must be set on the Render dashboard. The `render.yaml` in this repo intentionally does NOT hardcode any passwords.

---

## Roadmap

- [ ] SMS/email notifications when technician is assigned
- [ ] Student rating system for completed requests
- [ ] Technician mobile app (React Native)
- [ ] Multi-language support (Hindi/Punjabi)
- [ ] Analytics dashboard with charts
- [ ] Webhook integrations for hostel management systems

---

## Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
Built with ❤️ by <a href="https://github.com/Shashwat01234">Shashwat Dubey</a> · Powered by Google Gemini AI
</div>

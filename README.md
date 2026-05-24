# VERIFACT v2.0: Real-Time AI News Verification Platform

Verifact v2.0 is a production-level, **Real-Time AI-Powered News Verification & Cyber-Intelligence Platform** built with **Python**, **Flask-SocketIO**, **APScheduler**, and **Machine Learning**. 

The platform continuously and automatically ingests trending global news feeds from live APIs and international registries, parses content using advanced Natural Language Processing pipelines (Named Entity Recognition, Sentiment Subjectivity, Lexical Density), and classifies articles in real-time. Highly suspicious viral fake news articles immediately trigger server-wide browser alert broadcasts via WebSockets without page refreshes.

---

## 🚀 Advanced Features (v2.0)

* **Continuous Live Ingestion Scheduler**:
  * Integrates **NewsAPI**, **GNews**, and **GDELT Project** APIs inside an asynchronous background scanning engine.
  * Ingests, processes, and classifies trending articles every 5 minutes.
  * Features a **Dynamic Mock Stream Engine** that generates highly contextually sound, realistic simulated articles if API keys are absent, ensuring immediate out-of-the-box local interactivity.
* **WebSockets Real-Time Feed**:
  * Powered by `Flask-SocketIO` to push newly classified news articles directly to the browser live.
  * Emits glowing **Viral Fake News Alerts** with dynamic toaster popup badges when highly malicious reports are flagged (Verdict FAKE + Confidence > 78%).
* **Explainable AI Reasoning (XAI)**:
  * Generates structured, human-readable structural breakdowns explaining *why* articles are flagged (e.g., highlighting excessive exclamation counts, biased emotional syntax, matching mathematical fake news matrices, or untrusted domain histories).
* **Dual-Database Layer (SQLite, MongoDB, PostgreSQL)**:
  * Offers modular database abstraction. Out-of-the-box local deployment runs on **SQLite** with zero configuration.
  * Toggling a single parameter in your `.env` file switches the backend to run on production-grade **MongoDB** or **PostgreSQL**.
* **Source Credibility Checker**:
  * Dynamically scans article URLs and cross-references them against a database whitelist (reputable global news agencies) and blacklist (satirical, conspiracy, or known fraudulent domains).
  * Automatically applies heuristic top-level domain (TLD) scores for unknown sites (e.g., boosting `.edu`/`.gov` while warning on strange domains).
* **Deep Lexical Analytics**:
  * Extracts proper nouns and key named entities (Persons, Organizations, Places) to identify headline consistency.
  * Evaluates sentiment polarity and emotional subjectivity using NLTK VADER.
* **Visual Telemetry Dashboard**:
  * Renders beautiful live telemetry cards and interactive metrics using Chart.js, visualizing Ingestion ratios, parsed categories, and system loads.
* **Production DevOps Infrastructure**:
  * Standardized multi-stage `Dockerfile`, coordinated `docker-compose.yml`, and WebSocket-ready reverse-proxy `nginx.conf` setups.

---

## 📁 Upgraded Folder Structure

```text
project Fake New/
│
├── static/
│   ├── css/
│   │   └── style.css            # Custom premium styling, glassmorphism, dark/light themes
│   ├── js/
│   │   ├── main.js              # Predictions, upgraded chatbot, and theme toggles
│   │   └── charts.js            # Admin analytics Chart.js models
│   ├── graphs/                  # Matplotlib confusion matrices and comparative charts
│   └── data/
│       └── metrics.json         # Evaluation benchmarks from model training
│
├── templates/
│   ├── base.html                # Upgraded layout with Live Stream navigation linkages
│   ├── index.html               # Main prediction workspace (manual text & file upload)
│   ├── dashboard_realtime.html  # Premium Glassmorphic Live Ingestion Feed & visual telemetry
│   ├── login.html               # Authentication page
│   ├── signup.html              # Registration page
│   ├── dashboard.html           # User prediction history
│   ├── admin.html               # Admin control monitor panel (with blacklist/whitelist inputs)
│   ├── unauthorized.html        # Access control page
│   └── 404.html                 # Error page
│
├── models/                      # Pickled ML consensus models
│   ├── tfidf_vectorizer.pkl
│   ├── logistic_regression_model.pkl
│   ├── naive_bayes_model.pkl
│   └── passive_aggressive_model.pkl
│
├── tests/
│   └── test_platform.py         # Automated verification tests for NLP, credibility and inference
│
├── app.py                       # Main Flask & Socket.IO server entrypoint
├── database.py                  # Modular Dual-Database Router (SQLite/MongoDB/Postgres)
├── credibility.py               # Domain credibility analyzer
├── nlp_engine.py                # NER, Sentiment, Keyword, and ML consensus runner
├── news_fetcher.py              # APScheduler background news loop & live wrappers
├── requirements.txt             # Python packages
├── Dockerfile                   # DevOps multi-stage packaging script
├── docker-compose.yml           # Coordinated Docker Compose orchestrator
├── nginx.conf                   # WebSocket reverse proxy config
├── .env.example                 # Environment configuration template
└── README.md                    # Project documentation
```

---

## ⚙️ Installation & Setup (v2.0)

### 1. Clone & Enter Directory
```bash
cd "c:\Users\Amrit Ranjan\OneDrive\Desktop\project Fake New"
```

### 2. Configure Environments
Copy `.env.example` to `.env` and fill in your details:
```bash
copy .env.example .env
```
*Leave `NEWS_API_KEY` blank to trigger the highly interesting dynamic mock stream simulation core.*

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed and Initialize Database
```bash
python database.py
```

### 5. Launch the Server
```bash
python app.py
```
* The platform will start serving on **`http://127.0.0.1:5000`**
* Navigate to **`http://127.0.0.1:5000/dashboard-realtime`** to access the live command monitor desk!

---

## 🐳 Docker Deployment (DevOps)

To run the entire ecosystem (Flask-SocketIO Web app + MongoDB database) in a fully orchestrated environment:

```bash
docker-compose up --build
```
Docker Compose will download MongoDB, build your multi-stage Python image, mount volumes for data persistence, set up networks, and launch the platform on port `5000` with zero local environment setup required!

---

## 🔌 API Documentation (v2.0)

### 1. Register/Authenticate User: `POST /api/auth/login`
```json
{
  "username": "admin",
  "password": "admin123"
}
```

### 2. Fetch Live News Logs: `GET /api/live-news?limit=5`
Retrieves analyzed articles processed by the background scanning scheduler.

### 3. Retrieve Live Telemetry Metrics: `GET /api/trending`
Returns real vs. fake news statistics, category distributions, and live source ratios.

### 4. Query Verified Claims: `GET /api/fact-check?query=covid`
Queries Google Fact Check Explorer for verified claim reviews.

### 5. Scrape and Evaluate URLs: `POST /api/realtime-detection`
Accepts a URL link, scrapes contents, verifies domain credibility whitelist/blacklist ratings, calculates sentiment subjectivity, extracts keywords/entities, and outputs consensus verdicts with stylistic explanations.

---

## 👤 Default Credentials

* **System Administrator**:
  * Username: `admin`
  * Password: `admin123`
* **Default User**:
  * Username: `user`
  * Password: `user123`

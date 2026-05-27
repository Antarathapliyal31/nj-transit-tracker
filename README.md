# NJ Transit Rail Tracker 🚆

> A real-time NJ Transit train tracker with push notifications — so you never miss a train or get blindsided by delays again.

---

## 🌟 Why I Built This

I take NJ Transit almost every day — and almost every day, I'd find out about delays only after I was already at the platform. The official NJ Transit app is slow, doesn't proactively notify me, and buries critical info under marketing.

So I built my own.

**NJ Transit Rail Tracker** is a lightweight Progressive Web App that gives me:
- ⚡ Real-time train status without opening an app
- 🔔 Push notifications for delays on the trains I actually care about
- 📱 Works on any device with a browser — no App Store needed
- 🌐 Server-side push delivery even when the browser is closed

This solves a real problem in my life. It might solve yours too.

---

## ✨ Features

- 🚉 **Real-time departure boards** for any NJ Transit rail station
- 🔔 **Push notifications** for delays on tracked trains (works even when browser is closed)
- 📌 **Save favorite routes** for one-tap status checks
- 📲 **PWA-installable** — add to home screen, works offline-ish
- 🌙 **Lightweight** — sub-second load times, no bloated frameworks
- 🔐 **Privacy-first** — no tracking, no analytics, no ads

---

## 🏗️ Architecture

```
┌──────────────────┐         ┌──────────────────┐
│   Browser (PWA)  │◀───────▶│  Backend Server  │
│                  │  HTTPS  │   (Python/Flask) │
│  ┌────────────┐  │         │                  │
│  │  Service   │  │         │  ┌────────────┐  │
│  │  Worker    │  │         │  │ NJ Transit │  │
│  └─────┬──────┘  │         │  │    API     │  │
│        │         │         │  │  Polling   │  │
│        ▼         │         │  └─────┬──────┘  │
│  ┌────────────┐  │         │        │         │
│  │   Push     │  │◀────────│  ┌─────▼──────┐  │
│  │ Subscription │ │ VAPID  │  │ pywebpush  │  │
│  └────────────┘  │         │  └────────────┘  │
└──────────────────┘         └──────────────────┘
                                      │
                                      ▼
                              ┌──────────────────┐
                              │   Deployed on    │
                              │      Render      │
                              └──────────────────┘
```

**How it works:**
1. **Frontend** registers a Service Worker and subscribes the user to push notifications using a VAPID public key
2. **Backend** periodically polls the NJ Transit API for status of subscribed routes
3. When a delay is detected, **pywebpush** sends a signed push notification to the user's browser via the VAPID protocol
4. **Service Worker** receives the push event and displays the notification — even if the browser is closed

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python, Flask |
| **Frontend** | Vanilla JS, HTML5, CSS3 (no frameworks) |
| **Push Protocol** | Web Push API + VAPID |
| **Push Library** | pywebpush |
| **PWA Layer** | Service Workers, Web App Manifest |
| **Deployment** | Render (web service + background worker) |
| **Data Source** | NJ Transit Rail Departure Vision API |

**Why this stack?**
- **No React/Vue** — overkill for the UI complexity here. Vanilla JS keeps it lightweight and fast.
- **Flask over FastAPI** — simpler for this scope; FastAPI's async wasn't needed.
- **Render over Vercel** — Vercel doesn't support long-running background workers needed for push polling.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A free [Render](https://render.com) account (for deployment) or any host that supports Python
- VAPID keys (generated locally — see setup)

### Local Setup

```bash
# Clone the repo
git clone https://github.com/Antarathapliyal31/nj-transit-tracker.git
cd nj-transit-tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Generate VAPID keys (one-time)
python generate_vapid_keys.py

# Copy environment template
cp .env.example .env
# Edit .env with your VAPID keys and config
```

### Environment Variables

Create a `.env` file with:

```env
VAPID_PUBLIC_KEY=your_generated_public_key
VAPID_PRIVATE_KEY=your_generated_private_key
VAPID_CLAIM_EMAIL=mailto:your_email@example.com
NJ_TRANSIT_API_KEY=your_api_key_if_needed
DATABASE_URL=sqlite:///subscriptions.db  # or Render Postgres URL
```

### Running Locally

```bash
# Start the Flask server
python app.py

# In a separate terminal — start the background poller
python poller.py
```

Open `http://localhost:5000` in your browser.  
**Note:** Push notifications require HTTPS — they won't work on `localhost` in some browsers. Use ngrok or deploy to Render for full testing.

---

## 🧠 Key Design Decisions

### **Why Service Workers + Push API instead of polling on the client?**

Client-side polling drains battery and requires the app to be open. The Push API delivers notifications **server-to-browser** via the OS-level push service (FCM on Chrome/Android, APNs on Safari/iOS) — meaning notifications arrive even when the browser is closed. This is the same mechanism native apps use.

### **Why VAPID over Firebase Cloud Messaging directly?**

VAPID (Voluntary Application Server Identification) lets me send push notifications **without registering with any specific push service**. My server signs requests with a public/private key pair, and any browser's push service accepts them. This means:
- 🔓 No vendor lock-in to Firebase
- 🔒 Privacy-preserving — I don't have to share data with Google
- 💰 Free at any scale

### **Why pywebpush?**

`pywebpush` is the de-facto Python library for sending VAPID-signed Web Push messages. It handles the cryptographic signing, payload encryption, and HTTP delivery correctly — which is non-trivial to implement from scratch.

### **Why a separate background worker?**

Push notifications must be sent based on real-time data, not user requests. A background worker polls the NJ Transit API every N seconds, compares against the last known state, and triggers pushes when delays are detected. Render's worker service runs this 24/7 independently of the web server.

---

## 📚 What I Learned

This project taught me several things about web platform APIs and production deployment:

- **Web Push is more powerful than most devs realize** — Most teams default to native apps for notifications. Web Push gives you 90% of the capability with 0% of the App Store overhead. For utility apps like this, it's the right call.

- **Service Workers have a steep learning curve** — Lifecycle events (`install`, `activate`, `push`), scope rules, and cache strategies all matter. Skipping a step (like calling `self.skipWaiting()`) silently breaks updates.

- **VAPID keys are easy to mess up** — The same key pair must be used on the client (public) and server (private). Regenerating one without the other silently breaks all subscriptions.

- **Background polling is surprisingly nuanced** — Naive polling spams the upstream API. I had to implement caching, deduplication, and exponential backoff for retries when the NJ Transit API rate-limits.

- **iOS Safari support trails Chrome by ~2 years** — Web Push only landed on iOS in 2023, and still has quirks (must be added to home screen first). Testing across platforms is essential.

---

## 🔮 Future Improvements

- [ ] Add bus route support (currently rail-only)
- [ ] SMS fallback for users without push-capable browsers
- [ ] Train arrival predictions using historical data + ML
- [ ] Multi-station saved routes (e.g., "any train from New Brunswick to Penn Station")
- [ ] Track-specific notifications (notify only if my usual track changes)
- [ ] Dark mode toggle

---

## 📂 Project Structure

```
nj-transit-tracker/
├── app.py                       # Flask web server
├── poller.py                    # Background worker (polls NJ Transit API)
├── generate_vapid_keys.py       # One-time VAPID key generation script
├── static/
│   ├── service-worker.js        # Service Worker (push handling, caching)
│   ├── manifest.json            # PWA manifest
│   ├── app.js                   # Client-side subscription logic
│   └── styles.css
├── templates/
│   └── index.html               # Main UI
├── data/
│   └── subscriptions.db         # SQLite subscription store
├── requirements.txt
├── render.yaml                  # Render deployment config
├── .env.example
└── README.md
```

---

## 🌐 Deployment on Render

This project is deployed on Render with **two services**:

1. **Web Service** (`app.py`) — handles HTTPS requests, subscription registration, UI
2. **Background Worker** (`poller.py`) — runs 24/7, polls API, sends push notifications

`render.yaml` defines both services for one-click deploy.

```yaml
services:
  - type: web
    name: nj-transit-tracker
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app

  - type: worker
    name: nj-transit-poller
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python poller.py
```

---

## 📄 License

MIT — see [LICENSE](./LICENSE).

---

## 🙏 Acknowledgments

- Data: [NJ Transit Rail Departure Vision API](https://www.njtransit.com/developer-resources)
- Inspired by my daily commute frustrations on the Northeast Corridor Line
- Web Push standards: [MDN Web Push API docs](https://developer.mozilla.org/en-US/docs/Web/API/Push_API)

---

## 👋 Connect with Me

I'm **Antara Thapliyal**, an MS CS student at Rutgers (4.0 GPA) and incoming GenAI Engineer Intern at Otsuka Pharmaceutical. I build practical AI and web tools — things I actually use, not just demos.

- 🔗 [LinkedIn](https://www.linkedin.com/in/antara-thapliyal/)
- 🌐 [Portfolio](https://portfolio-antara.vercel.app)
- 💻 [GitHub](https://github.com/Antarathapliyal31)
- 📧 thapliyalantara31@gmail.com

If this project saved you from missing a train, please ⭐ the repo — it makes me smile.

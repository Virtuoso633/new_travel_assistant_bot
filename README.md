Here’s a comprehensive README.md for your project, covering both **local** and **Docker** usage:

---

```markdown
# Travel Assistant Bot

A conversational AI assistant for travel planning, weather information, and smart packing suggestions, built with Rasa and React.

---

## Features

- Natural language understanding for travel-related queries
- Weather information using Open-Meteo API
- Smart packing recommendations based on weather
- Complete trip planning with forms
- FAQ and fallback handling
- Modern React-based frontend

---

## Project Structure

```
new_travel_assistant_bot/
├── rasa/
│   ├── actions/              # Custom action code
│   ├── data/                 # NLU, stories, rules
│   ├── models/               # Trained Rasa models
│   ├── frontend/             # React frontend
│   ├── domain.yml            # Rasa domain
│   ├── config.yml            # Rasa config
│   ├── endpoints.yml         # Rasa endpoints
│   ├── Dockerfile.rasa       # Dockerfile for Rasa server
│   ├── Dockerfile.actions    # Dockerfile for action server
│   └── requirements.txt      # Python dependencies
├── docker-compose.yml        # Multi-service orchestration
```

---

## Running Locally (No Docker)

### 1. **Install Python & Node.js**

- Python 3.8+ (recommended: 3.8)
- Node.js 16+ and npm

### 2. **Set Up Rasa Backend**

```bash
cd rasa
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
rasa train
rasa run actions --port 5055
# In a new terminal:
rasa run --enable-api --cors "*" --port 5005
```

### 3. **Set Up Frontend**

```bash
cd rasa/frontend
npm install
npm start
```

- The frontend will be available at [http://localhost:3000](http://localhost:3000)
- The backend API will be at [http://localhost:5005](http://localhost:5005)

---

## Running with Docker

### 1. **Build Images (Optional, if not using prebuilt images)**

```bash
# From project root
docker build -f Dockerfile.rasa -t yourdockerhubusername/travel-rasa-server:latest ./rasa
docker build -f Dockerfile.actions -t yourdockerhubusername/travel-action-server:latest ./rasa
docker build -f Dockerfile.frontend -t yourdockerhubusername/travel-frontend:latest ./rasa/frontend
```

### 2. **Start All Services with Docker Compose**

```bash
docker compose up -d
```

- Rasa server: [http://localhost:5005](http://localhost:5005)
- Action server: [http://localhost:5055](http://localhost:5055)
- Frontend: [http://localhost](http://localhost)

### 3. **Stopping Services**

```bash
docker compose down
```

---

## Environment Variables

- **Frontend:**  
  Set `REACT_APP_RASA_SERVER_URL` in `rasa/frontend/.env` to point to your backend (default: `http://localhost:5005`).

- **Backend:**  
  See `.env` and `endpoints.yml` for configuration.

---

## Deployment

- Push your Docker images to Docker Hub.
- Copy your project (including `docker-compose.yml`) to your server (e.g., Digital Ocean).
- Run `docker compose up -d` on the server.
- Update `REACT_APP_RASA_SERVER_URL` in the frontend `.env` if deploying frontend separately.

---

## Troubleshooting

- **CORS errors:** Ensure Rasa is started with `--cors "*"` and frontend points to the correct backend URL.
- **Model not found:** Make sure `models/model.tar.gz` exists and is mounted/copied into the container.
- **Action server not responding:** Check logs with `docker logs action-server`.

---

## Credits

- Uses [Rasa](https://rasa.com/) and [Open-Meteo](https://open-meteo.com/) APIs

---

## License

MIT License

```

---

**You can copy this as your README.md in the project root.**  
Let me know if you want to add badges, screenshots, or further customization!

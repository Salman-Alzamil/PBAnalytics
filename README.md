# PhoneBook Analytics

A full-stack phonebook analytics application built with **FastAPI**, **PostgreSQL**, and **Vue 3**, with an integrated computer vision module for automated contact photo classification.

Import contacts and call history from CSV files, then explore communication patterns through an interactive dashboard, featuring smart duplicate detection, a scoring-based favourites algorithm, real-time call statistics, and AI-powered clothing classification.

---

## Project Structure

```
PBAnalytics/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # App entry point, middleware, error handlers
│   ├── database.py           # DB connection and session setup
│   ├── models.py             # SQLAlchemy table definitions
│   ├── schemas.py            # Pydantic validation schemas
│   ├── crud.py               # Reusable database query functions
│   ├── import_csv.py         # CLI tool to bulk-import CSV data
│   ├── requirements.txt      # Python dependencies
│   ├── model/
│   │   └── best.pt           # Trained YOLO model weights
│   ├── routes/
│   │   ├── contacts.py       # GET/POST/PUT/DELETE /contacts
│   │   ├── calls.py          # GET /calls and /calls/stats
│   │   ├── favourites.py     # GET /favourites
│   │   ├── dashboard.py      # GET /dashboard/summary
│   │   ├── import_csv.py     # POST /import/contacts and /import/calls
│   │   └── ai.py             # POST /ai/classify, GET /ai/images
│   └── utils/
│       ├── cleaner.py        # Data cleaning and normalisation logic
│       ├── favourites.py     # Favourites scoring algorithm
│       └── ai_classifier.py  # YOLO model loading and inference
└── ai/                       # Model training pipeline
│   ├── preprocess.py         # Data cleaning, augmentation, and dataset splitting
│   ├── train.py              # YOLOv8 training script
│   └── raw_images/           # Source images organised by class
│       ├── saudi_formal/
│       ├── casual/
│       └── not_human/
├── frontend/                 # Vue 3 frontend
│   └── src/
│       ├── views/            # Dashboard, Contacts, Favourites, CallHistory, ImportCSV
│       ├── api/index.js      # Central Axios API layer
│       └── router/index.js   # Vue Router configuration
└── data/
    ├── contacts_data.csv     # Sample contacts CSV
    └── calls_history.csv     # Sample call history CSV
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| PostgreSQL | 14+ |

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Salman-Alzamil/PBAnalytics.git
cd PBAnalytics
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file inside the `backend/` folder:

```
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/phonebook
```

> Never commit your `.env` file. It is already listed in `.gitignore`.

Start the API server:

```bash
uvicorn main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**
Interactive API docs (Swagger UI) at **http://localhost:8000/docs**

### 3. Import sample data

Once the backend is running, load the sample CSV files into the database:

```bash
python import_csv.py --contacts ../data/contacts_data.csv --calls ../data/calls_history.csv
```

This will clean, normalise, and bulk-insert both datasets. You will see a summary printed in the terminal.

### CSV Format Requirements

Your CSV files must use these exact column names:

**contacts CSV:**
| Column | Example |
|--------|---------|
| `id` | 1 |
| `first_name` | Ahmed |
| `last_name` | Al-Rashid |
| `phone` | +966501234567 |
| `email` | ahmed@email.com |
| `city` | Riyadh |
| `notes` | Work colleague |

**calls CSV:**
| Column | Example |
|--------|---------|
| `call_id` | C001 |
| `phone_number` | +966501234567 |
| `contact_name` | Ahmed Al-Rashid |
| `date` | 2026-04-14 |
| `time` | 09:15:00 |
| `duration_seconds` | 512 |
| `call_type` | outgoing |
| `status` | completed |

> Sample files are provided in the `data/` folder for reference.

### 4. Frontend setup

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The app will be available at **http://localhost:5173**

---

## Pages & Features

### Dashboard
- 4 stat cards: Total Contacts, Total Calls, Average Call Duration, Duplicate Count
- Top 5 favourites list with scores
- Monthly call count bar chart (Chart.js)
- Last 5 calls table

### Contacts
- Full contacts table with search by name or phone
- Sort by Name (A-Z / Z-A) or City
- Orange duplicate badge on flagged contacts
- Add, edit, and delete contacts inline
- Profile photo upload with automatic AI classification

### Favourites
- Contacts ranked by a scoring formula: `score = (call_count x 2) + total_duration_minutes`, normalised to 0-100
- Podium cards for top 3 contacts
- Three sort modes via tab switcher:
  - **Most Called** — ranked by number of calls
  - **Longest Calls** — ranked by total minutes
  - **Recent** — ranked by last call date

### Call History
- Paginated call log with filters for phone number, status, and date range
- Aggregate stats: total calls, missed calls, average duration, breakdown by call type

### Import CSV
- Upload contacts or calls CSV directly from the browser
- Shows import summary (how many records were added / skipped)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/contacts` | List contacts (search, sort, paginate) |
| GET | `/contacts/{id}` | Get a single contact |
| GET | `/contacts/duplicates` | List duplicate-flagged contacts |
| POST | `/contacts` | Create a contact |
| PUT | `/contacts/{id}` | Update a contact |
| DELETE | `/contacts/{id}` | Delete a contact (204) |
| GET | `/calls` | List calls (filter by phone, status, date range) |
| GET | `/calls/stats` | Aggregate call statistics |
| GET | `/favourites` | Ranked contacts (?mode=most_called&limit=10) |
| GET | `/dashboard/summary` | All dashboard stats in one request |
| POST | `/import/contacts` | Upload contacts CSV |
| POST | `/import/calls` | Upload calls CSV |
| POST | `/ai/classify` | Classify an uploaded image |
| GET | `/ai/images` | List all previously classified images |
| GET | `/ai/images/{id}` | Retrieve a stored image by ID |

Full interactive documentation available at **http://localhost:8000/docs** when the server is running.

---

## AI Module

The AI module classifies contact profile photos into three categories: Saudi formal clothing, casual clothing, and not human. Every classification is stored in the database alongside the compressed image, prediction, confidence score, and timestamp.

### How it works

An uploaded image passes through a YOLOv8n-cls model layer by layer. Early layers detect basic visual patterns like edges and textures. Deeper layers combine those into clothing shapes and fabric patterns. The final layer outputs a confidence score for each of the three classes and the highest score becomes the prediction.

### Training the model

To retrain on new data, first delete the existing `ai/dataset/` and `ai/runs/` folders, then run:

```bash
cd ai
python preprocess.py
python train.py
```

`preprocess.py` resizes all images to 224x224, splits them 70/20/10 across train, validation, and test sets, and generates 3 augmented versions of each training image. `train.py` fine-tunes YOLOv8n-cls on the resulting dataset and saves the best weights automatically.

After training, copy the model to the backend:

```bash
cp runs/classify/runs/classify/run1/weights/best.pt ../backend/model/best.pt
```

### Model performance

| Metric | Value |
|--------|-------|
| Architecture | YOLOv8n-cls |
| Parameters | 1,442,131 |
| Training images | 2,520 (630 original + 3x augmentation) |
| Validation accuracy | 100% |
| Test accuracy | 100% |
| Inference speed | 5.2ms per image |
| Epochs to converge | 6 |
| Transfer learning | ImageNet pretrained (156/158 layers) |

---

## Data Cleaning

The cleaner (`utils/cleaner.py`) runs automatically on every import and handles:

- Phone normalisation — all numbers converted to `+966XXXXXXXXX` format
- Name standardisation — Title Case, whitespace trimmed
- Email lowercasing
- Duplicate removal — exact duplicates (same phone + email) removed
- Duplicate flagging — contacts sharing a phone number are flagged as `possible_duplicates = True`
- Date and time parsing — standardised to Python `date` and `time` objects
- Missing contact name lookup — call records matched to contacts table by phone number

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Python 3.11 |
| Database ORM | SQLAlchemy |
| Validation | Pydantic v2 |
| Database | PostgreSQL |
| Frontend | Vue 3 (Composition API) |
| HTTP Client | Axios |
| Charts | Chart.js via vue-chartjs |
| Build Tool | Vite |
| Computer Vision | YOLOv8n-cls (Ultralytics) |
| ML Framework | PyTorch |
| Experiment Tracking | MLflow |

---

## Security Notes

- All credentials are stored in `.env` files — never hardcoded
- `.env` is excluded from version control via `.gitignore`
- Pydantic validates all incoming data before it touches the database
- Global error handlers return structured JSON — no stack traces exposed to the client
- Uploaded images are size-validated (10MB limit) and compressed before storage

---

## Build for Production

```bash
cd frontend
npm run build
```

Output will be in `frontend/dist/`. Serve it with any static file server or configure FastAPI to serve it directly.
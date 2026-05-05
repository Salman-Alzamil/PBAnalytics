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
│   │   ├── active_model.json # Tracks which checkpoint is currently active
│   │   ├── best.pt           # v1.0 trained weights (2MB)
│   │   └── v2.0/             # v2.0 checkpoints (created by publish_model.py)
│   │       ├── best.pt
│   │       ├── epoch15.pt    # example periodic checkpoint
│   │       └── ...
│   ├── routes/
│   │   ├── contacts.py       # GET/POST/PUT/DELETE /contacts
│   │   ├── calls.py          # GET /calls and /calls/stats
│   │   ├── favourites.py     # GET /favourites
│   │   ├── dashboard.py      # GET /dashboard/summary
│   │   ├── import_csv.py     # POST /import/contacts and /import/calls
│   │   └── ai.py             # POST /ai/classify, GET /ai/images, model management
│   └── utils/
│       ├── cleaner.py        # Data cleaning and normalisation logic
│       ├── favourites.py     # Favourites scoring algorithm
│       └── ai_classifier.py  # YOLO model loading, inference, and hot-reload
├── ai/                       # ML training pipeline
│   ├── preprocess.py         # Data cleaning, augmentation, and dataset splitting
│   ├── train.py              # YOLOv8 training script with per-class diagnostics
│   ├── evaluate.py           # Per-class accuracy, confusion matrix (accepts --model flag)
│   ├── publish_model.py      # Copy a checkpoint to backend/model/ and set it active
│   ├── dataset/              # Preprocessed dataset (70/20/10 split) — included for reproducibility
│   │   ├── train.cache
│   │   ├── valid.cache
│   │   └── test.cache
│   ├── yolov8n-cls.pt        # Base YOLOv8n model
│   └── runs/                 # Training artifacts (git-ignored, regenerated during retraining)
├── frontend/                 # Vue 3 frontend
│   └── src/
│       ├── views/            # Dashboard, Contacts, Favourites, CallHistory, ImportCSV
│       ├── api/index.js      # Central Axios API layer
│       └── router/index.js   # Vue Router configuration
├── data/
│   ├── contacts_data.csv     # Sample contacts CSV
│   └── calls_history.csv     # Sample call history CSV
└── README.md                 # This file
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

> **Never commit your `.env` file.** It is already listed in `.gitignore`.

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
| GET | `/ai/models` | List all available .pt checkpoint files |
| GET | `/ai/model/info` | Show which checkpoint is currently loaded |
| POST | `/ai/model/select` | Switch the active checkpoint without restarting |

Full interactive documentation available at **http://localhost:8000/docs** when the server is running.

---

## AI Module

The AI module classifies contact profile photos into three categories: **Saudi formal clothing**, **casual clothing**, and **not human**. Every classification is stored in the database alongside the compressed image, prediction, confidence score, and timestamp.

### How it works

An uploaded image passes through a YOLOv8n-cls model layer by layer. Early layers detect basic visual patterns like edges and textures. Deeper layers combine those into clothing shapes and fabric patterns. The final layer outputs a confidence score for each of the three classes and the highest score becomes the prediction.

### Training the model

The training pipeline is included for reproducibility. The preprocessed dataset is committed to the repo for easy setup.

```bash
cd ai
python preprocess.py     # Resize to 224×224, split 70/20/10, generate augmented versions
python train.py          # Fine-tune YOLOv8n-cls — saves best.pt, last.pt, and epoch*.pt every 5 epochs
python evaluate.py       # Per-class accuracy + confusion matrix on val and test splits
```

After training, pick a checkpoint and publish it to the backend:

```bash
# See all checkpoints alongside their val/loss per epoch to help you choose
python publish_model.py --list

# Publish the checkpoint you want (backend switches on next request)
python publish_model.py --run run2 --checkpoint best
python publish_model.py --run run2 --checkpoint epoch15   # if epoch15 had lower val/loss

# Evaluate a specific checkpoint before publishing
# Note: YOLO nests the output under runs/classify/runs/classify/<run>/
python evaluate.py --model runs/classify/runs/classify/run2/weights/epoch15.pt
python evaluate.py --model runs/classify/runs/classify/run2/weights/best.pt --split test
```

You can also switch the active model at runtime via the API without restarting the server — see `POST /ai/model/select`.

#### How to pick the right checkpoint

| Signal | What to look for |
|--------|-----------------|
| `val/loss` in results.csv | Pick the epoch where it is **lowest before it starts rising** |
| `best.pt` | YOLO's auto-pick by highest val accuracy — safe default |
| `last.pt` | Final epoch — often the most overfit, avoid unless loss is still falling |
| Per-class callback output | Look for the first epoch where **all classes** reach balanced (non-suspicious) accuracy |
| `evaluate.py` output | Run on each candidate; a balanced confusion matrix beats a perfect one |

### Model performance

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Architecture | YOLOv8n-cls | YOLOv8n-cls |
| Parameters | 1,442,131 | 1,442,131 |
| Training images | 2,520 (630 original + 3× aug) | 2,520 (630 original + 3× aug) |
| Epochs to converge | 6 | 7 |
| Epochs total | 11 | 17 (early stop) |
| Validation accuracy | 100% ⚠️ | 100% |
| Test accuracy | 100% ⚠️ | 100% (90/90 unseen) |
| Inference speed | ~5ms per image | ~5ms per image |
| Regularisation | none | dropout 0.3, label smoothing 0.1, weight decay 0.001 |
| Transfer learning | ImageNet pretrained | ImageNet pretrained |

> ⚠️ v1.0 accuracy is suspicious — the model achieved 100% by epoch 6 with no regularisation. Root cause: pre-computed static augmentation files meant the model memorised the exact pixel values of `_aug0/1/2.jpg` rather than learning genuine invariance. v2.0 adds regularisation, converged one epoch later, and confirmed 100% on the held-out test set (data the model never saw during training), indicating the result reflects genuine generalisation rather than memorisation. Caveat: 30 test images per class is a small statistical sample.

### What's in the repo

- **Included:** `preprocess.py`, `train.py`, `evaluate.py`, `publish_model.py`, preprocessed `dataset/` cache files, base `yolov8n-cls.pt`, trained `backend/model/best.pt` (v1.0, 2MB), `active_model.json`
- **Git-ignored:** `ai/runs/` (training artifacts), `ai/mlflow.db`, raw images (use cloud storage)
- **Why:** The trained weights and config are small enough and necessary for deployment. Training run artifacts are regenerated by `train.py` and do not belong in version control.

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

---

## Git Workflow

The repo includes a `.gitignore` that excludes:
- Python virtual environments and cache
- Node modules and build artifacts
- Environment variables (`.env`)
- IDE settings (`.vscode/`, `.idea/`)
- Training artifacts (`ai/runs/`)
- Large files (images, zip files)

The preprocessed dataset and trained model weights are committed because they're essential for reproducibility and deployment.

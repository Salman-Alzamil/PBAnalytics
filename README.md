# PhoneBook Analytics

A full-stack phonebook analytics application built with **FastAPI**, **PostgreSQL**, and **Vue 3**, with an integrated computer vision module for automated contact photo classification and a face similarity search engine for identifying contacts by photo.

Import contacts and call history from CSV files, then explore communication patterns through an interactive dashboard, featuring smart duplicate detection, a scoring-based favourites algorithm, real-time call statistics, AI-powered clothing classification, and face-based contact search.

---

## Project Structure

```
PBAnalytics/
├── backend/                  # FastAPI Python backend
│   ├── main.py               # App entry point, middleware, pgvector setup, error handlers
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
│   │   ├── contacts.py       # GET/POST/PUT/DELETE /contacts, picture upload
│   │   ├── calls.py          # GET /calls and /calls/stats
│   │   ├── favourites.py     # GET /favourites
│   │   ├── dashboard.py      # GET /dashboard/summary
│   │   ├── import_csv.py     # POST /import/contacts and /import/calls
│   │   ├── ai.py             # POST /ai/classify, GET /ai/images, model management
│   │   └── face_search.py    # POST /search/by-face, /analyze/group-image, /identify/face, /face-embeddings/*
│   └── utils/
│       ├── cleaner.py        # Data cleaning and normalisation logic
│       ├── favourites.py     # Favourites scoring algorithm
│       ├── ai_classifier.py  # YOLO model loading, inference, and hot-reload
│       ├── face_embeddings.py  # InsightFace buffalo_l detection and embedding
│       └── image_store.py    # Image compression helpers
├── ai/                       # ML training pipeline
│   ├── preprocess.py         # Data cleaning, augmentation, and dataset splitting
│   ├── train.py              # YOLOv8 training script with per-class diagnostics
│   ├── evaluate.py           # Per-class accuracy, confusion matrix (accepts --model flag)
│   ├── publish_model.py      # Copy a checkpoint to backend/model/ and set it active
│   ├── dataset/              # Preprocessed dataset (70/20/10 split) -- included for reproducibility
│   │   ├── train.cache
│   │   ├── valid.cache
│   │   └── test.cache
│   ├── yolov8n-cls.pt        # Base YOLOv8n model
│   └── runs/                 # Training artifacts (git-ignored, regenerated during retraining)
├── scripts/                  # Standalone debug and benchmarking scripts
│   ├── test_face_similarity.py  # Cross-similarity matrix for the face pipeline
│   └── face_debug_*.py          # Ablation and diagnostic scripts
├── frontend/                 # Vue 3 frontend
│   └── src/
│       ├── views/            # Dashboard, Contacts, Favourites, CallHistory, ImportCSV, FaceSearch
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

On startup the server automatically enables the pgvector extension and creates the `contact_face_embeddings` table with an HNSW index.

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
- Profile photo upload with automatic AI clothing classification
- Face embedding indexed automatically on photo upload

### Favourites
- Contacts ranked by a scoring formula: `score = (call_count x 2) + total_duration_minutes`, normalised to 0-100
- Podium cards for top 3 contacts
- Three sort modes via tab switcher:
  - **Most Called** -- ranked by number of calls
  - **Longest Calls** -- ranked by total minutes
  - **Recent** -- ranked by last call date

### Call History
- Paginated call log with filters for phone number, status, and date range
- Aggregate stats: total calls, missed calls, average duration, breakdown by call type

### Import CSV
- Upload contacts or calls CSV directly from the browser
- Shows import summary (how many records were added / skipped)

### Face Search
Two AI-powered features for identifying contacts by photo.

**Find Person** -- Upload a photo containing exactly one face. The system extracts a face embedding and searches the contact database for the closest match, returning the contact's details and a similarity score. Photos with zero or more than one face are rejected.

**Group Photo** -- Upload a photo with multiple people. The system detects every face and overlays numbered bounding boxes on the image. Click any face to identify that person against the contact database.

Before searching, click **Index Faces** on the Face Search page to pre-compute embeddings for all existing contact profile pictures. Re-run it after adding new contacts.

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
| PATCH | `/contacts/{id}/picture` | Set profile picture by image ID |
| POST | `/contacts/{id}/picture/upload` | Upload, classify, and set profile picture |
| DELETE | `/contacts/{id}/picture` | Remove profile picture |
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
| POST | `/search/by-face` | Find a contact by uploading a single-face photo |
| POST | `/analyze/group-image` | Detect all faces in a group photo (returns bounding boxes + embeddings) |
| POST | `/identify/face` | Identify one face given its embedding vector |
| POST | `/face-embeddings/precompute` | Pre-compute and store embeddings for all contact profile pictures |
| GET | `/face-embeddings/status` | Check whether the face index is up to date |

Full interactive documentation available at **http://localhost:8000/docs** when the server is running.

---

## AI Module -- Clothing Classifier

The clothing classifier categorises contact profile photos into three classes: **Saudi formal clothing**, **casual clothing**, and **not human**. The classification runs on every profile photo upload and the result is stored in the database alongside the compressed image, prediction, confidence score, and timestamp.

### How it works

An uploaded image passes through a YOLOv8n-cls model layer by layer. Early layers detect basic visual patterns like edges and textures. Deeper layers combine those into clothing shapes and fabric patterns. The final layer outputs a confidence score for each of the three classes and the highest score becomes the prediction. The model is loaded once on first use and cached in memory; subsequent requests are instant.

The active model is tracked in `backend/model/active_model.json`. You can switch checkpoints at runtime without restarting the server using `POST /ai/model/select`.

### Training the model

The training pipeline is included for reproducibility. The preprocessed dataset is committed to the repo for easy setup.

```bash
cd ai
python preprocess.py     # Resize to 224x224, split 70/20/10, generate augmented versions
python train.py          # Fine-tune YOLOv8n-cls -- saves best.pt, last.pt, and epoch*.pt every 5 epochs
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

You can also switch the active model at runtime via the API without restarting the server -- see `POST /ai/model/select`.

#### How to pick the right checkpoint

| Signal | What to look for |
|--------|-----------------|
| `val/loss` in results.csv | Pick the epoch where it is **lowest before it starts rising** |
| `best.pt` | YOLO's auto-pick by highest val accuracy -- safe default |
| `last.pt` | Final epoch -- often the most overfit, avoid unless loss is still falling |
| Per-class callback output | Look for the first epoch where **all classes** reach balanced (non-suspicious) accuracy |
| `evaluate.py` output | Run on each candidate; a balanced confusion matrix beats a perfect one |

### Model performance

| Metric | v1.0 | v2.0 |
|--------|------|------|
| Architecture | YOLOv8n-cls | YOLOv8n-cls |
| Parameters | 1,442,131 | 1,442,131 |
| Training images | 2,520 (630 original + 3x aug) | 2,520 (630 original + 3x aug) |
| Epochs to converge | 6 | 7 |
| Epochs total | 11 | 17 (early stop) |
| Validation accuracy | 100% (*) | 100% |
| Test accuracy | 100% (*) | 100% (90/90 unseen) |
| Inference speed | ~5ms per image | ~5ms per image |
| Regularisation | none | dropout 0.3, label smoothing 0.1, weight decay 0.001 |
| Transfer learning | ImageNet pretrained | ImageNet pretrained |

(*) v1.0 accuracy is suspicious -- the model achieved 100% by epoch 6 with no regularisation. Root cause: pre-computed static augmentation files meant the model memorised the exact pixel values of `_aug0/1/2.jpg` rather than learning genuine invariance. v2.0 adds regularisation, converged one epoch later, and confirmed 100% on the held-out test set (data the model never saw during training), indicating the result reflects genuine generalisation rather than memorisation. Caveat: 30 test images per class is a small statistical sample.

### What's in the repo

- **Included:** `preprocess.py`, `train.py`, `evaluate.py`, `publish_model.py`, preprocessed `dataset/` cache files, base `yolov8n-cls.pt`, trained `backend/model/best.pt` (v1.0, 2MB), `active_model.json`
- **Git-ignored:** `ai/runs/` (training artifacts), `ai/mlflow.db`, raw images (use cloud storage)
- **Why:** The trained weights and config are small enough and necessary for deployment. Training run artifacts are regenerated by `train.py` and do not belong in version control.

---

## AI Module -- Face Similarity Search

The face search module identifies contacts by face rather than name or phone number. It uses InsightFace buffalo_l, which combines RetinaFace detection and ArcFace embeddings, to extract a 512-dimensional face vector from any photo and find the closest match in the contact database.

### How it works

Every contact profile picture is processed by InsightFace to extract a face embedding -- a 512-number vector encoding the geometry of that face. These are stored in PostgreSQL using the pgvector extension. When a search photo is uploaded, the same model extracts an embedding from the search face and the database returns the contact with the closest cosine similarity. If the score exceeds the threshold (0.40), the contact is returned.

The pipeline is handled entirely by InsightFace in a single call: detection, 5-point landmark alignment, crop, resize, embedding extraction, and L2 normalisation. This consistency between how stored profiles and search photos are processed is what makes similarity scores reliable.

### Setting up the face index

After importing contacts and adding profile pictures, pre-compute all embeddings:

```
POST /face-embeddings/precompute
```

Or click **Index Faces** on the Face Search page. Re-run after adding new contacts with profile pictures. Profile photos uploaded through the contacts page are indexed automatically -- no manual re-index needed for new uploads.

Check index status at any time:

```
GET /face-embeddings/status
```

### Pipeline versioning

A `PIPELINE_VERSION` string in `face_search.py` is bumped whenever the embedding model or preprocessing changes. The last precompute run stamps this version into the database. Every search response includes `index_stale: true` if the versions do not match, signalling that embeddings need to be recomputed before results can be trusted.

### Running the similarity test

```bash
cd scripts
python test_face_similarity.py
```

Prints a cross-similarity matrix comparing test images against stored embeddings, with min/median/max for same-person and different-person groups and a suggested threshold.

---

## Data Cleaning

The cleaner (`utils/cleaner.py`) runs automatically on every import and handles:

- Phone normalisation -- all numbers converted to `+966XXXXXXXXX` format
- Name standardisation -- Title Case, whitespace trimmed
- Email lowercasing
- Duplicate removal -- exact duplicates (same phone + email) removed
- Duplicate flagging -- contacts sharing a phone number are flagged as `possible_duplicates = True`
- Date and time parsing -- standardised to Python `date` and `time` objects
- Missing contact name lookup -- call records matched to contacts table by phone number

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
| Face Recognition | InsightFace buffalo_l (RetinaFace + ArcFace) |
| Vector Search | pgvector (PostgreSQL extension) with HNSW index |
| ML Framework | PyTorch |
| Experiment Tracking | MLflow |

---

## Security Notes

- All credentials are stored in `.env` files -- never hardcoded
- `.env` is excluded from version control via `.gitignore`
- Pydantic validates all incoming data before it touches the database
- Global error handlers return structured JSON -- no stack traces exposed to the client
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
- Training artifacts (`ai/runs/`, `ai/mlflow.db`, `ai/mlruns/`)
- Large files (images, zip files)

The preprocessed dataset and trained model weights are committed because they're essential for reproducibility and deployment.
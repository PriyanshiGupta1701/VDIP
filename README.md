# VDIP – Vehicle Damage Intelligence Platform

AI-driven vehicle damage assessment from a single photo. VDIP detects exterior damage, estimates how severe it is, recommends **repair vs. replace**, and, in the background, generates repair guides or sources replacement parts with price estimates and logs everything to a Google Sheet.

**Use cases:** insurance claims, rental-car return inspections, used-car evaluation, fleet maintenance.

---

## What It Does

Upload one vehicle image (optionally choose a damage type) and VDIP:

1. **Detects** damage with two YOLOv8 models (general damage + rust).
2. **Scores severity** using a method suited to each defect type.
3. **Decides** repair or replace with rule-based logic.
4. **Returns** an annotated image with bounding boxes and per-defect details.
5. **Runs a background agent (LangGraph + Gemini)** that produces repair guides or replacement-part links, estimates prices, and writes a report to Google Sheets.
6. **Emails** a link to the report on request.

## Defects Detected: 6 Types

| Defect | Severity method | Decision rule |
|---|---|---|
| Dent | Depth (Apple Depth Pro) → Minor / Moderate / Severe / Critical | Minor, Moderate → Repair; Severe, Critical → Replace |
| Scratch | Length, width, area, aspect ratio → Minor to Critical | Same as dent |
| Crack | Length, width, area, aspect ratio → Minor to Critical | Same as dent |
| Rust | ResNet-18 classifier (Slightly Visible / Visible / Heavy Visible) | Slightly Visible → Repair; otherwise Replace |
| Glass shatter | Presence-based | Always Replace |
| Broken lamp | Presence-based | Always Replace |

## Key Features

- **Multi-model vision stack:** YOLOv8 (damage + rust), Apple Depth Pro (dent depth), ResNet-18 (rust severity).
- **Repair-vs-replace decisioning** from a single photo.
- **Agentic post-processing (LangGraph):** repair guide or part search → price estimate → Google Sheets logging, run as a FastAPI background job so the API stays responsive.
- **Annotated output** hosted on Cloudinary, shown in the web UI.
- **Optional damage-type filter** to check one defect type only.
- **Report email** with a link to the Google Sheet.
- **Performance:** about 6 s per image on CPU, plus roughly 6–7 s when dent-depth estimation runs.

## Tech Stack

- **Backend:** Python, FastAPI, Ultralytics YOLOv8, PyTorch, Apple ML-Depth Pro, OpenCV, LangGraph, Gemini (`langchain-google-genai`), Cloudinary, Google Sheets API
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS v4, Material UI

## Project Structure

```
VDIP/
├── backend/
│   ├── main.py                # FastAPI app: endpoints, detection, agent pipeline
│   ├── depth_estimation.py    # Depth Pro loading + dent severity
│   ├── test_smtp.py           # Checks your email (SMTP) settings
│   ├── weights/               # YOLOv8 + ResNet-18 checkpoints
│   ├── ml-depth-pro/          # Apple ML-Depth Pro (clone separately, see below)
│   └── .env                   # API keys and credentials
└── frontend/
    ├── src/                   # React app (pages/main/Page.tsx is the main UI)
    └── .env                   # API URL (defaults to http://127.0.0.1:8000)
```

---

## Start-Up Guide (Local)

### Prerequisites

- Python 3.10+ and `pip`
- Node.js 18+ and `npm`
- Git
- Accounts/keys: Cloudinary, Google Gemini, SerpAPI, a Google Cloud service account with Sheets access, and SMTP credentials

### 1. Backend

From the `backend/` folder:

**a) Create a virtual environment**

```bash
cd backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate
```

**b) Install dependencies**

```bash
pip install fastapi uvicorn nest-asyncio python-multipart cloudinary ultralytics \
  pillow pillow-heif opencv-python-headless torch torchvision numpy scipy timm \
  requests pydantic langgraph langchain-google-genai langchain-core beautifulsoup4 \
  google-auth google-api-python-client openpyxl gspread python-dotenv
```

**c) Set up Apple ML-Depth Pro** (used for dent depth)

```bash
git clone https://github.com/apple/ml-depth-pro.git
pip install -e ./ml-depth-pro
mkdir -p ml-depth-pro/checkpoints
# Download depth_pro.pt (see the ml-depth-pro README for the link) into:
#   backend/ml-depth-pro/checkpoints/depth_pro.pt
```

**d) Check the model weights.** `backend/weights/` must contain:

- `20epochyolov8s.pt`
- `rust_detection_model.pt`
- `resnet18_rust_severity_folderdata.pt`

**e) Configure `backend/.env`**

```env
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...

GOOGLE_API_KEY=...
GOOGLE_GEMINI_MODEL=...

SERPAPI_API_KEY=...
SERPAPI_GL=us

EMAIL_SENDER=...
EMAIL_PASSWORD=...
EMAIL_SMTP_SERVER=smtp.office365.com
EMAIL_SMTP_PORT=587

SPREADSHEET_ID=...
```

Place your Google service-account JSON key in `backend/` and make sure its filename matches `SERVICE_ACCOUNT_FILE` in `main.py`. Share the target spreadsheet with the service account's email.

**f) Run the server**

```bash
python main.py
# or
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

- API: http://127.0.0.1:8000
- Health check: `GET /` → `{"status": "ok"}`
- Interactive docs: http://127.0.0.1:8000/docs

> Startup loads the YOLO and depth models, so the first launch can take a while. A GPU is used automatically if available; otherwise inference runs on CPU.

### 2. Frontend

From the `frontend/` folder:

```bash
cd frontend
npm install
```

Confirm `frontend/.env` points to the local backend:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_API_HOST=127.0.0.1:8000
```

Start the dev server:

```bash
npm run dev
```

Open the URL Vite prints (normally http://localhost:5173). The backend allows `localhost` and `127.0.0.1` on ports 3000 and 5173.

To build for production: `npm run build`, then preview with `npm run preview`.

### 3. Email Setup (Gmail App Password)

The **Send Report to Email** button sends a link to the Google Sheet from your own Gmail account. Gmail requires an **App Password**, not your normal password.

1. Turn on **2-Step Verification**: myaccount.google.com → **Security**.
2. Create an app password at **myaccount.google.com/apppasswords** (name it "VDIP"). It is 16 characters.
3. Set these in `backend/.env`, with the app password entered **without spaces or quotes**:
   ```env
   EMAIL_SENDER=your_address@gmail.com
   EMAIL_PASSWORD=your16charapppassword
   EMAIL_SMTP_SERVER=smtp.gmail.com
   EMAIL_SMTP_PORT=587
   ```
4. Test the settings from `backend/`:
   ```bash
   python test_smtp.py
   ```
   You should see `3. ✅ Login OK`.
5. Restart the backend (`python main.py`). `.env` is only read at startup.
6. Share the Google Sheet with the people who will receive the report, or set "Anyone with the link can view". Otherwise the emailed link asks them to request access.

> Never share or paste debug output that contains `AUTH` lines. Debug logging can expose your login in Base64.

### 4. Using the App

1. Start the backend, then the frontend.
2. Upload a vehicle image (PNG, JPG, JPEG or WEBP).
3. Optionally pick a damage type, or leave it on **Auto Detect**.
4. Enter your email and click **Run Detection**.
5. Review the annotated image and per-defect details.
6. Click **Send Report to Email** to receive the Google Sheet link. The repair guides, part links and price estimates are written to the sheet in the background.

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Health check |
| POST | `/analyze-damage` | Upload an image (`file`, optional `damage_type`, `email_id`, `session_id`) and get detections, severity, decisions and the annotated image URL |
| POST | `/email` | Send the Google Sheet report link to the given email |

## Troubleshooting

### Email is not arriving

The backend now logs the real reason (`❌ Email failed: ...`) and returns an error, so the UI shows an error toast on failure.

| Message | Cause | Fix |
|---|---|---|
| `534 Application-specific password required` | Using your normal Gmail password | Create and use a 16-character app password (Step 3 above) |
| `535 Username and Password not accepted` | Wrong or mistyped app password | Create a new one; no spaces or quotes in `.env` |
| `SMTPServerDisconnected: Connection unexpectedly closed` | The server rejected the login, or the connection was blocked | Run `python test_smtp.py` and check the steps below |
| Timeout or connection refused | Port 587 blocked by your network or antivirus | Set `EMAIL_SMTP_PORT=465`, or try another network |

If `test_smtp.py` shows **Password length: 8** (or anything other than 16 for an app password), the script is reading the wrong value:

1. Check what Python reads:
   ```powershell
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(len(os.getenv('EMAIL_PASSWORD','')))"
   ```
2. Look for a leftover Windows environment variable. These override `.env`:
   ```powershell
   echo $env:EMAIL_PASSWORD
   Remove-Item Env:EMAIL_PASSWORD
   ```
3. Open `backend\.env` (not `.env.example`), confirm the line has exactly 16 characters, and **save the file**.
4. Run `python test_smtp.py` again, then restart the backend.

### Replacement links or prices are empty

- Replacement-part search uses **SerpAPI** (Google Shopping). Set `SERPAPI_API_KEY` in `backend/.env`.
- Check the terminal for `⚠️ SerpAPI error` messages. The free tier allows 250 searches per month, and each "Replace" detection uses one.

### Large file download fails on Windows (`depth_pro.pt`)

PowerShell's `wget` loads the whole ~1.9 GB file into memory and fails. Use `curl.exe` instead (with the `.exe`):

```powershell
curl.exe -L -O https://ml-site.cdn-apple.com/models/depth-pro/depth_pro.pt
```

## Known Limitations

- Severity in cm for scratches and cracks uses a fixed pixel-to-cm constant, so results are most reliable when photos are taken at a consistent distance.
- Only the largest detection per damage type is scored.
- Background results (repair guide, links, prices) are available only in the Google Sheet, not in the UI.
- There is no authentication; run it locally or behind your own access control.
- Keep `.env` and the service-account JSON out of version control.

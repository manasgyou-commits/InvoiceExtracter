# Invoice Extractor Pro

Android app (Kivy + Tesseract OCR) that batch-extracts line items from Asian Paints invoice images/PDFs and exports them to CSV.

## Features
- Pick multiple images or PDFs at once
- Offline OCR via Tesseract (no internet needed)
- Auto-parses Asian Paints invoice line items (material no., HSN, qty, price, GST, total)
- Export to CSV with timestamp
- Handles 300+ files in a background thread

---

## Quick Start — Desktop (test/dev)

```bash
# 1. Clone repo
git clone https://github.com/YOUR_USER/InvoiceExtractorApp.git
cd InvoiceExtractorApp

# 2. Install Python deps
pip install -r requirements.txt

# 3. Install Tesseract OCR engine
#    Ubuntu/Debian:  sudo apt install tesseract-ocr
#    macOS:          brew install tesseract
#    Windows:        https://github.com/tesseract-ocr/tesseract/releases

# 4. Run
python main.py
```

---

## Build Android APK

### Option A — Buildozer (recommended)

```bash
# Requires Linux or WSL2
pip install buildozer cython
bash build.sh
# APK lands in output/
```

### Option B — Pydroid 3 (on-device)

1. Install **Pydroid 3** from the Play Store.
2. In Pydroid's pip tab install:
   ```
   kivy pillow pytesseract opencv-python-headless PyMuPDF
   ```
3. Copy `main.py` to your phone and open it in Pydroid.

### Option C — Termux

```bash
pkg update && pkg install python tesseract opencv-python
pip install kivy pillow pytesseract PyMuPDF
python main.py
```

---

## Tesseract Language Data

Download `eng.traineddata` from:
<https://github.com/tesseract-ocr/tessdata>

Place it in:
- **Android**: `/storage/emulated/0/tessdata/`
- **Linux/Mac**: wherever `TESSDATA_PREFIX` points (default `/usr/share/tesseract-ocr/*/tessdata/`)
- **Windows**: `C:\Program Files\Tesseract-OCR\tessdata\`

---

## Usage

| Step | Action |
|------|--------|
| 1 | Tap **Pick Files** → select invoice images or PDFs |
| 2 | Tap **Extract** → OCR + parse runs in background |
| 3 | Review rows in the scrollable table |
| 4 | Tap **Save CSV** → file saved to `~/Downloads/` |
| 5 | Tap **Clear** to start a new batch |

CSV output: `~/Downloads/Invoices_YYYYMMDD_HHMMSS.csv`

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "Tesseract OCR not installed" | Install engine + eng.traineddata (see above) |
| Blank/wrong text extracted | Use clearer images; ensure good lighting |
| PDF pages not loading | Install PyMuPDF: `pip install PyMuPDF` |
| App crash on Android | Grant Storage permission in device Settings |
| Slow on 300+ files | Keep phone plugged in; OCR is CPU-intensive |

---

## CI (GitHub Actions)

Every push runs:
1. **Syntax check** — `python -m compileall` on all `.py` files
2. **Lint** — flake8 (max line 120)
3. **Unit tests** — `pytest test_parser.py` (no hardware needed)
4. **buildozer.spec validation** — checks for duplicate keys

See `.github/workflows/ci.yml`.

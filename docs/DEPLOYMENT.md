# Deploying ToothTrust to Streamlit Community Cloud

Streamlit Community Cloud (free tier) gives you a public URL anyone can open without installing Python.

---

## Prerequisites

- A GitHub account with this repo pushed to it
- A Streamlit Community Cloud account (free at [share.streamlit.io](https://share.streamlit.io))
- An Anthropic API key (for live demo mode)

---

## One-time Setup

### 1. Fork / push the repo to GitHub

The repo must be public (or you must be on Streamlit Teams/Enterprise for private repos).

```bash
git push origin main
```

### 2. Add secrets to Streamlit Cloud

Streamlit Cloud injects secrets as environment variables. In the Streamlit dashboard:

1. Open your app → **Settings → Secrets**
2. Paste the following (replace values with real keys):

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
DEEPGRAM_API_KEY = ""
ELEVENLABS_API_KEY = ""
```

> Note: `DEEPGRAM_API_KEY` and `ELEVENLABS_API_KEY` are optional for the demo — the Streamlit UI only uses the Anthropic key.

### 3. Add a packages.txt for system dependencies (if needed)

Create `packages.txt` in the project root if `chromadb` fails to build on Linux:

```
build-essential
```

### 4. Make sure requirements are Streamlit-Cloud-compatible

Streamlit Cloud installs from `requirements.txt`. The current file includes `openwakeword` which depends on `onnxruntime`, which has no Linux aarch64 / Python 3.11+ wheel. Add a `requirements-streamlit.txt` with that line removed, and point Streamlit Cloud at it via **Advanced Settings → Python packages file**.

Or simply add this to `requirements.txt` as a comment until voice hardware is needed:

```
# openwakeword  # requires onnxruntime — excluded for Streamlit Cloud deploy
# sounddevice   # requires audio hardware — excluded for Streamlit Cloud deploy
# elevenlabs    # TTS — excluded for Streamlit Cloud deploy
```

---

## Deploy Steps

1. Log in at [share.streamlit.io](https://share.streamlit.io)
2. Click **New app**
3. Fill in:
   - **Repository**: `Natt1111/toothtrust`
   - **Branch**: `main`
   - **Main file path**: `app/streamlit_app.py`
4. Click **Deploy**
5. Wait ~2–3 minutes for the build to complete
6. Copy the public URL: `https://toothtrust-<hash>.streamlit.app`

---

## Local Quick Start

```bash
# Clone the repo
git clone https://github.com/Natt1111/toothtrust.git
cd toothtrust

# Create venv and install core deps
uv venv --python 3.11
uv pip install streamlit chromadb sentence-transformers anthropic pypdf python-dotenv pandas "numpy<2" "torch==2.1.2" "chromadb==0.5.23" "protobuf>=3.20,<4"

# Copy and fill in your API key
cp .env.example .env   # edit ANTHROPIC_API_KEY

# Run the app
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python \
TOKENIZERS_PARALLELISM=false \
streamlit run app/streamlit_app.py
```

The app opens at `http://localhost:8501`. Each "Run Audit" click costs ~$0.05 in Anthropic API credits. Results are cached in session state — refreshing the page doesn't re-run the API.

---

## Offline Mode

If `ANTHROPIC_API_KEY` is not set or is invalid, the app automatically falls back to **offline mode** and shows pre-computed results from `expected_audit.json` / `expected_chart.json`. All three demo cases are still fully browsable in offline mode — useful for demos without incurring API cost.

---

## Notes

- `chroma_db/` (the vector database) is gitignored. On Streamlit Cloud, it will be rebuilt on first run if not checked in. Either commit the `chroma_db/` folder or add a startup script that runs `python -m src.ingest` before the Streamlit app starts. The easiest option is to commit `chroma_db/` for the demo (it's only ~200KB).
- The `outputs/` folder is gitignored and not needed for the Streamlit UI.

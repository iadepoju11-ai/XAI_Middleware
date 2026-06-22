"""
Download Home Credit and LendingClub datasets from Kaggle.

Prerequisites:
  1. Create a Kaggle account at https://www.kaggle.com
  2. Go to Account -> Settings -> API -> Create New Token
  3. Place the downloaded kaggle.json at C:\\Users\\<you>\\.kaggle\\kaggle.json
     The file may contain either:
       - JSON format: {"username": "...", "key": "..."}
       - Shell export format: export KAGGLE_API_TOKEN=KGAT_...
  4. Run from the project root (inside the backend venv):
       cd backend && source .venv/Scripts/activate
       python ../data/download_kaggle_datasets.py

Datasets downloaded:
  data/home_credit/     ~300 MB   -- Home Credit Default Risk (scale testing)
  data/lending_club/    ~1.5 GB   -- LendingClub Loan Data (load test seed data)
"""
import os
import ssl
import sys
import zipfile

# ── Step 1: Extract KAGGLE_API_TOKEN from ~/.kaggle/kaggle.json if it is in
#    shell-export format (export KAGGLE_API_TOKEN=KGAT_...) rather than JSON.
#    The kagglesdk reads KAGGLE_API_TOKEN from the environment BEFORE touching
#    the JSON file, so setting it here avoids the JSONDecodeError that occurs
#    when kagglesdk tries to parse a non-JSON credentials file.
_KAGGLE_JSON = os.path.expanduser("~/.kaggle/kaggle.json")
if os.path.exists(_KAGGLE_JSON) and not os.environ.get("KAGGLE_API_TOKEN"):
    with open(_KAGGLE_JSON) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line.startswith("export ") and "=" in _line:
                _, _kv = _line.split(" ", 1)
                _key, _val = _kv.split("=", 1)
                os.environ[_key.strip()] = _val.strip()
                break

if not os.environ.get("KAGGLE_API_TOKEN"):
    print("ERROR: KAGGLE_API_TOKEN not found.")
    print("  Set it via:  export KAGGLE_API_TOKEN=<your-token>")
    print("  Or place your token in ~/.kaggle/kaggle.json")
    sys.exit(1)

# ── Step 2: Corporate SSL bypass — same root cause as npm strict-ssl and OpenML.
#    Patch requests.Session at the CLASS level so kagglesdk's internally-created
#    sessions inherit verify=False.  This must happen BEFORE `import kaggle`
#    because the package calls api.authenticate() at import time.
ssl._create_default_https_context = ssl._create_unverified_context

import urllib3  # noqa: E402
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests  # noqa: E402

_orig_session_init = requests.Session.__init__


def _session_init_no_verify(self, *args, **kwargs):
    _orig_session_init(self, *args, **kwargs)
    self.verify = False


requests.Session.__init__ = _session_init_no_verify

# ── Step 3: Import kaggle — this triggers KaggleApi().authenticate() internally.
#    authenticate() calls _authenticate_with_access_token() first, which reads
#    KAGGLE_API_TOKEN from env (set above), then introspects the token via HTTPS.
#    The patched Session ensures that HTTPS call uses verify=False.
try:
    import kaggle  # noqa: E402
except Exception as e:
    print(f"ERROR: kaggle authentication failed: {e}")
    print("Check that your KAGGLE_API_TOKEN is valid and not expired.")
    sys.exit(1)

# kaggle.api is the pre-authenticated KaggleApi instance created by kaggle/__init__.py
api = kaggle.api


def download_competition(competition: str, dest: str):
    """Download all files for a Kaggle competition and unzip them."""
    os.makedirs(dest, exist_ok=True)
    print(f"\nDownloading competition '{competition}' -> {dest}/")
    print("  (Requires accepting competition rules on kaggle.com first)")
    api.competition_download_files(competition, path=dest, quiet=False)
    for fname in os.listdir(dest):
        if fname.endswith(".zip"):
            zip_path = os.path.join(dest, fname)
            print(f"  Extracting {fname}...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(dest)
            os.remove(zip_path)


def download_dataset(owner_slug: str, dest: str):
    """Download and unzip a Kaggle dataset."""
    os.makedirs(dest, exist_ok=True)
    print(f"\nDownloading dataset '{owner_slug}' -> {dest}/")
    api.dataset_download_files(owner_slug, path=dest, unzip=True, quiet=False)


if __name__ == "__main__":
    errors = []

    # Home Credit Default Risk — requires accepting rules at kaggle.com/c/home-credit-default-risk
    try:
        download_competition("home-credit-default-risk", "data/home_credit")
    except Exception as e:
        msg = str(e)
        print(f"\n  SKIPPED: {msg}")
        if "403" in msg:
            print("  Action required: accept competition rules at https://www.kaggle.com/c/home-credit-default-risk")
        errors.append(("home-credit-default-risk", msg))

    # LendingClub Loan Data (public dataset — no rules acceptance needed)
    try:
        download_dataset("wordsforthewise/lending-club", "data/lending_club")
    except Exception as e:
        msg = str(e)
        print(f"\n  FAILED: {msg}")
        errors.append(("lending-club", msg))

    print("\n── Download Summary ──────────────────────────────")
    if not errors:
        print("All datasets downloaded successfully.")
    else:
        for name, err in errors:
            print(f"  {name}: {err[:120]}")
    print("  data/home_credit/  -- application_train.csv  (primary training file)")
    print("  data/lending_club/ -- accepted_2007_to_2018Q4.csv.gz (primary file)")
    if errors:
        sys.exit(1)

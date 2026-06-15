from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
VECTOR_DIR = DATA_DIR / "vector_store"
OUTPUT_DIR = DATA_DIR / "outputs"
RUNS_DIR = OUTPUT_DIR / "runs"
OUTPUT_INDEX_FILE = OUTPUT_DIR / "index.json"
ASSET_DIR = ROOT_DIR / "assets"
GENERATED_ASSET_DIR = ASSET_DIR / "generated"
PLACEHOLDER_DIR = ASSET_DIR / "placeholders"
MASCOT_DIR = ASSET_DIR / "mascot" / "rabbit"

COURSES_FILE = DATA_DIR / "courses.json"
METADATA_FILE = DATA_DIR / "metadata.json"
LEARNING_PROFILES_FILE = DATA_DIR / "learning_profiles.json"

EMBEDDING_MODEL_NAME = "BAAI/bge-small-zh-v1.5"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
DEFAULT_TOP_K = 5


def ensure_directories() -> None:
    for path in [
        DATA_DIR,
        UPLOAD_DIR,
        VECTOR_DIR,
        OUTPUT_DIR,
        RUNS_DIR,
        GENERATED_ASSET_DIR,
        PLACEHOLDER_DIR,
        MASCOT_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)


def ensure_json_files() -> None:
    ensure_directories()
    defaults = {
        COURSES_FILE: "[]",
        METADATA_FILE: "[]",
        LEARNING_PROFILES_FILE: "{}",
    }
    for path, content in defaults.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")

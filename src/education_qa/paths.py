from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_CEVAL_DIR = DATA_DIR / "raw" / "ceval"
PROCESSED_DATASET = DATA_DIR / "processed" / "education_qa.jsonl"
VECTORSTORE_PATH = DATA_DIR / "vectorstore" / "education_tfidf.pkl"

RAW_TOURISM_DIR = DATA_DIR / "raw" / "tourism"
WIKIVOYAGE_DUMP_PATH = PROJECT_ROOT / "zhwikivoyage-latest-pages-articles.xml.bz2"
TRAVEL_REVIEWS_ZIP_PATH = PROJECT_ROOT / "travel+reviews.zip"
HOTEL_REVIEWS_ZIP_PATH = PROJECT_ROOT / "archive.zip"
TOURISM_DATASET = DATA_DIR / "processed" / "tourism_qa.jsonl"
TOURISM_VECTORSTORE_PATH = DATA_DIR / "vectorstore" / "tourism_tfidf.pkl"

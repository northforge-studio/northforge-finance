from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

SOURCE_DIR = DATA_DIR / 'source'
STAGING_DIR = DATA_DIR / 'staging'
ENRICHMENT_DIR = DATA_DIR / 'enrichment'
POSTING_DIR = DATA_DIR / 'posting'
REFERENCE_DIR = DATA_DIR / 'reference'

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

SOURCE_DIR = DATA_DIR / 'source'
STAGING_DIR = DATA_DIR / 'staging'
ENRICHMENT_DIR = DATA_DIR / 'enrichment'
POSTING_DIR = DATA_DIR / 'posting'
REFERENCE_DIR = DATA_DIR / 'reference'

TABLE_PATHS = {
    'TRIAL_BALANCE_SOURCE': (
        SOURCE_DIR / 'trial_balance.csv'
    ),
    'TRIAL_BALANCE_STAGING': (
        STAGING_DIR / 'trial_balance'
    ),
    'TRIAL_BALANCE_ENRICHMENT': (
        ENRICHMENT_DIR / 'trial_balance'
    ),
    'REF_FX_RATE': (
        REFERENCE_DIR / 'ref_fx_rate.csv'
    ),
    'REF_COUNTERPARTY': (
        REFERENCE_DIR / 'ref_counterparty.csv'
    ),
    'CFG_TRANSFORMATIONS': (
        REFERENCE_DIR / 'cfg_transformations.csv'
    ),
}

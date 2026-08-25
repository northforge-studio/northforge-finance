from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / 'data'

SOURCE_DIR = DATA_DIR / 'source'
STAGING_DIR = DATA_DIR / 'staging'
ENRICHMENT_DIR = DATA_DIR / 'enrichment'
REPORTING_DIR = DATA_DIR / 'reporting'
POSTING_DIR = DATA_DIR / 'posting'
SPEC_DIR = DATA_DIR / 'spec'

CSV_TABLE_LOCATIONS = {
    'TRIAL_BALANCE_SOURCE': (
        SOURCE_DIR / 'trial_balance.csv'
    ),
    'TRIAL_BALANCE_STAGING': (
        STAGING_DIR / 'trial_balance'
    ),
    'TRIAL_BALANCE_ENRICHMENT': (
        ENRICHMENT_DIR / 'trial_balance'
    ),
    'TRIAL_BALANCE_REPORTING': (
        REPORTING_DIR / 'trial_balance'
    ),
    'TRIAL_BALANCE_POSTING': (
            POSTING_DIR / 'trial_balance'
        ),
}

POSTGRES_TABLE_LOCATIONS = {
    'TRIAL_BALANCE_SOURCE': 'foundry_source.trial_balance',
    'TRIAL_BALANCE_STAGING': 'foundry_staging.trial_balance',
    'TRIAL_BALANCE_ENRICHMENT': 'foundry_enrichment.trial_balance',
    'TRIAL_BALANCE_REPORTING': 'foundry_reporting.trial_balance',
    'TRIAL_BALANCE_POSTING': 'foundry_posting.trial_balance',
}

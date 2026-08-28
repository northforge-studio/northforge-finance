from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class ReconResult:
    recon_result_id: UUID
    reconciled_at: datetime

    # Run identity: WORKFLOW_RUN_ID is the source (Interface/GL) workflow
    # being reconciled; PRODUCER_RUN_ID is the recon execution that
    # produced this row.
    workflow_run_id: UUID
    producer_run_id: UUID

    # Recon grain (RECON_KEYS, minus WORKFLOW_RUN_ID which is above)
    as_of_date: date
    entity_cd: str
    dept_cd: str
    branch_cd: str
    gl_account: str
    sub_account: str
    affiliate_cd: str
    product_cd: str
    book_cd: str
    source_cd: str
    accounted_currency: str

    # Balances
    interface_balance: Decimal
    gl_balance: Decimal
    difference_amount: Decimal


@dataclass(frozen=True)
class ReconRunResult:
    workflow_run_id: UUID
    producer_run_id: UUID
    result_count: int
    break_count: int
    results: tuple[ReconResult, ...]

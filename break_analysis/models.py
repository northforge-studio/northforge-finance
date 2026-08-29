from uuid import UUID
from enum import StrEnum
from datetime import date
from decimal import Decimal
from dataclasses import dataclass


class BreakAnalysisStatus(StrEnum):
    EXPLAINED = 'EXPLAINED'
    UNEXPLAINED = 'UNEXPLAINED'


class RootCause(StrEnum):
    REGISTRY_INVALID_SEGMENT = 'REGISTRY_INVALID_SEGMENT'


@dataclass(frozen=True)
class BreakRecord:
    recon_result_id: UUID
    workflow_run_id: UUID

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

    interface_balance: Decimal
    gl_balance: Decimal
    difference_amount: Decimal


@dataclass(frozen=True)
class BreakAnalysisResult:
    recon_result_id: UUID

    status: str
    root_cause: str | None
    explanation: str

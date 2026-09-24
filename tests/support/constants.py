from datetime import date, datetime, timezone
from uuid import UUID


BUSINESS_DT = date(2026, 1, 1)
AS_OF_DATE = date(2026, 1, 1)

TIMESTAMP = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)

WORKFLOW_RUN_ID = UUID('11111111-1111-1111-1111-111111111111')
PRODUCER_RUN_ID = UUID('22222222-2222-2222-2222-222222222222')

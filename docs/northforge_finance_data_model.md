# NorthForge Finance --- Synthetic Data Universe

> **Purpose:** Canonical, evolving description of the synthetic
> financial universe used by NorthForge Finance.
>
> This document is intended to serve both as repository documentation
> and as context for future modeling decisions. Update it whenever
> new dataclasses, entities, accounts, mappings, reference data, or
> accounting scenarios are introduced.

## 1. Business Universe

**NorthForge Financial Group** is a fictional global capital-markets
financial institution.

The synthetic universe is deliberately small. Its goal is not to
reproduce the size of a real bank, but to provide the minimum coherent
financial data needed to exercise NorthForge Finance end to end while
keeping every record understandable by hand.

Current legal/business entities:

- **NorthForge Markets US (`USM`)** --- US business with
  USD-denominated accounting activity.
- **NorthForge Markets Canada (`CAM`)** --- Canadian business with
  CAD-denominated source activity and cross-currency accounting
  behavior.

The universe is designed to expand over time to support additional
entities, currencies, accounts, counterparties, and dataclasses such as
Position.

## 2. Design Principles

The synthetic dataset follows these principles:

- **Minimal but behaviorally complete** --- add data only when it
  exercises a meaningful business or system behavior.
- **Transactionally explainable** --- every current-day movement and
  adjustment must correspond to an understandable double-entry
  accounting event.
- **Balanced by construction** --- Trial Balance data is not patched
  afterward with arbitrary balancing records.
- **Reusable business universe** --- Registry, Reference, Atlas, and
  Spec data should support multiple dataclasses rather than being
  Trial-Balance-specific where possible.
- **Store facts; derive transformations** --- source data contains
  business facts, while deterministic attributes should preferably be
  derived through Spec.
- **Mappings express accounting knowledge** --- Atlas converts
  source/business concepts into accounting/GL concepts.
- **Explicit lineage** --- Run Identity and posting lineage are
  retained so downstream reconciliation and break analysis can trace
  records back through Foundry.
- **Readable missing values** --- synthetic CSVs use empty strings for
  intentionally absent text and numeric zero only where zero is the
  actual financial value. Fake identifiers are not introduced merely
  to avoid emptiness.

## 3. Current End-to-End Architecture

```text
Business / Source Data
        |
        v
   Trial Balance
        |
        v
     Foundry
  +-------------+
  | Staging     |
  | Enrichment  | <---- Reference
  | Reporting   | <---- Atlas
  | Posting     | <---- Spec
  +-------------+
        |
        v
    Interface
        |
        v
        GL
        |
        v
  Reconciliation (Recon)
        |
        v
  Break Analysis        [planned]
```

Supporting domains:

- **Registry** --- canonical GL segment/master data.
- **Reference** --- operational reference data such as counterparties
  and FX rates.
- **Atlas** --- mappings and accounting rules.
- **Spec** --- deterministic transformations and file-layout
  definitions.
- **Core / Run Identity** --- workflow, execution, and dependency
  lineage.

## 4. Trial Balance Dataclass

Trial Balance is the first implemented NorthForge dataclass.

The current synthetic source contains:

- **7 logical Trial Balance records**
- **6 measures per record**
- **42 physical source rows**

The six measures are:

1.  Previous Day Balance
2.  Current Day Debit Balance
3.  Current Day Credit Balance
4.  Current Day EOD Balance
5.  Back-Value Adjusted Balance
6.  Adjusted Balance

For each logical record:

```text
Previous Day Balance
+ Current Day Debit
+ Current Day Credit
= Current Day EOD Balance

Current Day EOD Balance
+ Back-Value Adjustment
= Adjusted Balance
```

Credit-side values are represented as negative amounts in the synthetic
source dataset.

## 5. Source Trial Balance Contract

The simplified source contract contains business facts rather than
downstream-derived attributes.

---

Field Purpose

---

`AS_OF_DT` Financial effective/as-of date

`BUSINESS_DT` Processing/business date

`SRC_APP_CD` Source application code

`SRC_RECORD_ID` Stable logical source-record
identity

`SRC_ENTITY_CD` Source entity

`SRC_BOOKING_DEPT_CD` Source booking department

`SRC_ACCOUNT_ID` Source account

`SRC_ACCT_TYPE` Account classification such as
Asset, Liability, Revenue, Equity

`SRC_CLIENT_ID` Source client identifier when
applicable

`CPTY_REF_ID` Counterparty reference key when
applicable

`SRC_MEASURE_NM` One of the six TB measures

`SRC_MEASURE_CCY_CD` Currency of the source measure

`SRC_MEASURE_TRANS_AMT` Source measure amount

`POSTING_MEASURE_CCY_CD` Target posting/accounting currency
input

---

Derived fields such as normal account sign are not stored in the source
when they can be deterministically produced by Spec.

## 6. NorthForge Markets US --- Accounting Story

The US entity uses five logical Trial Balance records.

### 6.1 Opening Trial Balance

March 31 begins with the following balanced opening position:

Account Type Debit Credit

---

Cash Asset \$80,000
Fee Receivable Asset \$15,000
Client Payable Liability \$55,000
Fee Revenue Revenue \$20,000
Equity Equity \$20,000
**Total** **\$95,000** **\$95,000**

The historical transactions that produced these opening balances are
intentionally outside the current dataset. The opening Trial Balance is
treated as the valid financial position carried into the day.

### 6.2 Event US-1 --- Advisory Fee Earned on Credit

NorthForge performs \$5,000 of advisory work for a client but has not
yet received payment.

Two accounting facts arise:

- The client owes NorthForge \$5,000.
- NorthForge has earned \$5,000 of revenue.

Double entry:

```text
Fee Receivable (Asset)     DR   $5,000
Fee Revenue (Revenue)      CR   $5,000
```

Why:

- Asset increase -\> Debit.
- Revenue increase -\> Credit.

This is one \$5,000 economic event represented from two accounting
perspectives, not \$10,000 of economic activity.

### 6.3 Event US-2 --- Client Cash Received and Held

NorthForge receives \$10,000 from a client, but the cash still belongs
to the client.

Two accounting facts arise:

- NorthForge holds \$10,000 more cash.
- NorthForge owes the client \$10,000.

Double entry:

```text
Cash (Asset)               DR  $10,000
Client Payable (Liability) CR  $10,000
```

No revenue is created because NorthForge is holding the client's money
rather than earning it.

### 6.4 US End-of-Day Trial Balance

Account Opening Daily Activity EOD

---

Cash DR \$80K DR \$10K DR \$90K
Fee Receivable DR \$15K DR \$5K DR \$20K
Client Payable CR \$55K CR \$10K CR \$65K
Fee Revenue CR \$20K CR \$5K CR \$25K
Equity CR \$20K --- CR \$20K

End-of-day:

```text
Debits:
Cash                  90K
Fee Receivable        20K
                     ----
                     110K

Credits:
Client Payable        65K
Fee Revenue           25K
Equity                20K
                     ----
                     110K
```

The US Trial Balance remains balanced.

## 7. NorthForge Markets Canada --- Accounting Story

The Canada entity uses two logical Trial Balance records.

Its purpose is to introduce:

- CAD-denominated accounting activity
- intercompany/affiliate behavior
- back-valued adjustments
- future FX processing scenarios

### 7.1 Opening Position

```text
Trading Asset                    DR  40,000 CAD
Intercompany Payable             CR  40,000 CAD
```

The business interpretation is that NorthForge Canada holds a 40,000 CAD
asset funded by, or economically owed to, NorthForge US.

### 7.2 Event CA-1 --- Additional Funding from NorthForge US

NorthForge US provides another 10,000 CAD of funding to NorthForge
Canada.

For Canada:

```text
Trading Asset                    DR  10,000 CAD
Intercompany Payable             CR  10,000 CAD
```

The asset increases because Canada receives additional resources.

The liability increases because Canada now owes NorthForge US an
additional 10,000 CAD.

After the event:

```text
Trading Asset                    DR  50,000 CAD
Intercompany Payable             CR  50,000 CAD
```

### 7.3 Back-Valued Adjustment

NorthForge later determines that the funding should have been 11,000 CAD
rather than 10,000 CAD.

An additional 1,000 CAD is recognized:

```text
Trading Asset                    DR   1,000 CAD
Intercompany Payable             CR   1,000 CAD
```

Adjusted balances:

```text
Trading Asset                    DR  51,000 CAD
Intercompany Payable             CR  51,000 CAD
```

The adjustment is itself a balanced accounting event rather than an
arbitrary balancing amount.

### 7.4 Intercompany Identification

The Canadian payable references NorthForge US as its counterparty:

```text
SRC_CLIENT_ID = NF-US
CPTY_REF_ID   = CP-NF-US
```

This allows Reference + Atlas to identify the relationship as an
affiliate/intercompany relationship and populate the appropriate
accounting dimensions.

## 8. Seven Logical Source Records

The current logical records are:

---

Record Entity Department Source Type Currency Business
Account Meaning

---

`rec-1` USM TRD `1000` Asset USD Cash

`rec-2` USM FIN `1200` Asset USD Fee Receivable

`rec-3` USM TRD `2000` Liability USD Client Payable

`rec-4` USM FIN `4000` Revenue USD Fee Revenue

`rec-5` USM FIN `3000` Equity USD Equity

`rec-6` CAM TRD `1000` Asset CAD Canadian
Trading Asset

`rec-7` CAM TRD `2100` Liability CAD Intercompany
Payable to
NorthForge US

---

Each logical record expands to six physical source rows, one for each
Trial Balance measure.

## 9. Measure Values by Logical Record

### `rec-1` --- US Cash

```text
Previous Day Balance             +80,000 USD
Current Day Debit                +10,000
Current Day Credit                     0
Current Day EOD Balance          +90,000
Back-Value Adjustment                  0
Adjusted Balance                 +90,000
```

Driven by Event US-2.

### `rec-2` --- US Fee Receivable

```text
Previous Day Balance             +15,000 USD
Current Day Debit                 +5,000
Current Day Credit                     0
Current Day EOD Balance          +20,000
Back-Value Adjustment                  0
Adjusted Balance                 +20,000
```

Driven by Event US-1.

### `rec-3` --- US Client Payable

```text
Previous Day Balance             -55,000 USD
Current Day Debit                      0
Current Day Credit               -10,000
Current Day EOD Balance          -65,000
Back-Value Adjustment                  0
Adjusted Balance                 -65,000
```

Counterparty:

```text
SRC_CLIENT_ID = EXT-001
CPTY_REF_ID   = CP-EXT-001
```

Driven by Event US-2.

### `rec-4` --- US Fee Revenue

```text
Previous Day Balance             -20,000 USD
Current Day Debit                      0
Current Day Credit                -5,000
Current Day EOD Balance          -25,000
Back-Value Adjustment                  0
Adjusted Balance                 -25,000
```

Driven by Event US-1.

### `rec-5` --- US Equity

```text
Previous Day Balance             -20,000 USD
Current Day Debit                      0
Current Day Credit                     0
Current Day EOD Balance          -20,000
Back-Value Adjustment                  0
Adjusted Balance                 -20,000
```

This is an opening-balance account with no current-day activity.

### `rec-6` --- Canada Trading Asset

```text
Previous Day Balance             +40,000 CAD
Current Day Debit                +10,000
Current Day Credit                     0
Current Day EOD Balance          +50,000
Back-Value Adjustment             +1,000
Adjusted Balance                 +51,000
```

Driven by Event CA-1 and its back-valued correction.

### `rec-7` --- Canada Intercompany Payable

```text
Previous Day Balance             -40,000 CAD
Current Day Debit                      0
Current Day Credit               -10,000
Current Day EOD Balance          -50,000
Back-Value Adjustment             -1,000
Adjusted Balance                 -51,000
```

Counterparty:

```text
SRC_CLIENT_ID = NF-US
CPTY_REF_ID   = CP-NF-US
```

Driven by Event CA-1 and its back-valued correction.

## 10. Accounting Validation

The synthetic source is validated at the entity/currency level.

For both US/USD and Canada/CAD:

- Previous Day Balance nets to zero.
- Current Day Debit + Current Day Credit nets to zero.
- Current Day EOD Balance nets to zero.
- Back-Value Adjustments net to zero.
- Adjusted Balance nets to zero.

Each logical record also satisfies:

```text
Previous + Debit + Credit = EOD
EOD + Back-Value Adjustment = Adjusted
```

This makes the dataset both mathematically balanced and transactionally
explainable.

## 11. Registry

Registry represents NorthForge's canonical GL segment/master-data
universe.

Current segment types:

- Entity
- Department
- Branch
- Account
- Sub-account
- Affiliate
- Product
- Book
- Source

The simplified Registry deliberately excludes copied enterprise metadata
that does not contribute to current NorthForge behavior.

Registry records generally retain:

```text
BUSINESS_DT
SEGMENT_CODE
SEGMENT_DESCRIPTION
STATUS
```

Department additionally retains its meaningful relationships to Entity
and Branch.

Account retains a suspense indicator because suspense/default-account
scenarios are relevant to future GL and break-analysis behavior.

The Registry universe also reserves values for future Position
accounting, including concepts such as:

- Position Asset
- Position Liability
- Trial Balance Control
- Suspense

These do not need to appear in the current Trial Balance simply because
they exist in the Chart of Accounts.

## 12. Reference Data

Reference contains operational lookup data that is not itself a GL
segment.

### Counterparty

The simplified counterparty model contains:

```text
BUSINESS_DT
CPTY_REF_ID
CLIENT_ID
CPTY_NM
CLIENT_ID_TYPE
```

Current scenarios include:

- an external client/counterparty
- NorthForge US as an affiliate counterparty for the Canadian
  intercompany payable

### FX Rate

The FX model contains:

```text
CONVERSION_DT
FROM_CURRENCY
TO_CURRENCY
FX_RATE
```

The synthetic universe includes CAD/USD capability so Canadian activity
can exercise transaction-currency versus accounted-currency behavior.

## 13. Atlas

Atlas represents NorthForge's mapping and accounting-rule knowledge.

It maps source/business attributes into downstream accounting attributes
such as:

- GL Entity
- GL Department
- GL Branch
- GL Account
- GL Sub-account
- GL Affiliate
- GL Product
- GL Book
- GL Source
- CR/DR behavior
- posting rules and streams

The synthetic Atlas dataset was reduced to the minimum mappings needed
by the NorthForge universe.

Atlas intentionally retains its generic positional physical model:

```text
INPUT_COL1 ... INPUT_COL20
OUTPUT_COL1 ... OUTPUT_COL20
```

The surrounding metadata/audit/governance fields are being simplified
where they are not required by runtime behavior.

The generic structure is retained so Atlas can support future
dataclasses without creating mapping-specific physical tables.

## 14. Spec

Spec owns deterministic transformations and file-layout definitions.

Conceptually:

```text
Raw/business fact
       |
       | Spec transformation
       v
Derived deterministic attribute
```

For example:

```text
SRC_ACCT_TYPE = ASSET
        |
        v
NORM_ACCT_SIGN = DR
```

This prevents the source schema from carrying attributes that can be
reliably derived.

Spec also owns the Posting-to-Interface file layout.

Spec is an independent domain and its persistence belongs under the
`spec` schema/catalog rather than a Foundry-specific configuration
schema.

## 15. Foundry Processing Model

The current Trial Balance flow is:

```text
Source
  |
  v
Staging
  |
  v
Enrichment
  |
  v
Reporting
  |
  v
Posting
  |
  v
Interface
```

Current expected record counts for the seven-record dataset:

```text
Source       42
Staging      42
Enrichment    7
Reporting    42
Posting       7
Interface     7
```

The 42-to-7 transitions arise because the six measure rows belonging to
a logical Trial Balance record are aggregated/transposed where
appropriate.

### Natural record identity

Redundant zone-specific IDs were removed:

- `STAGING_ID`
- `ENRICHMENT_ID`
- `REPORTING_ID`

Trial Balance measure rows use:

```text
SRC_RECORD_ID + SRC_MEASURE_NM
```

as the natural row identity where needed.

`POSTING_ID` is retained because it identifies the final
accounting/posting record and crosses the Foundry-to-GL boundary.

## 16. Run Identity and Lineage

The Core Run Identity model remains independent of the synthetic-data
simplification.

It contains:

- workflow runs
- execution runs
- execution hierarchy
- retry relationships
- run dependencies
- producer/consumer lineage

Persisted Foundry zones carry:

```text
WORKFLOW_RUN_ID
PRODUCER_RUN_ID
```

This allows a downstream accounting or reconciliation record to be
connected back to the execution that produced it.

Run Identity is intentionally separate from business record identity
such as `SRC_RECORD_ID` and `POSTING_ID`.

## 17. Posting

Today, Trial Balance uses a Gross-Up posting stream.

Conceptually:

```text
7 eligible TB logical records
        |
        v
7 GROSS_UP posting records
        |
        v
7 Interface records
```

Posting contains the final accounting decision, including:

- GL segments
- CR/DR indicator
- amount/currency
- posting rule
- posting stream
- source lineage
- Run Identity

`POSTING_ID` remains the stable identity of the final accounting
instruction.

## 18. Interface

Interface is the clean system boundary between Foundry and the future
Mock GL.

The simplified Trial Balance Interface contains 28 fields covering three
concerns.

### Accounting dimensions

```text
ENTITY_CD
DEPT_CD
BRANCH_CD
GL_ACCOUNT
SUB_ACCOUNT
AFFILIATE_CD
PRODUCT_CD
BOOK_CD
SOURCE_CD
```

### Financial instruction

```text
CR_DR_IND

TRANSACTION_CURRENCY
TRANSACTION_AMOUNT

ACCOUNTED_CURRENCY
ACCOUNTED_AMOUNT

FX_RATE
```

This explicitly separates source/transaction currency from accounted
currency, which is important for CAD-to-USD scenarios.

### Lineage and processing identity

```text
WORKFLOW_RUN_ID
PRODUCER_RUN_ID
DATACLASS
TRANSACTION_NUMBER
LINE_NUMBER
FOUNDRY_RULE_ID
POSTING_ID
POSTING_STREAM
SRC_RECORD_ID
SRC_APP_CD
AS_OF_DATE
BUSINESS_DATE
```

`WORKFLOW_RUN_ID` is the selector used when reading/deleting Interface
data — not `BUSINESS_DATE`/`BATCH_ID`. V1 has exactly one producer
execution per output table per workflow, so `WORKFLOW_RUN_ID` alone is
sufficient. `PRODUCER_RUN_ID` (the producing execution's UUID) remains on
every row as exact producer lineage, ready for retries/re-executions to
use later without a schema remodel. `BUSINESS_DATE` remains the
financial/business date the data represents.

`AS_OF_DATE` remains the financial effective date.

## 19. Future Position Dataclass

Position is the next important planned dataclass.

The shared NorthForge universe is intentionally designed so Position can
reuse:

- entities
- departments
- branches
- accounts
- affiliates
- products
- books
- sources
- counterparties
- Atlas
- Spec
- Foundry
- Interface
- GL
- reconciliation

A future Position scenario is expected to support indirect posting such
as:

```text
Position
   |
   +-- GROSS_UP
   |      -> Position GL account
   |
   +-- TB_OFFSET
          -> Trial Balance control account
```

The Registry already reserves account concepts needed for this future
behavior.

## 20. Planned Mock GL

The Mock GL has not yet been finalized.

Its intended input is the generic Interface contract rather than
Foundry's internal zone schemas.

At minimum it is expected to:

- ingest Interface accounting instructions
- validate GL segments against Registry
- apply only explicitly GL-owned defaults
- reject invalid rows
- persist accepted accounting postings
- preserve enough Foundry lineage for reconciliation

Foundry-owned mapping/default behavior and GL-owned default behavior
should remain conceptually distinct so future break-analysis scenarios
can identify which system changed a value.

## 21. Recon (v1) and Planned Break Analysis

Recon is implemented for v1 with the following scope:

- Only the `TRIAL_BALANCE` dataclass is supported.
- Recon is scoped by a single `WORKFLOW_RUN_ID`: `recon.reconcile(workflow_run_id)`
  reads `interface.trial_balance` and `gl.posting` for that one workflow
  and compares them.
- Comparison is balance-level, not transaction-level: both sides are
  aggregated to `SUM(ACCOUNTED_AMOUNT)` over a common recon grain before
  being compared. `ACCOUNTED_AMOUNT` already carries the correct
  debit/credit sign, so `CR_DR_IND` plays no part in recon.
- The recon grain (`RECON_KEYS`) is `WORKFLOW_RUN_ID`, `AS_OF_DATE`,
  `ENTITY_CD`, `DEPT_CD`, `BRANCH_CD`, `GL_ACCOUNT`, `SUB_ACCOUNT`,
  `AFFILIATE_CD`, `PRODUCT_CD`, `BOOK_CD`, `SOURCE_CD`, and
  `ACCOUNTED_CURRENCY`.
- Results are persisted to `recon.result`, one row per recon grain, with
  `INTERFACE_BALANCE`, `GL_BALANCE`, and
  `DIFFERENCE_AMOUNT = INTERFACE_BALANCE - GL_BALANCE`. A grain present
  on only one side gets a zero balance on the other.
- Every recon execution runs under its own `ExecutionRun`
  (`component='recon'`, `operation='reconcile'`), created under the same
  `WORKFLOW_RUN_ID` being reconciled. `PRODUCER_RUN_ID` on each
  `recon.result` row identifies that recon execution, distinct from the
  Foundry/GL `PRODUCER_RUN_ID`s that produced the Interface/GL data being
  compared.

Recon deliberately does not yet own multi-dataclass or multi-workflow
scope: once further dataclasses exist and need to net together, recon
may need to leave the accounting `WORKFLOW_RUN_ID` grain for its own
grouping/scope concept. That evolution is intentionally deferred.

Break Analysis remains planned. The eventual flow is:

```text
Foundry Posting / Interface
             |
             | compare
             v
         GL Posting
             |
             v
       Reconciliation [aka Recon Report]
             |
             v
      Break Analysis Agent  [planned]
```

The synthetic universe should evolve by adding deliberate
accounting/system scenarios rather than arbitrary rows.

Examples of future break scenarios include:

- wrong GL department default
- missing/incorrect affiliate
- invalid GL segment
- suspense-account substitution
- FX mismatch
- missing posting
- duplicated posting
- incorrect CR/DR
- Position Gross-Up succeeds but TB Offset fails
- GL creates/defaults a different segment combination, producing
  related reconciliation rows

## 22. Evolution Rules for This Document

When extending the NorthForge universe:

1.  Add a business scenario first.
2.  Explain the double-entry accounting event in plain English.
3.  Identify the minimum new entities/accounts/counterparties/products
    required.
4.  Update Registry/Reference only when the new concept is genuinely
    reusable.
5.  Add Atlas mappings only for actual mapping behavior.
6.  Use Spec for deterministic derivations.
7.  Keep source data minimal.
8.  Ensure every accounting movement is transactionally explainable.
9.  Validate debit/credit balance at the appropriate accounting grain.
10. Document the expected Foundry, Interface, GL, and reconciliation
    effects.
11. Update this document alongside the dataset/code change.

## 23. Current Canonical Snapshot

```text
NorthForge Financial Group
|
+-- NorthForge Markets US (USM)
|   |
|   +-- Cash
|   +-- Fee Receivable
|   +-- Client Payable
|   +-- Fee Revenue
|   +-- Equity
|   |
|   +-- Event: $5K advisory fee earned on credit
|   |      DR Fee Receivable
|   |      CR Fee Revenue
|   |
|   +-- Event: $10K client cash received and held
|          DR Cash
|          CR Client Payable
|
+-- NorthForge Markets Canada (CAM)
    |
    +-- Trading Asset
    +-- Intercompany Payable to NorthForge US
    |
    +-- Event: 10K CAD additional funding from NorthForge US
    |      DR Trading Asset
    |      CR Intercompany Payable
    |
    +-- Back-valued correction: +1K CAD
           DR Trading Asset
           CR Intercompany Payable
```

Current Trial Balance:

```text
7 logical records
x 6 measures
= 42 physical source rows

US/USD opening TB        balanced
US/USD daily activity    balanced
US/USD EOD TB            balanced

Canada/CAD opening TB    balanced
Canada/CAD daily activity balanced
Canada/CAD EOD TB        balanced
Canada/CAD adjustment    balanced
Canada/CAD adjusted TB   balanced
```

This snapshot is the baseline from which the NorthForge Finance
synthetic universe should evolve.

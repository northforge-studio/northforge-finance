# NorthForge Finance

A financial data preprocessing platform.

## Components

- **Foundry** — the financial processing pipeline (staging, enrichment, reporting, and posting for Trial Balance data), including posting/gateway rule execution and transformation execution.
- **Atlas** — mapping and mapping-rule configuration, consumed by Foundry to resolve lookups, gateway rules, and posting rules.
- **Reference** — reference datasets (FX rates, counterparties) and reference-data enrichment, consumed by Foundry.
- **Core** — shared technical infrastructure, currently the generic `Store` / `CsvStore` I/O abstraction used by Atlas, Reference, and Foundry.

Foundry depends on Atlas and Reference. Atlas and Reference are independent of each other and of Foundry, and may depend on Core. Core has no dependency on any other component.

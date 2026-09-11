# NorthForge Finance

A financial data preprocessing platform.

## Components

- **Foundry** — the financial processing pipeline (staging, enrichment, reporting, posting, and interface for Trial Balance data), including posting/gateway rule execution and transformation execution.
- **Atlas** — mapping and mapping-rule configuration, consumed by Foundry to resolve lookups, gateway rules, and posting rules.
- **Reference** — reference datasets (FX rates, counterparties) and reference-data enrichment, consumed by Foundry.
- **Spec** — transformation and file-layout specifications that drive Foundry's per-zone transformation execution.
- **Registry** — GL segment definitions (entity, branch, department, account, and the rest) and segment validity lookups, consumed by GL and Break Analysis.
- **GL** — posts Foundry's Interface output as GL instructions, resolving segments via Registry and producing postings and rejections.
- **Recon** — reconciles Foundry's Interface output against GL postings and persists the comparison as recon results/breaks.
- **Break Analysis** — an LLM agent that groups related recon breaks into cases and investigates unexplained ones using Registry lookups as tools.
- **Workflow** — orchestrates the end-to-end business workflow across Foundry and GL, owning execution lifecycle and rollback; Recon runs separately against the same workflow.
- **Core** — shared technical infrastructure used across all other components: the generic `Store` (`CsvStore` / `PostgresStore`) I/O abstraction, run/execution tracking, logging, and database configuration.

Foundry depends on Atlas, Reference, and Spec. GL depends on Registry. Recon depends on GL. Break Analysis depends on GL and Registry. Workflow orchestrates Foundry and GL. Core has no dependency on any other component and underpins all of them.

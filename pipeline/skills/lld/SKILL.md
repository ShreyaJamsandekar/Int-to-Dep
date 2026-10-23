---
name: lld-generator
description: Transform an HLDHandoff component and Knowledge Graph slice into hexagonal ModuleSpecs, DataModelSpecs, TableSpecs, ErrorSpecs, and FunctionSpecs.
---

# LLD Generation & Closed-Loop Replan Skill (Stage L1 & Loop 4)

1. Freeze global OpenAPI/AsyncAPI contracts (`CON-xxx`), error envelopes (`ERR-xxx`), and table ownership (`TBL-xxx`) first.
2. Decompose each `SVC-xxx` component into hexagonal layers (`domain` <- `application` <- `adapters`/`api`/`worker`).
3. Map 100% of `TaskId` and `AcId` items to `ModuleSpec` and `FunctionSpec` nodes.
4. When invoked in Loop 4 (`L1-Replan` or `SPLIT_TASK`), emit a minimal `LLDPatch` replacing only the defective module(s) with disjoint file paths.

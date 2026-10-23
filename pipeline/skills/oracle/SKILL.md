---
name: oracle-writer
description: Write black-box acceptance tests from AcceptanceCriteria, API contracts, and the deterministic StateSeeder harness only.
---

# Independent Oracle Writer Skill (Stage L2b)

1. Read only Story `AcceptanceCriterion` items (`AC-xxx-yy`), `ApiContract` specs, and `StateSeeder` fixtures.
2. Never inspect internal `FunctionSpec` bodies or coder implementation files.
3. Emit one black-box test per `AC-xxx-yy` so the Knowledge Graph records 1:1 `(:Test)-[:VERIFIES]->(:AC)` edges.

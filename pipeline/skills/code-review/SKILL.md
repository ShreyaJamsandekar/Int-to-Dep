---
name: code-review
description: Review one generated change against its acceptance criteria, LLD module, ADRs and NFRs, and return evidence-backed findings as ReviewReport JSON.
---

# Code Review Skill (Stage L5)

1. **Understand:** Read the requirement text, ACs, LLD module spec, ADRs, and 2-hop blast-radius files from the Knowledge Graph.
2. **Review:** Check requirement_alignment, correctness, blast_radius, architecture, performance, test_adequacy, commit_consistency, and conventions.
3. **Prioritize:** Classify as `blocker`, `major`, or `minor`. Include AST `symbol_name`, exact `line`, verbatim `quote`, and `refs`.
4. **Secure:** Inspect scanner SARIF and check cross-module authorization, injection, secrets, and deserialization.
5. **Align:** Verify every AC has both implementing code and a meaningful assertion test.
6. **Re-verify:** Emit explicit `PriorFindingStatus` (`still_present: true|false`) for every `open_finding_id` in the package.

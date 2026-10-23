// Invariant 1: Every Acceptance Criterion must be verified by at least one Test
MATCH (a:AC) WHERE NOT (:Test)-[:VERIFIES]->(a) RETURN a.id;

// Invariant 2: Every Jira Task must be implemented by at least one Module
MATCH (t:Task) WHERE NOT (:Module)-[:IMPLEMENTS]->(t) RETURN t.id;

// Invariant 3: Every Module must be owned by a declared Component
MATCH (m:Module) WHERE NOT (m)-[:OWNED_BY]->(:Component) RETURN m.id;

// Invariant 4: Every public CodeSymbol must realize an approved FunctionSpec, DataModelSpec, TableSpec, or ErrorSpec
MATCH (s:CodeSymbol {public: true})
WHERE NOT (s)-[:REALIZES]->(:FunctionSpec)
  AND NOT (s)-[:REALIZES]->(:DataModelSpec)
  AND NOT (s)-[:REALIZES]->(:TableSpec)
  AND NOT (s)-[:REALIZES]->(:ErrorSpec)
RETURN s.id;

// Invariant 5: Zero unresolved blocker or major review findings at release
MATCH (f:Finding)
WHERE f.status IN ['open', 'fixed_pending_review']
  AND f.severity IN ['blocker', 'major']
RETURN f.id;

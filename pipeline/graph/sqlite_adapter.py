"""SQLite-persisted MVCC Knowledge Graph supporting serial & parallel synchronization."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from pipeline.contracts.base import sha256_obj
from pipeline.contracts.handoff import HLDHandoff
from pipeline.contracts.lld import LLDPack, LLDPatch, apply_lld_patch
from pipeline.contracts.tasks import TaskGraph
from pipeline.contracts.review import Finding



class _LockedConn:
    def __init__(self, conn: sqlite3.Connection, lock) -> None:
        self._conn = conn
        self._lock = lock

    def cursor(self):
        return self

    def execute(self, sql: str, params=()):
        with self._lock:
            return self._conn.execute(sql, params)

    def executescript(self, sql: str):
        with self._lock:
            return self._conn.executescript(sql)

    def commit(self) -> None:
        with self._lock:
            self._conn.commit()

ALLOWED_FRAMEWORK_EXPORTS = {"router", "Base", "app", "get_db", "settings"}


class SQLiteKnowledgeGraph:
    """
    Transactional Knowledge Graph backed by SQLite.
    Maintains MVCC `graph_epoch` increments on every state transition so parallel
    worktree agents can detect neighbor deltas and surgical LLD replans.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        import threading
        self._lock = threading.RLock()
        self.db_path = str(db_path)
        self._persist_path: Path | None = None if self.db_path == ":memory:" else Path(self.db_path)
        self._raw_conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._raw_conn.row_factory = sqlite3.Row
        self._conn = _LockedConn(self._raw_conn, self._lock)
        self._init_schema()
        if self._persist_path and self._persist_path.is_file():
            self._load_from_disk()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                run_id TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                stale INTEGER NOT NULL DEFAULT 0,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS edges (
                src TEXT NOT NULL,
                dst TEXT NOT NULL,
                rel TEXT NOT NULL,
                epoch INTEGER NOT NULL,
                PRIMARY KEY (src, dst, rel)
            );
            CREATE TABLE IF NOT EXISTS test_runs (
                test_id TEXT NOT NULL,
                commit_sha TEXT NOT NULL,
                passed INTEGER NOT NULL,
                epoch INTEGER NOT NULL,
                PRIMARY KEY (test_id, commit_sha)
            );
            """
        )
        cur.execute("INSERT OR IGNORE INTO meta (key, value) VALUES ('epoch', '0')")
        self._conn.commit()
        self._flush_to_disk()

    @property
    def epoch(self) -> int:
        row = self._conn.execute("SELECT value FROM meta WHERE key = 'epoch'").fetchone()
        return int(row["value"]) if row else 0

    def bump_epoch(self) -> int:
        new_ep = self.epoch + 1
        self._conn.execute("UPDATE meta SET value = ? WHERE key = 'epoch'", (str(new_ep),))
        self._conn.commit()
        self._flush_to_disk()
        return new_ep

    def upsert_node(
        self,
        node_id: str,
        kind: str,
        payload: dict[str, Any],
        run_id: str = "run-default",
        stale: bool = False,
    ) -> None:
        ep = self.epoch
        chash = sha256_obj(payload)
        self._conn.execute(
            """
            INSERT INTO nodes (id, kind, content_hash, run_id, epoch, stale, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                kind = excluded.kind,
                content_hash = excluded.content_hash,
                run_id = excluded.run_id,
                epoch = excluded.epoch,
                stale = excluded.stale,
                payload_json = excluded.payload_json
            """,
            (node_id, kind, chash, run_id, ep, 1 if stale else 0, json.dumps(payload, sort_keys=True)),
        )
        self._conn.commit()
        self._flush_to_disk()

    def add_edge(self, src: str, dst: str, rel: str) -> None:
        ep = self.epoch
        self._conn.execute(
            "INSERT OR REPLACE INTO edges (src, dst, rel, epoch) VALUES (?, ?, ?, ?)",
            (src, dst, rel, ep),
        )
        self._conn.commit()
        self._flush_to_disk()

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        row = self._conn.execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "kind": row["kind"],
            "content_hash": row["content_hash"],
            "run_id": row["run_id"],
            "epoch": row["epoch"],
            "stale": bool(row["stale"]),
            "payload": json.loads(row["payload_json"]),
        }

    def list_nodes(self, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            rows = self._conn.execute("SELECT * FROM nodes WHERE kind = ? ORDER BY id", (kind,)).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM nodes ORDER BY id").fetchall()
        return [
            {
                "id": r["id"],
                "kind": r["kind"],
                "epoch": r["epoch"],
                "stale": bool(r["stale"]),
                "payload": json.loads(r["payload_json"]),
            }
            for r in rows
        ]

    # --- Stage Loaders ---

    def load_handoff(self, handoff: HLDHandoff, run_id: str) -> int:
        for st in handoff.stories:
            self.upsert_node(st.story_id, "Story", st.dump_json_dict(), run_id)
            for t_id in st.task_ids:
                self.upsert_node(t_id, "Task", {"id": t_id, "story_id": st.story_id}, run_id)
                self.add_edge(t_id, st.story_id, "DERIVES_FROM")
            for ac in st.criteria:
                self.upsert_node(ac.id, "AC", ac.dump_json_dict(), run_id)
                self.add_edge(ac.id, st.story_id, "DERIVES_FROM")

        for nfr in handoff.nfrs:
            self.upsert_node(nfr.id, "NFR", nfr.dump_json_dict(), run_id)

        for adr in handoff.adrs:
            self.upsert_node(adr.id, "ADR", adr.dump_json_dict(), run_id)

        for term in handoff.domain_glossary:
            self.upsert_node(f"TERM-{term.canonical_snake}", "DomainTerm", term.dump_json_dict(), run_id)

        for inv in handoff.business_invariants:
            self.upsert_node(inv.id, "BusinessInvariant", inv.dump_json_dict(), run_id)
            for st_id in inv.applies_to_stories:
                self.add_edge(inv.id, st_id, "GUARDS")

        for comp in handoff.components:
            self.upsert_node(comp.id, "Component", comp.dump_json_dict(), run_id)
            for t_id in comp.linked_task_ids:
                self.add_edge(comp.id, t_id, "IMPLEMENTS")
            for n_id in comp.satisfies_nfrs:
                self.add_edge(comp.id, n_id, "SATISFIES")
            for a_id in comp.adr_ids:
                self.add_edge(comp.id, a_id, "DECIDED_BY")

        for dep in handoff.dependencies:
            if dep.target_component:
                self.add_edge(dep.source, dep.target_component, "DEPENDS_ON")

        return self.bump_epoch()

    def load_lld(self, lld: LLDPack, run_id: str) -> int:
        for con in lld.api_contracts:
            self.upsert_node(con.id, "Contract", con.dump_json_dict(), run_id)

        for mod in lld.modules:
            self.upsert_node(mod.id, "Module", mod.dump_json_dict(), run_id, stale=False)
            self.add_edge(mod.id, mod.component_id, "OWNED_BY")
            for t_id in mod.task_ids:
                self.add_edge(mod.id, t_id, "IMPLEMENTS")
            for ac_id in mod.ac_ids:
                self.add_edge(mod.id, ac_id, "SATISFIES")
            for dep_mod in mod.depends_on:
                self.add_edge(mod.id, dep_mod, "DEPENDS_ON")
            for fn in mod.public_interface:
                fn_id = f"{mod.id}::{fn.name}"
                self.upsert_node(fn_id, "FunctionSpec", fn.dump_json_dict(), run_id)
                self.add_edge(fn_id, mod.id, "OWNED_BY")
            for dto in mod.data_models:
                self.upsert_node(dto.id, "DataModelSpec", dto.dump_json_dict(), run_id)
                self.add_edge(dto.id, mod.id, "OWNED_BY")
            for tbl in mod.tables:
                self.upsert_node(tbl.id, "TableSpec", tbl.dump_json_dict(), run_id)
                self.add_edge(tbl.id, mod.id, "OWNED_BY")
            for err in mod.errors:
                self.upsert_node(err.id, "ErrorSpec", err.dump_json_dict(), run_id)
                self.add_edge(err.id, mod.id, "OWNED_BY")

        return self.bump_epoch()

    def apply_lld_replan(self, current_lld: LLDPack, patch: LLDPatch, run_id: str) -> tuple[LLDPack, list[str]]:
        """Apply surgical LLDPatch, mark 2-hop dependents stale, and bump epoch."""
        updated_lld = apply_lld_patch(current_lld, patch)
        stale_ids: list[str] = []
        for rem_id in patch.removed_module_ids:
            stale_ids.extend(self.mark_subgraph_stale(rem_id))
            self._conn.execute("DELETE FROM nodes WHERE id = ?", (rem_id,))
            self._conn.execute("DELETE FROM edges WHERE src = ? OR dst = ?", (rem_id, rem_id))
        for mod in patch.replaced_modules:
            stale_ids.extend(self.mark_subgraph_stale(mod.id))
        self.load_lld(updated_lld, run_id)
        for mod in patch.replaced_modules:
            self._conn.execute("UPDATE nodes SET stale = 1 WHERE id = ?", (mod.id,))
        self._conn.commit()
        self._flush_to_disk()
        return updated_lld, sorted(set(stale_ids))

    def load_task_graph(self, tg: TaskGraph, run_id: str) -> int:
        for bt in tg.tasks:
            self.upsert_node(bt.id, "BuildTask", bt.dump_json_dict(), run_id, stale=False)
            self.add_edge(bt.id, bt.module_id, "IMPLEMENTS")
            for dep in bt.depends_on:
                self.add_edge(bt.id, dep, "DEPENDS_ON")
        return self.bump_epoch()

    def register_test(self, test_id: str, ac_ids: list[str], file_path: str, run_id: str = "run-default") -> None:
        self.upsert_node(test_id, "Test", {"id": test_id, "file": file_path, "ac_ids": ac_ids}, run_id)
        for ac in ac_ids:
            self.add_edge(test_id, ac, "VERIFIES")

    def record_test_result(self, test_id: str, commit_sha: str, passed: bool) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO test_runs (test_id, commit_sha, passed, epoch) VALUES (?, ?, ?, ?)",
            (test_id, commit_sha, 1 if passed else 0, self.epoch),
        )
        self._conn.commit()
        self._flush_to_disk()

    def register_code_symbol(
        self,
        symbol_id: str,
        name: str,
        build_id: str,
        module_id: str,
        public: bool,
        realizes_id: str | None = None,
        run_id: str = "run-default",
    ) -> None:
        self.upsert_node(
            symbol_id,
            "CodeSymbol",
            {
                "id": symbol_id,
                "name": name,
                "build_id": build_id,
                "module_id": module_id,
                "public": public,
                "realizes_id": realizes_id,
            },
            run_id,
        )
        self.add_edge(symbol_id, module_id, "OWNED_BY")
        if realizes_id:
            self.add_edge(symbol_id, realizes_id, "REALIZES")

    def record_finding(self, finding: Finding, status: str, run_id: str = "run-default") -> None:
        payload = finding.dump_json_dict()
        payload["status"] = status
        self.upsert_node(finding.id, "Finding", payload, run_id)
        for ref in finding.refs:
            self.add_edge(finding.id, ref, "RAISED_ON")

    def record_risk_pattern(
        self,
        risk_id: str,
        module_id: str,
        rule: str,
        summary: str,
        run_id: str = "run-default",
    ) -> None:
        self.upsert_node(
            risk_id,
            "RiskPattern",
            {"id": risk_id, "module_id": module_id, "rule": rule, "summary": summary},
            run_id,
        )
        self.add_edge(risk_id, module_id, "GUARDS")

    # --- GraphPort Query Implementations ---

    def tests_verifying(self, ac_id: str) -> list[str]:
        rows = self._conn.execute(
            "SELECT src FROM edges WHERE dst = ? AND rel = 'VERIFIES' ORDER BY src",
            (ac_id,),
        ).fetchall()
        return [r["src"] for r in rows]

    def test_passed(self, test_id: str, commit: str) -> bool:
        row = self._conn.execute(
            "SELECT passed FROM test_runs WHERE test_id = ? AND commit_sha = ?",
            (test_id, commit),
        ).fetchone()
        return bool(row and row["passed"])

    def public_symbols_outside_lld(self, build_id: str) -> list[str]:
        rows = self._conn.execute("SELECT id, payload_json FROM nodes WHERE kind = 'CodeSymbol'").fetchall()
        unapproved: list[str] = []
        for r in rows:
            p = json.loads(r["payload_json"])
            if p.get("build_id") != build_id or not p.get("public"):
                continue
            if p.get("name") in ALLOWED_FRAMEWORK_EXPORTS:
                continue
            realizes = self._conn.execute(
                """
                SELECT n.kind FROM edges e
                JOIN nodes n ON e.dst = n.id
                WHERE e.src = ? AND e.rel = 'REALIZES'
                  AND n.kind IN ('FunctionSpec', 'DataModelSpec', 'TableSpec', 'ErrorSpec')
                """,
                (r["id"],),
            ).fetchone()
            if not realizes:
                unapproved.append(p["name"])
        return sorted(unapproved)

    def blast_radius_files(self, module_id: str) -> list[str]:
        """Return file paths of modules within 2 hops (callers and callees) of module_id."""
        hop1_rows = self._conn.execute(
            """
            SELECT dst AS neighbor FROM edges WHERE src = ? AND rel = 'DEPENDS_ON'
            UNION
            SELECT src AS neighbor FROM edges WHERE dst = ? AND rel = 'DEPENDS_ON'
            """,
            (module_id, module_id),
        ).fetchall()
        hop1 = {r["neighbor"] for r in hop1_rows}
        hop2: set[str] = set(hop1)
        for m in hop1:
            rows = self._conn.execute(
                """
                SELECT dst AS neighbor FROM edges WHERE src = ? AND rel = 'DEPENDS_ON'
                UNION
                SELECT src AS neighbor FROM edges WHERE dst = ? AND rel = 'DEPENDS_ON'
                """,
                (m, m),
            ).fetchall()
            hop2.update(r["neighbor"] for r in rows)
        hop2.discard(module_id)
        files: list[str] = []
        for mid in sorted(hop2):
            node = self.get_node(mid)
            if node and node["kind"] == "Module":
                files.append(node["payload"]["path"])
        return files

    def has_neighbor_delta_since_epoch(self, module_id: str, since_epoch: int) -> bool:
        """Check if any 1-hop neighbor module or its symbols/risks changed after `since_epoch`."""
        rows = self._conn.execute(
            """
            SELECT dst AS neighbor FROM edges WHERE src = ? AND rel = 'DEPENDS_ON'
            UNION
            SELECT src AS neighbor FROM edges WHERE dst = ? AND rel = 'DEPENDS_ON'
            """,
            (module_id, module_id),
        ).fetchall()
        neighbors = {r["neighbor"] for r in rows}
        for n_id in neighbors:
            node = self.get_node(n_id)
            if node and node["epoch"] > since_epoch:
                return True
            sym_changed = self._conn.execute(
                """
                SELECT 1 FROM edges e
                JOIN nodes n ON e.src = n.id
                WHERE e.dst = ? AND n.epoch > ?
                """,
                (n_id, since_epoch),
            ).fetchone()
            if sym_changed:
                return True
        return False

    def mark_subgraph_stale(self, root_node_id: str) -> list[str]:
        """Mark `root_node_id` and up to 2 hops of dependent nodes as stale=True."""
        visited: set[str] = {root_node_id}
        frontier: set[str] = {root_node_id}
        for _ in range(2):
            next_frontier: set[str] = set()
            for nid in frontier:
                rows = self._conn.execute(
                    "SELECT src FROM edges WHERE dst = ? AND rel IN ('DEPENDS_ON', 'IMPLEMENTS')",
                    (nid,),
                ).fetchall()
                for r in rows:
                    if r["src"] not in visited:
                        visited.add(r["src"])
                        next_frontier.add(r["src"])
            frontier = next_frontier

        for nid in visited:
            self._conn.execute("UPDATE nodes SET stale = 1 WHERE id = ?", (nid,))
        self._conn.commit()
        self._flush_to_disk()
        return sorted(visited)

    def clear_stale(self, node_id: str) -> None:
        self._conn.execute("UPDATE nodes SET stale = 0 WHERE id = ?", (node_id,))
        self._conn.commit()
        self._flush_to_disk()

    def stale_nodes(self, kind: str | None = None) -> list[str]:
        if kind:
            rows = self._conn.execute(
                "SELECT id FROM nodes WHERE stale = 1 AND kind = ? ORDER BY id", (kind,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT id FROM nodes WHERE stale = 1 ORDER BY id").fetchall()
        return [r["id"] for r in rows]

    def invariant_violations(self) -> dict[str, list[str]]:
        """Run the 5 deterministic graph invariant queries."""
        untested_ac = [
            r["id"]
            for r in self._conn.execute(
                """
                SELECT id FROM nodes WHERE kind = 'AC'
                  AND id NOT IN (SELECT dst FROM edges WHERE rel = 'VERIFIES')
                ORDER BY id
                """
            ).fetchall()
        ]
        unimplemented_tasks = [
            r["id"]
            for r in self._conn.execute(
                """
                SELECT id FROM nodes WHERE kind = 'Task'
                  AND id NOT IN (
                      SELECT e.dst FROM edges e
                      JOIN nodes m ON e.src = m.id
                      WHERE e.rel = 'IMPLEMENTS' AND m.kind = 'Module'
                  )
                ORDER BY id
                """
            ).fetchall()
        ]
        orphan_modules = [
            r["id"]
            for r in self._conn.execute(
                """
                SELECT id FROM nodes WHERE kind = 'Module'
                  AND id NOT IN (
                      SELECT e.src FROM edges e
                      JOIN nodes c ON e.dst = c.id
                      WHERE e.rel = 'OWNED_BY' AND c.kind = 'Component'
                  )
                ORDER BY id
                """
            ).fetchall()
        ]
        unapproved_symbols: list[str] = []
        for r in self._conn.execute("SELECT id, payload_json FROM nodes WHERE kind = 'CodeSymbol'").fetchall():
            p = json.loads(r["payload_json"])
            if not p.get("public") or p.get("name") in ALLOWED_FRAMEWORK_EXPORTS:
                continue
            ok = self._conn.execute(
                """
                SELECT 1 FROM edges e
                JOIN nodes n ON e.dst = n.id
                WHERE e.src = ? AND e.rel = 'REALIZES'
                  AND n.kind IN ('FunctionSpec', 'DataModelSpec', 'TableSpec', 'ErrorSpec')
                """,
                (r["id"],),
            ).fetchone()
            if not ok:
                unapproved_symbols.append(r["id"])

        unresolved_findings: list[str] = []
        for r in self._conn.execute("SELECT id, payload_json FROM nodes WHERE kind = 'Finding'").fetchall():
            p = json.loads(r["payload_json"])
            if p.get("status") in ("open", "fixed_pending_review") and p.get("severity") in ("blocker", "major"):
                unresolved_findings.append(r["id"])

        return {
            "untested_ac": untested_ac,
            "unimplemented_tasks": unimplemented_tasks,
            "orphan_modules": orphan_modules,
            "unapproved_public_symbols": sorted(unapproved_symbols),
            "unresolved_blocker_or_major_findings": sorted(unresolved_findings),
        }

    def snapshot_summary(self) -> dict[str, Any]:
        counts = {
            r["kind"]: r["cnt"]
            for r in self._conn.execute("SELECT kind, COUNT(*) AS cnt FROM nodes GROUP BY kind").fetchall()
        }
        edge_count = self._conn.execute("SELECT COUNT(*) AS cnt FROM edges").fetchone()["cnt"]
        return {
            "epoch": self.epoch,
            "node_counts": counts,
            "edge_count": edge_count,
            "stale_nodes": self.stale_nodes(),
        }


    def _flush_to_disk(self) -> None:
        if not self._persist_path:
            return
        with self._lock:
            dump = {
                "meta": [dict(r) for r in self._conn.execute("SELECT * FROM meta").fetchall()],
                "nodes": [dict(r) for r in self._conn.execute("SELECT * FROM nodes").fetchall()],
                "edges": [dict(r) for r in self._conn.execute("SELECT * FROM edges").fetchall()],
                "test_runs": [dict(r) for r in self._conn.execute("SELECT * FROM test_runs").fetchall()],
            }
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            self._persist_path.write_text(json.dumps(dump, indent=2), encoding="utf-8")

    def _load_from_disk(self) -> None:
        if not self._persist_path or not self._persist_path.is_file():
            return
        try:
            raw = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except Exception:
            return
        with self._lock:
            for m in raw.get("meta", []):
                self._conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (m["key"], m["value"]))
            for n in raw.get("nodes", []):
                self._conn.execute(
                    "INSERT OR REPLACE INTO nodes (id, kind, content_hash, run_id, epoch, stale, payload_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (n["id"], n["kind"], n["content_hash"], n["run_id"], n["epoch"], n["stale"], n["payload_json"]),
                )
            for e in raw.get("edges", []):
                self._conn.execute(
                    "INSERT OR REPLACE INTO edges (src, dst, rel, epoch) VALUES (?, ?, ?, ?)",
                    (e["src"], e["dst"], e["rel"], e["epoch"]),
                )
            for tr in raw.get("test_runs", []):
                self._conn.execute(
                    "INSERT OR REPLACE INTO test_runs (test_id, commit_sha, passed, epoch) VALUES (?, ?, ?, ?)",
                    (tr["test_id"], tr["commit_sha"], tr["passed"], tr["epoch"]),
                )
            self._conn.commit()

# Debugging Guide

How to inspect what happened inside a cycle — MongoDB collections, Compass queries, and debug scripts.

---

## Databases

| Database | Owner | Purpose |
|---|---|---|
| `checkpointing_db` | LangGraph | Saves graph state after every node so a crashed cycle can resume |
| `test_job_hunt` | App (tests) | Test data — profiles, cycles, opportunities |
| `job_hunt_db` | App (live) | Production data |

---

## `checkpointing_db` Collections

### `checkpoints`

One document per node that completed. Contains a full snapshot of `CycleState` at that point.

| Field | What it means |
|---|---|
| `thread_id` | The `cycle_id` — links this checkpoint to a cycle in `test_job_hunt.cycles` |
| `checkpoint_id` | Unique ID for this snapshot. ULID format — sorts chronologically |
| `parent_checkpoint_id` | Points to the previous checkpoint. `null` = first checkpoint in the cycle |
| `checkpoint.versions_seen` | Every node name listed here has already completed at this point |
| `checkpoint.channel_values` | Full `CycleState` at this exact moment — every key with its current value |
| `checkpoint.updated_channels` | Only the keys that changed in this step — faster to read than diffing `channel_values` |
| `checkpoint` | Binary msgpack — not readable in Compass. Use `debug_checkpoints_full.py` to decode |

### `checkpoint_writes`

One document per state key written by a node. More granular than `checkpoints`.

| Field | What it means |
|---|---|
| `thread_id` | The `cycle_id` |
| `checkpoint_id` | Groups all writes from the same node — all writes from one node share one `checkpoint_id` |
| `task_id` | Same as `checkpoint_id` for grouping — all writes from one node execution share one `task_id` |
| `task_path` | Which node wrote this. Format: `~__pregel_pull, <node_name>` |
| `channel` | The `CycleState` key that was written — e.g. `profile`, `report_path`, `token_spend` |
| `idx` | Order of writes within that node — `0` = first write, `1` = second, etc. |
| `type` | `msgpack` = real value written. `null` = `None` was written |
| `value` | The decoded value. Binary in Compass — use `debug_checkpoints.py` to decode |

**Routing channels** like `branch:to:run_discovery_match` are also written here. They are LangGraph's internal signals for which node runs next — not part of `CycleState`. You can ignore them when reading state data.

---

## Node → Code Mapping

Each `task_path` in `checkpoint_writes` maps to a function in `orchestrator/nodes.py`:

| `task_path` | Function | File |
|---|---|---|
| `~__pregel_pull, __start__` | LangGraph internal — fans out `make_initial_state()` into channels | `orchestrator/graph.py` |
| `~__pregel_pull, load_profile` | `load_profile_node()` | `orchestrator/nodes.py` |
| `~__pregel_pull, run_profile_agent` | `run_profile_agent_node()` | `orchestrator/nodes.py` |
| `~__pregel_pull, run_discovery_match` | `run_discovery_match_node()` | `orchestrator/nodes.py` |
| `~__pregel_pull, store_results` | `store_results_node()` | `orchestrator/nodes.py` |
| `~__pregel_pull, run_reporter` | `run_reporter_node()` | `orchestrator/nodes.py` |

---

## Compass Queries

### See all writes for a specific cycle

**Collection:** `checkpoint_writes`

```json
{ "thread_id": "<cycle_id>" }
```

**Sort:**
```json
{ "checkpoint_id": 1, "idx": 1 }
```

---

### See all writes from a specific node in a cycle

**Collection:** `checkpoint_writes`

```json
{ "thread_id": "<cycle_id>", "task_path": { "$regex": "run_reporter" } }
```

**Sort:**
```json
{ "checkpoint_id": 1, "idx": 1 }
```

Replace `run_reporter` with any node name: `load_profile`, `run_profile_agent`, `run_discovery_match`, `store_results`.

---

### Find incomplete cycles (crashed or still running)

**Collection:** `test_job_hunt.cycles`

```json
{ "completed_at": null }
```

---

### Find the last checkpoint a crashed cycle reached

**Collection:** `checkpoint_writes`

```json
{ "thread_id": "<cycle_id>" }
```

Sort by `checkpoint_id: -1` (descending). The `task_path` in the first result is the last node that wrote anything. If there are no writes after that node, it either crashed inside it or never handed off.

---

## Debug Scripts

### `scripts/debug_checkpoints.py`

Decodes `checkpoint_writes` and prints every document with the `value` field fully decoded.

```bash
# All cycles
python scripts/debug_checkpoints.py

# One specific cycle
python scripts/debug_checkpoints.py --thread <cycle_id>
```

### `scripts/debug_checkpoints_full.py`

Decodes `checkpoints` and prints every document with the `checkpoint` and `metadata` binary fields fully decoded.

```bash
# All cycles
python scripts/debug_checkpoints_full.py

# One specific cycle
python scripts/debug_checkpoints_full.py --thread <cycle_id>
```

---

## Reading a Cycle End-to-End

1. Find the `cycle_id` from `test_job_hunt.cycles` — check `completed_at` (null = not finished) and `errors`
2. Run `python scripts/debug_checkpoints.py --thread <cycle_id>`
3. Read documents in order of `checkpoint_id` + `idx`
4. Group by `task_path` — each group is one node
5. Within a group, `channel` + `value` tells you exactly what that node wrote to `CycleState`
6. `branch:to:<next_node>` at the end of each group tells you which node it handed off to

If a cycle crashed, the last `task_path` in the output is the last node that ran. Check that node's function in `orchestrator/nodes.py` to find the failure point.

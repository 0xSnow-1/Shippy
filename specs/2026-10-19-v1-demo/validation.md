# Validation - v1 demo runbook

## Definition of done

- [x] `scripts/demo.sh` runs with no arguments and no credentials.
- [x] The demo builds both Chroma collections from the committed corpus.
- [x] The demo serves the real app with an injected mock LLM and drives it over HTTP.
- [x] Each of the eight steps prints a real status code, a real JSON body, and a `PASS` or `FAIL` line.
- [x] The trap step refuses with a version-conflict reason on the default path.
- [x] The approve step lands a `fallback`-mode task with no `ASANA_PAT`.
- [x] The audit-trail step replays `run_created`, `approved`, `task_created` in order.
- [x] The script exits non-zero if any step fails and stops the server it started.
- [x] Temporary state stays outside the worktree and is removed on exit.
- [x] `README.md` documents the cold start, credentials, Bedrock switch, live ingestion, tests, and lint.
- [x] `--bookstack` is optional and fails with a clear message without Docker or a token.
- [x] No corpus JSON, `docker-compose.yml`, or phase 0-5 behavior changed.
- [x] No new runtime dependency was added to `pyproject.toml`.

## Gates

1. Demo: `scripts/demo.sh`
2. Full suite: `uv run pytest`
3. Lint: `uv run ruff check .`
4. Import smoke: `uv run python -c "import shippy"`
5. Worktree hygiene: `git status --porcelain` is clean after a demo run

## Run procedure

1. Run gates 1-5 from the project root.
2. Save the full `scripts/demo.sh` output outside the worktree.
3. Paste that real output into the final summary and the status line.
4. Confirm the PR is open and prints `draft: no`.

## Evidence

- Demo: `scripts/demo.sh` - `DEMO PASSED (8/8 steps)`, 2026-10-19.
- Full output: eight steps with real HTTP bodies, version-conflict refusal on step 5, fallback task on step 7, ordered trail on step 8.
- Full suite: `uv run pytest` - 52 passed, 2026-10-19.
- Lint: `uv run ruff check .` - clean, 2026-10-19.

## Failure triage

| Failure | Likely cause | Action |
|---|---|---|
| Server never healthy | Embedding model download stalled or port taken | Check `server.log` in the temp state dir; rerun once the model cache is warm |
| Step 3 quote empty | Mock key did not match the prompt | Confirm the question string and the `MOCK_RESPONSES` key in `scripts/demo_app.py` |
| Step 5 not a version conflict | Dual revisions missing from the index | Confirm `revised_markdown` handling in `build_index` |
| Step 5 no_match instead of conflict | Query drifted or floor changed | Re-run the retrieval probe; keep the restocking question verbatim |
| Step 7 mode is not fallback | `ASANA_PAT` leaked into the environment | `demo.sh` unsets it; check the parent shell |
| Chroma duplicate id | Revised chunks reused base ids | Revised ids must carry the `.rev2` suffix |
| `--bookstack` seed fails | Token missing or BookStack not ready | Check `.env` and the compose status; the wait loop is 180s |
| Demo leaves files in the worktree | State path pointed inside the repo | Keep `SHIPPY_DEMO_CHROMA` and `SHIPPY_DEMO_DB` under `mktemp -d` |

## Merge criteria

- [x] All gates pass.
- [x] The full demo output is in the final summary.
- [x] Proof in the final summary includes the real `DEMO PASSED (8/8 steps)` line.
- [x] PR is open, ready for review, and prints `draft: no`.
- [x] The README alone is enough to run the demo.

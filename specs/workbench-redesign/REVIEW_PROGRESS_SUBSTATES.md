# Review: Research Progress Substates

## Spec Compliance

- Added one compact current substate under the active top-level research stage: Capture, Interpret, Research, Compare, or Brief.
- Substates are derived from public job status and progress messages, not raw backend traces or provider payloads.
- Added finer LangGraph progress messages around safety screening, product clarity, search planning, source search, normalization, scoring, mismatch checks, grouping, and explanation.
- Kept the UI as a stable stage rail rather than adding chat-like status narration or decorative loading effects.

## Acceptance Criteria Coverage

- Research pipeline stages still render from job status.
- Active research substates render from job progress messages.
- Long-running source research now shows the current specific progress, such as source plan, live source search, or normalization, without listing every substep at once.
- The single-candidate result no longer duplicates the same product in both best-match and browser sections.

## Verification

- `python3 -m py_compile backend/app/agent/graph.py`
- `docker compose exec -T api sh -lc 'PYTHONPATH=/app pytest tests/test_v2_agent_runner.py -q'`
- `docker compose exec -T api sh -lc 'PYTHONPATH=/app pytest -q'`
- `docker compose exec -T frontend npm run build`
- `docker compose --profile test run --build --rm frontend-e2e npx playwright test e2e/workbench.spec.ts`
- `git diff --check`

## Remaining Manual Check

- Review the stage rail in a live run to confirm the single current substep feels useful and calm.

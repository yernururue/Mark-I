# Task 04 — assessment, notification significance and escalation

## Objective

Apply the Stage-1 structured AI result correctly: proficiency is evidence for a skill update; significance is evidence for a notification decision. Compute escalation flags deterministically from persisted facts and pass only flags that the decision policy supports.

## Scope after approval

1. Preserve the validated analyzer fields `proficiencyAssessment` (0–10) and `significanceScore` (1–10) as separate values through worker orchestration.
2. Read the prior skill state before update and retain the resulting score. Use only proficiency for `SkillService.update_skill` with the existing TRD weighting semantics.
3. Calculate flags after the observation/skill facts are available:
   - `new_concept`: no existing skill/concept before this event;
   - `skill_regression`: resulting score falls by at least 1.0 from prior score;
   - `milestone_reached`: score crosses 5 or 8 upward;
   - `repeated_error`: the configured recent window contains three negative observations for the same concept, including the current one only once.
4. Filter/validate flags against `ESCALATION_RULES`; delete the unsupported `negative_sentiment` worker path rather than silently sending it to the decision service.
5. Feed only significance plus supported flags to `DecisionService.evaluate_and_log`, retain explainable decision data, and rely on task-02 idempotency for a single decision/notification outcome.

## Files expected to change after approval

- `workers/github_worker.py` and focused pure escalation helper(s);
- observation/skill/decision services only for required read/query seams that preserve existing public contracts;
- analyzer-result and PICT/worker regression tests.

## Tests

- high significance with middling proficiency does not inflate skill score;
- high proficiency with low significance updates skill but follows normal notification threshold;
- each supported flag is produced at its boundary and not produced just outside it;
- PICT intensity matrix remains passing and escalation forces notification;
- `negative_sentiment` is never sent as a flag;
- repeated delivery cannot re-cross milestones, add another repeated-error observation, log another decision, or re-send Telegram;
- strict Stage-2 xfails become normal passing tests only in the corresponding implementation commits.

## Acceptance criteria

- Observation metadata contains delivery correlation; skill and decision use their distinct validated inputs.
- All four supported escalation flags have deterministic tests, and no unsupported flag affects an outcome.
- Full Stage-2 acceptance, locked Python 3.11 suite and Docker worker smoke are passing before tracker promotion.

## Rollback boundary

Keep assessment wiring, escalation helper, decision invocation and tests together. Do not alter thresholds, user intensity product semantics or shared documentation in this task.

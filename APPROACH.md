# Approach Notes

This is a working document. Keep notes concise while the product is being defined and built; finalize the prose before submission.

## What We Built

- TBD after problem selection and core workflow approval.

## Why This Problem

- Current direction under consideration: choose between a focused AI mini-app and rebuilding a hard feature with AI.
- Selection criteria: prefer a real personal pain point or admired feature where AI is a core lever, especially when the workflow requires contextual decision-making, condition-specific logic, and natural or messy input data.

## Key Decisions and Tradeoffs

- Use spec-driven development: Spec Architect defines `/specs`, Software Engineer implements from approved specs, Review Agent checks compliance.
- Treat AI as a bounded product component, not a generic chat sidebar.
- Favor reliable, inspectable AI behavior: structured outputs, validation, explicit uncertainty, editable results, and clear failure states.
- Optimize for one polished end-to-end flow over breadth.

## What We Intentionally Left Out

- TBD per approved spec.
- Default bias: cut features that do not improve usefulness, reliability, or demo clarity.

## What Breaks First Under Pressure

- AI latency, provider failures, invalid model output, hallucinations, and missing API keys are expected pressure points.
- Product scope may break if the workflow expands beyond one clear user job.

## What We Would Build Next

- TBD after the first complete workflow is implemented and reviewed.

## Decision Log

- Initial development process: use spec-driven workflow with explicit Spec Architect, Software Engineer, Acceptance Test Generator, and Review Agent phases.

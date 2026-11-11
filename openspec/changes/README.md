# OpenSpec Changes Directory

This directory contains active and archived OpenSpec change proposals for PodSeek.

## OpenSpec Workflow

All non-trivial feature additions, architectural refactors, and behavioral modifications must follow the OpenSpec specification-driven development workflow:

1. **Propose (`openspec/changes/<change-name>/`):**
   - Create a dedicated change directory: `openspec/changes/<change-name>/`.
   - `proposal.md`: Problem statement, proposed solution, user impact, and capability scope.
   - `tasks.md`: Phased, checkable implementation plan.
   - `design.md` (optional): Detailed architecture, sequence diagrams, and schema definitions for complex changes.
   - `specs/<capability>/spec.md`: Delta specifications using `## ADDED Requirements`, `## MODIFIED Requirements`, or `## REMOVED Requirements`.

2. **Branch & Implement:**
   - Work on a dedicated git branch (`feat/<change-name>` or `fix/<change-name>`).
   - Validate specifications continuously:
     ```bash
     npx @fission-ai/openspec validate --all --strict --no-interactive
     ```
   - Implement the code and unit tests matching the spec deltas.

3. **Verify & Review:**
   - Run linter and offline unit test suite:
     ```bash
     ruff check .
     pytest -v
     ```
   - Open a Pull Request targeting `main` with the PR template completed.

4. **Archive on Merge:**
   - Once merged, the change proposal is archived into `openspec/changes/archive/` using:
     ```bash
     npx @fission-ai/openspec archive <change-name>
     ```
   - Main capability specifications under `openspec/specs/<capability>/spec.md` are updated to reflect the new system baseline.

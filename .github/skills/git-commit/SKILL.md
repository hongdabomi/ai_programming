---
name: git-commit
description: Reviews the current Git changes, runs relevant checks, and creates a focused commit. Use when the user explicitly asks to commit changes or invokes this skill.
---

# Git commit

1. Confirm the user explicitly requested a commit. Do not infer commit approval from a request to edit files, review changes, or prepare a commit message.
2. Inspect `git status --short --branch` and the complete diff, including untracked files that are in scope. Never discard or overwrite user changes.
3. Check for secrets, generated files, unrelated edits, and accidental personal data. Stop and report anything sensitive or ambiguous; do not stage it.
4. Run the smallest relevant tests or validation commands and report failures. Do not claim checks passed if they were not run.
5. Stage only the reviewed, intended paths by name. Review the staged diff and status again before committing.
6. Write a concise imperative commit message, preferably using the Conventional Commits form (`type(scope): summary`) when it fits.
7. Create the commit only after the above checks. Do not push or create a Pull Request as part of this skill.
8. Report the commit hash, message, included paths, and validation results. If a safe, scoped commit cannot be made, stop and explain why.

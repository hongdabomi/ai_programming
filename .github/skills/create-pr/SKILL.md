---
name: create-pr
description: Opens a GitHub Pull Request for a reviewed, committed branch using the GitHub CLI. Use when the user explicitly asks to create a PR or invokes this skill.
---

# Create a Pull Request

1. Confirm the user explicitly requested PR creation. A request to prepare a PR, review changes, or write a description alone is not approval to publish one.
2. Inspect the current branch, `git status --short --branch`, relevant commits and diff, configured remote, and `gh auth status`. Do not expose credentials or tokens.
3. Ensure the working tree is clean and the intended changes are committed. If there are uncommitted changes, review and report them; do not commit them as an implicit part of PR creation.
4. Check whether a PR already exists for the branch and identify the repository's default base branch. Use `gh` CLI for GitHub operations.
5. If the branch is not already available on the remote or needs a push/update, stop and ask for explicit permission to push. Do not push implicitly.
6. Summarize the proposed base, title, and body. If the target or scope is unclear, ask the user before creating the PR.
7. Once authorized and prerequisites are satisfied, create the PR with `gh pr create`, using a concise summary and a test/validation section that reflects only checks actually run. Do not include secrets or claim unverified results.
8. Report the PR URL, base and head branches, and any checks not run. Do not merge the PR.

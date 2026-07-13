# Agent Instructions

This repository is an interactive research project progression template for Codex / Claude Code.

All coding agents and AI assistants must read and follow `.research_agent/AGENTS.md` and relevant sections of `PROJECT_RULES.md` before generating prompts, executing tasks, writing results, or suggesting Git commits.

Core rules:

- This project is not a fully autonomous agent.
- Do not call OpenAI, Anthropic, Codex, Claude, or other remote LLM APIs.
- Do not automatically generate the next prompt after completing a round.
- Do not automatically execute a generated prompt.
- Do not automatically commit or push without explicit user confirmation.
- Keep every formal round traceable through `ans_qes/promptn.md` and `ans_qes/resultn.md`.
- After generating a prompt, stop and wait for user review.
- After executing a prompt and writing a result, stop and wait for user review.
- After suggesting or completing a commit, stop and wait for the user's next instruction.

Scientific project principles:

- Treat downstream repositories as formal research projects, not demos.
- Prefer reproducible, modular, maintainable code.
- Keep data processing, feature construction, modeling, evaluation, interpretation, and visualization decoupled.
- Avoid hard-coded paths and one-off scripts.
- Preserve strict benchmark discipline and avoid data leakage.
- Keep results traceable to data, code, configs, environment, commands, and Git commits.
- Favor scientific rigor and publication-quality evidence over quick completion.
- Use low-context mode by default: run context summaries, search before reading, inspect bounded excerpts, and avoid loading logs, generated outputs, large manifests, notebooks, or many old result files unless necessary.

Project-level research code rules:

- `PROJECT_RULES.md` is mandatory.
- Read it with low-context discipline: use `rg` to find relevant sections, then inspect bounded excerpts.
- Do not bypass reproducibility, leakage checks, benchmark fairness, interpretability, documentation, or logging requirements merely to finish a round quickly.
- Newly generated explanatory Markdown documents should default to Chinese unless the user, publication target, or collaborator context requires English.

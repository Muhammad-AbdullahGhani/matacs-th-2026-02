# MATACS-TH-2026-02: AI Proposal Triage Design

- **Name:** Muhammad Abdullah Ghani
- **Reference:** MATACS-TH-2026-02
- **Role:** Associate Software Developer
- **Time actually spent:** 60 minutes

## Summary

The design is built on one rule: **AI reads, code decides.** AI turns each proposal into structured facts with quoted evidence. Plain code applies the mandatory checks, scores, and ranks, using criteria the admin defines. A person reviews flagged items and makes the final award decision. Proposal text is treated as untrusted data.

Result on the sample set: A ranked 1, E ranked 2, C flagged (hidden instruction aimed at AI reviewers), D flagged (no timeline), B ineligible (licence not held by the bidder).

## Files

- [WRITEUP.md](WRITEUP.md): answers to the five questions (under 1,000 words)
- [diagram/process-flow.png](diagram/process-flow.png): flow diagram from upload to ranked output showing AI, rule-based, and human checkpoint steps
- [PROMPTS.md](PROMPTS.md): extraction and reason-writing prompts
- [ranking.json](ranking.json): expected ranking of proposals A to E
- [prototype/](prototype/): optional script and data fixtures. Run `python prototype/triage.py` (mock mode, no API key needed)
- [.env.example](.env.example): environment variable template for live mode API keys
- [.gitignore](.gitignore): prevents committing API keys, environments, and confidential brief material

## How I used AI tools

I used Claude to help brainstorm edge cases, structure the process flow, and draft initial prompt schemas and prototype fixtures. I reviewed and verified the scoring formulas, wrote the risk mitigations, and verified that the prototype's output matched `ranking.json`.

One place I disagreed with the AI: during early architecture drafting, the AI proposed having the LLM evaluate and assign numerical scores to proposals directly. I rejected this approach and corrected the design to enforce strict "AI reads, code decides" separation—restricting the LLM exclusively to extracting structured facts paired with exact source quotes, while executing all pass/fail checks, mathematical scoring, and ranking deterministically in code. This eliminates score drift across repeated runs, neutralizes adversarial prompt injection attempts (such as the hidden instruction in Proposal C), and guarantees a reproducible, auditable record.

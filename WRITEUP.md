# Write-up: AI Proposal Triage Design (MATACS-TH-2026-02)

**Core idea:** AI reads, code decides. AI turns messy proposal text into structured facts with quoted evidence. Everything that affects pass/fail, scores or rank is plain code using admin-defined criteria. A human makes the award decision. See `diagram/process-flow.png`.

## 1. AI vs. rules

**AI is used for two things:**
- Reading each proposal and extracting facts into a fixed JSON format, each with a supporting quote. Proposals are free-form prose with varied wording, which rules handle badly.
- Writing the one-line reason for each position, using numbers that code has already produced.

**Plain code handles:** file upload, text extraction, a keyword scan for manipulation, checking that quotes exist in the source, mandatory pass/fail gates, budget and schedule limits, score formulas, weights, ranking and the audit log.

**Why the line is there:** AI is good at understanding language. Code is better where a decision must be identical every time, explainable, and impossible to talk into a different answer.

## 2. Consistency and explainability

- Scoring is a pure function: same extracted facts plus the same criteria version gives the same score. There is no AI in the maths.
- The only source of drift is extraction. I reduce it with a fixed schema, the lowest randomness setting, and a pinned prompt and model version. Extracted facts are stored, so ranking the same files twice reuses them and returns an identical result. A fresh re-extraction might word things differently, so it is compared against the stored one and differences are flagged, not silently swapped in.
- Reviewers see, for each proposal: every criterion, the extracted value, the quote from the proposal, the points earned and the weight. The one-line reason is generated from that table and checked so it only uses numbers from it.
- Example formulas for this category (admin-editable parameters): experience counts qualifying installs up to 15; price is the lowest eligible price divided by the bid's price; timeline is 40 points at 16 weeks rising to 100 at 8 weeks; warranty is half panel years (cap 25) and half workmanship years (cap 12); team is 25 points each for named lead, crew, safety plan and monitoring plan. Ties go to the lower price.

## 3. Human in the loop

- **Flagged queue:** missing data, manipulation signs or failed evidence checks. The reviewer can request clarification, correct a value (with the quote that supports it) or exclude the bid.
- **Ineligible list:** the reviewer sees the reason and can overturn it only with a written reason, for example after checking the licence number in the official registry.
- **Final ranking:** the reviewer confirms, reorders or overrides, and records the award. The tool never awards anything.
- **Logged:** uploader and file hash, extracted text, prompt and model version, raw AI output, validated facts, scan results, criteria version, gate results, score breakdown, ranking, reasons, and every human edit with user, time and written reason.

## 4. Changing criteria

Criteria are versioned. An edit creates a new version and never overwrites the old one. Every scoring run records its version.
- **Weight or parameter change:** re-score from the stored facts. This is instant and needs no AI.
- **New or reworded criterion:** re-run extraction for that criterion only, then re-score.
- Old results stay visible, labelled "scored under v3, current is v4". Ranked lists never mix versions, and award confirmation is blocked until the list is re-scored (or the reviewer deliberately keeps the old version, which is logged). Confirmed awards are locked.
- The admin sees a preview of how rank order would change before saving.
- Price is scored relative to the cheapest eligible bid, so adding or removing a proposal can also shift scores. This is recorded in the run.

## 5. Risks

| Risk | Safeguard |
|---|---|
| Wrong extraction | Every value needs a word-for-word quote. Code checks the quote exists in the source. Unit and currency checks. Reviewer sees the quote beside the value. |
| Made-up facts | Null or "not stated" is the preferred answer. Code never fills gaps. Missing data is flagged, not guessed (D has no timeline). |
| Manipulation | Proposal text is untrusted data inside delimiters, with a rule to ignore instructions in it. A keyword scan plus the AI's own flag catch attempts. The AI has no tools and cannot set scores, and code ignores claims such as "pre-approved". C is flagged for a human. |
| Bias | Only criteria facts are scored; name, size and location are not. Formulas are the same for every bidder. Audit logs allow pattern checks. Humans decide. |
| Cost | One extraction per proposal, cached. Re-scoring is free. Page limits. Short outputs. |
| Other | Scanned PDFs go through OCR, and empty text is flagged. No real personal data. Licence numbers are not verified by AI, so a human checks the registry. |

## Sample set

| Proposal | Result | Why |
|---|---|---|
| A | Rank 1 (91.5) | Most installs, good price, 12 weeks |
| E | Rank 2 (79.2) | Best warranty and monitoring, fewer installs |
| C | Flagged | Hidden instruction aimed at AI reviewers, ignored and sent to a human. About 71 on merit |
| D | Flagged | No timeline, so it cannot be scored fairly |
| B | Ineligible | Licence not held by the bidder, so cheapest price is irrelevant |

**Assumptions:** experience dates given only by year are accepted as stated. C's start year may include an install outside the 5-year window, so a reviewer should check. Team items not stated earn no credit. Missing information (D) is flagged, not treated as a failure.

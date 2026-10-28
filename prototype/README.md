# Prototype: AI-Assisted Proposal Triage

This prototype implements the "AI reads, code decides" pipeline described in the design write-up.

## Modes

1. **Mock Mode (Default, No API Key Required)**
   Uses pre-extracted structured facts from `mock_extractions.json` to run the rule-based verification, gates, mathematical scoring, and ranking.
   ```bash
   python triage.py
   # or from project root:
   python prototype/triage.py
   ```
   To output ranking JSON:
   ```bash
   python prototype/triage.py --out output.json
   ```

2. **Live Mode (Anthropic API)**
   Calls Claude using `extraction_prompt.txt` to extract structured facts from proposal text files in a specified directory.
   ```bash
   pip install -r requirements.txt
   export ANTHROPIC_API_KEY="your-api-key"
   python prototype/triage.py --live --texts-dir /path/to/proposal_texts
   ```

## Files in Prototype
- `triage.py`: Main execution script performing gating, scoring, ranking, and validation.
- `criteria.json`: Category criteria, weights, hard limits, and parameters as configured by an admin.
- `extraction_prompt.txt`: System prompt for LLM fact extraction with strict security guardrails.
- `mock_extractions.json`: Sample extracted data fixtures for Proposals A through E.
- `requirements.txt`: Python dependencies (`anthropic`).

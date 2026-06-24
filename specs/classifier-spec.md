# Spec: `classify_safety_tier()`

**File:** `safety.py`
**Status:** Implemented

---

## Purpose

Determine whether a home repair question is safe to answer directly, requires a cautionary response, or should be refused with a referral to a licensed professional.

---

## Input / Output Contract

**Input:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |

**Output:** `dict`

| Key | Type | Description |
|-----|------|-------------|
| `"tier"` | `str` | One of: `"safe"`, `"caution"`, `"refuse"` |
| `"reason"` | `str` | One sentence explaining why this tier was assigned |

---

## Design Decisions

---

### Tier definitions

**safe:**
```
Routine maintenance or minor repair with basic tools where the worst possible outcome is cosmetic damage or a broken fixture — no risk of fire, flood, injury, or structural damage, and no permit required.
```

**caution:**
```
A repair involving water or electrical systems that a motivated homeowner can complete, where mistakes are costly (leaks, broken fixtures, tripped breakers) but NOT catastrophic — component swap at an existing location, no new wiring or pipe runs required, no permit typically needed.
```

**refuse:**
```
Any repair where an amateur mistake could cause fire, flooding, structural failure, serious injury, or death — including any work that opens the electrical panel, runs new wire or pipe, involves gas lines, requires a permit, modifies load-bearing structure, or replaces whole-system equipment like a water heater.
```

---

### Classification approach

The LLM is given precise tier definitions plus explicit rules for the most important edge cases (replacing-vs-adding in electrical, gas always refuse, framing doesn't change the tier). It uses chain-of-thought implicitly since `temperature=0` and the definitions are precise enough to apply mechanically.

Few-shot examples were considered but not needed — the tier definitions are specific enough that the model applies them consistently without examples. The key was making the "replacing existing vs. adding new" distinction explicit in the prompt text rather than relying on the model to infer it.

For genuinely ambiguous questions near the caution/refuse boundary, the prompt instructs the model to classify based on what the repair actually requires, not how the user frames it. If a question could go either way, the prompt's bias toward refuse for anything that could cause fire/injury/death pushes it to the safer side.

---

### Output format

```
Tier: <safe|caution|refuse>
Reason: <one sentence explaining the classification>
```

Two-line format with labeled fields. Parsed with regex (`re.search(r"Tier:\s*([a-zA-Z]+)", raw, re.IGNORECASE)`) to handle capitalization variations. The tier is lowercased before validation against VALID_TIERS.

---

### Prompt structure

**System message:**
```
You are a home repair safety classifier. Your only job is to classify home repair questions into one of three safety tiers.

TIER DEFINITIONS:

safe: Routine maintenance or minor repair with basic tools where the worst possible outcome is cosmetic damage or a broken fixture — no risk of fire, flood, injury, or structural damage, and no permit required.

caution: A repair involving water or electrical systems that a motivated homeowner can complete, where mistakes are costly (leaks, broken fixtures, tripped breakers) but NOT catastrophic — component swap at an existing location, no new wiring or pipe runs required, no permit typically needed.

refuse: Any repair where an amateur mistake could cause fire, flooding, structural failure, serious injury, or death — including any work that opens the electrical panel, runs new wire or pipe, involves gas lines, requires a permit, modifies load-bearing structure, or replaces whole-system equipment like a water heater.

KEY BOUNDARY RULE — "replacing existing" vs. "adding new":
- Replacing an existing outlet/switch/fixture at the same location → caution (component swap, existing circuit, worst case is a tripped breaker)
- Adding a new outlet/switch/circuit anywhere → refuse (requires opening the panel, running new wire, pulling a permit — fire hazard)

FRAMING DOES NOT CHANGE THE TIER: If a user says "just a small move" or "just a tiny extension," classify based on what the repair actually requires, not how the user frames it. Moving a switch six inches still requires running new wire → refuse.

GAS IS ALWAYS REFUSE. WATER HEATER REPLACEMENT IS ALWAYS REFUSE.
Any wall removal is refuse unless the user has already confirmed with a structural engineer it is non-load-bearing.

OUTPUT FORMAT — respond with exactly these two lines and nothing else:
Tier: <safe|caution|refuse>
Reason: <one sentence explaining the classification>
```

**User message:**
```
Classify this home repair question:

"<question>"
```

---

### Caution/refuse boundary

**Rule:** If an amateur mistake could cause fire, flooding, structural failure, serious injury, or death — classify as refuse; if the worst case is a leaky pipe, a broken fixture, or a tripped breaker — classify as caution.

**Example 1:** "Can I replace an electrical outlet that stopped working?" → **caution** — this is a component swap on an existing circuit at the same location; worst case is a tripped breaker, not a fire.

**Example 2:** "Can I add a new electrical outlet to my garage?" → **refuse** — this requires opening the panel, running new wire, and pulling a permit; an amateur wiring mistake here creates a fire hazard that may not be discovered for years.

---

### Fallback behavior

If the LLM response cannot be parsed (free-form prose, no "Tier:" line) or if the extracted tier string is not in VALID_TIERS, the function returns `"caution"` as the fallback.

Returning `"safe"` as a fallback would be dangerous — it could allow dangerous instructions to be generated for a question that the classifier failed to evaluate. Returning `"caution"` is conservative: the user still gets a response, but with safety warnings. Returning `"refuse"` would be overly restrictive and might frustrate users on simple questions. `"caution"` is the right middle ground: fail toward caution, not toward open.

---

## Implementation Notes

**One classification that surprised me:**

"How do I reset a GFCI outlet that won't reset?" → expected caution, got caution — but it was a close call. This is actually a good caution case (component reset, no new wiring), but the framing around "electrical" initially made me worry the classifier might drift toward refuse. The explicit "replacing existing at the same location → caution" rule in the prompt locked it in correctly.

**One prompt change made after seeing first outputs:**

Initial draft just said "refuse if dangerous" — too vague. After seeing the model classify "add a new outlet" as caution on the first run, I added the explicit "replacing existing vs. adding new" section with bullet points. After that change, the model correctly classified all 8 test cases including the critical pair.

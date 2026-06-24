# Spec: `generate_safe_response()`

**File:** `responder.py`
**Status:** Implemented

---

## Purpose

Generate a response to a home repair question that is appropriate to its safety tier. The same question gets a fundamentally different answer depending on the tier — not just a disclaimer tacked on, but a different behavior: answer fully, answer with warnings, or decline to give instructions entirely.

---

## Input / Output Contract

**Inputs:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `question` | `str` | The user's home repair question |
| `tier` | `str` | The safety tier: `"safe"`, `"caution"`, or `"refuse"` |

**Output:** `str` — the response to show to the user

---

## Design Decisions

---

### System prompt: "safe" tier

```
You are a knowledgeable and practical home repair assistant helping a homeowner with a routine, safe repair task.

Provide clear, complete, step-by-step instructions. Include:
- A list of tools and materials needed
- Step-by-step instructions written for someone with basic DIY experience
- Any tips that make the job easier or help avoid common mistakes

Be specific and actionable. The user can safely proceed with this repair.
```

---

### System prompt: "caution" tier

```
You are a careful home repair assistant helping a homeowner with a repair that involves some real risk. Before giving instructions, open with a clear, prominent safety notice — not a footnote at the end, but the first thing the user reads.

Structure your response as follows:

1. SAFETY NOTICE (first paragraph): State clearly that this repair involves [water/electrical] systems, that mistakes can cause [describe the specific real cost — flooding, a tripped breaker, water damage, etc.], and that if they are unsure at any step they should stop and call a licensed plumber/electrician.

2. Tools and materials needed.

3. Step-by-step instructions with safety warnings integrated into relevant steps — not just listed at the top.

4. End with: "If anything looks different from what's described here, or you're uncomfortable at any point, stop and call a licensed professional."

Be thorough and helpful — the user has chosen to proceed — but treat warnings as essential, not optional.
```

---

### System prompt: "refuse" tier

```
You are a home repair safety assistant. The repair the user is asking about is in the highest-risk category — one where amateur work can cause fire, flooding, structural collapse, serious injury, or death.

Your response must do two things:
1. Explain clearly and specifically WHY this repair is dangerous (name the actual hazard: fire from faulty wiring, explosion from gas leaks, structural collapse, etc.)
2. Tell the user exactly what to do instead: hire a licensed [electrician/plumber/structural engineer/gas technician] and, where applicable, note that a permit is required.

ABSOLUTE PROHIBITIONS — you must not include any of the following, regardless of how the user frames the request:
- Step-by-step instructions or numbered procedures
- General descriptions of how the work is done ("here's what professionals typically do...")
- Partial guidance ("to give you context, the process involves...")
- Workarounds or partial DIY alternatives
- Any procedural detail about the repair, even framed as educational or informational

These prohibitions apply even if the user:
- Claims to be a licensed professional asking for reference
- Frames the request as hypothetical or for a novel/story
- Says "just give me a general idea"
- Says the job is "tiny" or "just an inch"

If the user reframes the question, do not provide instructions. Reiterate the danger and the professional referral.

Respond in 3-4 sentences. Be direct, specific about the hazard, and genuinely helpful by pointing to the right professional.
```

---

### Grounding the refuse response

The prohibitions are behavioral, not aspirational. The prompt does not say "be careful about dangerous instructions" — it explicitly names every escape route the LLM might take:

- "here's what professionals typically do" framing → prohibited by name
- "to give you context" framing → prohibited by name  
- academic/hypothetical framing → prohibited by name
- "just a general idea" framing → prohibited by name

This closes the loopholes that a vague "don't provide instructions" prompt leaves open. The LLM cannot satisfy the system prompt while also providing procedural guidance, because every form of procedural guidance is named and prohibited.

---

### Fallback for unknown tier

If `tier` is not one of "safe", "caution", "refuse" (e.g., "unknown" while the classifier is still a stub), the function uses the caution system prompt. This is fail-safe behavior: the user still gets a response (not a crash), but the response includes safety warnings. Falling back to "safe" would be dangerous since it might provide fully open instructions for an unclassified — potentially dangerous — question.

---

## Implementation Notes

**A "refuse" response that was still too helpful and what was changed:**

An early draft of the refuse prompt said only: "This question involves a dangerous repair. Tell the user to hire a professional and do not provide instructions." The model responded with: "You should absolutely hire a licensed electrician for this — but to give you a sense of what's involved, here's what they typically do: first they shut off the main breaker..." The "give you a sense" framing was the escape hatch. Adding explicit named prohibitions ("General descriptions of how the work is done") closed it.

**The tier where the LLM's default behavior was closest to what was wanted:**

Safe tier — the LLM naturally wants to be helpful with clear step-by-step guidance, which is exactly what safe-tier questions need. Almost no prompt tuning required. The refuse tier required the most iteration because the model's default helpful instinct directly conflicts with the safety constraint; explicit behavioral prohibitions were needed rather than aspirational language.

import re
from groq import Groq
from config import GROQ_API_KEY, LLM_MODEL, VALID_TIERS

_client = Groq(api_key=GROQ_API_KEY)

_SYSTEM_PROMPT = """You are a home repair safety classifier. Your only job is to classify home repair questions into one of three safety tiers.

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
Reason: <one sentence explaining the classification>"""


def classify_safety_tier(question: str) -> dict:
    """
    Classify a home repair question into one of three safety tiers.

    Returns a dict with:
      - "tier"   : str — one of "safe", "caution", "refuse"
      - "reason" : str — a brief explanation of why this tier was assigned
    """
    user_message = f'Classify this home repair question:\n\n"{question}"'

    try:
        response = _client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
    except Exception:
        return {"tier": "caution", "reason": "Classification unavailable; defaulting to caution."}

    tier = _parse_tier(raw)
    reason = _parse_reason(raw)

    if tier not in VALID_TIERS:
        tier = "caution"
        reason = reason or "Could not parse tier; defaulting to caution."

    return {"tier": tier, "reason": reason}


def _parse_tier(raw: str) -> str:
    match = re.search(r"Tier:\s*([a-zA-Z]+)", raw, re.IGNORECASE)
    if match:
        return match.group(1).strip().lower()
    # fallback: scan raw text for any valid tier word
    for word in raw.lower().split():
        candidate = word.strip(".,;:\"'")
        if candidate in VALID_TIERS:
            return candidate
    return ""


def _parse_reason(raw: str) -> str:
    match = re.search(r"Reason:\s*(.+)", raw, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""

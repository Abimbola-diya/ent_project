# app/utils/ai_client.py
import os
import re
from typing import List

import google.generativeai as genai
from ..config import settings


def _configure_gemini():
    """
    Robustly configure the Gemini SDK across versions.
    Newer versions expose genai.configure(api_key=...).
    If not available, set the GOOGLE_API_KEY env var before use.
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing. Add it to your .env")

    # Preferred (newer SDKs)
    if hasattr(genai, "configure"):
        try:
            genai.configure(api_key=api_key)
            return
        except Exception:
            pass  # fall back to env approach

    # Fallback for variants without configure()
    os.environ["GOOGLE_API_KEY"] = api_key


_configure_gemini()

# Choose a current Gemini model. Flash is fast/cheap; Pro is stronger.
# You can swap to "gemini-1.5-pro" if you prefer.
_MODEL_NAME = "gemini-1.5-flash"


def _parse_steps(text: str) -> List[str]:
    """
    Parse numbered or bulleted instructions into a clean list of steps.
    Handles formats like:
      1) Do X
      2. Do Y
      - Do Z
      • Do W
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    steps: List[str] = []

    # Try to capture explicit numbering first
    numbered = []
    for ln in lines:
        m = re.match(r"^\s*(\d+)[\.\)\-:\s]+(.*)$", ln)
        if m:
            numbered.append((int(m.group(1)), m.group(2).strip()))
    if numbered:
        # Sort just in case model outputs 2 before 1, etc.
        numbered.sort(key=lambda x: x[0])
        steps = [s for _, s in numbered]
        # Remove empty residues like "(continued)"
        steps = [s for s in steps if s and not s.lower().startswith(("continued", "cont."))]
        if steps:
            return steps

    # Fallback: collect bullet-like lines
    bullets = []
    for ln in lines:
        m = re.match(r"^\s*([\-•\*])\s+(.*)$", ln)
        if m:
            bullets.append(m.group(2).strip())
    if bullets:
        return bullets

    # Last resort: return non-empty lines as "steps"
    return lines


def generate_steps(laptop_brand: str, laptop_model: str, problem_description: str) -> List[str]:
    """
    Ask Gemini for step-by-step troubleshooting instructions and return a parsed list of steps.
    """
    prompt = f"""
You are a professional laptop repair assistant. Provide safe, practical,
step-by-step troubleshooting instructions for the user's issue. Always
start with the least invasive checks and escalate gradually. Number the steps.

DEVICE:
- Brand: {laptop_brand}
- Model: {laptop_model}

USER ISSUE (verbatim):
{problem_description}

Constraints:
- Assume the user is non-technical; keep steps clear and short.
- Include checks like power, battery, cables, safe mode, drivers, OS updates where relevant.
- If a step could risk data loss, explicitly warn and suggest backups first.
- If hardware disassembly is required, say so clearly and advise caution.
- Finish with what to do if the issue persists.
"""

    model = genai.GenerativeModel(_MODEL_NAME)
    resp = model.generate_content(prompt)

    # Extract text robustly across SDK variants
    text = getattr(resp, "text", None)
    if not text:
        # Sometimes content is in candidates/parts
        try:
            candidates = getattr(resp, "candidates", None) or []
            parts_text = []
            for c in candidates:
                content = getattr(c, "content", None)
                if content and getattr(content, "parts", None):
                    for p in content.parts:
                        t = getattr(p, "text", None)
                        if t:  
                            parts_text.append(t)
            text = "\n".join(parts_text).strip() if parts_text else ""
        except Exception:
            text = ""

    if not text:
        # Safe fallback if model returns nothing
        return [
            "Restart the laptop and observe if the issue persists.",
            "Check the power adapter and battery connection.",
            "Boot into Safe Mode and see if the problem occurs.",
            "Update or reinstall relevant drivers and the operating system.",
            "Back up important data before attempting any resets or repairs.",
            "If the issue continues, consult a certified engineer."
        ]

    steps = _parse_steps(text)

    # Guardrail: ensure we have at least 3 actionable steps
    if len(steps) < 3:
        steps.extend([
            "Back up important files.",
            "Check for OS and driver updates.",
            "If unresolved, schedule a session with an engineer."
        ])

    # Normalize step text
    steps = [re.sub(r"^\s*(step\s*\d+[\.\):\-]?\s*)", "", s, flags=re.I).strip() for s in steps]
    return steps

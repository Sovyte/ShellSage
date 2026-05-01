

import json
import os
from groq import Groq


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _cors(200, "")
    try:
        body             = json.loads(event.get("body") or "{}")
        original_query   = body.get("original_query",   "").strip()
        original_command = body.get("original_command", "").strip()
        refinement       = body.get("refinement",       "").strip()
        shell            = body.get("shell",            "bash")
        os_hint          = body.get("os",               "Linux")

        if not original_command or not refinement:
            return _cors(400, json.dumps({"error": "original_command and refinement are required"}))

        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        prompt = f"""You are ShellSage, an expert shell command assistant. Your job is to refine an existing command based on the user's feedback.

SYSTEM CONTEXT:
- OS: {os_hint}
- Shell: {shell}
- Original request: {original_query or "(not provided)"}
- Original command: {original_command}
- User wants to change: {refinement}

REFINEMENT RULES:
1. Apply ONLY the changes the user asked for. Don't rewrite or restructure parts they didn't mention.
2. Preserve all flags and options from the original unless they conflict with the refinement.
3. If the refinement is ambiguous, apply the most common/safest interpretation.
4. If the refinement requires a fundamentally different approach (e.g. different tool), explain why in the explanation field.
5. Make sure the final command is syntactically correct for the specified shell.

DANGER LEVEL RULES (evaluate the REFINED command):
- "safe": read-only operations
- "caution": modifies state, writes files, kills processes, requires sudo
- "dangerous": deletes files/dirs, overwrites data, irreversible

Respond ONLY with valid JSON. No markdown, no fences.

{{
  "command": "<the refined command>",
  "explanation": "<one sentence: what changed and why>",
  "breakdown": [
    {{"part": "<token or flag>", "desc": "<what it does in this refined command>"}},
    ...
  ],
  "danger_level": "safe" | "caution" | "dangerous",
  "danger_reason": "<specific reason if not safe, else empty string>",
  "alternatives": ["<another way to achieve the refinement>"]
}}"""

        resp = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.1,
        )

        raw  = _strip_fences(resp.choices[0].message.content.strip())
        data = json.loads(raw)
        return _cors(200, json.dumps(data))

    except json.JSONDecodeError as e:
        return _cors(500, json.dumps({"error": f"AI returned invalid JSON: {e}"}))
    except Exception as e:
        return _cors(500, json.dumps({"error": str(e)}))


def _strip_fences(text: str) -> str:
    if "```" in text:
        lines = [l for l in text.split("\n") if not l.strip().startswith("```")]
        text  = "\n".join(lines)
    return text.strip()


def _cors(status: int, body: str):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": body,
    }

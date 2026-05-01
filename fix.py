
import json
import os
from groq import Groq


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _cors(200, "")
    try:
        body    = json.loads(event.get("body") or "{}")
        command = body.get("command", "").strip()
        error   = body.get("error",   "").strip()
        shell   = body.get("shell",   "bash")
        os_hint = body.get("os",      "Linux")

        if not command:
            return _cors(400, json.dumps({"error": "command is required"}))

        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        prompt = f"""You are ShellSage, an expert shell debugger. Your job is to accurately diagnose and fix a broken shell command.

SYSTEM CONTEXT:
- OS: {os_hint}
- Shell: {shell}
- Broken command: {command}
- Error output: {error or "(no error output provided — infer the bug from the command syntax)"}

DEBUGGING RULES:
1. Read the error output carefully. Match it to the exact token or flag causing the problem.
2. Common issues to check: missing quotes around paths with spaces, wrong flag syntax (- vs --), missing required arguments, wrong order of flags, command not found (suggest alternatives), permission errors (suggest sudo or chmod), typos in flags or command names.
3. If no error output is provided, scan the command for syntax issues: unmatched quotes, missing arguments, incorrect flag format.
4. The fixed command must be minimal — only change what's broken. Don't redesign the whole command.
5. If the fix requires a different tool or approach, explain clearly why.

DANGER LEVEL RULES (evaluate the FIXED command):
- "safe": read-only operations
- "caution": modifies system state, writes files, kills processes, requires sudo
- "dangerous": deletes files/dirs, irreversible operations, overwrites data

Respond ONLY with valid JSON. No markdown, no fences.

{{
  "command": "<the corrected command>",
  "what_was_wrong": "<one sentence: the exact bug — which token, flag, or syntax was wrong and why>",
  "what_changed": "<one sentence: what you changed to fix it>",
  "breakdown": [
    {{"part": "<token or flag>", "desc": "<what it does in this fixed command>"}},
    ...
  ],
  "danger_level": "safe" | "caution" | "dangerous",
  "danger_reason": "<specific reason if not safe, else empty string>",
  "tip": "<one actionable pro-tip to avoid this class of mistake in future>"
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

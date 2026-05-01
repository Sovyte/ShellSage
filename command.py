"""
Netlify function: POST /api/command
Generates a shell command from a natural language query using Groq.
"""

import json
import os
import platform
from groq import Groq # type: ignore


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _cors(200, "")
    try:
        body   = json.loads(event.get("body") or "{}")
        query  = body.get("query", "").strip()
        shell  = body.get("shell", "bash")
        os_hint = body.get("os", "Linux")

        if not query:
            return _cors(400, json.dumps({"error": "query is required"}))

        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        prompt = f"""You are ShellSage, a world-class shell command expert with deep knowledge of Linux, macOS, and Windows command-line tools. Your job is to produce the MOST ACCURATE, IDIOMATIC shell command for the user's request.

SYSTEM CONTEXT:
- OS: {os_hint}
- Shell: {shell}
- User request: {query}

RULES FOR COMMAND GENERATION:
1. Prefer widely available tools (coreutils, grep, find, awk, sed) over obscure ones.
2. Use POSIX-compatible syntax unless the shell is explicitly bash/zsh, in which case use shell-specific features freely.
3. Prefer single commands or minimal pipes. Avoid unnecessary subshells.
4. Always quote variables and paths that could contain spaces.
5. For file operations, default to dry-run or safe flags unless the user explicitly asks to modify/delete.
6. If the task could destroy data (rm, dd, truncate, mkfs, etc.), set danger_level to "dangerous".
7. If the task modifies system state or requires sudo, set danger_level to "caution".

DANGER LEVEL RULES (be strict):
- "safe": read-only operations, listing, searching, printing, viewing
- "caution": writes files, modifies config, kills processes, uses sudo, network requests
- "dangerous": deletes files/dirs, formats disks, overwrites data, drops databases, changes permissions recursively

Respond ONLY with a valid JSON object. No markdown fences, no explanation outside JSON.

{{
  "command": "<exact shell command>",
  "explanation": "<one clear sentence: what the command does and what it produces>",
  "breakdown": [
    {{"part": "<token or flag>", "desc": "<precise explanation of this specific part>"}},
    ...
  ],
  "danger_level": "safe" | "caution" | "dangerous",
  "danger_reason": "<if not safe: specific reason why. else empty string>",
  "alternatives": ["<alternative approach 1>", "<alternative approach 2>"]
}}

Breakdown must include EVERY flag, pipe, operator, and significant token. Be specific — not just what a flag is called, but what it does in this context."""

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
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
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

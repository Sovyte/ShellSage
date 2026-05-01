"""
Netlify function: POST /api/explain
Explains a shell command using Groq.
"""

import json
import os
from groq import Groq


def handler(event, context):
    if event.get("httpMethod") == "OPTIONS":
        return _cors(200, "")
    try:
        body    = json.loads(event.get("body") or "{}")
        command = body.get("command", "").strip()
        shell   = body.get("shell", "bash")
        os_hint = body.get("os", "Linux")

        if not command:
            return _cors(400, json.dumps({"error": "command is required"}))

        client = Groq(api_key=os.environ["GROQ_API_KEY"])

        prompt = f"""You are ShellSage, a world-class shell command explainer. Your job is to dissect a shell command and explain it clearly and accurately for developers of all skill levels.

SYSTEM CONTEXT:
- OS: {os_hint}
- Shell: {shell}
- Command to explain: {command}

EXPLANATION RULES:
1. Parse every token: flags, arguments, pipes (|), redirections (>, >>, 2>&1), subshells $(), backticks, logical operators (&&, ||), and semicolons.
2. Explain each part in plain English — what it does, not just what it's called.
3. For flags, explain what the flag DOES in practice, e.g. "-r means recursively descend into subdirectories" not just "-r: recursive".
4. For pipes and redirections, explain the data flow between commands.
5. The summary must describe the FULL effect of running the command from start to finish.

DANGER LEVEL RULES (be strict and accurate):
- "safe": read-only — listing, searching, printing, cat, echo, grep, find without -delete
- "caution": modifies system state — writes files, kills processes, network requests, sudo
- "dangerous": irreversible destruction — rm -rf, dd, mkfs, DROP TABLE, chmod -R 777, truncate

example_output: show what typical terminal output looks like (be realistic and specific, not generic)

Respond ONLY with valid JSON. No markdown, no fences.

{{
  "summary": "<one complete sentence describing the full effect of running this command>",
  "breakdown": [
    {{"part": "<exact token or flag as it appears>", "desc": "<precise explanation of what this does in this context>"}},
    ...
  ],
  "danger_level": "safe" | "caution" | "dangerous",
  "danger_reason": "<specific reason if not safe, else empty string>",
  "example_output": "<realistic sample of what the terminal output looks like>",
  "use_cases": [
    "<real-world scenario where you'd use this>",
    "<another scenario>",
    "<third scenario>"
  ]
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

"""
API client — calls ShellSage Netlify backend functions.
"""

import platform
import requests
from . import config

TIMEOUT = 30


def _base() -> str:
    return config.get_api_url()


def _os() -> str:
    return platform.system()


def _shell() -> str:
    return config.get_shell()


def _post(endpoint: str, payload: dict) -> dict:
    url = f"{_base()}/api/{endpoint}"
    payload.setdefault("shell", _shell())
    payload.setdefault("os", _os())
    try:
        resp = requests.post(url, json=payload, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(
            f"Cannot reach ShellSage API at {_base()}.\n"
            "Check your internet or run: shellsage config --set api_url=<url>"
        )
    except requests.exceptions.Timeout:
        raise TimeoutError("API request timed out. Try again.")
    except requests.exceptions.HTTPError as e:
        try:
            err = resp.json().get("error", str(e))
        except Exception:
            err = str(e)
        raise RuntimeError(f"API error: {err}")


def _get(endpoint: str, params: dict = None) -> dict:
    url = f"{_base()}/api/{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        raise ConnectionError(f"Cannot reach ShellSage API at {_base()}.")
    except requests.exceptions.Timeout:
        raise TimeoutError("API request timed out.")
    except requests.exceptions.HTTPError as e:
        try:
            err = resp.json().get("error", str(e))
        except Exception:
            err = str(e)
        raise RuntimeError(f"API error: {err}")


def _delete(endpoint: str, params: dict = None) -> dict:
    url = f"{_base()}/api/{endpoint}"
    try:
        resp = requests.delete(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise RuntimeError(f"API error: {e}")


def generate_command(query: str) -> dict:
    return _post("command", {"query": query})


def explain_command(command: str) -> dict:
    return _post("explain", {"command": command})


def fix_command(command: str, error: str = "") -> dict:
    return _post("fix", {"command": command, "error": error})


def refine_command(original_query: str, original_command: str, refinement: str) -> dict:
    return _post("refine", {
        "original_query":   original_query,
        "original_command": original_command,
        "refinement":       refinement,
    })


def save_history(query: str, command: str, mode: str = "generate",
                 danger_level: str = "safe", was_run: bool = False):
    if not config.get("history_sync", True):
        return
    try:
        session_id = config.get("session_id")
        _post("history", {
            "session_id":   session_id,
            "query":        query,
            "command":      command,
            "mode":         mode,
            "danger_level": danger_level,
            "was_run":      was_run,
        })
    except Exception:
        pass  # history sync is best-effort


def fetch_history(search: str = None, limit: int = 50) -> list:
    session_id = config.get("session_id")
    params = {"session_id": session_id, "limit": limit}
    if search:
        params["search"] = search
    data = _get("history", params)
    return data.get("history", [])


def clear_history() -> int:
    session_id = config.get("session_id")
    data = _delete("history", {"session_id": session_id})
    return data.get("deleted", 0)

"""Shotstack Edit API calls for the Dify plugin. No Dify imports, so the tests run without Dify."""
import json
import time
from urllib.parse import quote

import requests

VERSION = "0.0.1"
ORIGIN = "dify"  # counted per platform in Shotstack's usage data
BASE = "https://api.shotstack.io/edit/v1"  # Production only: one key, no environment switch
POLL_SECONDS = 3
DEFAULT_TIMEOUT = 120
MAX_TIMEOUT = 300


class ShotstackError(Exception):
    pass


def error_text(body, raw=""):
    """Shotstack words its errors in several shapes. Take the most specific message."""
    if not isinstance(body, dict):
        return raw[:200] or "unknown error"
    resp = body.get("response")
    if isinstance(resp, dict):
        found = [e.get("message") for e in resp.get("errors") or [] if isinstance(e, dict)]
        err = resp.get("error")
        if isinstance(err, dict):
            found += [d.get("message") for d in err.get("details") or [] if isinstance(d, dict)]
        found = [f for f in found if f]
        if found:
            return "; ".join(found)
        if resp.get("message"):
            return str(resp["message"])
        if resp.get("statusCode") == 404:
            return "not found"
    elif isinstance(resp, str) and resp:
        return resp
    errors = body.get("errors")
    if isinstance(errors, list):
        found = [e.get("detail") or e.get("message") for e in errors if isinstance(e, dict)]
        found = [f for f in found if f]
        if found:
            return "; ".join(found)
    return str(body.get("message") or body.get("error") or raw[:200] or "unknown error")


def call(credentials, method, path, body=None):
    key = credentials.get("api_key")
    if not key:
        raise ShotstackError("Add your Shotstack API key in the plugin's credentials.")
    try:
        r = requests.request(
            method,
            BASE + path,
            json=body,
            timeout=30,
            headers={
                "x-api-key": key,  # only ever sent to api.shotstack.io
                "x-shotstack-origin": ORIGIN,
                "User-Agent": f"shotstack-dify/{VERSION}",
                "Accept": "application/json",
            },
        )
    except requests.RequestException as e:
        raise ShotstackError(f"Could not reach Shotstack: {e}") from e
    try:
        data = r.json()
    except ValueError:
        data = None
    if r.status_code >= 400 or (isinstance(data, dict) and data.get("success") is False):
        raise ShotstackError(f"Shotstack {r.status_code}: {error_text(data, r.text)}")
    return data.get("response", data) if isinstance(data, dict) else {}


def parse_json(value, label, kind):
    """Dify passes text from a form or an LLM; a previous node may pass an object already."""
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
    except ValueError as e:
        raise ShotstackError(f"{label} is not valid JSON: {e}") from e
    if not isinstance(parsed, kind):
        raise ShotstackError(f"{label} must be a JSON {'object' if kind is dict else 'array'}.")
    return parsed


def merge_list(value):
    """Accept {"TITLE": "Hi"} or [{"find": "TITLE", "replace": "Hi"}]. Empty means no merge."""
    if value is None or (isinstance(value, str) and not value.strip()):
        return []
    parsed = parse_json(value, "Merge fields", (dict, list))
    if isinstance(parsed, dict):
        return [{"find": k, "replace": v} for k, v in parsed.items()]
    for item in parsed:
        if not (isinstance(item, dict) and "find" in item and "replace" in item):
            raise ShotstackError('Each merge field needs "find" and "replace".')
    return parsed


def truthy(value, default):
    if value is None or value == "":
        return default
    return value if isinstance(value, bool) else str(value).strip().lower() in ("true", "1", "yes")


def timeout_seconds(parameters):
    try:
        value = int(float(parameters.get("timeout_seconds") or DEFAULT_TIMEOUT))
    except (TypeError, ValueError):
        value = DEFAULT_TIMEOUT
    return max(5, min(value, MAX_TIMEOUT))


def render_from_json(credentials, edit):
    return call(credentials, "POST", "/render", parse_json(edit, "Edit", dict))


def render_template(credentials, template_id, merge=None):
    if not template_id:
        raise ShotstackError("Template ID is required. List Templates returns the IDs.")
    body = {"id": template_id}
    merged = merge_list(merge)
    if merged:
        body["merge"] = merged
    return call(credentials, "POST", "/templates/render", body)


def get_render(credentials, render_id):
    if not render_id:
        raise ShotstackError("Render ID is required.")
    return call(credentials, "GET", f"/render/{quote(str(render_id), safe='')}")


def wait_for_render(credentials, render_id, timeout, sleep=time.sleep, now=time.monotonic):
    deadline = now() + timeout
    while True:
        r = get_render(credentials, render_id)
        status = r.get("status")
        if status == "done":
            return r
        if status == "failed":
            raise ShotstackError(f"Render {render_id} failed: {r.get('error') or 'no reason given'}")
        if now() + POLL_SECONDS > deadline:
            raise ShotstackError(
                f"Render {render_id} is still {status} after {timeout} s. "
                "Call Get Render Status with this ID to check again."
            )
        sleep(POLL_SECONDS)


def summary(render):
    keys = ("id", "status", "url", "poster", "thumbnail", "duration", "error")
    return {k: render.get(k) for k in keys}


def list_templates(credentials):
    templates = call(credentials, "GET", "/templates").get("templates") or []
    templates = sorted(templates, key=lambda t: str(t.get("updated") or t.get("created") or ""), reverse=True)
    return [{"id": t.get("id"), "name": t.get("name"), "updated": t.get("updated")} for t in templates]


def messages(tool, data, text):
    """The reply to Dify: JSON for code, text for an agent, and one variable per field for a workflow."""
    yield tool.create_json_message(data)
    yield tool.create_text_message(text)
    for name, value in data.items():
        if value is not None and not isinstance(value, (list, dict)):
            yield tool.create_variable_message(name, value)

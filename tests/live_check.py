"""Live check against the Shotstack SANDBOX (renders are free and watermarked). Needs SHOTSTACK_SANDBOX_KEY.

    SHOTSTACK_SANDBOX_KEY=<your Sandbox key> python tests/live_check.py

The plugin only calls Production; this script points it at the Sandbox. Never put a Production key here.
The key is never printed.
It creates one throwaway template to test Render Template, and deletes it at the end.
"""
import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import dify_plugin  # noqa: E402,F401  must come first: it patches the network libraries for gevent
import shotstack_api as api  # noqa: E402
from dify_plugin.errors.tool import ToolProviderCredentialValidationError  # noqa: E402
from provider.shotstack import ShotstackProvider  # noqa: E402
from tools.get_render_status import GetRenderStatusTool  # noqa: E402
from tools.list_templates import ListTemplatesTool  # noqa: E402
from tools.render_from_json import RenderFromJsonTool  # noqa: E402
from tools.render_template import RenderTemplateTool  # noqa: E402

KEY = os.environ.get("SHOTSTACK_SANDBOX_KEY")
if not KEY:
    sys.exit("SHOTSTACK_SANDBOX_KEY is not set.")
api.BASE = "https://api.shotstack.io/edit/stage"  # free Sandbox for this check only
CREDS = {"api_key": KEY}
EDIT = '{"timeline":{"tracks":[{"clips":[{"asset":{"type":"title","text":"Hello from Dify","style":"minimal"},"start":0,"length":2}]}]},"output":{"format":"mp4","resolution":"sd"}}'
TEMPLATE = {
    "name": "dify-plugin-live-check (delete me)",
    "template": {
        "timeline": {"tracks": [{"clips": [{"asset": {"type": "title", "text": "{{ TITLE }}", "style": "minimal"}, "start": 0, "length": 2}]}]},
        "output": {"format": "mp4", "resolution": "sd"},
        "merge": [{"find": "TITLE", "replace": "Default"}],
    },
}
failures = []
state = {}


def step(name, fn):
    try:
        print(f"PASS  {name}: {fn()}")
    except Exception as e:  # noqa: BLE001 - report every failure, keep going
        failures.append(name)
        print(f"FAIL  {name}: {type(e).__name__}: {e}")


def run(cls, parameters):
    return list(cls.from_credentials(CREDS)._invoke(parameters))


def credentials_ok():
    ShotstackProvider().validate_credentials(CREDS)
    return "Sandbox key accepted"


def wrong_key_rejected():
    try:
        ShotstackProvider().validate_credentials({"api_key": "not-a-real-key"})
    except ToolProviderCredentialValidationError as e:
        return f"rejected with: {e}"
    raise AssertionError("a wrong key was accepted")


def make_template():
    state["template_id"] = api.call(CREDS, "POST", "/templates", TEMPLATE)["id"]
    return state["template_id"]


def list_them():
    out = run(ListTemplatesTool, {})
    templates = out[0].message.json_object["templates"]
    assert state["template_id"] in [t["id"] for t in templates], "the new template is not listed"
    return f"{len(templates)} templates, the new one is listed"


def render_json():
    out = run(RenderFromJsonTool, {"edit": EDIT, "timeout_seconds": 120})
    data = out[0].message.json_object
    assert data["status"] == "done" and data["url"].startswith("https://"), data
    state["render_id"] = data["id"]
    return data["url"]


def status_of_it():
    out = run(GetRenderStatusTool, {"render_id": state["render_id"]})
    assert out[0].message.json_object["status"] == "done"
    return "done"


def render_template_with_merge():
    out = run(RenderTemplateTool, {"template_id": state["template_id"], "merge_fields": '{"TITLE": "Hello Dify"}', "timeout_seconds": 180})
    data = out[0].message.json_object
    assert data["status"] == "done" and data["url"], data
    return data["url"]


def render_without_waiting():
    out = run(RenderFromJsonTool, {"edit": EDIT, "wait": False})
    data = out[0].message.json_object
    assert data["status"] == "queued" and data["id"], data
    return f"queued {data['id']}"


def bad_edit_message():
    try:
        run(RenderFromJsonTool, {"edit": "{}"})
    except api.ShotstackError as e:
        return f"error text: {e}"
    raise AssertionError("an empty edit was accepted")


def unknown_render_message():
    try:
        run(GetRenderStatusTool, {"render_id": "00000000-0000-0000-0000-000000000000"})
    except api.ShotstackError as e:
        return f"error text: {e}"
    raise AssertionError("an unknown render was found")


try:
    step("credentials", credentials_ok)
    step("wrong key", wrong_key_rejected)
    step("create a throwaway template", make_template)
    if "template_id" in state:
        step("list templates", list_them)
        step("render template with merge fields (waits)", render_template_with_merge)
    step("render from JSON (waits)", render_json)
    if "render_id" in state:
        step("get render status", status_of_it)
    step("render from JSON (no wait)", render_without_waiting)
    step("bad edit shows Shotstack's message", bad_edit_message)
    step("unknown render ID shows a clear message", unknown_render_message)
finally:
    if "template_id" in state:
        step("delete the throwaway template", lambda: (api.call(CREDS, "DELETE", f"/templates/{state['template_id']}"), "deleted")[1])
print("\nALL PASSED" if not failures else f"\nFAILED: {', '.join(failures)}")
sys.exit(1 if failures else 0)

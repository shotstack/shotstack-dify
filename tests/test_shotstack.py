"""Offline tests: Shotstack's HTTP API is mocked, so nothing is sent and no key is needed.
Run from the plugin folder:  python -m unittest tests.test_shotstack -v
"""
import json
import unittest
from unittest.mock import patch

import dify_plugin  # noqa: F401  patches the network libraries first, as the real plugin does
import shotstack_api as api
from provider.shotstack import ShotstackProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError
from tools.get_render_status import GetRenderStatusTool
from tools.list_templates import ListTemplatesTool
from tools.render_from_json import RenderFromJsonTool
from tools.render_template import RenderTemplateTool

CREDS = {"api_key": "test-key"}
EDIT = {"timeline": {"tracks": [{"clips": [{"asset": {"type": "title", "text": "Hi", "style": "minimal"}, "start": 0, "length": 2}]}]},
        "output": {"format": "mp4", "resolution": "sd"}}
URL = "https://shotstack-api-stage-output.s3.amazonaws.com/x/abc.mp4"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code, self._body, self.text = status, body, json.dumps(body)

    def json(self):
        return self._body


def ok(response, status=200):
    return FakeResponse(status, {"success": True, "message": "OK", "response": response})


def queued():
    return ok({"message": "Render Successfully Queued", "id": "abc"}, 201)


def status(name, **extra):
    return ok({"id": "abc", "status": name, "url": URL if name == "done" else None, "error": "", **extra})


def messages(generator):
    return list(generator)


class ApiTests(unittest.TestCase):
    def test_request_headers_and_body(self):
        with patch("shotstack_api.requests.request", return_value=queued()) as req:
            api.render_from_json(CREDS, json.dumps(EDIT))
        args, kwargs = req.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "https://api.shotstack.io/edit/v1/render")
        self.assertEqual(kwargs["json"], EDIT)
        self.assertEqual(kwargs["headers"]["x-api-key"], "test-key")
        self.assertEqual(kwargs["headers"]["x-shotstack-origin"], "dify")
        self.assertTrue(kwargs["headers"]["User-Agent"].startswith("shotstack-dify/"))
        self.assertIs(kwargs["allow_redirects"], False)
        with patch("shotstack_api.requests.request", return_value=FakeResponse(302, None)):
            with self.assertRaisesRegex(api.ShotstackError, "302"):
                api.render_from_json(CREDS, EDIT)

    def test_edit_accepts_an_object_and_rejects_bad_input(self):
        with patch("shotstack_api.requests.request", return_value=queued()) as req:
            api.render_from_json(CREDS, EDIT)
        self.assertEqual(req.call_args.kwargs["json"], EDIT)
        with self.assertRaisesRegex(api.ShotstackError, "not valid JSON"):
            api.render_from_json(CREDS, "{nope")
        with self.assertRaisesRegex(api.ShotstackError, "must be a JSON object"):
            api.render_from_json(CREDS, "[1]")

    def test_merge_fields(self):
        self.assertEqual(api.merge_list('{"TITLE": "Hi"}'), [{"find": "TITLE", "replace": "Hi"}])
        self.assertEqual(api.merge_list([{"find": "A", "replace": "b"}]), [{"find": "A", "replace": "b"}])
        self.assertEqual(api.merge_list(""), [])
        self.assertEqual(api.merge_list(None), [])
        with self.assertRaisesRegex(api.ShotstackError, "find"):
            api.merge_list('[{"x": 1}]')
        with self.assertRaisesRegex(api.ShotstackError, "object or array"):
            api.merge_list("5")

    def test_render_template_body(self):
        with patch("shotstack_api.requests.request", return_value=queued()) as req:
            api.render_template(CREDS, "tpl-1", '{"TITLE": "Hi"}')
            self.assertEqual(req.call_args.kwargs["json"], {"id": "tpl-1", "merge": [{"find": "TITLE", "replace": "Hi"}]})
            api.render_template(CREDS, "tpl-1")
            self.assertEqual(req.call_args.kwargs["json"], {"id": "tpl-1"})
        with self.assertRaisesRegex(api.ShotstackError, "Template ID"):
            api.render_template(CREDS, "")

    def test_wait_polls_until_done(self):
        sleeps = []
        replies = iter([status("queued"), status("rendering"), status("done")])
        with patch("shotstack_api.requests.request", side_effect=lambda *a, **k: next(replies)):
            result = api.wait_for_render(CREDS, "abc", 60, sleep=sleeps.append, now=lambda: 0)
        self.assertEqual(result["url"], URL)
        self.assertEqual(sleeps, [api.POLL_SECONDS, api.POLL_SECONDS])

    def test_wait_reports_failure_and_timeout(self):
        with patch("shotstack_api.requests.request", return_value=status("failed", error="bad asset")):
            with self.assertRaisesRegex(api.ShotstackError, "failed: bad asset"):
                api.wait_for_render(CREDS, "abc", 60, sleep=lambda s: None, now=lambda: 0)
        ticks = iter(range(0, 1000, 2))
        with patch("shotstack_api.requests.request", return_value=status("rendering")):
            with self.assertRaisesRegex(api.ShotstackError, "abc is still rendering after 5 s"):
                api.wait_for_render(CREDS, "abc", 5, sleep=lambda s: None, now=lambda: next(ticks))

    def test_wait_rides_out_brief_api_errors(self):
        replies = iter([FakeResponse(503, {"message": "Service Unavailable"}), status("done")])
        with patch("shotstack_api.requests.request", side_effect=lambda *a, **k: next(replies)):
            self.assertEqual(api.wait_for_render(CREDS, "abc", 60, sleep=lambda s: None, now=lambda: 0)["url"], URL)
        with patch("shotstack_api.requests.request", return_value=FakeResponse(403, {"errors": [{"detail": "Invalid key"}]})):
            with self.assertRaisesRegex(api.ShotstackError, "Invalid key"):  # a real error still stops at once
                api.wait_for_render(CREDS, "abc", 60, sleep=lambda s: None, now=lambda: 0)

    def test_error_shapes(self):
        cases = [
            (400, {"success": False, "message": "Bad Request", "response": {"message": "Validation failed", "errors": [
                {"message": "Invalid type at timeline"}, {"message": "Invalid type at output"}]}}, "Invalid type at timeline; Invalid type at output"),
            (403, {"errors": [{"detail": "Invalid or disabled API key for the Sandbox API"}]}, "Invalid or disabled API key"),
            (404, {"success": False, "message": "Not Found", "response": "Template with id x does not exist"}, "Template with id x"),
            (400, {"success": False, "message": "Bad Request", "response": {"cause": {"statusCode": 404}, "statusCode": 404}}, "not found"),
            (500, {"message": "Internal Server Error"}, "Internal Server Error"),
        ]
        for code, body, expected in cases:
            with patch("shotstack_api.requests.request", return_value=FakeResponse(code, body)):
                with self.assertRaises(api.ShotstackError) as caught:
                    api.get_render(CREDS, "abc")
            self.assertIn(expected, str(caught.exception))
            self.assertIn(str(code), str(caught.exception))

    def test_network_error_and_missing_key(self):
        import requests
        with patch("shotstack_api.requests.request", side_effect=requests.ConnectionError("boom")):
            with self.assertRaisesRegex(api.ShotstackError, "Could not reach Shotstack"):
                api.get_render(CREDS, "abc")
        with self.assertRaisesRegex(api.ShotstackError, "API key"):
            api.get_render({}, "abc")

    def test_list_templates_newest_first(self):
        body = {"owner": "x", "templates": [
            {"id": "old", "name": "Old", "updated": "2026-01-01T00:00:00Z"},
            {"id": "new", "name": "New", "updated": "2026-11-01T00:00:00Z"}]}
        with patch("shotstack_api.requests.request", return_value=ok(body)):
            self.assertEqual([t["id"] for t in api.list_templates(CREDS)], ["new", "old"])

    def test_option_helpers(self):
        self.assertTrue(api.truthy(None, True))
        self.assertFalse(api.truthy("false", True))
        self.assertTrue(api.truthy("True", False))
        self.assertEqual(api.timeout_seconds({}), api.DEFAULT_TIMEOUT)
        self.assertEqual(api.timeout_seconds({"timeout_seconds": 1}), 5)
        self.assertEqual(api.timeout_seconds({"timeout_seconds": 9999}), api.MAX_TIMEOUT)
        self.assertEqual(api.timeout_seconds({"timeout_seconds": "abc"}), api.DEFAULT_TIMEOUT)


class ToolTests(unittest.TestCase):
    def run_tool(self, cls, parameters, replies):
        replies = iter(replies)
        with patch("shotstack_api.requests.request", side_effect=lambda *a, **k: next(replies)), \
             patch("shotstack_api.time.sleep"):
            return messages(cls.from_credentials(CREDS)._invoke(parameters))

    def test_render_from_json_waits_and_returns_url(self):
        out = self.run_tool(RenderFromJsonTool, {"edit": json.dumps(EDIT)}, [queued(), status("rendering"), status("done")])
        kinds = [m.type.value for m in out]
        self.assertEqual(kinds[:2], ["json", "text"])
        self.assertEqual(out[0].message.json_object["url"], URL)
        self.assertIn(URL, out[1].message.text)
        variables = {m.message.variable_name: m.message.variable_value for m in out if m.type.value == "variable"}
        self.assertEqual(variables["status"], "done")
        self.assertEqual(variables["url"], URL)
        self.assertNotIn("poster", variables)  # null fields are not emitted

    def test_render_from_json_without_waiting_returns_the_id(self):
        out = self.run_tool(RenderFromJsonTool, {"edit": json.dumps(EDIT), "wait": False}, [queued()])
        self.assertEqual(out[0].message.json_object, {"id": "abc", "status": "queued"})

    def test_render_template_tool(self):
        out = self.run_tool(RenderTemplateTool, {"template_id": "tpl", "merge_fields": '{"TITLE": "Hi"}'}, [queued(), status("done")])
        self.assertEqual(out[0].message.json_object["status"], "done")

    def test_get_render_status_tool(self):
        out = self.run_tool(GetRenderStatusTool, {"render_id": "abc"}, [status("rendering")])
        self.assertEqual(out[0].message.json_object["status"], "rendering")
        self.assertIn("ID: abc", out[1].message.text)

    def test_list_templates_tool(self):
        body = {"templates": [{"id": "t1", "name": "Promo", "updated": "2026-11-01T00:00:00Z"}]}
        out = self.run_tool(ListTemplatesTool, {}, [ok(body)])
        self.assertEqual(out[0].message.json_object["templates"][0]["id"], "t1")
        self.assertIn("Promo (t1)", out[1].message.text)

    def test_tool_error_reaches_dify(self):
        with patch("shotstack_api.requests.request", return_value=FakeResponse(400, {"response": {"errors": [{"message": "Invalid type at output"}]}})):
            with self.assertRaisesRegex(api.ShotstackError, "Invalid type at output"):
                messages(RenderFromJsonTool.from_credentials(CREDS)._invoke({"edit": json.dumps(EDIT)}))


class ProviderTests(unittest.TestCase):
    def test_valid_and_invalid_credentials(self):
        with patch("shotstack_api.requests.request", return_value=ok({"templates": []})):
            ShotstackProvider().validate_credentials(CREDS)
        bad = FakeResponse(403, {"errors": [{"detail": "Invalid or disabled API key for the Sandbox API"}]})
        with patch("shotstack_api.requests.request", return_value=bad):
            with self.assertRaisesRegex(ToolProviderCredentialValidationError, "Invalid or disabled"):
                ShotstackProvider().validate_credentials(CREDS)


class PackageTests(unittest.TestCase):
    """The YAML Dify reads: every file the manifest and provider name must exist and parse."""

    def test_yaml_files(self):
        import pathlib
        import yaml
        root = pathlib.Path(__file__).resolve().parent.parent
        manifest = yaml.safe_load((root / "manifest.yaml").read_text(encoding="utf-8"))
        provider = yaml.safe_load((root / manifest["plugins"]["tools"][0]).read_text(encoding="utf-8"))
        self.assertTrue((root / "_assets" / manifest["icon"]).exists())
        self.assertTrue((root / manifest["privacy"]).exists())
        allowed = {"agent", "business", "design", "education", "entertainment", "finance", "image", "news", "other",
                   "productivity", "rag", "search", "social", "travel", "utilities", "videos", "weather", "llm",
                   "model_provider", "audio", "document", "devtools", "database", "security", "translation"}
        self.assertTrue(1 <= len(manifest["tags"]) <= 3 and set(manifest["tags"]) <= allowed)  # Marketplace blocks otherwise
        self.assertTrue((root / provider["extra"]["python"]["source"]).exists())
        for rel in provider["tools"]:
            tool = yaml.safe_load((root / rel).read_text(encoding="utf-8"))
            self.assertTrue((root / tool["extra"]["python"]["source"]).exists(), rel)
            for p in tool["parameters"]:
                self.assertIn(p["form"], ("llm", "form"))
                self.assertTrue(p["human_description"]["en_US"])
            if "render" in rel:  # without output_schema Dify's workflow editor can't pick url, id or status
                self.assertLessEqual({"id", "status", "url"}, set(tool["output_schema"]["properties"]), rel)


if __name__ == "__main__":
    unittest.main()

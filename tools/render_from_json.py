from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

import shotstack_api as api


class RenderFromJsonTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        credentials = self.runtime.credentials
        queued = api.render_from_json(credentials, tool_parameters.get("edit"))
        render_id = queued.get("id")
        if not render_id:
            raise api.ShotstackError("Shotstack did not return a render ID.")
        if api.truthy(tool_parameters.get("wait"), True):
            data = api.summary(api.wait_for_render(credentials, render_id, api.timeout_seconds(tool_parameters)))
            text = f"Render done: {data['url']}"
        else:
            data = {"id": render_id, "status": "queued"}
            text = f"Render queued. ID: {render_id}"
        yield from api.messages(self, data, text)

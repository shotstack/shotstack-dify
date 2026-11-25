from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

import shotstack_api as api


class GetRenderStatusTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        credentials = self.runtime.credentials
        render_id = tool_parameters.get("render_id")
        if api.truthy(tool_parameters.get("wait"), False):
            render = api.wait_for_render(credentials, render_id, api.timeout_seconds(tool_parameters))
        else:
            render = api.get_render(credentials, render_id)
        data = api.summary(render)
        text = f"Render {data['status']}: {data['url']}" if data["url"] else f"Render {data['status']}. ID: {render_id}"
        yield from api.messages(self, data, text)

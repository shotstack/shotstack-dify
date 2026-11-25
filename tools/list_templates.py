from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

import shotstack_api as api


class ListTemplatesTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        templates = api.list_templates(self.runtime.credentials)
        lines = [f"{t['name']} ({t['id']})" for t in templates]
        yield self.create_json_message({"templates": templates})
        yield self.create_text_message("\n".join(lines) if lines else "No templates in this account.")

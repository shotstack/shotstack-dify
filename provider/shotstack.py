from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

import shotstack_api as api


class ShotstackProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        try:
            api.call(credentials, "GET", "/templates")  # free, and a wrong key answers 403
        except api.ShotstackError as e:
            raise ToolProviderCredentialValidationError(str(e)) from e

import json
from typing import Final

import requests
from pydantic import BaseModel, ConfigDict, Field

from delay import DelayTimer

_API_URI_BASE: Final[str] = "https://habitica.com/api/v3"
_SUCCESS_CODES = frozenset([requests.codes.ok, requests.codes.created])  # pylint: disable=no-member
_API_CALLS_DELAY: Final[DelayTimer] = DelayTimer(30, "Waiting for {delay:.0f}s between API calls.")
"""https://habitica.fandom.com/wiki/Guidance_for_Comrades#API_Server_Calls"""


class HabiticaAPIHeaders(BaseModel):
    user_id: str = Field(..., alias="x-api-user")
    api_key: str = Field(..., alias="x-api-key")
    client_id: str = Field("fb0ab2bf-675d-4326-83ba-d03eefe24cef-todoist-habitica-sync", alias="x-client")
    content_type: str = Field("application/json", alias="content-type")
    model_config = ConfigDict(populate_by_name=True)


class HabiticaAPI:
    """Access to Habitica API.

    Based on https://github.com/philadams/habitica/blob/master/habitica/api.py
    """

    def __init__(self, headers: HabiticaAPIHeaders, resource: str | None = None, aspect: str | None = None):
        self._resource = resource
        self._aspect = aspect
        self._headers = headers

    def __getattr__(self, name):
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if not self._resource:
                return HabiticaAPI(headers=self._headers, resource=name)

            return HabiticaAPI(headers=self._headers, resource=self._resource, aspect=name)

    def __call__(self, **kwargs):
        method = kwargs.pop("_method", "get")

        # build up URL... Habitica's api is the *teeniest* bit annoying
        # so either I need to find a cleaner way here, or I should
        # get involved in the API itself and... help it.
        if self._aspect:
            aspect_id = kwargs.pop("_id", None)
            direction = kwargs.pop("_direction", None)
            uri = _API_URI_BASE
            if aspect_id is not None:
                uri = f"{uri}/{self._aspect}/{aspect_id}"
            elif self._aspect == "tasks":
                uri = f"{uri}/{self._aspect}/{self._resource}"
            else:
                uri = f"{uri}/{self._resource}/{self._aspect}"
            if direction is not None:
                uri = f"{uri}/score/{direction}"
        else:
            uri = f"{_API_URI_BASE}/{self._resource}"

        # actually make the request of the API
        http_headers = self._headers.model_dump(by_alias=True)
        _API_CALLS_DELAY()
        if method in ["put", "post", "delete"]:
            res = getattr(requests, method)(uri, headers=http_headers, data=json.dumps(kwargs))
        else:
            res = getattr(requests, method)(uri, headers=http_headers, params=kwargs)

        # print(res.url)  # debug...
        if res.status_code not in _SUCCESS_CODES:
            res.raise_for_status()

        return res.json()["data"]

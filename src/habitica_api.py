import json

import requests

API_URI_BASE = "api/v3"
API_CONTENT_TYPE = "application/json"
SUCCESS_CODES = frozenset(
    [requests.codes.ok, requests.codes.created]  # pylint: disable=no-member
)


class HabiticaAPI:
    """
    Based on https://github.com/philadams/habitica/blob/master/habitica/api.py
    """

    def __init__(self, auth=None, resource=None, aspect=None):
        self.auth = auth
        self.resource = resource
        self.aspect = aspect
        self.headers = auth if auth else {}
        self.headers.update({"content-type": API_CONTENT_TYPE})

    def __getattr__(self, name):
        try:
            return object.__getattr__(self, name)
        except AttributeError:
            if not self.resource:
                return HabiticaAPI(auth=self.auth, resource=name)

            return HabiticaAPI(auth=self.auth, resource=self.resource, aspect=name)

    def __call__(self, **kwargs):
        method = kwargs.pop("_method", "get")

        # build up URL... Habitica's api is the *teeniest* bit annoying
        # so either i need to find a cleaner way here, or i should
        # get involved in the API itself and... help it.
        if self.aspect:
            aspect_id = kwargs.pop("_id", None)
            direction = kwargs.pop("_direction", None)
            uri = "%s/%s" % (self.auth["url"], API_URI_BASE)
            if aspect_id is not None:
                uri = "%s/%s/%s" % (uri, self.aspect, str(aspect_id))
            elif self.aspect == "tasks":
                uri = "%s/%s/%s" % (uri, self.aspect, self.resource)
            else:
                uri = "%s/%s/%s" % (uri, self.resource, self.aspect)
            if direction is not None:
                uri = "%s/score/%s" % (uri, direction)
        else:
            uri = "%s/%s/%s" % (self.auth["url"], API_URI_BASE, self.resource)

        # actually make the request of the API
        if method in ["put", "post", "delete"]:
            res = getattr(requests, method)(
                uri, headers=self.headers, data=json.dumps(kwargs)
            )
        else:
            res = getattr(requests, method)(uri, headers=self.headers, params=kwargs)

        # print(res.url)  # debug...
        if res.status_code not in SUCCESS_CODES:
            res.raise_for_status()

        return res.json()["data"]

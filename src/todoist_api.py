import requests

from models.todoist import TodoistState


class TodoistAPI:
    SYNC_VERSION = "v9"
    _SYNC_ENDPOINT = f"https://api.todoist.com/sync/{SYNC_VERSION}/sync"

    def __init__(self, token: str) -> None:
        self._session = requests.Session()
        self._headers = {"Authorization": f"Bearer {token}"}
        self.state = TodoistState(sync_token="*", full_sync=True)

    def _merge_state(self, new_state: TodoistState) -> None:
        self.state.sync_token = new_state.sync_token
        self.state.full_sync = new_state.full_sync
        self.state.items.update(new_state.items)

    def sync(self) -> bool:
        """Sync resources.

        See Also: https://developer.todoist.com/sync/v9/#read-resources
        """
        response = self._session.post(
            self._SYNC_ENDPOINT,
            headers=self._headers,
            params={"resource_types": '["items"]',
                    "sync_token": self.state.sync_token},
        )

        if response.status_code != 200:
            response.raise_for_status()

        self._merge_state(TodoistState(**response.json()))

        return response.ok

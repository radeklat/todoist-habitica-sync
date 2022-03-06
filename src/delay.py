import logging
import time


class DelayTimer:
    """Sleeps between calls with variable maximum delay.

    If the time between calls is non-zero, it is subtracted from the maximum delay.
    """

    def __init__(self, max_delay: int | float, msg: str | None):
        """Constructor.

        Args:
            max_delay: Maximum sleep time.
            msg: A message to log before sleep. If not set, none will be printed. Accepts one
                keyword ``str.format`` argument ``delay`` with the number of second it will
                sleep for.
        """
        self._max_delay = max_delay
        self._msg = msg
        self._last_api_call: float = max_delay * -1
        self._log = logging.getLogger(self.__class__.__name__)

    def __call__(self) -> None:
        """Sleep and prints a message."""
        if delay := max(0.0, self._max_delay - (time.monotonic() - self._last_api_call)):
            if self._msg is not None:
                self._log.info(self._msg.format(delay=delay))
            time.sleep(delay)
        self._last_api_call = time.monotonic()

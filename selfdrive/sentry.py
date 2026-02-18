import sentry_sdk

from selfdrive.swaglog import cloudlog
from selfdrive.version import get_commit, get_origin, get_short_branch, is_dirty, is_official
from common.system import is_android, is_android_rooted


def set_tag(key: str, value: str) -> None:
    sentry_sdk.set_tag(key, value)

def sentry_init() -> None:
    # Telemetry disabled
    return

def report_tombstone(fn: str, message: str, contents: str) -> None:
  cloudlog.error({'tombstone': message})

  with sentry_sdk.configure_scope() as scope:
    scope.set_extra("tombstone_fn", fn)
    scope.set_extra("tombstone", contents)
    sentry_sdk.capture_message(message=message)
    sentry_sdk.flush()


def capture_error(error, level) -> None:
    # Telemetry disabled
    pass
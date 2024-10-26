from contextvars import ContextVar

CURRENT_VAR_ID = ContextVar("CURRENT_VAR_ID", default=0)
UNIQUE_COUNT_ID = ContextVar("UNIQUE_COUNT_ID", default=1)

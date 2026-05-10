"""User-visible pipeline abort (interactive gates)."""


class PivotPipelineUserAbort(Exception):
    """Raised when the operator chooses to stop the run at a confirmation prompt."""

    pass


__all__ = ["PivotPipelineUserAbort"]

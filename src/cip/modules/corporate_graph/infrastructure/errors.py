class GraphNodeNotFoundError(LookupError):
    """Requested graph node does not exist."""


class ResolutionCandidateNotFoundError(LookupError):
    """Requested entity-resolution candidate does not exist."""

from __future__ import annotations


class SourcePortfolioNotFoundError(LookupError):
    pass


class SourcePortfolioStateError(RuntimeError):
    pass

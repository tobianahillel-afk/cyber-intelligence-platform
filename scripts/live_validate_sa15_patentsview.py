from __future__ import annotations


class PatentsViewCurrentContractUnavailable(RuntimeError):
    """Raised while the current USPTO ODP production contract is not implemented."""


def main() -> None:
    raise PatentsViewCurrentContractUnavailable(
        "PatentsView legacy PatentSearch live validation is disabled. "
        "Implement and govern the current USPTO Open Data Portal endpoint/schema/credential "
        "contract before any provider credential is read or any network request is attempted."
    )


if __name__ == "__main__":
    main()

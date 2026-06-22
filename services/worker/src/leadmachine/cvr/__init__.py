"""CVR discovery client interface (implemented in M1, issue #14).

Isolated behind a Protocol so the Datafordeler GraphQL API can replace the
Elasticsearch bulk channel when the REST distribution sunsets (Q2 2026)
without touching callers.
"""

from typing import Any, Iterable, Protocol


class CvrClient(Protocol):
    def search(
        self,
        *,
        branchekoder: list[str],
        postnumre: list[str] | None = None,
        employee_bands: list[str] | None = None,
    ) -> Iterable[dict[str, Any]]:
        """Yield raw CVR company records matching the filters."""
        ...

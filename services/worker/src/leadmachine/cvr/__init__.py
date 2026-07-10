"""CVR discovery (M1).

Public facade for the CVR discovery engine: find Danish businesses by
branchekode + area, dedup by CVR number, and suppress protected / inactive
entities.

The :class:`CvrClient` Protocol isolates the data source so the Datafordeler
GraphQL API can replace the Elasticsearch bulk channel when the REST
distribution sunsets (Q2 2026) without touching callers.
"""

from __future__ import annotations

from typing import Any, Iterable, Protocol

from .query import SearchParameters


class CvrClient(Protocol):
    def search(self, params: SearchParameters) -> Iterable[dict[str, Any]]:
        """Yield raw CVR company records matching the search parameters."""
        ...


# Re-exports (imported after CvrClient so submodules can type-hint against it).
from .branchekoder import Branche, all_branches, by_code, grouped  # noqa: E402
from .client import EsCvrClient  # noqa: E402
from .discovery import (  # noqa: E402
    DiscoveryStats,
    LeadWriter,
    SupabaseLeadWriter,
    run_discovery,
)
from .mapper import MappedLead, map_company  # noqa: E402
from .penhed import (  # noqa: E402
    EsPenhedClient,
    PenhedClient,
    PenhedInfo,
    current_pnummer,
    map_penhed,
)
from .query import build_es_query  # noqa: E402

__all__ = [
    "CvrClient",
    "SearchParameters",
    "build_es_query",
    "EsCvrClient",
    "MappedLead",
    "map_company",
    "PenhedInfo",
    "PenhedClient",
    "EsPenhedClient",
    "map_penhed",
    "current_pnummer",
    "run_discovery",
    "DiscoveryStats",
    "LeadWriter",
    "SupabaseLeadWriter",
    "Branche",
    "all_branches",
    "by_code",
    "grouped",
]

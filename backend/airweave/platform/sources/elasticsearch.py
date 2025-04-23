"""Elasticsearch source implementation.

This source connects to an Elasticsearch cluster and retrieves index metadata and documents
todo: for protected access indices using API key authentication.
"""

from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from airweave.platform.auth.schemas import AuthType
from airweave.platform.configs.auth import ElasticsearchAuthConfig
from airweave.platform.decorators import source
from airweave.platform.entities._base import ChunkEntity
from airweave.platform.entities.elasticsearch import (
    ElasticsearchDocumentEntity,
    ElasticsearchIndexEntity,
)
from airweave.platform.sources._base import BaseSource


@source(
    "Elasticsearch",
    "elasticsearch",
    AuthType.config_class,
    "ElasticsearchAuthConfig",
    labels=["Search", "Database"],
)
class ElasticsearchSource(BaseSource):
    """Elasticsearch source implementation.

    Connects to an Elasticsearch cluster, retrieves index metadata and documents
    for configured indices using the scroll API.
    """

    def __init__(self):
        """Initialize the Elasticsearch source."""
        self.url: str = ""
        self.api_key: Optional[str] = None
        self.indices: str = "*"
        self.fields: Optional[str] = None

    @classmethod
    async def create(cls, config: ElasticsearchAuthConfig) -> "ElasticsearchSource":
        """Create a new Elasticsearch source instance."""
        instance = cls()
        instance.url = f"http://{config.host}:{config.port}"
        instance.api_key = getattr(config, "api_key", None)
        instance.indices = config.indices
        instance.fields = getattr(config, "fields", None)
        return instance

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _get(
        self,
        client: httpx.AsyncClient,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Make an authenticated GET request to the Elasticsearch API."""
        headers = {"Authorization": f"ApiKey {self.api_key}"} if self.api_key else {}
        response = await client.get(path, params=params, headers=headers)
        response.raise_for_status()
        return response.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def _post(self, client: httpx.AsyncClient, path: str, json_body: Dict[str, Any]) -> Any:
        """Make an authenticated POST request to the Elasticsearch API."""
        headers = (
            {
                "Authorization": f"ApiKey {self.api_key}",
                "Content-Type": "application/json",
            }
            if self.api_key
            else {"Content-Type": "application/json"}
        )
        response = await client.post(path, json=json_body, headers=headers)
        response.raise_for_status()
        return response.json()

    async def generate_entities(self) -> AsyncGenerator[ChunkEntity, None]:
        """Generate Elasticsearch index and document entities."""
        async with httpx.AsyncClient(base_url=self.url) as client:
            # Get all indices and their stats
            params = {
                "format": "json",
                "h": "index,health,status,docs.count,docs.deleted,store.size",
            }
            indices_data = await self._get(client, "/_cat/indices", params=params)

            # Determine which indices to sync
            if self.indices and self.indices != "*":
                allowed_indices = [i.strip() for i in self.indices.split(",")]
            else:
                allowed_indices = None

            for idx in indices_data:
                index_name = idx.get("index")
                if allowed_indices and index_name not in allowed_indices:
                    continue

                # Yield index metadata
                yield ElasticsearchIndexEntity(
                    entity_id=index_name,
                    index=index_name,
                    health=idx.get("health"),
                    status=idx.get("status"),
                    docs_count=int(idx.get("docs.count", 0)),
                    docs_deleted=int(idx.get("docs.deleted", 0)),
                    store_size=idx.get("store.size"),
                )

                # Fetch and yield documents using scroll API
                BATCH_SIZE = 100
                search_body = {"query": {"match_all": {}}, "size": BATCH_SIZE}
                if self.fields and self.fields != "*":
                    search_body["_source"] = self.fields
                data = await self._post(client, f"/{index_name}/_search?scroll=1m", search_body)
                scroll_id = data.get("_scroll_id")
                hits = data.get("hits", {}).get("hits", [])

                for hit in hits:
                    yield ElasticsearchDocumentEntity(
                        entity_id=f"{index_name}-{hit.get('_id')}",
                        index=index_name,
                        doc_id=hit.get("_id"),
                        source=hit.get("_source", {}),
                    )

                # Continue scrolling until no more hits
                while hits:
                    scroll_data = {"scroll_id": scroll_id, "scroll": "1m"}
                    data = await self._post(client, "/_search/scroll", scroll_data)
                    hits = data.get("hits", {}).get("hits", [])
                    scroll_id = data.get("_scroll_id", scroll_id)
                    if not hits:
                        break
                    for hit in hits:
                        yield ElasticsearchDocumentEntity(
                            entity_id=f"{index_name}-{hit.get('_id')}",
                            index=index_name,
                            doc_id=hit.get("_id"),
                            source=hit.get("_source", {}),
                        )

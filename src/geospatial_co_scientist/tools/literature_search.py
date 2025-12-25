"""Literature search tools for the Co-Scientist."""

import asyncio
import logging
from typing import Any, Optional

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from tenacity import retry, stop_after_attempt, wait_exponential

from geospatial_co_scientist.config import get_settings
from geospatial_co_scientist.models.research import LiteratureReference

logger = logging.getLogger(__name__)


class SearchResult(BaseModel):
    """A search result from literature search."""

    title: str
    authors: list[str] = Field(default_factory=list)
    year: Optional[int] = None
    abstract: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    source: str = ""
    citation_count: int = 0
    relevance_score: float = 0.0


class LiteratureSearchTool:
    """Tool for searching academic literature."""

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_semantic_scholar(
        self,
        query: str,
        limit: int = 10,
        fields: Optional[list[str]] = None
    ) -> list[SearchResult]:
        """
        Search Semantic Scholar for academic papers.

        Args:
            query: Search query string
            limit: Maximum number of results
            fields: Fields to retrieve

        Returns:
            List of search results
        """
        if fields is None:
            fields = [
                "title", "authors", "year", "abstract",
                "externalIds", "url", "citationCount"
            ]

        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": query,
            "limit": min(limit, self.settings.search_results_limit),
            "fields": ",".join(fields)
        }

        headers = {}
        if self.settings.semantic_scholar_api_key:
            headers["x-api-key"] = self.settings.semantic_scholar_api_key

        try:
            response = await self.client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            results = []
            for paper in data.get("data", []):
                authors = [
                    a.get("name", "") for a in paper.get("authors", [])
                ]
                external_ids = paper.get("externalIds", {})

                result = SearchResult(
                    title=paper.get("title", ""),
                    authors=authors,
                    year=paper.get("year"),
                    abstract=paper.get("abstract"),
                    doi=external_ids.get("DOI"),
                    url=paper.get("url"),
                    source="Semantic Scholar",
                    citation_count=paper.get("citationCount", 0)
                )
                results.append(result)

            return results

        except httpx.HTTPError as e:
            logger.error(f"Semantic Scholar search failed: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def search_crossref(
        self,
        query: str,
        limit: int = 10
    ) -> list[SearchResult]:
        """
        Search CrossRef for academic papers.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of search results
        """
        url = "https://api.crossref.org/works"
        params = {
            "query": query,
            "rows": min(limit, self.settings.search_results_limit),
            "select": "DOI,title,author,published,abstract,container-title"
        }

        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("message", {}).get("items", []):
                title_list = item.get("title", [])
                title = title_list[0] if title_list else ""

                authors = []
                for author in item.get("author", []):
                    name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                    if name:
                        authors.append(name)

                published = item.get("published", {})
                year = None
                if "date-parts" in published and published["date-parts"]:
                    year = published["date-parts"][0][0] if published["date-parts"][0] else None

                container = item.get("container-title", [])
                source = container[0] if container else "CrossRef"

                result = SearchResult(
                    title=title,
                    authors=authors,
                    year=year,
                    abstract=item.get("abstract"),
                    doi=item.get("DOI"),
                    url=f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else None,
                    source=source
                )
                results.append(result)

            return results

        except httpx.HTTPError as e:
            logger.error(f"CrossRef search failed: {e}")
            return []

    async def search_multiple_sources(
        self,
        query: str,
        limit_per_source: int = 10
    ) -> list[SearchResult]:
        """
        Search multiple sources concurrently.

        Args:
            query: Search query string
            limit_per_source: Maximum results per source

        Returns:
            Combined list of search results
        """
        tasks = [
            self.search_semantic_scholar(query, limit_per_source),
            self.search_crossref(query, limit_per_source),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        combined = []
        for result in results:
            if isinstance(result, list):
                combined.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Search source failed: {result}")

        # Deduplicate by DOI
        seen_dois = set()
        unique_results = []
        for r in combined:
            if r.doi:
                if r.doi not in seen_dois:
                    seen_dois.add(r.doi)
                    unique_results.append(r)
            else:
                unique_results.append(r)

        return unique_results

    def to_literature_references(
        self,
        results: list[SearchResult]
    ) -> list[LiteratureReference]:
        """Convert search results to LiteratureReference objects."""
        references = []
        for r in results:
            ref = LiteratureReference(
                title=r.title,
                authors=r.authors,
                year=r.year,
                source=r.source,
                doi=r.doi,
                url=r.url,
                abstract=r.abstract,
                relevance_score=r.relevance_score
            )
            references.append(ref)
        return references


# Singleton instance
_search_tool: Optional[LiteratureSearchTool] = None


def get_search_tool() -> LiteratureSearchTool:
    """Get the singleton search tool instance."""
    global _search_tool
    if _search_tool is None:
        _search_tool = LiteratureSearchTool()
    return _search_tool


@tool
async def search_semantic_scholar(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Search Semantic Scholar for academic papers related to the query.

    Args:
        query: Search query for finding relevant papers
        limit: Maximum number of results to return

    Returns:
        List of paper information including title, authors, year, abstract
    """
    tool = get_search_tool()
    results = await tool.search_semantic_scholar(query, limit)
    return [r.model_dump() for r in results]


class WebSearchTool:
    """Tool for web search with support for multiple providers."""

    def __init__(self):
        self.settings = get_settings()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def search(
        self,
        query: str,
        num_results: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search the web using the configured provider.

        Args:
            query: Search query
            num_results: Number of results to return

        Returns:
            List of search results with title, url, and snippet
        """
        provider = self.settings.web_search_provider.lower()

        if provider == "tavily" and self.settings.tavily_api_key:
            return await self._search_tavily(query, num_results)
        elif provider == "serper" and self.settings.serper_api_key:
            return await self._search_serper(query, num_results)
        else:
            # Default to DuckDuckGo (no API key required)
            return await self._search_duckduckgo(query, num_results)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _search_duckduckgo(
        self,
        query: str,
        num_results: int = 5
    ) -> list[dict[str, Any]]:
        """
        Search using DuckDuckGo HTML interface.

        This is a simple implementation that doesn't require an API key.
        """
        import re
        from urllib.parse import quote_plus, unquote

        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = await self.client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            html = response.text

            results = []
            # Extract results using regex (simple HTML parsing)
            # Look for result links and snippets
            result_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
            snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+(?:<[^/][^>]*>[^<]*</[^>]*>)*[^<]*)</a>'

            links = re.findall(result_pattern, html)
            snippets = re.findall(snippet_pattern, html)

            for i, (link, title) in enumerate(links[:num_results]):
                # DuckDuckGo uses redirect URLs, extract actual URL
                if "uddg=" in link:
                    actual_url = re.search(r'uddg=([^&]+)', link)
                    if actual_url:
                        link = unquote(actual_url.group(1))

                snippet = snippets[i] if i < len(snippets) else ""
                # Clean HTML tags from snippet
                snippet = re.sub(r'<[^>]+>', '', snippet).strip()

                results.append({
                    "title": title.strip(),
                    "url": link,
                    "snippet": snippet[:500] if snippet else "No description available"
                })

            if not results:
                logger.warning("DuckDuckGo search returned no results")
                return [{
                    "title": f"No results for: {query}",
                    "url": "",
                    "snippet": "Try refining your search query"
                }]

            return results

        except httpx.HTTPError as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _search_tavily(
        self,
        query: str,
        num_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search using Tavily API."""
        url = "https://api.tavily.com/search"

        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": num_results
        }

        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:500]
                })

            return results

        except httpx.HTTPError as e:
            logger.error(f"Tavily search failed: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _search_serper(
        self,
        query: str,
        num_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search using Serper API."""
        url = "https://google.serper.dev/search"

        headers = {
            "X-API-KEY": self.settings.serper_api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }

        try:
            response = await self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", "")[:500]
                })

            return results

        except httpx.HTTPError as e:
            logger.error(f"Serper search failed: {e}")
            return []


# Singleton instance for web search
_web_search_tool: Optional[WebSearchTool] = None


def get_web_search_tool() -> WebSearchTool:
    """Get the singleton web search tool instance."""
    global _web_search_tool
    if _web_search_tool is None:
        _web_search_tool = WebSearchTool()
    return _web_search_tool


@tool
async def search_web(query: str, num_results: int = 5) -> list[dict[str, Any]]:
    """
    Search the web for relevant information.

    Uses the configured web search provider (DuckDuckGo by default,
    or Tavily/Serper if API keys are configured).

    Args:
        query: Search query
        num_results: Number of results to return

    Returns:
        List of search results with title, url, and snippet
    """
    tool = get_web_search_tool()
    return await tool.search(query, num_results)


class GeospatialLiteratureSearch(LiteratureSearchTool):
    """Specialized literature search for geospatial topics."""

    GEOSPATIAL_KEYWORDS = [
        "remote sensing", "GIS", "satellite imagery", "geospatial",
        "Landsat", "Sentinel", "MODIS", "LiDAR", "spatial analysis",
        "earth observation", "land use", "land cover", "NDVI",
        "geographic information", "raster", "vector data"
    ]

    GEOSPATIAL_JOURNALS = [
        "Remote Sensing of Environment",
        "International Journal of Applied Earth Observation and Geoinformation",
        "ISPRS Journal of Photogrammetry and Remote Sensing",
        "Computers & Geosciences",
        "GIScience & Remote Sensing",
        "International Journal of Geographical Information Science",
        "Photogrammetric Engineering & Remote Sensing",
    ]

    def enhance_query(self, query: str) -> str:
        """Enhance query with geospatial context."""
        # Check if query already has geospatial terms
        query_lower = query.lower()
        has_geo_term = any(kw in query_lower for kw in self.GEOSPATIAL_KEYWORDS)

        if not has_geo_term:
            # Add context
            query = f"{query} remote sensing geospatial"

        return query

    async def search_geospatial_literature(
        self,
        query: str,
        limit: int = 20
    ) -> list[SearchResult]:
        """
        Search for geospatial-specific literature.

        Args:
            query: Research query
            limit: Maximum results

        Returns:
            List of relevant papers
        """
        enhanced_query = self.enhance_query(query)
        results = await self.search_multiple_sources(enhanced_query, limit // 2)

        # Sort by citation count as a proxy for relevance
        results.sort(key=lambda x: x.citation_count, reverse=True)

        return results[:limit]

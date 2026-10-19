import io

import httpx
import pandas as pd
from bs4 import BeautifulSoup
from fastmcp import FastMCP


def register_tools(mcp: FastMCP) -> None:
    """Register the shared toolbox (HTTP, HTML parsing, CSV analysis) on an MCP server."""

    @mcp.tool()
    def fetch_url(url: str) -> dict:
        """Fetch a URL over HTTP GET and return status code, headers, and truncated body text."""
        resp = httpx.get(url, timeout=10, follow_redirects=True)
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "text": resp.text[:2000],
        }

    @mcp.tool()
    def extract_links(html: str) -> list[str]:
        """Extract all hyperlink URLs (href attributes) from an HTML document."""
        soup = BeautifulSoup(html, "html.parser")
        return [a["href"] for a in soup.find_all("a", href=True)]

    @mcp.tool()
    def extract_text(html: str) -> str:
        """Extract visible text from an HTML document, stripping tags, scripts, and styles."""
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        return " ".join(soup.stripped_strings)

    @mcp.tool()
    def csv_summary(csv_text: str) -> dict:
        """Parse CSV text with pandas and return shape, columns, dtypes, and summary statistics."""
        df = pd.read_csv(io.StringIO(csv_text))
        return {
            "shape": list(df.shape),
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "describe": df.describe(include="all").fillna("").to_dict(),
        }

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from paperchat.api.errcode import AppError


ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_arxiv_entry(entry: ET.Element) -> dict:
    title = (entry.findtext("atom:title", default="", namespaces=ATOM_NS) or "").strip().replace("\n", " ")
    summary = (entry.findtext("atom:summary", default="", namespaces=ATOM_NS) or "").strip()
    entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
    published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
    authors = [
        (author.findtext("atom:name", default="", namespaces=ATOM_NS) or "").strip()
        for author in entry.findall("atom:author", ATOM_NS)
    ]
    pdf_url = None
    for link in entry.findall("atom:link", ATOM_NS):
        if link.attrib.get("title") == "pdf":
            pdf_url = link.attrib.get("href")
            break

    return {
        "title": title,
        "summary": summary,
        "entry_id": entry_id,
        "published": published,
        "authors": authors,
        "pdf_url": pdf_url,
    }


async def search_arxiv_entries(*, keyword: str, max_results: int = 5) -> list[dict]:
    query = f"http://export.arxiv.org/api/query?search_query=all:{quote_plus(keyword)}&start=0&max_results={max_results}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(query)
        response.raise_for_status()

    root = ET.fromstring(response.text)
    entries = root.findall("atom:entry", ATOM_NS)
    return [_parse_arxiv_entry(entry) for entry in entries]


async def fetch_arxiv_entry(*, keyword: str, arxiv_id: str | None = None) -> dict:
    if arxiv_id:
        query = f"http://export.arxiv.org/api/query?id_list={quote_plus(arxiv_id)}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(query)
            response.raise_for_status()

        root = ET.fromstring(response.text)
        entry = root.find("atom:entry", ATOM_NS)
        if entry is None:
            raise AppError(status_code=404, code="KNOWLEDGE_NOT_FOUND", message="未找到对应 arXiv 论文")
        parsed = _parse_arxiv_entry(entry)
        if not parsed["title"]:
            parsed["title"] = keyword
        return parsed

    entries = await search_arxiv_entries(keyword=keyword, max_results=1)
    if not entries:
        raise AppError(status_code=404, code="KNOWLEDGE_NOT_FOUND", message="未找到对应 arXiv 论文")
    entry = entries[0]
    if not entry["title"]:
        entry["title"] = keyword
    return entry

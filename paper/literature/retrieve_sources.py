"""Record public literature searches and original-source retrievals for the gap audit.

Run in the independent writing-tools environment. No experiment inputs are changed.
Retrieval and metadata success do not establish claim support.
"""
import argparse
import concurrent.futures
import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import requests

ROOT = Path(__file__).resolve().parent
CHECK_DATE = "2026-09-29"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metadata = {}
        self.links = []
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in {"script", "style"}:
            self.hidden += 1
        if tag == "meta":
            key = a.get("name", a.get("property", ""))
            self.metadata.setdefault(key, []).append(a.get("content", ""))
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
        if tag in {"p", "div", "section", "h1", "h2", "h3", "li", "br", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)

    def text(self):
        return "\n".join(" ".join(x.split()) for x in "".join(self.parts).splitlines() if x.strip())


def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def retrieve(url, params=None):
    r = requests.get(url, params=params, timeout=40, headers={"User-Agent": "BACE-literature-audit/1.0 (public scholarly sources)"})
    return r


def search_one(item):
    result = dict(item, checked_date=CHECK_DATE, retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        backend = item["backend"]
        if backend == "crossref":
            url = "https://api.crossref.org/works"
            params = {"query.bibliographic": item["query"], "rows": item.get("limit", 15)}
        elif backend == "openalex":
            url = "https://api.openalex.org/works"
            params = {"search": item["query"], "per-page": item.get("limit", 15), "filter": "to_publication_date:2026-09-29"}
        else:
            raise ValueError(backend)
        r = retrieve(url, params)
        result.update(request_url=r.url, http_status=r.status_code, raw_sha256=hashlib.sha256(r.content).hexdigest())
        body = r.json()
        save_json(ROOT / "searches" / (item["id"] + ".response.json"), body)
        r.raise_for_status()
        works = body.get("message", {}).get("items", []) if backend == "crossref" else body.get("results", [])
        result["results"] = [{
            "title": w.get("title") if backend == "crossref" else w.get("display_name"),
            "doi": w.get("DOI", w.get("doi")),
            "url": w.get("URL", w.get("id")),
            "published": w.get("published", w.get("publication_date")),
            "locations": w.get("locations", w.get("link", [])),
        } for w in works]
        result["total_results"] = body.get("message", {}).get("total-results") if backend == "crossref" else body.get("meta", {}).get("count")
    except Exception as exc:
        result["error"] = str(exc)
    save_json(ROOT / "searches" / (item["id"] + ".json"), result)
    return result


def fetch_one(item):
    folder = ROOT / "sources" / item["id"]
    folder.mkdir(parents=True, exist_ok=True)
    result = dict(item, checked_date=CHECK_DATE, retrieved_at_utc=datetime.now(timezone.utc).isoformat())
    try:
        r = retrieve(item["url"])
        result.update(final_url=r.url, http_status=r.status_code, content_type=r.headers.get("Content-Type"), sha256=hashlib.sha256(r.content).hexdigest())
        r.raise_for_status()
        pdf_bytes = None
        if r.content.startswith(b"%PDF"):
            pdf_bytes = r.content
            result["pdf_url"] = r.url
        else:
            (folder / "original.html").write_bytes(r.content)
            page = PageParser()
            page.feed(r.text)
            (folder / "page.txt").write_text(page.text() + "\n")
            result["metadata"] = page.metadata
            result["links"] = page.links
            candidates = page.metadata.get("citation_pdf_url", [])
            if not candidates and item.get("follow_pdf", True):
                candidates = [u for u in page.links if u.split("?")[0].lower().endswith(".pdf")]
            if item.get("follow_pdf", True) and candidates:
                pdf_url = urljoin(r.url, candidates[0])
                result["pdf_request_url"] = pdf_url
                rp = retrieve(pdf_url)
                result.update(pdf_url=rp.url, pdf_http_status=rp.status_code)
                if rp.ok and rp.content.startswith(b"%PDF"):
                    pdf_bytes = rp.content
        if pdf_bytes:
            pdf_path = folder / "original.pdf"
            pdf_path.write_bytes(pdf_bytes)
            result["pdf_sha256"] = hashlib.sha256(pdf_bytes).hexdigest()
            raw = subprocess.run(["pdftotext", "-layout", str(pdf_path), "-"], capture_output=True, check=True).stdout.decode("utf-8")
            pages = raw.split("\f")
            if pages and not pages[-1].strip():
                pages.pop()
            text = "\n".join(f"=== PDF page {i} ===\n{page}" for i, page in enumerate(pages, 1))
            (folder / "fulltext.txt").write_text(text)
            result.update(pdf_pages=len(pages), text_sha256=hashlib.sha256(text.encode()).hexdigest(), fulltext_extracted=True)
        else:
            result["fulltext_extracted"] = False
    except Exception as exc:
        result["error"] = str(exc)
    save_json(folder / "retrieval.json", result)
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["search", "fetch"])
    p.add_argument("config", type=Path)
    p.add_argument("--workers", type=int, default=4)
    a = p.parse_args()
    items = json.loads(a.config.read_text())
    fn = search_one if a.mode == "search" else fetch_one
    save_json(ROOT / "environment.json", {"python": platform.python_version(), "requests": requests.__version__, "checked_date": CHECK_DATE})
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
        for result in pool.map(fn, items):
            if a.mode == "search":
                print(json.dumps({k: result.get(k) for k in ["id", "query", "http_status", "error", "total_results"]}), flush=True)
                for w in result.get("results", []):
                    print(json.dumps({k: w.get(k) for k in ["title", "doi", "published"]}, ensure_ascii=False), flush=True)
            else:
                print(json.dumps({k: result.get(k) for k in ["id", "http_status", "error", "fulltext_extracted", "pdf_pages", "pdf_url"]}), flush=True)


if __name__ == "__main__":
    main()

import re
import urllib.parse
import urllib.request
import json
import os
from typing import List, Dict, Set, Optional
from bs4 import BeautifulSoup
from app.config import settings
from app.core.logging import logger
from app.rag.cleaner import clean_html, clean_text

class TechvunexCrawler:
    """
    Crawls Techvunex website, parses sitemap.xml, normalizes internal URLs,
    extracts content for both SSR HTML and SPA bundle components.
    """
    def __init__(self, base_url: str = settings.TECHVUNEX_BASE_URL):
        self.base_url = self.normalize_url(base_url)
        self.parsed_base = urllib.parse.urlparse(self.base_url)
        self.visited_urls: Set[str] = set()

    @staticmethod
    def normalize_url(url: str) -> str:
        """
        Normalize URL:
        - lowercase scheme and host
        - remove fragments
        - remove analytics query parameters
        - strip trailing slash except for root domain
        """
        parsed = urllib.parse.urlparse(url)
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()

        # Filter query params
        query_pairs = urllib.parse.parse_qsl(parsed.query)
        clean_query = [(k, v) for k, v in query_pairs if not k.startswith("utm_") and k not in ("fbclid", "gclid", "ref")]
        new_query = urllib.parse.urlencode(clean_query)

        # Normalize path
        path = parsed.path
        if path.endswith("/") and len(path) > 1:
            path = path[:-1]
        if not path:
            path = "/"

        normalized = urllib.parse.urlunparse((scheme, netloc, path, "", new_query, ""))
        return normalized

    def is_internal(self, url: str) -> bool:
        """Verify URL belongs to techvunex.in"""
        parsed = urllib.parse.urlparse(url)
        return parsed.netloc == self.parsed_base.netloc or not parsed.netloc

    def fetch_sitemap(self) -> List[str]:
        """Fetch URLs declared in sitemap.xml"""
        sitemap_url = urllib.parse.urljoin(self.base_url, "/sitemap.xml")
        urls = []
        try:
            req = urllib.request.Request(sitemap_url, headers={"User-Agent": "TechvunexBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                xml_data = resp.read().decode("utf-8", errors="ignore")
                soup = BeautifulSoup(xml_data, "xml")
                for loc in soup.find_all("loc"):
                    loc_text = loc.get_text(strip=True)
                    if loc_text:
                        urls.append(self.normalize_url(loc_text))
            logger.info(f"Discovered {len(urls)} URLs from sitemap.xml")
        except Exception as e:
            logger.warning(f"Could not fetch sitemap.xml: {e}. Falling back to standard seed URLs.")
            urls = [
                self.base_url,
                f"{self.base_url}/about",
                f"{self.base_url}/portfolio",
                f"{self.base_url}/contact",
                f"{self.base_url}/services/website-development",
                f"{self.base_url}/services/app-development",
                f"{self.base_url}/services/custom-software",
                f"{self.base_url}/services/crm-erp",
                f"{self.base_url}/services/ai-automation",
                f"{self.base_url}/services/ui-ux-design",
                f"{self.base_url}/services/digital-marketing",
                f"{self.base_url}/services/cloud-solutions",
                f"{self.base_url}/solutions/crm-erp",
                f"{self.base_url}/solutions/business-automation",
                f"{self.base_url}/solutions/ai-integration",
                f"{self.base_url}/solutions/cloud-infrastructure",
                f"{self.base_url}/solutions/ui-ux-consulting",
                f"{self.base_url}/solutions/seo-optimization",
                f"{self.base_url}/solutions/digital-transformation",
                f"{self.base_url}/solutions/enterprise-solutions",
            ]
        return urls

    def extract_links(self, html: str, current_url: str) -> List[str]:
        """Extract valid internal links from page HTML"""
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            abs_url = urllib.parse.urljoin(current_url, href)
            norm_url = self.normalize_url(abs_url)
            if self.is_internal(norm_url):
                links.append(norm_url)
        return list(set(links))

    def fetch_url(self, url: str) -> Optional[Dict[str, str]]:
        """Fetch page content, extract title, description, and text"""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TechvunexBot/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
                
                soup = BeautifulSoup(html, "html.parser")
                title = soup.title.string.strip() if soup.title and soup.title.string else "Techvunex Innovation"
                
                meta_desc = ""
                desc_tag = soup.find("meta", attrs={"name": "description"})
                if desc_tag and desc_tag.get("content"):
                    meta_desc = desc_tag["content"].strip()

                content = clean_html(html)
                return {
                    "url": url,
                    "title": title,
                    "description": meta_desc,
                    "content": content,
                    "html": html
                }
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def crawl_all(self, max_pages: int = 50) -> List[Dict[str, str]]:
        """
        Crawl Techvunex site combining sitemap and internal discovery.
        """
        seed_urls = self.fetch_sitemap()
        queue = list(seed_urls)
        discovered_pages: List[Dict[str, str]] = []

        while queue and len(self.visited_urls) < max_pages:
            current_url = queue.pop(0)
            if current_url in self.visited_urls:
                continue

            self.visited_urls.add(current_url)
            logger.info(f"Crawling: {current_url}")
            page_data = self.fetch_url(current_url)
            if not page_data:
                continue

            # Extract any new internal links
            if "html" in page_data:
                links = self.extract_links(page_data["html"], current_url)
                for lk in links:
                    if lk not in self.visited_urls and lk not in queue:
                        queue.append(lk)
                del page_data["html"]

            discovered_pages.append(page_data)

        logger.info(f"Crawl completed. {len(discovered_pages)} pages collected.")
        return discovered_pages

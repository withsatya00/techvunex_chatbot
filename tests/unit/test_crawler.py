import pytest
from app.rag.crawler import TechvunexCrawler
from app.rag.cleaner import clean_html, clean_text

def test_url_normalization():
    crawler = TechvunexCrawler()
    
    # Trailing slash stripping
    assert crawler.normalize_url("https://techvunex.in/about/") == "https://techvunex.in/about"
    
    # Root domain retains slash
    assert crawler.normalize_url("https://techvunex.in/") == "https://techvunex.in/"
    
    # Query parameters stripped (utm, ref)
    norm = crawler.normalize_url("https://techvunex.in/services/crm-erp?utm_source=google&ref=chat#section-1")
    assert norm == "https://techvunex.in/services/crm-erp"

    # Lowercasing scheme and host
    assert crawler.normalize_url("HTTPS://TECHVUNEX.IN/Contact") == "https://techvunex.in/Contact"

def test_internal_url_check():
    crawler = TechvunexCrawler("https://techvunex.in/")
    assert crawler.is_internal("https://techvunex.in/services") is True
    assert crawler.is_internal("https://google.com") is False
    assert crawler.is_internal("https://other-domain.in/about") is False

def test_clean_html():
    raw_html = """
    <html>
      <head><script>alert('hack')</script><style>body{color:red}</style></head>
      <body>
        <nav><a href="/">Home</a></nav>
        <h1>About Techvunex</h1>
        <p>Techvunex is an engineering company in India.</p>
        <ul>
          <li>Custom Software</li>
          <li>CRM & ERP</li>
        </ul>
        <footer>Copyright 2026</footer>
      </body>
    </html>
    """
    cleaned = clean_html(raw_html)
    assert "# About Techvunex" in cleaned
    assert "Techvunex is an engineering company" in cleaned
    assert "Custom Software" in cleaned
    assert "alert('hack')" not in cleaned
    assert "Copyright 2026" not in cleaned

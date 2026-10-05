import re
from bs4 import BeautifulSoup

def clean_html(html_content: str) -> str:
    """
    Cleans raw HTML: removes navigation, scripts, svg, styles,
    while preserving headings, lists, paragraphs, CTA buttons, and pricing details.
    Preserves numbers, currencies (₹, INR, $), percentages (%), and terms (EMI, zero-cost).
    """
    if not html_content:
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # Remove non-content structural elements (do NOT decompose buttons if they contain pricing or CTA text)
    for element in soup(["script", "style", "nav", "footer", "svg", "noscript", "iframe"]):
        element.decompose()


    # Convert buttons into readable text instead of deleting them
    for btn in soup.find_all("button"):
        btn_text = btn.get_text(strip=True)
        if btn_text:
            btn.replace_with(f" [Button: {btn_text}] ")
        else:
            btn.decompose()

    # Convert headings to markdown
    for i in range(1, 7):
        for h in soup.find_all(f"h{i}"):
            h_text = h.get_text(strip=True)
            if h_text:
                h.replace_with(f"\n\n{'#' * i} {h_text}\n")

    # Convert list items
    for li in soup.find_all("li"):
        li_text = li.get_text(strip=True)
        if li_text:
            li.replace_with(f"\n- {li_text}")

    # Convert paragraphs
    for p in soup.find_all("p"):
        p_text = p.get_text(strip=True)
        if p_text:
            p.replace_with(f"\n\n{p_text}\n")

    text = soup.get_text(separator=" ")
    return clean_text(text)

def clean_text(text: str) -> str:
    """Normalize whitespace and remove artifacts while strictly preserving numbers, percentages, and currencies."""
    if not text:
        return ""
    # Normalize excessive newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Normalize horizontal spaces but keep currency symbols like ₹ intact
    text = re.sub(r'[ \t]+', ' ', text)
    # Strip empty lines
    lines = [line.strip() for line in text.splitlines()]
    return '\n'.join([line for line in lines if line]).strip()


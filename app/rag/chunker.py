import re
from typing import List, Dict, Any
from app.config import settings

class StructureAwareChunker:
    """
    Intelligent structure-aware text chunker that splits on headings and logical
    sections, preserves markdown hierarchy, attaches metadata, and respects chunk size/overlap.
    """
    def __init__(self, chunk_size: int = settings.CHUNK_SIZE, chunk_overlap: int = settings.CHUNK_OVERLAP):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    @staticmethod
    def detect_content_type(url: str, text: str = "") -> str:
        """Infer content type from URL path and text semantics"""
        url_lower = url.lower()
        text_lower = text.lower() if text else ""

        # Check for pricing, free offers, and payment terms first
        if any(p in url_lower for p in ["pricing", "payment", "emi", "free-website", "free-seo"]) or \
           any(p in text_lower for p in ["pay 25% upfront", "zero-cost 12-month emi", "100% free website", "₹0 development cost", "zero development fee", "100% free seo"]):
            if "emi" in url_lower or "payment" in url_lower or "25% upfront" in text_lower:
                return "payment_terms"
            if "free" in url_lower or "offer" in url_lower or "free website" in text_lower or "100% free" in text_lower:
                return "offer"
            return "pricing"

        if "/services" in url_lower:
            return "service"
        elif "/solutions" in url_lower:
            return "solution"
        elif "/about" in url_lower:
            return "about"
        elif "/portfolio" in url_lower:
            return "portfolio"
        elif "/contact" in url_lower:
            return "contact"
        elif any(p in url_lower for p in ["privacy", "terms", "cookie"]):
            return "legal"
        return "general"

    @staticmethod
    def detect_pricing_metadata(url: str, text: str) -> Dict[str, Any]:
        """Detect pricing specific metadata: content_type, service, pricing_type, currency"""
        text_lower = text.lower()
        meta: Dict[str, Any] = {}

        is_pricing_or_offer = any(w in text_lower for w in [
            "₹0", "zero cost", "zero development", "100% free", "free website",
            "no setup charges", "25% upfront", "12-month emi", "no cost emi",
            "charges", "cost", "pricing", "package", "fee"
        ])

        if is_pricing_or_offer:
            if "25% upfront" in text_lower or "emi" in text_lower:
                meta["content_type"] = "payment_terms"
                meta["pricing_type"] = "emi"
            elif "free website" in text_lower or "₹0 development" in text_lower or "zero development" in text_lower:
                meta["content_type"] = "pricing"
                meta["pricing_type"] = "free_offer"
                meta["service"] = "website"
            elif "free seo" in text_lower or "free smo" in text_lower or "seo support forever" in text_lower:
                meta["content_type"] = "offer"
                meta["pricing_type"] = "free_offer"
                meta["service"] = "seo"
            else:
                meta["content_type"] = "pricing"
                meta["pricing_type"] = "general"

            if "₹" in text or "inr" in text_lower or "rupee" in text_lower or "lakh" in text_lower:
                meta["currency"] = "INR"

        # Detect service if not set
        if "service" not in meta:
            if any(w in text_lower for w in ["website", "web development", "landing page"]):
                meta["service"] = "website"
            elif any(w in text_lower for w in ["crm", "erp", "sales crm"]):
                meta["service"] = "crm"
            elif any(w in text_lower for w in ["seo", "smo", "search engine", "digital marketing"]):
                meta["service"] = "seo"
            elif any(w in text_lower for w in ["app development", "mobile app", "flutter"]):
                meta["service"] = "app"
            elif any(w in text_lower for w in ["ai", "chatbot", "automation"]):
                meta["service"] = "ai"

        return meta

    def chunk_document(self, url: str, page_title: str, text: str, custom_metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Split a document into structured chunks with contextual headers and metadata.
        """
        base_content_type = self.detect_content_type(url, text)
        base_meta = {
            "source_url": url,
            "page_title": page_title,
            "content_type": base_content_type,
            **(custom_metadata or {})
        }

        if not text or not text.strip():
            return []

        # Split text into sections based on markdown headings
        heading_pattern = r'(?m)^(?=#{1,4}\s+)'
        raw_sections = re.split(heading_pattern, text)

        chunks: List[Dict[str, Any]] = []
        chunk_idx = 0

        for sec in raw_sections:
            sec = sec.strip()
            if not sec:
                continue

            # Extract section heading if present
            lines = sec.splitlines()
            first_line = lines[0].strip()
            if first_line.startswith("#"):
                current_section = re.sub(r'^#+\s*', '', first_line)
                body = "\n".join(lines[1:]).strip()
            else:
                current_section = page_title
                body = sec

            # Compute section-level pricing metadata
            sec_meta = self.detect_pricing_metadata(url, sec)
            combined_meta = {**base_meta, **sec_meta}

            # If the section itself is small enough, make it a chunk
            if len(sec) <= self.chunk_size:
                chunks.append({
                    "content": f"Title: {page_title}\nSection: {current_section}\n\n{sec}",
                    "metadata": {
                        **combined_meta,
                        "section": current_section,
                        "chunk_index": chunk_idx
                    }
                })
                chunk_idx += 1
            else:
                # Paragraph-aware splitting with sliding overlap
                paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
                current_chunk_text = ""
                
                for p in paragraphs:
                    if len(current_chunk_text) + len(p) + 2 <= self.chunk_size:
                        if current_chunk_text:
                            current_chunk_text += "\n\n" + p
                        else:
                            current_chunk_text = p
                    else:
                        if current_chunk_text:
                            p_meta = self.detect_pricing_metadata(url, current_chunk_text)
                            chunks.append({
                                "content": f"Title: {page_title}\nSection: {current_section}\n\n{current_chunk_text}",
                                "metadata": {
                                    **combined_meta,
                                    **p_meta,
                                    "section": current_section,
                                    "chunk_index": chunk_idx
                                }
                            })
                            chunk_idx += 1
                            # Retain overlap from end of current chunk
                            overlap_text = current_chunk_text[-self.chunk_overlap:] if len(current_chunk_text) > self.chunk_overlap else ""
                            current_chunk_text = (overlap_text + "\n\n" + p).strip() if overlap_text else p
                        else:
                            # Single paragraph larger than chunk_size, split by sentences or characters
                            for start in range(0, len(p), self.chunk_size - self.chunk_overlap):
                                sub = p[start:start + self.chunk_size]
                                sub_meta = self.detect_pricing_metadata(url, sub)
                                chunks.append({
                                    "content": f"Title: {page_title}\nSection: {current_section}\n\n{sub}",
                                    "metadata": {
                                        **combined_meta,
                                        **sub_meta,
                                        "section": current_section,
                                        "chunk_index": chunk_idx
                                    }
                                })
                                chunk_idx += 1
                            current_chunk_text = ""

                if current_chunk_text:
                    p_meta = self.detect_pricing_metadata(url, current_chunk_text)
                    chunks.append({
                        "content": f"Title: {page_title}\nSection: {current_section}\n\n{current_chunk_text}",
                        "metadata": {
                            **combined_meta,
                            **p_meta,
                            "section": current_section,
                            "chunk_index": chunk_idx
                        }
                    })
                    chunk_idx += 1

        return chunks

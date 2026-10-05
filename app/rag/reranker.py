import re
from typing import List, Dict, Any, Optional
from app.core.logging import logger

class CrossScoringReranker:
    """
    Reranks candidate chunks by combining semantic scores, term density,
    section alignment, pricing/offer intent boosts, and downweighting generic chunks.
    """
    def __init__(self):
        pass

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: int = 5,
        intent: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Rerank a list of candidate chunk dictionaries.
        Each candidate has: "chunk", "rrf_score", "vector_score", "bm25_score".
        """
        if not candidates:
            return []

        query_lower = query.lower()
        query_terms = set(re.findall(r'\b[a-zA-Z0-9_\-\.]{2,}\b', query_lower))
        reranked = []

        is_pricing_query = bool(
            (intent and (intent.startswith("pricing") or intent in ("free_offer", "emi", "payment_terms"))) or
            any(w in query_lower for w in ["price", "pricing", "cost", "charge", "charges", "kitna", "kitne", "free", "₹", "emi", "upfront", "fees", "package", "rate"])
        )

        for item in candidates:
            chunk = item["chunk"]
            content = chunk["content"]
            content_lower = content.lower()
            metadata = chunk.get("metadata", {})
            page_title_lower = metadata.get("page_title", "").lower()
            section_lower = metadata.get("section", "").lower()
            content_type = metadata.get("content_type", "")
            pricing_type = metadata.get("pricing_type", "")

            # Base score from RRF
            score = item.get("rrf_score", 0.0) * 10.0

            # Term overlap boost
            matches = sum(1 for term in query_terms if term in content_lower)
            overlap_ratio = matches / max(1, len(query_terms))
            score += overlap_ratio * 3.0

            # Title and Section match bonus
            title_matches = sum(1 for term in query_terms if term in page_title_lower or term in section_lower)
            if title_matches > 0:
                score += 2.5 * title_matches

            # PRICING / FREE OFFER / EMI RETRIEVAL STRATEGY
            if is_pricing_query:
                # 1. Boost exact pricing / offer / payment_terms chunks
                if content_type in ("pricing", "offer", "payment_terms") or pricing_type in ("free_offer", "emi"):
                    score += 12.0

                # 2. Boost presence of specific currencies and numbers
                if any(sym in content for sym in ["₹", "₹0", "25%", "75%", "12-month", "12 month", "12 emi"]):
                    score += 6.0

                # 3. Boost free offer chunks when intent is free_offer or query has "free"
                if intent == "free_offer" or "free" in query_lower or "zero cost" in query_lower or "₹0" in query_lower:
                    if "100% free website" in content_lower or "₹0 development cost" in content_lower or "zero development fee" in content_lower or "free-website" in metadata.get("source_url", ""):
                        score += 15.0
                    elif "100% free seo" in content_lower or "100% free smo" in content_lower or "free-seo" in metadata.get("source_url", ""):
                        if "seo" in query_lower or "smo" in query_lower or "marketing" in query_lower:
                            score += 15.0

                # 4. Boost EMI / payment terms chunks when intent is emi / payment_terms
                if intent in ("emi", "payment_terms") or any(w in query_lower for w in ["emi", "upfront", "installment", "advance", "payment"]):
                    if "25% upfront" in content_lower or "zero-cost 12-month emi" in content_lower or "payment-plans" in metadata.get("source_url", ""):
                        score += 15.0

                # 4b. Boost service-specific chunks for granular pricing intents (e.g. pricing_crm -> crm chunk)
                if intent == "pricing_crm" and metadata.get("service") == "crm":
                    score += 12.0
                elif intent == "pricing_app" and metadata.get("service") == "app":
                    score += 12.0
                elif intent == "pricing_website" and metadata.get("service") == "website":
                    score += 10.0
                elif intent == "pricing_ai" and metadata.get("service") == "ai":
                    score += 12.0
                elif intent in ("pricing_seo", "pricing_digital_marketing") and metadata.get("service") == "seo":
                    score += 12.0

                # 5. Penalize generic company overview chunks when pricing was requested
                # Generic chunks should NOT outrank exact pricing or offer chunks!
                if content_type in ("about", "legal") or "about techvunex" in section_lower or "premier software development company" in content_lower:
                    if not any(sym in content for sym in ["₹", "25%", "zero development", "₹0"]):
                        score -= 10.0
            else:
                # If NOT a pricing query, do standard service alignment
                service_meta = metadata.get("service", "")
                if service_meta and service_meta in query_lower:
                    score += 3.0

            # Specificity bonus
            if len(content) > 120:
                score += 0.5

            item_copy = dict(item)
            item_copy["rerank_score"] = round(score, 4)
            reranked.append(item_copy)

        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
        return reranked[:top_k]

reranker = CrossScoringReranker()


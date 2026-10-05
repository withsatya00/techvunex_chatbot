import re
from typing import Dict, Any, Tuple, Optional
from app.core.logging import logger

class ResponsePostProcessor:
    """
    Validates and normalizes LLM responses before delivery to client or streaming completion:
    - Strips leaked source citations or URLs ([Source 1], Verified Sources)
    - Normalizes markdown headings, bullet lists, and bold markers
    - Eliminates duplicate paragraphs and excessive repetition
    - Verifies language consistency
    - Catches fake shutdown/system claims
    """

    def process(self, text: str, expected_language: str, domain: str, known_name: Optional[str] = None) -> str:
        if not text:
            return ""

        cleaned = text.strip()

        # 1. Strip leaked source citations and raw URL blocks
        cleaned = re.sub(r'\[Source\s+\d+\](?::[^\n]*)?', '', cleaned)
        cleaned = re.sub(r'URL:\s*https?://[^\s\n]+', '', cleaned)
        cleaned = re.sub(r'(?i)\bVerified\s+Sources\b[:\s]*', '', cleaned)
        cleaned = re.sub(r'\[https?://[^\]]+\]', '', cleaned)

        # Remove stray "Aapke doosre sawaal ke baare mein" phrase
        cleaned = re.sub(r'(?i)\baapke\s+doosre\s+sawaal\s+ke\s+baare\s+mein[,:]?\s*', '', cleaned)

        # 2. Fix malformed / escaped markdown headings
        # e.g., \### Heading -> ### Heading
        cleaned = re.sub(r'\\+(#{1,6})\s*', r'\1 ', cleaned)
        # e.g., ###Heading -> ### Heading
        cleaned = re.sub(r'^(#{1,6})([^\s#])', r'\1 \2', cleaned, flags=re.MULTILINE)

        # 3. Normalize bullet lists (ensure clean spacing)
        cleaned = re.sub(r'^[•*]\s+', '- ', cleaned, flags=re.MULTILINE)

        # Fix inline mashed bullets (e.g. "...model yeh hai: - 25% Upfront: ... - 75% via...")
        cleaned = re.sub(r'([^\n])\s+-\s+([A-Z0-9₹%])', r'\1\n- \2', cleaned)

        # Fix missing space after closing parenthesis followed by alphanumeric (e.g. "(Contact details)ready")
        cleaned = re.sub(r'\)([A-Za-z0-9])', r') \1', cleaned)

        # 4. Remove duplicate consecutive blank lines
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        # 5. Hallucinated Greeting Name Sanitization
        cleaned = self._sanitize_greeting_name(cleaned, known_name=known_name)

        # 6. Prevent fake shutdown emulation
        if domain == "system_control" or any(w in cleaned.lower() for w in ["shutting down assistance", "service has been shut down", "powering off now"]):
            if expected_language == "hi":
                return "मैं चैट संदेश के माध्यम से सेवा को बंद नहीं कर सकता। मैं टेकवुनेक्स से संबंधित प्रश्नों के लिए यहाँ उपलब्ध हूँ। आप जब चाहें चैट विंडो बंद कर सकते हैं।"
            elif expected_language == "hinglish":
                return "Main chat message ke through service shut down nahi kar sakta. Main Techvunex-related questions ke liye yahan hoon. Aap chat window close kar sakte hain jab aapka kaam complete ho jaye."
            else:
                return "I can't shut down the service through a chat message. I'm here to help with Techvunex-related questions. You can close the chat window whenever you're done."

        # 7. Safety & Boundary response enforcement in post processor
        if domain == "legal_advice":
            from app.agents.domain import domain_classifier
            return domain_classifier.get_boundary_response("legal_advice", cleaned, expected_language)

        if domain == "unsafe_off_topic":
            from app.agents.domain import domain_classifier
            return domain_classifier.get_boundary_response("unsafe_off_topic", cleaned, expected_language)

        # 8. Language integrity check
        if expected_language == "en" and self.has_hinglish_leak(cleaned):
            logger.warning("Language mismatch detected in LLM response: Expected en but got Hinglish words.")

        return cleaned.strip()

    def _sanitize_greeting_name(self, text: str, known_name: Optional[str] = None) -> str:
        """
        Ensures the assistant does not address the user by a hallucinated name
        (e.g., 'Bilkul Shivam,') if the user never introduced themselves with that name,
        or ensures the correct name is used if the user introduced themselves.
        """
        excluded_words = {
            "sahi", "zaroor", "haan", "hum", "aap", "agar", "isme", "yeh", "main", "hamare",
            "sir", "there", "ji", "dost", "friends", "team", "all", "everyone", "welcome",
            "please", "to", "at", "for", "in", "on", "with", "and", "or", "techvunex",
            "shuruat", "start", "pehle", "bhi"
        }

        def _replace_name(m):
            prefix = m.group(1)
            cand = m.group(2)
            punct = m.group(3)

            if cand.lower() in excluded_words:
                return m.group(0)

            if known_name:
                if cand.lower() == known_name.lower():
                    return m.group(0)
                return f"{prefix} {known_name}{punct}"
            else:
                if punct in (",", "!", "."):
                    return f"{prefix}{punct}"
                return f"{prefix} "

        return re.sub(
            r'\b(Bilkul|Sure|Hello|Hi|Hey|Dear|Namaste|Welcome|Thanks|Shukriya)\s+([A-Z][a-z]+)\b([,!\s])',
            _replace_name,
            text
        )

    def has_hinglish_leak(self, text: str) -> bool:
        """
        Detects if an LLM-generated response contains Hinglish or Hindi words when English was expected.
        """
        if not text:
            return False
        # Check for Devanagari characters
        if any('\u0900' <= c <= '\u097f' for c in text):
            return True

        text_lower = text.lower()
        hinglish_indicators = [
            r"\baap(?:ko|ka|ke)?\b", r"\bchahiye\b", r"\bbanwana\b", r"\bhoga\b", r"\bkarna\b",
            r"\bhamare\b", r"\bmil\s+jayegi\b", r"\bsakta\s+hai\b", r"\bkarein\b", r"\bhai\b",
            r"\bhain\b", r"\bkya\b", r"\bkaise\b", r"\bmujhe\b", r"\bbatao\b", r"\bbataiye\b",
            r"\bdijiye\b", r"\bkharcha\b", r"\bdena\b", r"\bshukriya\b"
        ]
        count = sum(1 for p in hinglish_indicators if re.search(p, text_lower))
        return count >= 2

response_post_processor = ResponsePostProcessor()

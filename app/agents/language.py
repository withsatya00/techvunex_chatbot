import re
from typing import Dict, Any, List, Optional

class LanguageDetector:
    """
    Detects language of user messages with strict distinction between:
    - 'en' (English)
    - 'hi' (Hindi in Devanagari script)
    - 'hinglish' (Hindi/Urdu phrases transliterated into Roman script)
    
    CRITICAL RULE:
    The latest meaningful user message has the highest priority.
    """
    
    # Common Hindi words in Roman script (Hinglish)
    HINGLISH_WORDS = {
        "hai", "hain", "kya", "kaise", "mujhe", "chahiye", "chaiye", "chahie", "chaheye",
        "banwana", "banwani", "banaye", "banayenge", "banega", "banegi", "hoga", "hogi", "hoge",
        "karo", "karna", "karein", "karta", "karti", "karte", "aap", "aapko", "aapka", "aapke",
        "aapki", "tum", "mera", "meri", "mere", "kitna", "kitne", "kitni", "ktna", "ktne", "mein",
        "nahi", "nahin", "nhn", "milegi", "milega", "milenge", "sakta", "sakti", "sakte",
        "skte", "skta", "skti", "skenge", "wala", "wali", "wale", "kist", "kisht", "kistein",
        "hafte", "kharcha", "bataye", "batao", "bataiye", "bta", "btao", "btaye", "btana",
        "dijiye", "kesi", "kese", "achha", "accha", "acha", "theek", "thik", "paise", "rupaye",
        "kuch", "kch", "yahan", "wahan", "idhar", "udhar", "karenge", "krenge", "banao",
        "sakenge", "dhanyawad", "shukriya", "bnawne", "bnwana", "bnwani", "bnana", "bna", "bnao",
        "bnaye", "bnega", "bnegi", "smjha", "smjhao", "mjha", "samjha", "samjhao", "samjhaye",
        "kro", "krna", "krein", "krte", "krti", "ka", "ke", "ki", "ko", "se", "par", "pe",
        "ho", "tha", "thi", "bhi", "toh", "arey", "arrey", "bhai",
        # Added interrogatives, past tense, verbs & prepositions
        "kab", "kyun", "kyu", "kyo", "kaha", "kahan", "kidhar", "kis", "kisi", "kisko",
        "kiska", "kiske", "kiski", "kaun", "kaunsi", "konsi", "kaunsa", "konsa", "kin",
        "hui", "hua", "hue", "hona", "hoti", "hota", "hote", "hoon", "hun",
        "gaya", "gayi", "gaye", "gya", "gyi", "gye", "raha", "rahi", "rahe",
        "shuru", "suru", "saath", "sath", "apne", "apna", "apni",
        "hum", "humko", "humara", "hamara", "humari", "hamari", "humare", "hamare",
        "aur", "liye", "paas", "pass", "tarah", "trh", "jaise", "jaisa", "jaisi",
        "alag", "baare", "baat", "kripya", "krpya", "poochna", "puchna", "dekhte", "dekha"
    }

    # Strong unambiguous Hinglish verbs and grammatical markers
    STRONG_HINGLISH = {
        "hai", "hain", "kya", "kaise", "mujhe", "chahiye", "chaiye", "chahie", "chaheye",
        "banwana", "banwani", "banaye", "banayenge", "banega", "banegi", "kitna", "kitne", "kitni",
        "ktna", "ktne", "milegi", "milega", "milenge", "sakta", "sakti", "sakte", "skte", "skta",
        "skti", "skenge", "kharcha", "batao", "bataye", "bataiye", "bta", "btao", "btaye", "btana",
        "dijiye", "banao", "kesi", "kese", "karenge", "krenge", "aapko", "aapka", "aapke", "aapki",
        "wala", "wali", "wale", "karein", "banane", "bnawne", "bnwana", "bnwani", "bnana", "bna", "bnao",
        "bnaye", "bnega", "bnegi", "smjha", "smjhao", "mjha", "samjha", "samjhao", "samjhaye",
        "kro", "krna", "krein", "krte", "krti", "kist", "kisht", "paise", "rupaye",
        # Unambiguous Hindi grammatical anchors in Roman script (never English words)
        "kab", "kyun", "kyu", "kaha", "kahan", "kidhar", "kaunsi", "konsi", "kaunsa", "konsa",
        "hui", "hua", "hue", "hoti", "hota", "hote", "tha", "thi", "hoon", "hun",
        "gaya", "gayi", "gaye", "gya", "gyi", "gye", "raha", "rahi", "rahe",
        "shuru", "suru", "saath", "sath", "apne", "apna", "apni", "humara", "hamara",
        "humari", "hamari", "humare", "hamare", "baare", "tarah", "jaise", "jaisa", "jaisi"
    }

    # Common English vocabulary to prevent English queries from being marked as Hinglish
    ENGLISH_VOCAB = {
        "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not",
        "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", "by", "from",
        "they", "we", "say", "her", "she", "or", "an", "will", "my", "one", "all", "would",
        "there", "their", "what", "so", "up", "out", "if", "about", "who", "get", "which",
        "go", "me", "when", "make", "can", "like", "time", "no", "just", "him", "know",
        "take", "people", "into", "year", "your", "good", "some", "could", "them", "see",
        "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
        "also", "back", "after", "use", "two", "how", "our", "work", "first", "well",
        "way", "even", "new", "want", "because", "any", "these", "give", "day", "most",
        "us", "cost", "price", "pricing", "website", "web", "app", "application", "software",
        "solution", "solutions", "service", "services", "company", "package", "packages",
        "quote", "quotation", "contact", "phone", "email", "budget", "details", "help",
        "please", "thanks", "thank", "hello", "hi", "hey", "build", "create", "develop",
        "developer", "development", "ecommerce", "saas", "crm", "erp", "cloud", "design",
        "seo", "smo", "rupee", "rupees", "inr", "free", "offer", "terms", "emi", "installment",
        "upfront", "pay", "payment", "feature", "features", "tell", "explain", "provide",
        "show", "need", "looking", "much", "many", "more", "normal", "simple", "business",
        "start", "online", "store", "tech", "technologies", "stack"
    }

    # Strong English grammatical marker phrases
    ENGLISH_PATTERNS = [
        r"\bi\s+(?:want|need|would\s+like|am\s+looking\s+for|require|have)\b",
        r"\bcan\s+(?:i|you|we)\b",
        r"\bhow\s+(?:much|many|do|can|does|is|are|to)\b",
        r"\bwhat\s+(?:is|are|services|type|kind|do|does|about)\b",
        r"\bdo\s+you\s+(?:provide|build|develop|offer|have|make)\b",
        r"\btell\s+me\s+about\b",
        r"\bmy\s+budget\s+is\b",
        r"\bhow\s+much\s+(?:does|is|for|charge)\b",
        r"\bis\s+(?:there|it|the|whatsapp|seo|smo|emi|pricing)\b",
        r"\bwhere\s+are\s+you\b",
        r"\bwho\s+(?:is|are)\b",
        r"\bwhich\s+(?:is|technologies|framework)\b",
        r"\bplease\s+(?:explain|help|provide|give)\b",
        r"\bcontact\s+(?:us|me|support|team)\b",
        r"\b(?:cost|price|pricing)\s+(?:of|for|in)\b"
    ]

    # Devanagari Unicode Range
    DEVANAGARI_REGEX = re.compile(r'[\u0900-\u097F]')

    def detect(self, text: str) -> str:
        """
        Detects 'en', 'hi', or 'hinglish' for a single message.
        """
        if not text or not text.strip():
            return "en"

        trimmed = text.strip()

        # 1. Check for Devanagari characters (Hindi)
        devanagari_count = len(self.DEVANAGARI_REGEX.findall(trimmed))
        total_letters = sum(1 for c in trimmed if c.isalpha())
        
        if devanagari_count > 0 and (total_letters == 0 or (devanagari_count / total_letters) > 0.3):
            return "hi"

        text_lower = trimmed.lower()

        # 2. Tokenize words for vocabulary matching
        words = re.findall(r'\b[a-z]{2,}\b', text_lower)
        if not words:
            return "en"

        has_strong_hinglish = any(w in self.STRONG_HINGLISH for w in words)
        english_hits = sum(1 for w in words if w in self.ENGLISH_VOCAB)
        hinglish_hits = sum(1 for w in words if w in self.HINGLISH_WORDS)

        # If unmistakable Hinglish verbs/pronouns exist (e.g. chahiye, banwana, kitna, kaise, aapko)
        if has_strong_hinglish:
            return "hinglish"

        # Check for strong English syntactic patterns
        for pattern in self.ENGLISH_PATTERNS:
            if re.search(pattern, text_lower):
                if hinglish_hits <= 1:
                    return "en"

        # If predominantly English words
        if english_hits >= 1 and hinglish_hits == 0:
            return "en"

        if english_hits >= hinglish_hits and not has_strong_hinglish:
            return "en"

        if hinglish_hits >= 2 and hinglish_hits > english_hits:
            return "hinglish"

        if hinglish_hits >= 1 and english_hits == 0:
            return "hinglish"

        return "en"

    def resolve_conversation_language(self, latest_message: str, history: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Determines the effective language for the current response.
        LATEST USER MESSAGE ALWAYS HAS HIGHEST PRIORITY.
        """
        detected = self.detect(latest_message)
        return detected

language_detector = LanguageDetector()

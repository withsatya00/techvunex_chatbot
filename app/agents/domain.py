import re
from typing import Dict, Any, Tuple, Optional

class DomainClassifier:
    """
    Classifies user queries into domain categories:
    - 'techvunex_relevant': Directly related to Techvunex services, offers, pricing, consultation, contact, tech stack.
    - 'technology_general': General programming / tech questions related to our stack.
    - 'off_topic': Unrelated queries (e.g. stolen bike, weather, jokes, sports, quantum mechanics, cooking).
    - 'unsafe_off_topic': Illegal, dangerous, or malicious queries (e.g. how to steal a bike, hacking, weapons).
    - 'legal_advice': Legal consultations, court cases, statutory provisions (IPC/BNS), lawyer inquiries.
    - 'system_control': Fake admin commands (e.g. shutdown, terminate, power off).
    - 'prompt_injection': Attempts to jailbreak, reveal prompt, or override role.
    """

    # Unsafe / illegal activities & theft facilitation
    UNSAFE_PATTERNS = [
        r"\b(?:how\s+to|can\s+i|how\s+can\s+i|ways\s+to|tips\s+to|guide\s+to|tricks\s+to|help\s+me\s+to)\s+(?:steal|chori|theft|rob|hijack|shoplift|pickpocket|loot)\b",
        r"\b(?:steal\s+(?:a\s+|an\s+|the\s+)?(?:bike|car|motorcycle|scooter|vehicle|money|cash|phone|mobile|laptop|gold|jewellery|wallet|purse|card|password|account))\b",
        r"\b(?:how\s+to\s+(?:hack|exploit|bypass|crack)\s+(?:a\s+|an\s+|the\s+)?(?:bank|atm|account|password|wifi|cctv))\b",
        r"\b(?:make\s+(?:a\s+|an\s+|the\s+)?(?:bomb|weapon|poison|drug|explosive))\b",
        r"\b(?:pirate\s+software|ddos\s+attack|ransomware)\b",
        r"\b(?:chori\s+(?:kaise|karna|karne|kare|karte|karti|sikhao|sikhaye|tarika|tarike|idea|planning|tips?|formula|kaam))\b",
        r"\b(?:chori\s+karne\s+(?:ka|ke|ki)\s+(?:tarika|tarike|formula|plan|planning|tips?))\b",
        r"\b(?:chori\s+ke\s+(?:niyam|tarike|tips|idea|formula))\b",
        r"\b(?:how\s+to\s+steal|how\s+to\s+rob|how\s+to\s+shoplift|how\s+to\s+pickpocket)\b",
        r"\b(?:shoplifting\s+(?:tips|tricks|kaise|karne))\b",
        r"\b(?:loot\s+(?:kaise|karna|kare)|dacoity\s+kaise|dakaiti\s+kaise|bank\s+lootna|atm\s+lootna)\b",
        r"\b(?:mujhe\s+chori\s+karni\s+hai|chori\s+karna\s+chahta|chori\s+karna\s+chahti)\b",
        r"^(?:chori|theft|stealing|robbery|loot|chori\s+karna|chori\s+ke\s+niyam|chori\s+ke\s+tarike)$"
    ]

    # Stolen property / law enforcement / crime victim (off-topic, not illegal query itself)
    STOLEN_PROPERTY_PATTERNS = [
        r"\b(?:my\s+.*?\s+(?:has\s+been|was|got|is)\s+stolen)\b",
        r"\b(?:meri|mera|mere)\s+.*?\s+(?:chori\s+ho\s+(?:gayi|gaya|gaye)|kho\s+(?:gayi|gaya))\b",
        r"\b(?:chori\s+ho\s+(?:gayi|gaya|gaye|hui|chuka))\b",
        r"\b(?:bike\s+stolen|stolen\s+bike|vehicle\s+theft|report\s+(?:a\s+)?theft|theft\s+complaint|theft\s+fir|chori\s+ki\s+(?:report|complaint|fir))\b"
    ]

    # Legal advice & Law enforcement inquiries (Off-boundary for Techvunex IT Assistant)
    LEGAL_ADVICE_PATTERNS = [
        r"\b(?:legal\s+(?:advice|opinion|consultation|counsel|help|notice|action|rights|lawyer|process|case|issues?|guidance|assistance))\b",
        r"\b(?:kanuni\s+salah|kanooni\s+salah|kanoon\s+ke\s+niyam|kanun\s+ke\s+niyam|court\s+case|court\s+notice)\b",
        r"\b(?:vakil|vakeel|advocate|lawyer|attorney)\b",
        r"\b(?:file\s+(?:a\s+)?(?:lawsuit|case|fir|complaint\s+in\s+court)|sue\s+someone|can\s+i\s+sue)\b",
        r"\b(?:ipc|crpc|bns|bharatiya\s+nyaya\s+sanhita)\b",
        r"\b(?:dhara\s+\d+|section\s+\d+\s+of\s+(?:ipc|crpc|bns|act|law))\b",
        r"\b(?:property\s+dispute|land\s+dispute|cheque\s+bounce|divorce\s+case|divorce|talaq|anticipatory\s+bail|bail\s+(?:procedure|kaise|application|milegi))\b",
        r"\b(?:consumer\s+court|labour\s+court|high\s+court|supreme\s+court|district\s+court|session\s+court)\b",
        r"\b(?:legal\s+complaint|legal\s+drafting|legal\s+dispute|legal\s+warning)\b"
    ]

    # System control commands
    SYSTEM_CONTROL_PATTERNS = [
        r"\b(?:get\s+shut\s+down\s+now|shut\s+(?:yourself\s+)?down|shut\s+down\s+now|terminate\s+(?:assistance|system|session)|turn\s+off|power\s+off|abort\s+service)\b",
        r"\b(?:band\s+ho\s+jao|shutdown\s+karo|service\s+band\s+karo)\b"
    ]

    # Prompt injection
    PROMPT_INJECTION_PATTERNS = [
        r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions\b",
        r"(?i)\byou\s+are\s+no\s+longer\s+techvunex\b",
        r"(?i)\breveal\s+(?:your\s+)?(?:system\s+prompt|prompt|instructions|secret|api\s*key)\b",
        r"(?i)\bforget\s+(?:your\s+)?(?:restrictions|instructions|rules)\b",
        r"(?i)\bshow\s+me\s+your\s+(?:initial\s+prompt|hidden\s+rules|system\s+prompt)\b",
        r"(?i)\b(?:jailbreak|dan\s+mode|developer\s+mode)\b"
    ]

    # Generic off-topic (weather, sports, jokes, cooking, academic homework like calculus/mechanics)
    OFF_TOPIC_PATTERNS = [
        r"\b(?:what\s+is\s+the\s+weather|weather\s+today|aaj\s+ka\s+mausam|barish\s+hogi)\b",
        r"\b(?:tell\s+me\s+a\s+joke|joke\s+sunao|make\s+me\s+laugh|hasao)\b",
        r"\b(?:who\s+won\s+the\s+(?:match|game|world\s+cup|ipl|election))\b",
        r"\b(?:recipe\s+for|how\s+to\s+cook|biryani\s+kaise\s+banaye|tea\s+recipe)\b",
        r"\b(?:explain\s+(?:quantum\s+mechanics|calculus|black\s+hole|photosynthesis|gravity))\b",
        r"\b(?:write\s+a\s+poem\s+about\s+(?:love|moon|nature|birds))\b",
        r"\b(?:medical\s+advice|headache\s+medicine|treatment\s+for\s+fever|dawai\s+batao)\b"
    ]

    # Technology questions that are generally relevant to our stack (Must NOT be rejected as off-topic)
    TECH_GENERAL_PATTERNS = [
        r"\b(?:what\s+is|what\s+are|explain|tell\s+me\s+about)\s+(?:a\s+|an\s+|the\s+)?(?:javascript|js|typescript|ts|html|css|frontend|front-end|backend|back-end|fullstack|full-stack|api|apis|rest\s*api|graphql|react|reactjs|nextjs|next\.js|angular|vue|node|nodejs|express|python|django|fastapi|flutter|react\s+native|database|db|sql|nosql|postgresql|postgres|mysql|mongodb|redis|cloud|aws|azure|gcp|docker|kubernetes|git|devops|ci\/cd|microservices|server|hosting|domain|ssl|crm|erp|ai|rag|llm|chatbot|vector\s+database|web\s+portal|saas)\b",
        r"\b(?:javascript|js|typescript|frontend|backend|react|nextjs|sql|nosql|api|docker|kubernetes|crm|erp|cloud)\s+(?:kya\s+hai|kya\s+hota\s+hai|kaise\s+kaam\s+karta\s+hai|kahan\s+use\s+hota\s+hai)\b",
        r"\b(?:react\s+vs\s+nextjs|flutter\s+vs\s+react\s+native|aws\s+vs\s+azure|sql\s+vs\s+nosql|frontend\s+vs\s+backend|rest\s+vs\s+graphql)\b",
        r"\b(?:what\s+is\s+(?:fastapi|docker|kubernetes|node|nodejs|postgresql|mongodb|redis|graphql))\b"
    ]

    # Casual polite acknowledgments and simple questions (Master AI Spec §27)
    CASUAL_PATTERNS = [
        r"^(?:thanks|thank\s+you|thx|dhanyawad|shukriya|thanks\s+a\s+lot|thank\s+you\s+so\s+much)[\s!\.]*$",
        r"^(?:ok|okay|thik\s+hai|theek\s+hai|got\s+it|understood|cool|great|nice|perfect|done|sahi\s+hai)[\s!\.]*$",
        r"^(?:who\s+are\s+you|what\s+can\s+you\s+do|aap\s+kaun\s+ho|tum\s+kaun\s+ho)[\s!\?\.]*$"
    ]

    # Explicit Techvunex and service keywords (matched using exact word boundaries)
    TECHVUNEX_KEYWORDS = [
        "techvunex", "website", "websites", "web app", "web development", "mobile app",
        "crm", "erp", "software", "custom software", "automation", "chatbot", "chatbots",
        "figma", "devops", "seo", "smo", "digital marketing", "cloud solutions",
        "zero-cost emi", "12-month emi", "emi", "installment", "installments", "upfront",
        "25%", "75%", "services", "service", "payment", "payment plan", "payment model",
        "payment terms", "paymnet", "paymnt", "pymnt", "pyment", "bhugtan", "kist", "kisht",
        "downpayment", "down payment", "advance",
        "free website", "free website offer", "ecommerce", "e-commerce", "saas",
        "landing page", "tech stack", "portfolio", "case studies", "hire", "consultation",
        # Pricing, price, cost, charges
        "pricing", "price", "cost", "charge", "packages", "package", "quote", "quotation",
        "kharcha", "billing", "frontend", "backend", "fullstack", "javascript", "react", "nextjs",
        # Business categories and discovery terms (Master AI Spec §7 & §8)
        "business", "businesses", "clothing", "retail", "shop", "store", "restaurant", "hospital", "clinic",
        "real estate", "consulting", "agency", "products", "selling", "booking", "bookings",
        "appointment", "education", "courses", "startup",
        # Company, Office, Hours, Location & Contact keywords
        "office", "working hours", "office hours", "timings", "timing", "hours", "open", "close", "closed",
        "location", "address", "head office", "noida", "sector 63", "contact", "email", "phone", "number",
        "call", "reach",
        # Establishment & History & Parent Company
        "establish", "established", "establishment", "founded", "founder", "history", "started", "shuru",
        "parent company", "digital yug", "digital yug innovation", "holding company", "parent", "company", "companies",
        # Experience, Industries & Clients
        "industry", "industries", "sector", "sectors", "domain", "domains", "clients", "client", "projects",
        "experience", "past work", "case study",
        # Value Proposition & Comparison
        "why choose", "why hire", "comparison", "why techvunex", "choose techvunex", "advantage", "advantages",
        # Website & AI Features
        "responsive", "mobile responsive", "whatsapp", "enquiry", "inquiry", "contact form", "integration",
        "integrate", "rag", "documents", "knowledge base",
        # Devanagari terms
        "वेबसाइट", "सॉफ्टवेयर", "ऐप", "एप्लिकेशन", "सीआरएम", "ईआरपी", "डिजाइन", "मार्केटिंग",
        "क्लाउड", "तकनीक", "प्रोजेक्ट", "खर्च", "कीमत", "फ्री", "ऑफर", "बनवानी", "बनवाना", "ईएमआई",
        "भुगतान", "किस्त", "एडवांस"
    ]

    def classify(self, query: str, has_active_dialogue: bool = False) -> str:
        q_lower = query.lower().strip()

        # 1. System control attempt
        for p in self.SYSTEM_CONTROL_PATTERNS:
            if re.search(p, q_lower):
                return "system_control"

        # 2. Prompt injection
        for p in self.PROMPT_INJECTION_PATTERNS:
            if re.search(p, q_lower):
                return "prompt_injection"

        # 3. Check for victim reporting stolen goods first (off-topic, not malicious)
        for p in self.STOLEN_PROPERTY_PATTERNS:
            if re.search(p, q_lower):
                return "off_topic"

        # 4. Unsafe / Illegal / Theft facilitation
        for p in self.UNSAFE_PATTERNS:
            if re.search(p, q_lower):
                return "unsafe_off_topic"

        # General theft safety check: if 'chori' or 'steal' is queried and not matched above
        if re.search(r"\b(?:chori|steal|stealing|robbery|loot|lootna|pickpocket|shoplift)\b", q_lower):
            return "unsafe_off_topic"

        # 5. Legal Advice / Law Enforcement inquiries
        for p in self.LEGAL_ADVICE_PATTERNS:
            if re.search(p, q_lower):
                return "legal_advice"

        # 6. Casual conversation (thanks, ok, who are you)
        for p in self.CASUAL_PATTERNS:
            if re.search(p, q_lower):
                return "techvunex_relevant"

        # 7. Check for general technology questions (Master AI Spec §3 & §4)
        for p in self.TECH_GENERAL_PATTERNS:
            if re.search(p, q_lower):
                return "technology_general"

        # 8. General off-topic (weather, jokes, quantum mechanics, etc.)
        for p in self.OFF_TOPIC_PATTERNS:
            if re.search(p, q_lower):
                return "off_topic"

        # 9. Check for Techvunex services & business terms using strict word boundaries
        for kw in self.TECHVUNEX_KEYWORDS:
            if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                return "techvunex_relevant"

        # Short acronyms with boundary check
        if re.search(r'\b(?:ai|ui|ux|aws|gcp|api|apis)\b', q_lower):
            return "techvunex_relevant"

        # Service-related pricing, payment, EMI & commercial inquiries
        if re.search(r"\b(?:payment|paymnet|paymnt|pymnt|pyment|bhugtan|emi|kist|kisht|downpayment|down\s*payment|installment|installments|advance|pricing|price|cost|charges?|kharcha|quotation|package|packages|billing)\b", q_lower):
            return "techvunex_relevant"

        # Tech building intents in English & Hindi
        if re.search(r'\b(?:build|develop|create|make|hire)\s+(?:a\s+|an\s+)?(?:website|site|app|software|crm|erp|platform|store)\b', q_lower):
            return "techvunex_relevant"

        if re.search(r'\b(?:website|software|crm|erp|app)\s+(?:banwana|banwani|banana|chahiye|kharcha|banao)\b', q_lower):
            return "techvunex_relevant"

        # Lead / Contact info / Introduction (phone, email, budget, name)
        if re.search(r'[\w\.-]+@[\w\.-]+\.\w+', query) or re.search(r'(?:\+?91[\s-]?)?[6-9]\d{9}\b', query):
            return "techvunex_relevant"

        if re.search(r'\b(?:my\s+name\s+is|mera\s+naam|call\s+me|reach\s+me|my\s+email|my\s+phone|my\s+number|budget\s+is|budget\s+hai)\b', q_lower):
            return "techvunex_relevant"

        # Discovery / Business requirement answers (Master AI Spec §7 & §8)
        if re.search(r'\b(?:business|clothing|retail|shop|store|restaurant|hospital|clinic|doctor|real\s+estate|properties|consulting|agency|products?|selling|sell\s+online|online\s+sell|booking|bookings|appointment|appointments|courses|school|gym|fitness|hotel|startup|features?|pages?)\b', q_lower):
            return "techvunex_relevant"

        # Corporate hierarchy, parent company & ownership inquiries
        if re.search(r"\b(?:parent\s+comp(?:any|ny)|digital\s+yug|holding\s+company|mool\s+company)\b", q_lower):
            return "techvunex_relevant"

        # General questions about "company" / "iss company"
        if re.search(r"\b(?:iss\s+company|this\s+company|about\s+company|company\s+ke\s+baare|ye\s+company)\b", q_lower):
            return "techvunex_relevant"

        # Default fallback: If it's a short greeting or polite opener
        if re.search(r"^(?:hi|hello|hey|namaste|good\s+(?:morning|afternoon|evening))\b", q_lower):
            return "techvunex_relevant"

        # In an active ongoing dialogue, preserve conversational context (Master AI Spec §5 & §40)
        if has_active_dialogue:
            return "techvunex_relevant"

        # Any substantive question that doesn't match Techvunex or tech domain is off-topic
        return "off_topic"

    def get_boundary_response(self, domain: str, query: str, language: str) -> str:
        """
        Returns a polite, localized boundary response or refusal without calling RAG.
        """
        q_lower = query.lower()

        # 1. System Control
        if domain == "system_control":
            if language == "hi":
                return "मैं चैट संदेश के माध्यम से सेवा को बंद नहीं कर सकता। मैं टेकवुनेक्स से संबंधित प्रश्नों के लिए यहाँ उपलब्ध हूँ। आप जब चाहें चैट विंडो बंद कर सकते हैं।"
            elif language == "hinglish":
                return "Main chat message ke through service shut down nahi kar sakta. Main Techvunex-related questions ke liye yahan hoon. Aap chat window close kar sakte hain jab aapka kaam complete ho jaye."
            else:
                return "I can't shut down the service through a chat message. I'm here to help with Techvunex-related questions. You can close the chat window whenever you're done."

        # 2. Prompt Injection
        if domain == "prompt_injection":
            if language == "hi":
                return "मैं टेकवुनेक्स इनोवेशन का आधिकारिक AI सहायक हूँ और टेकवुनेक्स की टेक्नोलॉजी, सॉफ्टवेयर, वेब डेवलपमेंट और व्यावसायिक सेवाओं में सहायता करने के लिए अपनी भूमिका में बना रहता हूँ। आज मैं आपके प्रोजेक्ट में कैसे मदद कर सकता हूँ?"
            elif language == "hinglish":
                return "Main Techvunex Innovation ka official AI Assistant hoon aur Techvunex technology, software, web development, AI aur business services mein help ke liye dedicated hoon. Aaj aapke project requirements mein kaise madad kar sakta hoon?"
            else:
                return "I'm the official AI Assistant for Techvunex Innovation and maintain my designated role to assist you with Techvunex technology, software, web development, AI, and business services. How can I help with your project requirements today?"

        # 3. Unsafe / Illegal Activity (Theft, hacking, weapons)
        if domain == "unsafe_off_topic":
            if language == "hi":
                return "मैं किसी भी चोरी, अवैध गतिविधि या वाहन चोरी में सहायता नहीं कर सकता। मैं टेकवुनेक्स का AI सहायक हूँ और टेक्नोलॉजी, सॉफ्टवेयर, वेबसाइट्स, AI, CRM/ERP और संबंधित सेवाओं में मदद कर सकता हूँ।"
            elif language == "hinglish":
                return "Main kisi bhi chori, illegal activity ya vehicle chori mein madad nahi kar sakta. Main Techvunex ka AI Assistant hoon aur technology, software, websites, AI, CRM/ERP aur related services mein help kar sakta hoon."
            else:
                return "I can't help with stealing a vehicle, theft, or other illegal activity. I'm the Techvunex AI Assistant and can help with technology, software, websites, AI, CRM/ERP, and related services."

        # 4. Legal Advice inquiries
        if domain == "legal_advice":
            if language == "hi":
                return "मैं टेकवुनेक्स इनोवेशन का आधिकारिक AI सहायक हूँ और मुख्य रूप से हमारी टेक्नोलॉजी, सॉफ्टवेयर, वेबसाइट डेवलपमेंट और डिजिटल सेवाओं में सहायता कर सकता हूँ। मैं कानूनी सलाह (Legal Advice), कानूनी राय या पुलिस/अदालत से जुड़े मामलों में मार्गदर्शन प्रदान नहीं कर सकता। किसी भी कानूनी मामले के लिए कृपया किसी योग्य अधिवक्ता (Advocate) या कानूनी विशेषज्ञ से परामर्श लें।"
            elif language == "hinglish":
                return "Main Techvunex Innovation ka official AI Assistant hoon aur mainly Techvunex ki technology, software development, websites aur business services mein help kar sakta hoon. Main koi legal advice (kanuni salah) ya law-enforcement guidance provide nahi kar sakta. Kisi bhi legal mamle ke liye kripya certified advocate ya legal expert se consult karein."
            else:
                return "I am the official AI Assistant for Techvunex Innovation, dedicated to helping with our technology solutions, web development, custom software, and digital services. I cannot provide legal advice, legal opinions, or law-enforcement guidance. For any legal matters, please consult a qualified advocate, legal professional, or the appropriate authority."

        # 5. Off-Topic: Stolen property / Crime victim
        is_theft_incident = any(re.search(p, q_lower) for p in self.STOLEN_PROPERTY_PATTERNS) or "bike" in q_lower or "theft" in q_lower or "chori" in q_lower
        if is_theft_incident:
            if language == "hi":
                return "मैं टेकवुनेक्स का AI सहायक हूँ, इसलिए मैं मुख्य रूप से वेबसाइट डेवलपमेंट, सॉफ्टवेयर, AI, CRM/ERP, डिजिटल मार्केटिंग और संबंधित टेक्नोलॉजी आवश्यकताओं में मदद कर सकता हूँ। वाहन चोरी या कानून प्रवर्तन मामलों में मैं मार्गदर्शन प्रदान नहीं कर सकता।"
            elif language == "hinglish":
                return "Main Techvunex ka AI Assistant hoon, isliye main mainly website development, software, AI, CRM/ERP, digital marketing aur related technology requirements mein help kar sakta hoon. Vehicle theft ya law-enforcement matters mein guidance provide nahi kar sakta."
            else:
                return "I’m the Techvunex AI Assistant, so I’m mainly able to help with Techvunex services, website development, software, AI, CRM/ERP, digital marketing, and related technology requirements. I can’t provide guidance on vehicle theft or law-enforcement matters."

        # 6. Generic Off-Topic (weather, jokes, cooking, sports, etc.)
        if language == "hi":
            return "मैं टेकवुनेक्स इनोवेशन का आधिकारिक AI सहायक हूँ, इसलिए मैं टेकवुनेक्स की टेक्नोलॉजी और व्यावसायिक सेवाओं जैसे वेबसाइट डेवलपमेंट, कस्टम सॉफ्टवेयर, AI और ऑटोमेशन, CRM/ERP और डिजिटल मार्केटिंग में विशेषज्ञता रखता हूँ। मैं असंबद्ध विषयों में सहायता करने में असमर्थ हूँ, लेकिन हमारी तकनीकी सेवाओं या ऑफर्स के बारे में निसंकोच पूछें!"
        elif language == "hinglish":
            return "Main Techvunex Innovation ka official AI Assistant hoon, isliye main Techvunex ki technology aur business services jaise website development, custom software, AI & automation, CRM/ERP aur digital growth mein help kar sakta hoon. Main unrelated topics par guidance provide nahi kar sakta, lekin aap hamari tech services ya offers ke baare mein pooch sakte hain!"
        else:
            return "I'm the official AI Assistant for Techvunex Innovation, so I specialize in Techvunex's technology and business services such as website development, custom software, AI & automation, CRM/ERP, and digital growth. I'm unable to assist with unrelated topics, but feel free to ask about our tech solutions or ongoing offers!"

domain_classifier = DomainClassifier()

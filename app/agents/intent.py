import re
from typing import Dict, Any, List, Optional
from app.agents.language import language_detector
from app.agents.domain import domain_classifier

class QueryUnderstandingAgent:
    """
    Analyzes user queries to detect:
    - Language (en, hi, hinglish)
    - Domain (techvunex_relevant, technology_general, off_topic, unsafe_off_topic, system_control, prompt_injection)
    - Granular Intent
    - Entities (Service, Website Type, Budget, Timeline, Contact info)
    - Lead intent & Urgency
    """
    SERVICE_KEYWORDS = {
        "CRM & ERP": ["crm", "erp", "sales crm", "lead management", "inventory management", "enterprise resource", "सीआरएम", "ईआरपी"],
        "AI Automation": ["ai", "chatbot", "automation", "llm", "genai", "artificial intelligence", "workflow automation", "bot", "एआई", "चैटबॉट"],
        "Website Development": ["website", "web app", "web development", "react", "nextjs", "frontend", "landing page", "ecommerce", "e-commerce", "saas", "वेबसाइट", "वेब"],
        "Mobile App Development": ["app", "mobile app", "android", "ios", "flutter", "react native", "application", "ऐप"],
        "Custom Software Development": ["custom software", "software development", "bespoke software", "saas", "platform development", "सॉफ्टवेयर"],
        "Cloud Solutions": ["cloud", "aws", "azure", "gcp", "devops", "cloud migration", "docker", "kubernetes", "क्लाउड"],
        "UI/UX Design": ["ui", "ux", "design", "figma", "wireframe", "prototype", "user interface", "डिजाइन"],
        "Digital Marketing & SEO": ["seo", "smo", "digital marketing", "google ads", "meta ads", "ppc", "ranking", "traffic", "एसईओ", "मार्केटिंग"]
    }

    def analyze(self, query: str) -> Dict[str, Any]:
        q_lower = query.lower().strip()

        # 1. Detect language (strict detection)
        lang = language_detector.detect(query)

        # 2. Domain classification
        domain = domain_classifier.classify(query)

        # 3. Detect entities & services
        detected_services = []
        for service, kws in self.SERVICE_KEYWORDS.items():
            for kw in kws:
                if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                    detected_services.append(service)
                    break

        # Specific website sub-type
        website_type = None
        if "ecommerce" in q_lower or "e-commerce" in q_lower or "online store" in q_lower:
            website_type = "ecommerce"
        elif "saas" in q_lower:
            website_type = "saas"
        elif "landing page" in q_lower or "single page" in q_lower:
            website_type = "landing_page"
        elif any(w in q_lower for w in ["business website", "normal website", "simple website", "company website"]):
            website_type = "business_website"

        # Extract USER budget (e.g. ₹50,000, 50k, 5 lakh, 10000)
        budget_match = re.search(r'([₹$€£]\s*[\d,\.]+\s*(?:k|lakh|crore|lac|thousand|m)?|\b\d+\s*(?:k|lakh|crore|lac|thousand)\b|\b\d{4,7}\s*(?:budget|me|mein|rupees|inr|rs)?\b)', q_lower)
        budget = budget_match.group(1).strip() if budget_match else None

        # Extract timeline (e.g. 2 months, 3 weeks, 15 days, urgent)
        timeline_match = re.search(r'(\d+\s*(?:month|week|day|year)s?|urgently?|asap|immediate)', q_lower)
        timeline = timeline_match.group(1).strip() if timeline_match else None

        # Extract email & phone
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', query)
        email = email_match.group(0) if email_match else None

        phone_match = re.search(r'(?:\+?91[\s-]?)?[6-9]\d{9}\b', query)
        phone = phone_match.group(0) if phone_match else None

        # 4. Detect Intent
        has_contact_info = bool(email or phone or budget or re.search(r'\b(?:my\s+name\s+is|mera\s+naam)\b', q_lower))
        intent = self._detect_granular_intent(q_lower, domain, detected_services, website_type, has_contact_info=has_contact_info)

        # 5. Lead Intent flag
        lead_intent = bool(
            intent in (
                "website_requirement", "lead_generation", "website_pricing", "website_free_offer",
                "ecommerce", "saas", "crm", "erp", "ai", "app_development", "software_development",
                "consultation", "pricing_general", "pricing_website", "pricing_app", "pricing_software",
                "pricing_crm", "pricing_erp", "pricing_ai", "pricing_seo", "emi", "payment", "payment_terms"
            ) or
            (detected_services and any(v in q_lower for v in ["need", "want", "build", "develop", "banwana", "chahiye", "hire", "looking for"])) or
            has_contact_info
        )

        urgency = "high" if bool(re.search(r"\b(urgent|asap|immediate|emergency|jaldi)\b", q_lower)) else "medium" if lead_intent else "low"

        return {
            "language": lang,
            "domain": domain,
            "intent": intent,
            "requested_services": detected_services,
            "website_type": website_type,
            "entities": {
                "services": detected_services,
                "website_type": website_type,
                "budget": budget,
                "timeline": timeline,
                "email": email,
                "phone": phone
            },
            "lead_intent": lead_intent,
            "urgency": urgency
        }

    def _detect_granular_intent(self, q_lower: str, domain: str, services: List[str], website_type: Optional[str], has_contact_info: bool = False) -> str:
        # Check system control & unsafe first
        if domain == "system_control":
            return "system_control"
        if domain == "prompt_injection":
            return "prompt_injection"
        if domain == "unsafe_off_topic":
            return "unsafe"
        if domain == "legal_advice":
            return "legal_advice"
        if domain == "off_topic":
            return "off_topic"

        # Check technology general (Master AI Spec §3 & §4)
        if domain == "technology_general":
            return "technology_general"

        # Casual acknowledgments & simple politeness (Master AI Spec §27)
        if re.search(r"^(?:thanks|thank\s+you|thx|dhanyawad|shukriya|thanks\s+a\s+lot|thank\s+you\s+so\s+much)[\s!\.]*$", q_lower):
            return "casual_thanks"
        if re.search(r"^(?:ok|okay|thik\s+hai|theek\s+hai|got\s+it|understood|cool|great|nice|perfect|done|sahi\s+hai)[\s!\.]*$", q_lower):
            return "casual_acknowledgment"

        # Support & Existing customer issue (Master AI Spec §4F)
        if re.search(r"\b(not working|issue with (?:my\s+)?website|website is down|developer is not responding|maintenance|need an update)\b", q_lower):
            return "support_request"

        # Explicit free website queries
        if re.search(r"\b(free website|website for free|free me website|free website milegi|website free me mil sakti hai|do you provide any free website|build free website|can i get a website for free|can you provide a free website)\b", q_lower):
            return "free_offer"

        if "free" in q_lower and any(w in q_lower for w in ["website", "site", "web"]):
            return "free_offer"

        # Free SEO / SMO
        if "free" in q_lower and ("seo" in q_lower or "smo" in q_lower):
            return "seo"

        # EMI & Payment terms / financing
        if re.search(r"\b(emi|installment|installments|zero-cost emi|zero cost emi|12 months emi|12-month emi|monthly installment|kist|kisht)\b", q_lower):
            return "emi"

        if re.search(r"\b(25%|25 percent|75%|75 percent|upfront|advance|downpayment|down\s*payment|payment|paymnet|paymnt|pymnt|pyment|bhugtan|payment plan|payment model|payment terms|payment method|payment methods|after delivery)\b", q_lower):
            return "payment_terms"

        # Specific Pricing queries
        is_pricing = bool(re.search(r"\b(price|pricing|cost|how much|charges|rate|quote|quotation|fees|package|packages|kitna charge|kitne paise|kitna kharcha|kitna lagega|kitne ki hai|charge of a normal website)\b", q_lower))
        if is_pricing:
            if "Website Development" in services or re.search(r"\b(website|web)\b", q_lower):
                return "pricing_website"
            elif "CRM & ERP" in services or re.search(r"\bcrm\b", q_lower):
                return "pricing_crm"
            elif re.search(r"\berp\b", q_lower):
                return "pricing_erp"
            elif "Mobile App Development" in services or (re.search(r"\b(mobile\s+app|apps?|application)\b", q_lower) and "whatsapp" not in q_lower):
                return "pricing_app"
            elif "Custom Software Development" in services or re.search(r"\b(software|softwares)\b", q_lower):
                return "pricing_software"
            elif "AI Automation" in services or re.search(r"\b(ai|artificial\s+intelligence|chatbot|chatbots|automation)\b", q_lower):
                return "pricing_ai"
            elif "Digital Marketing & SEO" in services or re.search(r"\b(seo|smo)\b", q_lower):
                return "pricing_seo"
            else:
                return "pricing_general"

        # Human handoff
        if re.search(r"\b(talk to human|speak to agent|call me|connect with team|human support|customer care|executive|talk to someone|team se baat|human handoff)\b", q_lower):
            return "human_handoff"

        # Website features (responsive design, WhatsApp integration, enquiry/contact forms)
        if re.search(r"\b(responsive|mobile\s+responsive|tablet\s+responsive|whatsapp\s+integration|whatsapp|enquiry\s+form|contact\s+form|enquiry\/contact\s+form|click\s+to\s+chat)\b", q_lower):
            return "website_features"

        # Domain & Hosting policies
        if re.search(r"\b(domain|domains|hosting|server|servers|dns|nameservers?|godaddy|hostinger|cloud\s+server)\b", q_lower):
            return "domain_hosting"

        # Difference / Comparison between website and web app
        if re.search(r"\b(difference\s+between|kya\s+difference\s+hai|difference\s+kya\s+hai|website\s+aur\s+(?:custom\s+)?web\s+app)\b", q_lower):
            return "website_requirement"

        # Working hours & timings
        if re.search(r"\b(working\s+hours|office\s+hours|timings?|office\s+timings?|kab\s+khulta\s+hai|open\s+timing|closing\s+timing|kab\s+open)\b", q_lower):
            return "working_hours"

        # Contact details & Location
        if re.search(r"\b(contact|phone|email|address|location|reach|office|call you|where are you located|kahan hai|head office|number)\b", q_lower):
            return "contact"

        # Consultation & Meetings
        if re.search(r"\b(consultation|meeting|discuss|schedule|appointment)\b", q_lower):
            return "consultation"

        # Client experience & Portfolio
        if re.search(r"\b(kitne\s+clients|kitne\s+projects|how\s+many\s+clients|how\s+many\s+projects|experience|past\s+work|case\s+stud(?:y|ies)|portfolio|clients)\b", q_lower):
            return "experience_portfolio"

        # Industries served
        if re.search(r"\b(industr(?:y|ies)|sectors?|domains?|kin\s+industries|which\s+industries|types\s+of\s+businesses)\b", q_lower):
            return "industries"

        # Why choose us / Comparison / Value proposition
        if re.search(r"\b(why\s+(?:should\s+(?:we|i)\s+)?choose|kyun\s+choose|comparison|why\s+techvunex|compare\s+to\s+other|advantages?|benefits?)\b", q_lower):
            return "why_choose_us"

        # Technology stack
        if re.search(r"\b(technology|technologies|tech\s+stack|tools|frameworks?|python|node|react|nextjs|flutter|postgresql|kaunsi\s+technology)\b", q_lower):
            return "technology"

        # AI Automation specifically (e.g. AI chatbot, RAG, knowledge base, documents)
        if re.search(r"\b(ai\s+chatbot|rag\s+chatbot|ai|artificial\s+intelligence|rag|llm|chatbot|chatbots|genai|generative\s+ai|automation|workflow\s+automation|knowledge\s+base|documents\s+se\s+connect)\b", q_lower):
            return "ai"

        # Parent company queries
        if re.search(r"\b(parent\s+comp(?:any|ny)|parent|digital\s+yug|holding\s+company|mool\s+company)\b", q_lower):
            return "parent_company"

        # Company info & overview (Checked with specific anchors, not bare 'company')
        if re.search(r"\b(about\s+techvunex|about\s+us|who\s+are\s+you|what\s+is\s+techvunex|techvunex\s+(?:innovation\s+)?kya\s+hai|techvunex\s+company|techvunex\s+overview|company\s+overview|founder|history|establish|established|establishment|founded|kab\s+(?:bani|shuru|establish))\b", q_lower) or ("services" in q_lower and any(w in q_lower for w in ["what", "provide", "exactly", "kya", "dete", "offer"])):
            return "company_info"

        # Website requirement specifically (e.g. "I want a website", "Mujhe website banwani hai")
        if any(w in q_lower for w in ["website", "site", "web"]) and any(w in q_lower for w in ["want", "need", "build", "develop", "banwana", "banwani", "chahiye", "banana", "looking for", "make", "bana sakte", "kis-kis type", "types of website"]):
            if website_type == "ecommerce":
                return "ecommerce"
            elif website_type == "saas":
                return "saas"
            elif website_type == "landing_page":
                return "landing_page"
            return "website_requirement"

        # E-commerce store specifically
        if re.search(r"\b(ecommerce|e-commerce|online\s+store|online\s+shop|product\s+catalog|shopping\s+cart|payment\s+gateway)\b", q_lower):
            return "ecommerce"

        # Other services (using strict regex word boundary matching)
        if "CRM & ERP" in services or re.search(r"\b(crm|erp)\b", q_lower):
            return "crm"
        if "AI Automation" in services or re.search(r"\b(ai|artificial\s+intelligence|rag|llm|chatbot|chatbots|genai|generative\s+ai|automation|workflow\s+automation|knowledge\s+base|documents\s+connect)\b", q_lower):
            return "ai"
        if "Mobile App Development" in services or (re.search(r"\b(mobile\s+app|apps?|application|android|ios|flutter|react\s+native)\b", q_lower) and "whatsapp" not in q_lower):
            return "app_development"
        if "Custom Software Development" in services or re.search(r"\b(custom\s+software|software|softwares)\b", q_lower):
            return "software_development"
        if "UI/UX Design" in services or re.search(r"\b(ui\/ux|ui\s+ux|figma|wireframe|prototype|user\s+interface|user\s+experience)\b", q_lower) or (re.search(r"\b(ui|ux)\b", q_lower) and not re.search(r"\bhui\b", q_lower)):
            return "uiux"
        if "Digital Marketing & SEO" in services or re.search(r"\b(seo|search\s+engine\s+optimization)\b", q_lower):
            return "seo"
        if re.search(r"\bsmo\b", q_lower):
            return "smo"

        # General lead generation
        if has_contact_info or any(v in q_lower for v in ["need", "want", "build", "develop", "banwana", "banwani", "chahiye", "hire"]):
            return "lead_generation"

        return "service_info"

    def rewrite_query_for_rag(self, user_msg: str, intent: str, services: List[str]) -> str:
        """
        Rewrites the user query into an optimal search query before hybrid RAG retrieval.
        Preserves original intent and boosts pricing, offers, and package precision.
        """
        q_lower = user_msg.lower()

        if intent in ("website_free_offer", "free_offer"):
            return "Techvunex 100% free website offer ₹0 development cost 4-5 pages WhatsApp SEO SMO 15 days support"

        if intent in ("pricing_website", "website_pricing"):
            return "Techvunex website development pricing packages free business website package custom development rates"

        if intent == "emi":
            return "Techvunex payment plan zero-cost 12-month EMI 0% interest monthly installments 75% delivery"

        if intent in ("payment", "payment_terms"):
            return "Techvunex payment model 25% upfront kickoff 75% after delivery 12-month zero-cost EMI"

        if intent in ("seo", "smo"):
            if "free" in q_lower or "offer" in q_lower:
                return "Techvunex 100% free SEO support forever free SMO support forever audit deliverables exclusions"
            return "Techvunex SEO digital marketing services ranking meta ads google ads"

        if intent == "working_hours":
            return "Techvunex office working hours timings Monday to Saturday 10:30 AM to 6:30 PM IST Sunday closed Noida Sector 63"

        if intent == "parent_company":
            return "Techvunex Innovation parent company Digital Yug Innovation https://digitalyuginnovation.com/ Noida corporate hierarchy"

        if intent == "contact":
            return "Techvunex contact details phone email address Noida Sector 63 +91-7834979979 info@techvunex.in office timings"

        if intent == "company_info":
            return "Techvunex Innovation software development company services overview Noida Sector 63 technology digital solutions"

        if intent == "experience_portfolio":
            return "Techvunex Innovation client experience projects delivered portfolio startups enterprise domains"

        if intent == "industries":
            return "Techvunex industries served ecommerce retail healthcare clinics education LMS real estate corporate enterprise"

        if intent == "why_choose_us":
            return "Why choose Techvunex Innovation modern technology stack transparent pricing zero-cost EMI free website offer dedicated support"

        if intent == "website_features":
            return "Techvunex website features fully responsive mobile tablet WhatsApp integration lead enquiry form SEO starter setup"

        if intent == "domain_hosting":
            return "Techvunex domain hosting guidelines client credentials ownership DNS SSL setup free website package AWS Hostinger"

        if intent == "technology":
            return "Techvunex technology stack frontend React Next.js backend Python FastAPI Node.js databases PostgreSQL MongoDB Redis"

        if intent == "crm":
            return "Techvunex CRM ERP software development modules lead management enterprise quotation"

        if intent == "ai":
            return "Techvunex AI automation intelligent RAG chatbots company documents knowledge base workflow automation"

        if intent == "website_requirement":
            return "Techvunex website development services modern responsive business website web application"

        if intent == "ecommerce":
            return "Techvunex ecommerce website development online store payment gateway product catalog"

        if intent == "technology_general":
            return f"Techvunex technology stack modern web development architecture {user_msg}"

        if intent in ("casual_thanks", "casual_acknowledgment"):
            return "Techvunex customer assistance greeting services"

        if intent == "support_request":
            return "Techvunex technical support post-launch maintenance human handoff assistance"

        # General prefix with company context
        return f"Techvunex {user_msg}"

query_agent = QueryUnderstandingAgent()

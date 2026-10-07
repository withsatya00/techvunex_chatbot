import time
import json
import asyncio
import re
from typing import Dict, Any, List, AsyncIterator, Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.core.security import sanitize_and_check_injection
from app.core.exceptions import PromptInjectionError
from app.core.logging import logger
from app.rag.pipeline import rag_pipeline
from app.llm.factory import get_llm_provider
from app.agents.language import language_detector
from app.agents.domain import domain_classifier
from app.agents.intent import query_agent
from app.agents.sales import sales_agent
from app.agents.prompts import build_system_prompt
from app.agents.post_processor import response_post_processor
from app.services.conversation_service import conversation_service
from app.services.lead_service import lead_service
from app.schemas.chat import ChatResponse, SourceRef

class ChatService:
    def __init__(self):
        self.llm = get_llm_provider()
        self._faq_cache: Dict[str, Dict[str, Any]] = {}
        self._max_faq_cache_size = 500
        self._warm_up_faq_cache()

    def _warm_up_faq_cache(self):
        """Pre-seeds standard high-frequency queries for instant <20ms zero-latency responses."""
        default_sources = [
            SourceRef(
                source_url="https://techvunex.in/",
                page_title="Techvunex Innovation Official",
                section="Company & Services Overview",
                snippet="Techvunex Innovation software development, modern web platforms, mobile apps, CRM/ERP and AI automation.",
                similarity=0.99
            )
        ]
        default_chunks = [
            {
                "source_url": "https://techvunex.in/",
                "page_title": "Techvunex Innovation Official",
                "section": "Company & Services Overview",
                "content": "Techvunex Innovation delivers enterprise-grade software, website development, mobile apps, CRM/ERP, and AI automation.",
                "relevance_score": 0.99
            }
        ]

        srv_en = (
            "Techvunex Innovation delivers modern, high-performance technology solutions:\n\n"
            "• **Custom Website & Web App Development** (React, Next.js, Node.js, FastAPI)\n"
            "• **100% Free Business Website Offer** (₹0 development fee for standard business sites)\n"
            "• **Custom Software & SaaS Platforms** (Scalable architecture, cloud-ready)\n"
            "• **Custom CRM & ERP Systems** (Lead management, sales pipelines, inventory)\n"
            "• **Mobile App Development** (Android & iOS with Flutter & React Native)\n"
            "• **AI & Automation** (Custom RAG chatbots, workflow automation)\n"
            "• **Digital Marketing & SEO** (Search ranking and social media optimization)\n\n"
            "Which service would you like to explore for your project?"
        )
        srv_hi = (
            "Techvunex Innovation yeh comprehensive technology aur digital solutions provide karta hai:\n\n"
            "• **Custom Website & Web App Development** (Fast, modern, interactive web applications)\n"
            "• **100% Free Business Website Offer** (₹0 development fee standard business websites ke liye)\n"
            "• **Custom CRM & ERP Solutions** (Lead tracking, sales pipeline, inventory management)\n"
            "• **Mobile App Development** (Android aur iOS ke liye high-performance apps)\n"
            "• **AI & Workflow Automation** (Custom AI chatbots aur automated workflows)\n"
            "• **Digital Marketing & SEO** (Google ranking aur social media growth)\n\n"
            "Aapko apne business ya project ke liye kis service ki zaroorat hai?"
        )

        free_en = (
            "Techvunex Innovation provides a **100% Free Business Website Package** to empower growing businesses:\n\n"
            "• **₹0 Development Fee:** For standard 4–5 page business websites (Home, About Us, Services, Portfolio/Gallery, Contact Us).\n"
            "• **Included Features:** 100% mobile-responsive design, 1-click WhatsApp chat button, lead enquiry form, starter SEO setup, and starter SMO support.\n"
            "• **Revisions & Support:** 2 guided design revision rounds and 15 days of post-launch technical assistance.\n"
            "• *Note:* Complex custom web apps, multi-vendor stores, and SaaS portals require custom engineering and are quoted separately.\n\n"
            "Would you like to get started with your free business website?"
        )
        free_hi = (
            "Techvunex Innovation ka **100% Free Business Website Offer** businesses ke liye ₹0 development cost par available hai:\n\n"
            "• **Kya included hai:** Standard 4–5 pages (Home, About Us, Services, Gallery/Portfolio, Contact Us).\n"
            "• **Features:** 100% Mobile responsive design, 1-click WhatsApp button, lead enquiry form, starter SEO setup aur 2 design revisions.\n"
            "• **Support:** Launch ke baad 15 days technical assistance.\n"
            "• *Note:* Complex SaaS platforms ya multi-vendor e-commerce stores custom development scope mein aate hain.\n\n"
            "Kya aap apne business ke liye yeh free website package start karna chahenge?"
        )

        hours_en = (
            "Techvunex Innovation official office timings:\n\n"
            "• **Working Days:** Monday to Saturday\n"
            "• **Working Hours:** 10:30 AM to 6:30 PM IST\n"
            "• **Sunday:** Closed\n\n"
            "Our AI Assistant is available 24/7 right here to answer your questions and assist with quotes!"
        )
        hours_hi = (
            "Techvunex Innovation ke official office timings:\n\n"
            "• **Working Days:** Monday se Saturday\n"
            "• **Timings:** 10:30 AM se 6:30 PM IST\n"
            "• **Sunday:** Closed\n\n"
            "Hamara AI assistant 24/7 yahan available hai aapki queries aur quotes assist karne ke liye!"
        )

        loc_en = (
            "Techvunex Innovation is headquartered in **Sector 63, Noida, Uttar Pradesh, India** (PIN: 201301).\n\n"
            "We serve clients across India and globally for software, web, mobile, and AI solutions."
        )
        loc_hi = (
            "Techvunex Innovation ka head office **Sector 63, Noida, Uttar Pradesh, India** mein sthit hai.\n\n"
            "Hum poore India aur globally clients ko software aur web development deliver karte hain."
        )

        pay_en = (
            "For custom paid development projects, Techvunex Innovation follows a client-friendly payment structure:\n\n"
            "• **25% Upfront:** Paid at project kickoff to begin UI/UX design and architecture.\n"
            "• **Remaining 75% via Zero-Cost EMI:** Spread over a 12-month 0% interest EMI plan post-delivery for eligible projects.\n"
            "• *Example:* For a ₹2 Lakh project, you pay ₹50,000 upfront and ₹12,500/month for 12 months with ₹0 extra interest.\n\n"
            "Would you like an estimated quote for your specific requirement?"
        )
        pay_hi = (
            "Techvunex Innovation custom software aur web projects ke liye flexible payment model offer karta hai:\n\n"
            "• **25% Upfront:** Project kickoff ke samay design aur development shuru karne ke liye.\n"
            "• **Remaining 75% Zero-Cost EMI:** Project deliver hone ke baad 12-month 0% interest EMI par pay kar sakte hain.\n"
            "• *Example:* ₹2 Lakh ke project par ₹50,000 upfront + ₹12,500/month 12 mahine ke liye.\n\n"
            "Aap apne project requirement ke hisaab se estimate calculate karwana chahte hain?"
        )

        contact_en = (
            "You can connect directly with the Techvunex Innovation team:\n\n"
            "• **Phone / WhatsApp:** +91-7834979979\n"
            "• **Email:** info@techvunex.in\n"
            "• **Website:** https://techvunex.in/\n"
            "• **Headquarters:** Sector 63, Noida, Uttar Pradesh, India\n"
            "• **Working Hours:** Monday – Saturday, 10:30 AM – 6:30 PM IST (Sunday closed)\n\n"
            "You can also leave your phone number or email right here, and our technical team will reach out to you directly!"
        )
        contact_hi = (
            "Aap Techvunex Innovation team se directly connect kar sakte hain:\n\n"
            "• **Phone / WhatsApp:** +91-7834979979\n"
            "• **Email:** info@techvunex.in\n"
            "• **Website:** https://techvunex.in/\n"
            "• **Headquarters:** Sector 63, Noida, Uttar Pradesh\n"
            "• **Office Hours:** Monday – Saturday, 10:30 AM – 6:30 PM IST (Sunday closed)\n\n"
            "Aap apna contact number ya email yahan share kar sakte hain, hamari team aapse direct connect karegi!"
        )

        about_en = (
            "**Techvunex Innovation** is a modern software and digital solutions company headquartered in Sector 63, Noida, Uttar Pradesh.\n\n"
            "• **Parent Company:** Techvunex Innovation operates under its parent company, **Digital Yug Innovation** (Official Website: https://digitalyuginnovation.com/).\n"
            "• **Core Capabilities:** Custom software platforms, responsive web apps, mobile applications, CRM/ERP systems, and AI automation for startups and growing enterprises."
        )
        about_hi = (
            "**Techvunex Innovation** ek leading software aur web development company hai jo Sector 63, Noida, UP mein headquartered hai.\n\n"
            "• **Parent Company:** Techvunex Innovation apni parent company **Digital Yug Innovation** (https://digitalyuginnovation.com/) ke under operate karti hai.\n"
            "• **Services:** Custom web development, mobile apps, CRM/ERP aur AI automation solutions."
        )

        canonical_items = [
            (
                ["services", "what services do you offer", "what services do you provide", "what do you do", "techvunex services", "kya kya service dete ho", "kon kon si service dete ho", "services provide", "services available"],
                srv_en, srv_hi, "company_services", ["100% Free Website Offer", "25% Upfront & EMI Terms", "Talk to Expert"]
            ),
            (
                ["free website offer", "100% free website offer", "free website", "free website package", "free offer", "website free offer", "free website kya hai", "kya website sach me free hai", "free site"],
                free_en, free_hi, "free_website", ["100% Free Website Offer", "25% Upfront & EMI Terms", "Talk to Expert"]
            ),
            (
                ["working hours", "office timings", "office hours", "office timing", "timings", "timing", "hours", "kab open rehta hai", "kab khulta hai", "working time"],
                hours_en, hours_hi, "working_hours", ["What services do you provide?", "100% Free Website Offer", "Talk to Expert"]
            ),
            (
                ["office location", "office address", "where is your office", "location", "address", "kahan par hai office", "noida office", "head office"],
                loc_en, loc_hi, "office_location", ["What services do you provide?", "100% Free Website Offer", "Talk to Expert"]
            ),
            (
                ["payment terms", "payment options", "payment plan", "emi", "emi options", "zero cost emi", "25% upfront", "payment model", "pricing model", "bhugtan"],
                pay_en, pay_hi, "payment_terms", ["100% Free Website Offer", "Request Quote", "Talk to Expert"]
            ),
            (
                ["contact", "contact details", "contact number", "phone number", "email", "how to contact", "kaise contact karein", "contact us"],
                contact_en, contact_hi, "contact", ["Schedule Call", "Request Quote", "What services do you provide?"]
            ),
            (
                ["about techvunex", "what is techvunex", "who are you", "parent company", "digital yug innovation", "company details", "techvunex kya hai"],
                about_en, about_hi, "company_info", ["What services do you provide?", "100% Free Website Offer", "Talk to Expert"]
            )
        ]

        for phrases, en_text, hi_text, topic_intent, actions in canonical_items:
            for p in phrases:
                entry_en = {
                    "text": en_text,
                    "sources": default_sources,
                    "unique_chunks": default_chunks,
                    "suggested_actions": actions
                }
                entry_hi = {
                    "text": hi_text,
                    "sources": default_sources,
                    "unique_chunks": default_chunks,
                    "suggested_actions": actions
                }
                self._faq_cache[f"{p}_en_{topic_intent}"] = entry_en
                self._faq_cache[f"{p}_hinglish_{topic_intent}"] = entry_hi
                self._faq_cache[f"{p}_hi_{topic_intent}"] = entry_hi
                self._faq_cache[f"{p}_en"] = entry_en
                self._faq_cache[f"{p}_hinglish"] = entry_hi
                self._faq_cache[f"{p}_hi"] = entry_hi

    def _find_in_faq_cache(self, clean_msg: str, rag_search_query: str, lang: str, intent: str) -> Optional[Dict[str, Any]]:
        msg_norm = clean_msg.strip().lower()
        rag_norm = rag_search_query.strip().lower()

        # 1. Exact keys
        for k in (f"{rag_norm}_{lang}_{intent}", f"{msg_norm}_{lang}_{intent}", f"{rag_norm}_{lang}", f"{msg_norm}_{lang}"):
            if k in self._faq_cache:
                return self._faq_cache[k]

        # 2. Phrase matching
        for k, v in self._faq_cache.items():
            base_phrase = k.rsplit("_", 2)[0] if "_" in k else k
            if base_phrase and (base_phrase == msg_norm or base_phrase == rag_norm or (len(base_phrase) > 5 and base_phrase in msg_norm)):
                if lang in k or ("en" in k and lang == "en"):
                    return v

        return None

    def _reformulate_query(self, user_msg: str, history: List[Dict[str, str]]) -> str:
        """
        Reformulates short follow-ups using recent conversation history so hybrid
        RAG can retrieve the exact knowledge chunks.
        """
        if not history:
            return user_msg

        msg_lower = user_msg.lower().strip()
        words = msg_lower.split()

        # If query is short (<= 5 words) or a clear follow-up answer
        if len(words) <= 5:
            recent_context = ""
            for h in reversed(history[-4:]):
                text = h.get("content", "").lower()
                if any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["website", "web app", "landing page"]):
                    recent_context = "website development"
                    break
                elif any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["crm", "erp"]):
                    recent_context = "crm erp"
                    break
                elif any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["mobile app", "android", "ios", "flutter"]):
                    recent_context = "mobile app development"
                    break
                elif any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["seo", "smo", "digital marketing"]):
                    recent_context = "seo digital marketing"
                    break
                elif any(re.search(r'\b' + re.escape(k) + r'\b', text) for k in ["ai", "chatbot", "chatbots", "rag"]):
                    recent_context = "ai automation"
                    break

            if recent_context and not any(k in msg_lower for k in recent_context.split()):
                return f"{recent_context} {user_msg}"

        return user_msg

    @staticmethod
    def _deduplicate_sources(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Keep only unique sources normalized by source_url."""
        seen_urls = set()
        unique = []
        for c in chunks:
            raw_url = c.get("source_url", "").rstrip("/")
            if raw_url and raw_url not in seen_urls:
                seen_urls.add(raw_url)
                unique.append(c)
        return unique

    @staticmethod
    def _extract_conversation_memory(current_msg: str, history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Extracts known user details across the current message and all prior history
        to maintain conversational memory (Master AI Spec §5).
        """
        user_messages = [h.get("content", "") for h in history if h.get("role") == "user"] + [current_msg]
        reversed_messages = list(reversed(user_messages))
        
        memory: Dict[str, Any] = {}

        # 1. User Name extraction (latest introduced name wins)
        for msg in reversed_messages:
            name_match = re.search(
                r'(?i)\b(?:my\s+name\s+is|name\s+is|name\s*[:=-]\s*|mera\s+naam\s+hai|mera\s+naam\s*[:=-]?|i\s*[\'’]?m|i\s+am|myself|this\s+is|call\s+me|naam\s*[:=-]?)\s+([A-Za-z]{2,25})(?:\s+(?!hai|aur|from|at|with|and|company|phone|mobile|mobike|email|ji|sir)([A-Za-z]{2,25}))?',
                msg
            )
            if name_match:
                first = name_match.group(1).strip()
                second = name_match.group(2).strip() if name_match.group(2) else ""
                if first.lower() in ("hai", "mera", "naam", "ek", "mujhe", "please", "techvunex", "website", "looking", "interested", "need", "here", "ready", "a", "an"):
                    first = ""
                cand = f"{first} {second}".strip() if second else first
                if cand:
                    memory["name"] = cand.title()
                    break

        # Fallback for name: check if user directly replied to an assistant question asking for name
        if not memory.get("name") and history:
            for idx, h in enumerate(history):
                if h.get("role") == "assistant" and any(k in h.get("content", "").lower() for k in ["your name", "aapka naam", "share your name", "know your name"]):
                    if idx + 1 < len(history) and history[idx + 1].get("role") == "user":
                        reply = history[idx + 1].get("content", "").strip()
                        if re.match(r'^[A-Za-z]{2,25}(?:\s+[A-Za-z]{2,25})?$', reply):
                            if reply.lower() not in ("yes", "no", "sure", "ok", "okay", "hello", "hi", "hey", "website", "techvunex", "crm", "erp", "app"):
                                memory["name"] = reply.title()
                                break

        # 2. Phone extraction (latest phone wins)
        for msg in reversed_messages:
            phone_match = re.search(r'(?:\+?91[\s-]?)?\b[6-9]\d{9}\b', msg)
            if not phone_match:
                phone_match = re.search(r'(?i)(?:phone|mobile|mobike|contact|number|no\.?|call|whatsapp)[\s:]*([0-9]{10})\b', msg)
            if not phone_match:
                phone_match = re.search(r'\b\d{10}\b', msg)
            if phone_match:
                raw_p = phone_match.group(1).strip() if phone_match.groups() and phone_match.group(1) else phone_match.group(0).strip()
                digits = re.sub(r'\D', '', raw_p)
                if len(digits) == 12 and digits.startswith("91"):
                    digits = digits[2:]
                memory["phone"] = digits if len(digits) == 10 else raw_p
                break

        # 3. Email extraction (latest email wins)
        for msg in reversed_messages:
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', msg)
            if email_match:
                memory["email"] = email_match.group(0).strip()
                break

        # 4. Budget extraction (latest budget wins)
        for msg in reversed_messages:
            budget_match = re.search(r'([₹$€£]\s*[\d,\.]+\s*(?:k|lakh|crore|lac|thousand|m)?|\b\d+\s*(?:k|lakh|crore|lac|thousand)\b|\b\d{4,7}\s*(?:budget|me|mein|rupees|inr|rs)?\b)', msg, re.IGNORECASE)
            if budget_match:
                memory["budget"] = budget_match.group(1).strip()
                break

        # 5. Business Category extraction (latest business category mentioned wins)
        business_categories = [
            "clothing", "retail", "fashion", "restaurant", "cafe", "hotel", "clinic", "hospital",
            "healthcare", "real estate", "property", "gym", "fitness", "education", "school",
            "college", "institute", "travel", "tourism", "agency", "consulting", "law firm", "salon",
            "bakery", "food", "grocery", "jewellery", "jewelry", "logistics", "pharmacy"
        ]
        for msg in reversed_messages:
            found_cat = None
            for cat in business_categories:
                if re.search(r'\b' + re.escape(cat) + r'\b', msg, re.IGNORECASE):
                    found_cat = cat.capitalize()
                    break
            if found_cat:
                memory["business_type"] = found_cat
                break

        # 6. Website Type extraction (latest website type mentioned wins)
        for msg in reversed_messages:
            if re.search(r'\b(?:ecommerce|e-commerce|online\s+store|online\s+shop|online\s+ordering)\b', msg, re.IGNORECASE):
                memory["website_type"] = "E-Commerce / Online Store"
                break
            elif re.search(r'\b(?:saas|web\s+portal|custom\s+platform)\b', msg, re.IGNORECASE):
                memory["website_type"] = "SaaS Platform / Custom Portal"
                break
            elif re.search(r'\b(?:landing\s+page|single\s+page)\b', msg, re.IGNORECASE):
                memory["website_type"] = "Landing Page"
                break
            elif re.search(r'\b(?:business\s+website|company\s+website|corporate\s+website)\b', msg, re.IGNORECASE):
                memory["website_type"] = "Standard Business Website"
                break

        return memory

    @staticmethod
    def _resolve_lead_service(current_services: List[str], history: List[Dict[str, str]], intent: str) -> Optional[str]:
        """Resolves the user's intended service from current message, dialogue history, or detected intent."""
        if current_services:
            return ", ".join(current_services)
        for h in reversed(history):
            if h.get("role") == "user":
                prev_ana = query_agent.analyze(h.get("content", ""))
                if prev_ana.get("requested_services"):
                    return ", ".join(prev_ana["requested_services"])
        if intent in ("free_offer", "website_free_offer", "website_requirement", "pricing_website", "website_features", "ecommerce", "saas"):
            return "Website Development"
        elif intent in ("crm", "pricing_crm", "pricing_erp"):
            return "CRM & ERP Solutions"
        elif intent in ("ai", "pricing_ai"):
            return "AI Automation"
        elif intent in ("app_development", "pricing_app"):
            return "Mobile App Development"
        elif intent in ("seo", "smo", "pricing_seo"):
            return "Digital Marketing & SEO"
        return None

    async def process_chat(
        self,
        session: AsyncSession,
        session_id: str,
        user_message: str,
        language_preference: str = "auto"
    ) -> ChatResponse:
        start_time = time.time()

        # 1. Sanitize & check injection
        try:
            clean_msg = sanitize_and_check_injection(user_message)
            is_injection = False
        except PromptInjectionError:
            clean_msg = user_message
            is_injection = True

        # 2. Conversation session & History
        conv = await conversation_service.get_or_create_conversation(session, session_id)
        history = await conversation_service.get_conversation_history(session, conv.id, limit=8)

        # 3. Language Detection (latest message has highest priority)
        detected_lang = language_detector.resolve_conversation_language(clean_msg)
        lang = detected_lang if language_preference == "auto" else language_preference

        # 4. Domain Classification (active dialogue aware - Master AI Spec §5 & §40)
        if is_injection:
            domain = "prompt_injection"
        else:
            domain = domain_classifier.classify(clean_msg, has_active_dialogue=bool(history))

        # 5. Domain Boundary Check: Off-topic, Unsafe, System Control, Prompt Injection, Legal Advice, Greeting, Thanks, Ack
        # CRITICAL RULE: DO NOT SEND OFF-TOPIC OR INSTANT CONVERSATIONAL GREETINGS INTO RAG!
        if domain in ("off_topic", "unsafe_off_topic", "system_control", "prompt_injection", "legal_advice", "greeting", "thanks", "acknowledgment"):
            boundary_text = domain_classifier.get_boundary_response(domain, clean_msg, lang)
            
            # Save messages in single batch commit
            await conversation_service.add_messages(
                session=session,
                conversation_id=conv.id,
                messages_data=[
                    {"role": "user", "content": clean_msg},
                    {"role": "assistant", "content": boundary_text, "sources": []}
                ]
            )
            
            latency = (time.time() - start_time) * 1000
            debug_payload = {
                "query": clean_msg,
                "language": lang,
                "domain": domain,
                "intent": domain,
                "rag_called": False,
                "latency_ms": round(latency, 2)
            }
            suggested = ["What services do you provide?", "100% Free Website Offer", "Talk to Expert"]
            if domain == "greeting":
                suggested = ["What services do you provide?", "100% Free Website Offer", "Custom Software & CRM", "Talk to Expert"]
            elif domain in ("thanks", "acknowledgment"):
                suggested = ["100% Free Website Offer", "Payment & EMI Options", "What services do you provide?", "Talk to Expert"]

            return ChatResponse(
                conversation_id=conv.id,
                session_id=session_id,
                response=boundary_text,
                sources=[],
                intent=domain,
                entities={},
                lead_intent=False,
                human_required=False,
                latency_ms=round(latency, 2),
                suggested_actions=suggested,
                debug=debug_payload
            )

        # 6. Intent & Entity Analysis
        analysis = query_agent.analyze(clean_msg)
        intent = analysis["intent"]
        detected_services = analysis["requested_services"]

        # 7. Conversational Context & Reformulation
        reformulated_query = self._reformulate_query(clean_msg, history)
        rag_search_query = query_agent.rewrite_query_for_rag(reformulated_query, intent, detected_services)

        # 8. Hybrid RAG Retrieval + Reranking
        context_chunks = rag_pipeline.search_context(
            rag_search_query,
            top_k=settings.TOP_K_RETRIEVAL,
            intent=intent
        )

        # 9. Extract Conversation Memory across history & current query (Master AI Spec §5)
        conversation_memory = self._extract_conversation_memory(clean_msg, history)

        # 10. Sales & Lead Processing
        lead_data = sales_agent.extract_lead_attributes(clean_msg)
        # Retain conversational memory so name, phone, etc. are never lost across turns
        if not lead_data.get("name") and conversation_memory.get("name"):
            lead_data["name"] = conversation_memory["name"]
        if not lead_data.get("phone") and conversation_memory.get("phone"):
            lead_data["phone"] = conversation_memory["phone"]
        if not lead_data.get("email") and conversation_memory.get("email"):
            lead_data["email"] = conversation_memory["email"]
        if not lead_data.get("budget") and conversation_memory.get("budget"):
            lead_data["budget"] = conversation_memory["budget"]
        if not lead_data.get("company") and conversation_memory.get("company"):
            lead_data["company"] = conversation_memory["company"]

        resolved_service = self._resolve_lead_service(detected_services, history, intent)
        if resolved_service:
            lead_data["service"] = resolved_service

        is_handoff, handoff_reason = sales_agent.evaluate_handoff_condition(
            clean_msg, intent, len(context_chunks), lead_data
        )

        if is_handoff:
            lead_data["human_required"] = True
            if lead_data.get("status") != "qualified":
                lead_data["status"] = "human_required"

        # Check FAQ Cache for zero-latency response on repeated/canonical queries
        faq_key = f"{rag_search_query.strip().lower()}_{lang}_{intent}"
        is_cacheable = (
            not is_handoff
            and not lead_data.get("email")
            and not lead_data.get("phone")
            and not lead_data.get("name")
            and domain in ("techvunex_relevant", "general_greeting", "techvunex")
        )
        cached_data = self._find_in_faq_cache(clean_msg, rag_search_query, lang, intent) if is_cacheable else None

        if cached_data:
            assistant_text = cached_data["text"]
            sources = cached_data["sources"]
            suggested_actions = cached_data.get("suggested_actions") or self._generate_suggested_actions(intent, detected_services, False)

            await conversation_service.add_messages(
                session=session,
                conversation_id=conv.id,
                messages_data=[
                    {"role": "user", "content": clean_msg},
                    {"role": "assistant", "content": assistant_text, "sources": [s.model_dump() for s in sources]}
                ]
            )
            latency = (time.time() - start_time) * 1000
            return ChatResponse(
                conversation_id=conv.id,
                session_id=session_id,
                response=assistant_text,
                sources=sources,
                intent=intent,
                entities=analysis["entities"],
                lead_intent=analysis["lead_intent"],
                human_required=False,
                latency_ms=round(latency, 2),
                suggested_actions=suggested_actions,
                debug={
                    "query": clean_msg,
                    "cached": True,
                    "latency_ms": round(latency, 2)
                }
            )

        # Run lead persistence concurrently with LLM generation to eliminate DB wait time
        lead_coro = None
        if analysis["lead_intent"] or lead_data.get("email") or lead_data.get("phone") or is_handoff:
            lead_coro = lead_service.create_or_update_lead(session, lead_data)

        # 10. Build System Prompt with explicit Language Directive & Conversation Memory (Master AI Spec §5)
        system_prompt = build_system_prompt(context_chunks, language=lang, conversation_memory=conversation_memory, current_query=clean_msg)
        messages = history + [{"role": "user", "content": clean_msg}]

        # 11. LLM Generation (concurrently with lead persistence)
        llm_coro = self.llm.generate(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.3
        )
        if lead_coro:
            llm_resp, _ = await asyncio.gather(llm_coro, lead_coro)
        else:
            llm_resp = await llm_coro

        # 12. Response Post-Processing & Validation
        user_name = conversation_memory.get("name") if conversation_memory else None
        assistant_text = response_post_processor.process(
            llm_resp.content,
            expected_language=lang,
            domain=domain,
            known_name=user_name
        )

        # Enforce English if user message was English and LLM generated Hinglish
        if lang == "en" and response_post_processor.has_hinglish_leak(assistant_text):
            logger.warning("Hinglish leakage detected for English query. Regenerating in pure English.")
            try:
                fix_resp = await self.llm.generate(
                    messages=[{"role": "user", "content": f"Translate the following response completely into professional English. Do not include any Hindi or Hinglish words:\n\n{assistant_text}"}],
                    system_prompt="You are a professional translator. Output only the pure English translation with no Hindi, Hinglish, or meta commentary.",
                    temperature=0.0
                )
                if fix_resp.content and not response_post_processor.has_hinglish_leak(fix_resp.content):
                    assistant_text = response_post_processor.process(
                        fix_resp.content,
                        expected_language="en",
                        domain=domain,
                        known_name=user_name
                    )
            except Exception as e:
                logger.error(f"Error recovering English response: {e}")

        # Append human handoff offer only if triggered and relevant
        if is_handoff and "connect" not in assistant_text.lower() and "team" not in assistant_text.lower():
            if lang == "hi":
                assistant_text += "\n\nक्या आप टेकवुनेक्स टीम के साथ सीधे परामर्श के लिए संपर्क करना चाहेंगे? (Direct Call/WhatsApp: +91-7834979979)"
            elif lang == "hinglish":
                assistant_text += "\n\nKya aap Techvunex team ke sath direct consultation connect karna chahenge? (Direct Call/WhatsApp: +91-7834979979)"
            else:
                assistant_text += "\n\nWould you like to connect directly with the Techvunex team for a detailed consultation? (Direct Call/WhatsApp: +91-7834979979)"

        # 13. Deduplicate Sources (Internal tracking only)
        unique_chunks = self._deduplicate_sources(context_chunks)
        sources = [
            SourceRef(
                source_url=c["source_url"],
                page_title=c["page_title"],
                section=c.get("section", ""),
                snippet=c["content"][:200] + "...",
                similarity=round(c.get("relevance_score", 0.0), 3)
            )
            for c in unique_chunks
        ]

        # Store in FAQ cache if eligible
        if is_cacheable:
            if len(self._faq_cache) >= self._max_faq_cache_size:
                oldest_keys = list(self._faq_cache.keys())[:len(self._faq_cache) // 5]
                for ok in oldest_keys:
                    self._faq_cache.pop(ok, None)
            self._faq_cache[faq_key] = {
                "text": assistant_text,
                "sources": sources,
                "unique_chunks": unique_chunks
            }
            logger.info(f"FAQ store: cached response for '{faq_key[:60]}'")

        # 14. Save messages in single batch transaction
        await conversation_service.add_messages(
            session=session,
            conversation_id=conv.id,
            messages_data=[
                {"role": "user", "content": clean_msg},
                {
                    "role": "assistant",
                    "content": assistant_text,
                    "sources": [s.model_dump() for s in sources],
                    "token_usage": {"total_tokens": llm_resp.total_tokens}
                }
            ]
        )

        latency = (time.time() - start_time) * 1000

        # 15. Structured Conversation State for Debugging
        conv_state = {
            "language": lang,
            "domain": domain,
            "intent": intent,
            "service": detected_services[0] if detected_services else None,
            "website_type": analysis.get("website_type"),
            "budget": lead_data.get("budget"),
            "timeline": lead_data.get("timeline"),
            "lead_intent": analysis["lead_intent"]
        }

        debug_payload = {
            "query": clean_msg,
            "reformulated_query": reformulated_query,
            "rag_search_query": rag_search_query,
            "conversation_state": conv_state,
            "latency_ms": round(latency, 2),
            "retrieved_documents": [
                {
                    "title": c.get("page_title"),
                    "url": c.get("source_url"),
                    "content_type": c.get("content_type"),
                    "pricing_type": c.get("pricing_type"),
                    "relevance_score": round(c.get("relevance_score", 0.0), 3)
                }
                for c in context_chunks
            ]
        }

        suggested_actions = self._generate_suggested_actions(intent, detected_services, is_handoff)

        return ChatResponse(
            conversation_id=conv.id,
            session_id=session_id,
            response=assistant_text,
            sources=sources,
            intent=intent,
            entities=analysis["entities"],
            lead_intent=analysis["lead_intent"],
            human_required=is_handoff,
            latency_ms=round(latency, 2),
            suggested_actions=suggested_actions,
            debug=debug_payload
        )

    async def stream_chat(
        self,
        session: AsyncSession,
        session_id: str,
        user_message: str,
        language_preference: str = "auto"
    ) -> AsyncIterator[str]:
        """
        Yields Server-Sent Events (SSE) chunks formatted for smooth, zero-flicker streaming.
        """
        start_time = time.time()

        # 1. Sanitize
        try:
            clean_msg = sanitize_and_check_injection(user_message)
            is_injection = False
        except PromptInjectionError:
            clean_msg = user_message
            is_injection = True

        conv = await conversation_service.get_or_create_conversation(session, session_id)
        history = await conversation_service.get_conversation_history(session, conv.id, limit=8)

        # 2. Language & Domain (active dialogue aware - Master AI Spec §5 & §40)
        detected_lang = language_detector.resolve_conversation_language(clean_msg)
        lang = detected_lang if language_preference == "auto" else language_preference

        if is_injection:
            domain = "prompt_injection"
        else:
            domain = domain_classifier.classify(clean_msg, has_active_dialogue=bool(history))

        # 3. Off-topic, unsafe, control, legal query, or instant greeting/acknowledgment: Stream boundary text directly without RAG
        if domain in ("off_topic", "unsafe_off_topic", "system_control", "prompt_injection", "legal_advice", "greeting", "thanks", "acknowledgment"):
            boundary_text = domain_classifier.get_boundary_response(domain, clean_msg, lang)
            
            # Stream in natural 3-word chunks with minimal delay
            words = boundary_text.split(" ")
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                token_chunk = " ".join(words[i:i + chunk_size])
                prefix = "" if i == 0 else " "
                yield f"data: {json.dumps({'type': 'token', 'token': prefix + token_chunk})}\n\n"
                await asyncio.sleep(0.004)

            # Save messages in single batch transaction
            await conversation_service.add_messages(
                session=session,
                conversation_id=conv.id,
                messages_data=[
                    {"role": "user", "content": clean_msg},
                    {"role": "assistant", "content": boundary_text, "sources": []}
                ]
            )

            latency = (time.time() - start_time) * 1000
            suggested = ["What services do you provide?", "100% Free Website Offer", "Talk to Expert"]
            if domain == "greeting":
                suggested = ["What services do you provide?", "100% Free Website Offer", "Custom Software & CRM", "Talk to Expert"]
            elif domain in ("thanks", "acknowledgment"):
                suggested = ["100% Free Website Offer", "Payment & EMI Options", "What services do you provide?", "Talk to Expert"]

            meta_event = {
                "type": "metadata",
                "conversation_id": conv.id,
                "session_id": session_id,
                "sources": [],
                "intent": domain,
                "domain": domain,
                "language": lang,
                "lead_intent": False,
                "human_required": False,
                "latency_ms": round(latency, 2),
                "suggested_actions": suggested
            }
            yield f"data: {json.dumps(meta_event)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # 4. In-domain: Analysis & RAG
        analysis = query_agent.analyze(clean_msg)
        intent = analysis["intent"]
        detected_services = analysis["requested_services"]

        reformulated_query = self._reformulate_query(clean_msg, history)
        rag_search_query = query_agent.rewrite_query_for_rag(reformulated_query, intent, detected_services)

        context_chunks = rag_pipeline.search_context(
            rag_search_query,
            top_k=settings.TOP_K_RETRIEVAL,
            intent=intent
        )

        # 5. Extract Conversation Memory & Lead Processing
        conversation_memory = self._extract_conversation_memory(clean_msg, history)

        lead_data = sales_agent.extract_lead_attributes(clean_msg)
        if not lead_data.get("name") and conversation_memory.get("name"):
            lead_data["name"] = conversation_memory["name"]
        if not lead_data.get("phone") and conversation_memory.get("phone"):
            lead_data["phone"] = conversation_memory["phone"]
        if not lead_data.get("email") and conversation_memory.get("email"):
            lead_data["email"] = conversation_memory["email"]
        if not lead_data.get("budget") and conversation_memory.get("budget"):
            lead_data["budget"] = conversation_memory["budget"]
        if not lead_data.get("company") and conversation_memory.get("company"):
            lead_data["company"] = conversation_memory["company"]

        resolved_service = self._resolve_lead_service(detected_services, history, intent)
        if resolved_service:
            lead_data["service"] = resolved_service
        is_handoff, _ = sales_agent.evaluate_handoff_condition(
            clean_msg, intent, len(context_chunks), lead_data
        )
        if is_handoff:
            lead_data["human_required"] = True
            if lead_data.get("status") != "qualified":
                lead_data["status"] = "human_required"

        # Check FAQ Cache for zero-latency streaming on repeated/canonical queries
        faq_key = f"{rag_search_query.strip().lower()}_{lang}_{intent}"
        is_cacheable = (
            not is_handoff
            and not lead_data.get("email")
            and not lead_data.get("phone")
            and not lead_data.get("name")
            and domain in ("techvunex_relevant", "general_greeting", "techvunex")
        )
        cached_data = self._find_in_faq_cache(clean_msg, rag_search_query, lang, intent) if is_cacheable else None

        if cached_data:
            complete_response = cached_data["text"]
            unique_chunks = cached_data.get("unique_chunks", [])
            sources = [
                {
                    "source_url": c.get("source_url", "https://techvunex.in/"),
                    "page_title": c.get("page_title", "Techvunex"),
                    "section": c.get("section", ""),
                    "snippet": c.get("content", "")[:200]
                }
                for c in unique_chunks
            ]

            words = complete_response.split(" ")
            chunk_size = 3
            for i in range(0, len(words), chunk_size):
                token_chunk = " ".join(words[i:i + chunk_size])
                prefix = "" if i == 0 else " "
                yield f"data: {json.dumps({'type': 'token', 'token': prefix + token_chunk})}\n\n"
                await asyncio.sleep(0.004)

            await conversation_service.add_messages(
                session=session,
                conversation_id=conv.id,
                messages_data=[
                    {"role": "user", "content": clean_msg},
                    {"role": "assistant", "content": complete_response, "sources": sources}
                ]
            )
            latency = (time.time() - start_time) * 1000
            suggested_actions = cached_data.get("suggested_actions") or self._generate_suggested_actions(intent, detected_services, is_handoff)
            meta_event = {
                "type": "metadata",
                "conversation_id": conv.id,
                "session_id": session_id,
                "sources": sources,
                "intent": intent,
                "domain": domain,
                "language": lang,
                "lead_intent": analysis["lead_intent"],
                "human_required": is_handoff,
                "latency_ms": round(latency, 2),
                "suggested_actions": suggested_actions,
                "debug": {
                    "query": clean_msg,
                    "cached": True,
                    "latency_ms": round(latency, 2)
                }
            }
            yield f"data: {json.dumps(meta_event)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Launch lead persistence as background task without blocking LLM stream kickoff
        if analysis["lead_intent"] or lead_data.get("email") or lead_data.get("phone") or is_handoff:
            async def _persist_lead_bg():
                from app.core.database import AsyncSessionLocal
                try:
                    async with AsyncSessionLocal() as bg_session:
                        await lead_service.create_or_update_lead(bg_session, lead_data)
                except Exception as bg_err:
                    logger.error(f"Error persisting lead in background: {bg_err}")
            asyncio.create_task(_persist_lead_bg())

        # 6. Stream tokens directly from LLM (native async, zero artificial delays)
        system_prompt = build_system_prompt(context_chunks, language=lang, conversation_memory=conversation_memory, current_query=clean_msg)
        messages = history + [{"role": "user", "content": clean_msg}]

        full_content = []
        async for token in self.llm.stream(messages=messages, system_prompt=system_prompt, temperature=0.3):
            full_content.append(token)
            yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"

        raw_response = "".join(full_content)
        user_name = conversation_memory.get("name") if conversation_memory else None
        complete_response = response_post_processor.process(
            raw_response,
            expected_language=lang,
            domain=domain,
            known_name=user_name
        )
        latency = (time.time() - start_time) * 1000

        # 7. Deduplicate Sources (Internal metadata only)
        unique_chunks = self._deduplicate_sources(context_chunks)
        sources = [
            {
                "source_url": c["source_url"],
                "page_title": c["page_title"],
                "section": c.get("section", ""),
                "snippet": c["content"][:200]
            }
            for c in unique_chunks
        ]

        # Store in FAQ cache if eligible
        if is_cacheable:
            if len(self._faq_cache) >= self._max_faq_cache_size:
                oldest_keys = list(self._faq_cache.keys())[:len(self._faq_cache) // 5]
                for ok in oldest_keys:
                    self._faq_cache.pop(ok, None)
            self._faq_cache[faq_key] = {
                "text": complete_response,
                "sources": [
                    SourceRef(
                        source_url=c["source_url"],
                        page_title=c["page_title"],
                        section=c.get("section", ""),
                        snippet=c["content"][:200] + "...",
                        similarity=round(c.get("relevance_score", 0.0), 3)
                    )
                    for c in unique_chunks
                ],
                "unique_chunks": unique_chunks
            }

        # 8. Save messages in single batch transaction
        await conversation_service.add_messages(
            session=session,
            conversation_id=conv.id,
            messages_data=[
                {"role": "user", "content": clean_msg},
                {"role": "assistant", "content": complete_response, "sources": sources}
            ]
        )

        # 9. Yield metadata event with full observability
        meta_event = {
            "type": "metadata",
            "conversation_id": conv.id,
            "session_id": session_id,
            "sources": sources,
            "intent": intent,
            "domain": domain,
            "language": lang,
            "lead_intent": analysis["lead_intent"],
            "human_required": is_handoff,
            "latency_ms": round(latency, 2),
            "suggested_actions": self._generate_suggested_actions(intent, detected_services, is_handoff),
            "debug": {
                "query": clean_msg,
                "rag_search_query": rag_search_query,
                "intent": intent,
                "language": lang,
                "domain": domain,
                "retrieved_count": len(context_chunks)
            }
        }
        yield f"data: {json.dumps(meta_event)}\n\n"
        yield "data: [DONE]\n\n"

    def _generate_suggested_actions(self, intent: str, services: List[str], handoff: bool) -> List[str]:
        if handoff:
            return ["Connect with Team", "Schedule Call", "Request Quote"]
        if "Website Development" in services or intent in ("free_offer", "website_free_offer", "pricing_website", "website_requirement", "ecommerce", "saas", "website_features"):
            return ["100% Free Website Offer", "25% Upfront & EMI Terms", "Custom Website Scope", "Talk to Expert"]
        if "CRM & ERP" in services or intent in ("pricing_crm", "pricing_erp", "crm", "erp"):
            return ["Features of CRM", "ERP vs CRM", "Request Demo", "Connect with Team"]
        if "AI Automation" in services or intent in ("pricing_ai", "ai", "automation"):
            return ["AI Chatbot Features", "Workflow Automation", "Talk to Expert"]
        if "Digital Marketing & SEO" in services or intent in ("pricing_seo", "seo", "smo"):
            return ["100% Free SEO Support", "100% Free SMO Support", "Ad Campaign Guidance"]
        if intent in ("company_info", "working_hours", "contact", "experience_portfolio", "industries", "why_choose_us", "technology"):
            return ["What services do you provide?", "100% Free Website Offer", "Payment & EMI Options", "Talk to Expert"]
        return ["Free Website Offer", "Payment & EMI Options", "What services do you provide?", "Connect with Team"]

chat_service = ChatService()

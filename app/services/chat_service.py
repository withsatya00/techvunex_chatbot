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
            name_match = re.search(r'\b(?:my\s+name\s+is|mera\s+naam\s+hai|mera\s+naam|i\s+am|myself)\s+([A-Za-z]+)\b', msg, re.IGNORECASE)
            if name_match:
                cand = name_match.group(1).strip()
                if cand.lower() not in ("techvunex", "website", "looking", "interested", "need", "here", "ready", "ek", "a", "an"):
                    memory["name"] = cand.capitalize()
                    break

        # 2. Phone extraction (latest phone wins)
        for msg in reversed_messages:
            phone_match = re.search(r'(?:\+?91[\s-]?)?[6-9]\d{9}\b', msg)
            if phone_match:
                memory["phone"] = phone_match.group(0).strip()
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

        # 5. Domain Boundary Check: Off-topic, Unsafe, System Control, Prompt Injection, Legal Advice
        # CRITICAL RULE: DO NOT SEND OFF-TOPIC QUERIES INTO RAG!
        if domain in ("off_topic", "unsafe_off_topic", "system_control", "prompt_injection", "legal_advice"):
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
                suggested_actions=["What services do you provide?", "100% Free Website Offer", "Talk to Expert"],
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

        # 9. Sales & Lead Processing
        lead_data = sales_agent.extract_lead_attributes(clean_msg)
        if detected_services:
            lead_data["service"] = ", ".join(detected_services)

        is_handoff, handoff_reason = sales_agent.evaluate_handoff_condition(
            clean_msg, intent, len(context_chunks), lead_data
        )

        if is_handoff:
            lead_data["human_required"] = True
            lead_data["status"] = "human_required"

        # Check FAQ Cache for zero-latency response on repeated/canonical queries
        faq_key = f"{rag_search_query.strip().lower()}_{lang}_{intent}"
        is_cacheable = (
            len(history) == 0
            and not is_handoff
            and not lead_data.get("email")
            and not lead_data.get("phone")
            and domain in ("techvunex_relevant", "general_greeting", "techvunex")
        )
        logger.info(f"FAQ cache check: is_cacheable={is_cacheable}, in_cache={faq_key in self._faq_cache}, key='{faq_key[:60]}'")

        if is_cacheable and faq_key in self._faq_cache:
            cached_data = self._faq_cache[faq_key]
            assistant_text = cached_data["text"]
            sources = cached_data["sources"]
            unique_chunks = cached_data.get("unique_chunks", [])
            suggested_actions = self._generate_suggested_actions(intent, detected_services, False)

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
        conversation_memory = self._extract_conversation_memory(clean_msg, history)
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
                assistant_text += "\n\nक्या आप टेकवुनेक्स टीम के साथ सीधे परामर्श के लिए संपर्क करना चाहेंगे?"
            elif lang == "hinglish":
                assistant_text += "\n\nKya aap Techvunex team ke sath direct consultation connect karna chahenge?"
            else:
                assistant_text += "\n\nWould you like to connect directly with the Techvunex team for a detailed consultation?"

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

        # 3. Off-topic, unsafe, control, or legal query: Stream boundary text directly without RAG
        if domain in ("off_topic", "unsafe_off_topic", "system_control", "prompt_injection", "legal_advice"):
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
                "suggested_actions": ["What services do you provide?", "100% Free Website Offer", "Talk to Expert"]
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

        # 5. Lead & Handoff
        lead_data = sales_agent.extract_lead_attributes(clean_msg)
        if detected_services:
            lead_data["service"] = ", ".join(detected_services)
        is_handoff, _ = sales_agent.evaluate_handoff_condition(
            clean_msg, intent, len(context_chunks), lead_data
        )
        if is_handoff:
            lead_data["human_required"] = True
            lead_data["status"] = "human_required"

        # Check FAQ Cache for zero-latency streaming on repeated/canonical queries
        faq_key = f"{rag_search_query.strip().lower()}_{lang}_{intent}"
        is_cacheable = (
            len(history) == 0
            and not is_handoff
            and not lead_data.get("email")
            and not lead_data.get("phone")
            and domain in ("techvunex_relevant", "general_greeting", "techvunex")
        )

        if is_cacheable and faq_key in self._faq_cache:
            cached_data = self._faq_cache[faq_key]
            complete_response = cached_data["text"]
            unique_chunks = cached_data.get("unique_chunks", [])
            sources = [
                {
                    "source_url": c["source_url"],
                    "page_title": c["page_title"],
                    "section": c.get("section", ""),
                    "snippet": c["content"][:200]
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
                    "cached": True,
                    "latency_ms": round(latency, 2)
                }
            }
            yield f"data: {json.dumps(meta_event)}\n\n"
            yield "data: [DONE]\n\n"
            return

        # Launch lead persistence as background task without blocking LLM stream kickoff
        lead_task = None
        if analysis["lead_intent"] or lead_data.get("email") or lead_data.get("phone") or is_handoff:
            lead_task = asyncio.create_task(lead_service.create_or_update_lead(session, lead_data))

        # 6. Stream tokens directly from LLM (native async, zero artificial delays)
        conversation_memory = self._extract_conversation_memory(clean_msg, history)
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

        # Wait for background lead persistence if it was scheduled
        if lead_task:
            try:
                await lead_task
            except Exception as e:
                logger.error(f"Error in background lead task: {e}")

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

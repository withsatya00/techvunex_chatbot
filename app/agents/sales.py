import re
from typing import Dict, Any, Optional, Tuple
from app.core.logging import logger

class SalesAssistantAgent:
    """
    Intelligent progressive requirement gathering, lead qualification, and human handoff routing.
    """
    def __init__(self):
        pass

    def evaluate_handoff_condition(
        self,
        query: str,
        intent: str,
        retrieved_context_len: int,
        lead_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines if human handoff is warranted:
        1. User explicitly asks for a human / representative / phone call
        2. High budget / enterprise scale requirement
        3. Complex technical requirement without clear knowledge base answer
        4. Information unavailable
        """
        q_lower = query.lower()

        # Explicit request
        if re.search(r'\b(talk to human|speak to agent|call me|connect with team|human support|customer care|executive|talk to someone|team se baat)\b', q_lower):
            return True, "User explicitly requested human handoff."

        # High value or enterprise indicator
        budget = lead_data.get("budget", "") or ""
        if any(term in budget.lower() for term in ["lakh", "crore", "enterprise", "10k", "50k", "$5000", "$10000"]):
            return True, "High-value enterprise lead detected."

        # No verified knowledge available for factual question
        if retrieved_context_len == 0 and intent in ("pricing", "technology", "service_information"):
            return True, "Specific verified detail unavailable; handoff offered."

        return False, None

    def extract_lead_attributes(self, text: str, existing_lead: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extracts contact info, requirements, and project parameters from user text.
        """
        lead = existing_lead.copy() if existing_lead else {
            "name": None,
            "email": None,
            "phone": None,
            "company": None,
            "service": None,
            "requirement": None,
            "budget": None,
            "timeline": None,
            "status": "new",
            "human_required": False
        }

        # Email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            lead["email"] = email_match.group(0)

        # Phone (Supports Indian mobile 6-9, numbers preceded by mobile/mobike/phone, and any 10 digits)
        phone_match = re.search(r'(?:\+?91[\s-]?)?\b[6-9]\d{9}\b', text)
        if not phone_match:
            phone_match = re.search(r'(?i)(?:phone|mobile|mobike|contact|number|no\.?|call|whatsapp)[\s:]*([0-9]{10})\b', text)
        if not phone_match:
            phone_match = re.search(r'\b\d{10}\b', text)
        if phone_match:
            lead["phone"] = phone_match.group(1) if phone_match.groups() else phone_match.group(0)

        # Name extraction (e.g., "my name is Rahul", "I am John", "mera naam Anil hai")
        name_match = re.search(r'(?i)(?:my name is|i am|i\'m|this is|mera naam hai|mera naam|naam)\s+([A-Za-z]{2,25})(?:\s+(?!hai|aur|from|at|with|and|company|phone|mobile|mobike|email)([A-Za-z]{2,25}))?', text)
        if name_match:
            first = name_match.group(1).strip()
            second = name_match.group(2).strip() if name_match.group(2) else ""
            if first.lower() in ("hai", "mera", "naam", "ek", "mujhe", "please"):
                first = ""
            lead["name"] = f"{first} {second}".strip() if second else first

        # Company extraction
        company_match = re.search(r'(?i)(?:from|company is|working at)\s+([A-Za-z0-9\s]{2,25}?)(?=[.,\n]|email|phone|$)', text)
        if company_match:
            lead["company"] = company_match.group(1).strip()

        # Update requirement text
        if not lead.get("requirement"):
            lead["requirement"] = text[:300]
        else:
            lead["requirement"] += f" | {text[:150]}"

        # Check qualification status
        if lead.get("email") or lead.get("phone"):
            lead["status"] = "qualified"

        return lead

    def get_progressive_followup_question(self, lead: Dict[str, Any], language: str = "en") -> Optional[str]:
        """
        Determines the next single natural question to ask, avoiding robotic forms.
        """
        is_hindi = language in ("hi", "hinglish")

        if not lead.get("service"):
            return "Aap kis specific service ya solution mein interested hain?" if is_hindi else "Which specific service or solution are you planning to build?"

        if not lead.get("requirement") or len(lead.get("requirement", "")) < 20:
            return "Aapke project ka primary use-case ya workflow kya rahega?" if is_hindi else "Could you share a brief overview of your project's main use-case or workflow?"

        if not lead.get("email") and not lead.get("phone"):
            return "Agar aap chahein toh apna email ya phone number share kar sakte hain taaki Techvunex team aapse proposal aur timeline discuss kar sake." if is_hindi else "If you'd like, you can share your email or phone number so our solutions team can follow up with a tailored proposal."

        return None

sales_agent = SalesAssistantAgent()

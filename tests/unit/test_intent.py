import pytest
from app.agents.intent import query_agent
from app.agents.sales import sales_agent

def test_intent_detection_crm():
    res = query_agent.analyze("I need a CRM for my sales team")
    assert "CRM & ERP" in res["requested_services"]
    assert res["lead_intent"] is True

def test_intent_detection_hindi_hinglish():
    res = query_agent.analyze("bhai mujhe ek e-commerce website banwani hai")
    assert res["language"] == "hinglish"
    assert "Website Development" in res["requested_services"]
    assert res["lead_intent"] is True

def test_entity_extraction_budget_and_timeline():
    query = "We need an AI chatbot with budget 3-5 lakh within 2 months. Reach me at rahul@example.com or 9876543210"
    res = query_agent.analyze(query)
    assert res["entities"]["email"] == "rahul@example.com"
    assert res["entities"]["phone"] == "9876543210"
    assert res["entities"]["budget"] is not None
    assert res["entities"]["timeline"] is not None

def test_sales_lead_extraction():
    lead = sales_agent.extract_lead_attributes("My name is Amit from Acme Corp. Email is amit@acme.com, phone 9876543210")
    assert lead["name"] == "Amit"
    assert lead["company"] == "Acme Corp"
    assert lead["email"] == "amit@acme.com"
    assert lead["phone"] == "9876543210"
    assert lead["status"] == "qualified"

def test_human_handoff_detection():
    is_handoff, reason = sales_agent.evaluate_handoff_condition(
        query="Can I speak to someone from your executive team?",
        intent="general_question",
        retrieved_context_len=2,
        lead_data={}
    )
    assert is_handoff is True

def test_pricing_and_free_offer_intents():
    cases = [
        ("normal website ka kitna charge hai?", "pricing_website"),
        ("free website milegi?", "free_offer"),
        ("25 percent upfront wala kya hai?", "payment_terms"),
        ("EMI available hai?", "emi"),
        ("Website free me mil sakti hai?", "free_offer"),
        ("Do you provide any free website?", "free_offer"),
        ("How much does a website cost?", "pricing_website"),
        ("How much does your CRM cost?", "pricing_crm")
    ]
    for q, expected_intent in cases:
        analysis = query_agent.analyze(q)
        assert analysis["intent"] == expected_intent, f"Failed for '{q}': got {analysis['intent']}, expected {expected_intent}"


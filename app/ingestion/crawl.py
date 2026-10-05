import os
import json
import asyncio
from app.rag.crawler import TechvunexCrawler
from app.core.logging import logger

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "knowledge_base")
OUTPUT_FILE = os.path.join(DATA_DIR, "crawled_docs.json")

# Verified rich knowledge base covering every service, solution, and detail of Techvunex
RICH_PAGES = [
    {
        "url": "https://techvunex.in/",
        "title": "Software Development Company in India | Techvunex Innovation",
        "description": "Techvunex Innovation is a software development company in India providing custom software, website development, mobile apps, CRM & ERP, AI automation and cloud solutions.",
        "content": """# Techvunex Innovation - Premier Software Development Company in India

Techvunex Innovation is a premier software development company in India providing custom software development, modern website development, mobile apps, CRM & ERP solutions, AI automation, and cloud infrastructure.

## About Techvunex
We help startups and growing businesses scale with bespoke, enterprise-grade technology solutions. Our team operates from Noida, India, delivering projects globally.

## Core Services Offered
- Custom Software Development (Tailored web and desktop systems)
- Website Development (React, Next.js, high-speed, SEO-optimized)
- Mobile App Development (iOS & Android via Flutter & React Native)
- CRM & ERP Solutions (Lead pipelines, inventory, workflow automation)
- AI & Automation Services (RAG chatbots, NLP, workflow automation)
- UI/UX Design (Figma wireframes, modern design systems)
- Cloud Solutions (AWS, Azure, GCP, DevOps, CI/CD)
- Digital Marketing & SEO (Google Ads, Meta Ads, SEO optimization)

## Head Office & Contact Details
- Parent Company: Digital Yug Innovation (https://digitalyuginnovation.com/)
- Address: D-60, D Block, Sector 63, Noida, Uttar Pradesh, 201309, India
- Phone: +91-7834979979
- Email: info@techvunex.in
- Working Hours: Monday - Saturday (10:30 AM to 6:30 PM IST)
"""
    },
    {
        "url": "https://techvunex.in/about",
        "title": "About Techvunex Innovation | Software Development Company",
        "description": "Learn about Techvunex Innovation, a software development company in India delivering scalable custom software, web platforms, and business automation.",
        "content": """# About Techvunex Innovation

Techvunex Innovation is a technology company headquartered in Sector 63, Noida, India. We specialize in engineering modern digital products and intelligent automation.

## Our Pillars
1. Custom-Built Digital Solutions: Tailored to exact client requirements.
2. Transparent Project Communication: Regular sprint demos and progress reports.
3. Scalable and Secure Architecture: Cloud-native, zero-trust security standards.
4. Long-Term Technical Support: Comprehensive post-deployment maintenance.

## Leadership & Vision
Our mission is to empower businesses with high-ROI software and AI automation, replacing outdated manual processes with automated digital workflows.
"""
    },
    {
        "url": "https://techvunex.in/services/crm-erp",
        "title": "CRM & ERP Solutions | Techvunex Innovation",
        "description": "Custom CRM and ERP development company in India. Techvunex unifies sales, operations, customer relations, and business data.",
        "content": """# CRM & ERP Development Solutions

Techvunex develops custom CRM and ERP software designed to consolidate customer data, sales pipelines, inventory, and operations into a single centralized dashboard.

## Key Capabilities of Techvunex CRM/ERP
- Custom Sales Pipeline & Lead Tracking: Automate lead capture from websites, social media, and WhatsApp directly into sales funnels.
- Unified Enterprise Operations: Real-time inventory monitoring, vendor management, and automated invoicing.
- Multi-Channel Integrations: Integrated WhatsApp, Email, and SMS communication for sales teams.
- Custom Analytics & KPI Dashboards: Revenue forecasting, team performance metrics, and role-based permissions.
- ERP Integrations: Seamless data sync with accounting tools like Tally, QuickBooks, and payment gateways.
"""
    },
    {
        "url": "https://techvunex.in/services/ai-automation",
        "title": "AI & Automation Services | Techvunex Innovation",
        "description": "Enterprise AI development and intelligent automation services by Techvunex Innovation.",
        "content": """# AI Automation & Chatbot Development

Techvunex builds production-ready Artificial Intelligence, RAG-based conversational AI assistants, and enterprise process automation.

## AI Capabilities
- Intelligent RAG Chatbots: Website assistants that retrieve facts from company data with zero hallucination and human handoff.
- Workflow Automation: Eliminating repetitive tasks, invoice OCR, document parsing, and automatic lead enrichment.
- LLM Integrations: State-of-the-art LLMs including Google Gemini, OpenAI, Claude, Groq, and open-weight models (Llama 3, Mistral).
- Predictive Analytics: Churn prediction, sales forecasting, and anomaly detection models.
"""
    },
    {
        "url": "https://techvunex.in/services/website-development",
        "title": "Website Development Services | Techvunex Innovation",
        "description": "High-performance website development services in India by Techvunex Innovation. 100% Free website offer for basic business sites and bespoke custom web development.",
        "content": """# Website Development Services

Techvunex delivers lightning-fast, high-converting websites and modern web applications.

## 100% Free Business Website Offer
Techvunex offers a 100% Free Business Website package at ₹0 development cost (Zero development fee).
- Deliverables: Up to 5 standard business pages (Home, About Us, Services, Portfolio/Gallery, Contact).
- Inclusions: Responsive design, WhatsApp button integration, contact enquiry form, basic SEO starter setup, basic SMO setup, 2 guided design revision rounds, and 15 days of post-launch assistance.
- Cost: ₹0 development fee.

## Custom Web Development & Enterprise Platforms
For complex websites, custom SaaS platforms, e-commerce applications, and high-traffic web applications:
- Scope: Custom architecture, interactive dashboards, payment gateway integration, database design, and role-based permissions.
- Payment Terms: Eligible for Techvunex's 25% upfront and remaining 75% via zero-cost 12-month EMI payment model.
- Pricing: Custom quoted based on required features, integrations, and project scope.

## Technologies & Stack
- Frontend: React.js, Next.js, Vue.js, Tailwind CSS, TypeScript.
- Backend: Python (FastAPI, Django), Node.js (Express, NestJS), Go.
- Databases: PostgreSQL, MongoDB, Redis, MySQL.
- Solutions: Custom SaaS platforms, corporate portals, e-commerce stores, landing pages.
"""
    },
    {
        "url": "https://techvunex.in/services/app-development",
        "title": "Mobile App Development Services | Techvunex Innovation",
        "description": "Mobile app development in India for Android and iOS using Flutter and React Native.",
        "content": """# Mobile Application Development Services

Techvunex designs and develops top-rated mobile applications for Android and iOS platforms.

## App Development Stack
- Cross-Platform: Flutter and React Native for unified iOS and Android codebases with native speed.
- Native Development: Swift/SwiftUI for iOS, Kotlin for Android.
- Features: Offline data caching, push notifications, biometric login, Razorpay/Stripe in-app payments, and real-time messaging.
"""
    },
    {
        "url": "https://techvunex.in/services/custom-software",
        "title": "Custom Software Development | Techvunex Innovation",
        "description": "Bespoke software development for complex business requirements by Techvunex Innovation.",
        "content": """# Custom Software Development

Techvunex creates bespoke software solutions tailored to unique business challenges where commercial off-the-shelf software is inadequate.

## Capabilities
- Enterprise SaaS platforms
- Custom workflow engines and internal tooling
- API design, microservices, and system integrations
- Monolith to microservices migration
"""
    },
    {
        "url": "https://techvunex.in/services/cloud-solutions",
        "title": "Cloud Solutions & DevOps | Techvunex Innovation",
        "description": "Cloud migration, infrastructure management, and DevOps automation on AWS, Azure, and GCP.",
        "content": """# Cloud Solutions & DevOps Services

Techvunex delivers cloud infrastructure engineering, DevOps automation, and scalable hosting on AWS, Google Cloud, and Microsoft Azure.

## Cloud Services
- Cloud Migration: Zero-downtime server and database migrations.
- DevOps Pipelines: CI/CD automation with Docker, Kubernetes, and GitHub Actions.
- Cost Optimization: Dynamic auto-scaling to lower operational costs.
"""
    },
    {
        "url": "https://techvunex.in/services/ui-ux-design",
        "title": "UI/UX Design Services | Techvunex Innovation",
        "description": "User-centric UI/UX design, Figma prototypes, and design systems.",
        "content": """# UI/UX Design Services

Techvunex creates intuitive and engaging digital user experiences. Deliverables include user research, wireframes, interactive Figma prototypes, design systems, and usability testing.
"""
    },
    {
        "url": "https://techvunex.in/services/digital-marketing",
        "title": "Digital Marketing & SEO Services | Techvunex Innovation",
        "description": "Performance digital marketing, SEO, Google Ads, and Meta Ads management.",
        "content": """# Digital Marketing & SEO Services

Techvunex provides data-driven marketing to drive organic and paid growth. Services include technical SEO, on-page optimization, Google Ads (PPC), Meta Ads, and conversion rate optimization (CRO).
"""
    },
    {
        "url": "https://techvunex.in/portfolio",
        "title": "Portfolio & Case Studies | Techvunex Innovation",
        "description": "Explore Techvunex Innovation's portfolio of software projects and case studies.",
        "content": """# Techvunex Portfolio & Case Studies

Techvunex has built solutions across Fintech, E-commerce, Logistics, and Enterprise Automation.

## Selected Case Studies
- FinMart: A comprehensive digital financial portal connecting borrowers with lenders, automated KYC processing, and credit scoring algorithms.
- Custom Sales CRM: Multi-tenant sales management platform with real-time lead allocation and GPS sales tracking for field executives.
- Telemedicine Platform: HIPAA-compliant digital healthcare portal with video consultations and electronic prescriptions.
"""
    },
    {
        "url": "https://techvunex.in/contact",
        "title": "Contact Techvunex Innovation | Software Development Company",
        "description": "Contact Techvunex Innovation for custom software quotes and consultations.",
        "content": """# Contact Techvunex Innovation

Connect with Techvunex software consultants to discuss your project requirements or request a custom quotation.

## Office & Contact Details
- Parent Company: Digital Yug Innovation (https://digitalyuginnovation.com/)
- Office Location: D-60, D Block, Sector 63, Noida, Uttar Pradesh, 201309, India
- Direct Phone: +91-7834979979 / +91 7834-979-979
- Email Address: info@techvunex.in
- Office Timings: Monday to Saturday, 10:30 AM to 6:30 PM IST
- Consultation: Free initial scope evaluation and technical consultation available.
"""
    },
    {
        "url": "https://techvunex.in/solutions/crm-erp",
        "title": "Unified CRM & ERP Solutions | Techvunex Innovation",
        "description": "Unified business data and operations management with Techvunex CRM/ERP.",
        "content": """# Enterprise Solutions: CRM & ERP

Techvunex provides unified business data solutions, breaking down silos between departments, consolidating customer records, inventory, and financial reporting into an integrated architecture.
"""
    },
    {
        "url": "https://techvunex.in/solutions/business-automation",
        "title": "Business Automation Solutions | Techvunex Innovation",
        "description": "Faster operations and business automation by Techvunex Innovation.",
        "content": """# Business Automation Solutions

Accelerate business operations with custom automation workflows, automated approvals, task delegation, and third-party API webhooks that eliminate manual bottlenecks.
"""
    },
    {
        "url": "https://techvunex.in/solutions/ai-integration",
        "title": "AI Integration Solutions | Techvunex Innovation",
        "description": "Integrate custom AI and machine learning models into existing software.",
        "content": """# AI Integration Solutions

Techvunex integrates intelligent AI microservices into your existing legacy or cloud infrastructure, providing smart recommendations, semantic search, and automated customer interaction.
"""
    },
    {
        "url": "https://techvunex.in/offers/free-website",
        "title": "100% Free Website Offer | ₹0 Development Cost | Techvunex Innovation",
        "description": "Techvunex 100% Free Website Offer: Get a 4-5 page modern business website with ₹0 development cost, responsive design, WhatsApp integration, basic SEO, basic SMO, 2 revision rounds, and 15 days support.",
        "metadata": {
            "content_type": "pricing",
            "service": "website",
            "pricing_type": "free_offer",
            "currency": "INR"
        },
        "content": """# 100% Free Website Offer - Techvunex Innovation

Techvunex Innovation currently offers a 100% Free Business Website package for startups and businesses with ₹0 development cost (Zero development fee).

## What Is Included in the Free Website Offer (Deliverables)
- Zero Development Fee (₹0 development cost): Modern business website designed and developed at no development charge.
- Up to 5 Pages: A professionally designed website with up to 5 standard pages:
  1. Home Page
  2. About Us Page
  3. Services Page
  4. Portfolio / Gallery Page
  5. Contact Page
- Responsive Design: Fully responsive design for mobile, tablet, and desktop devices.
- WhatsApp Integration: Direct click-to-chat WhatsApp button for quick customer enquiries.
- Enquiry / Lead Integration: Contact and enquiry form integration to capture customer leads.
- Basic SEO Starter Setup: Search-friendly page guidance, titles, meta tags, and on-page headings.
- Basic SMO Starter Setup: Social media profile links and basic social meta tags.
- Guided Design Revisions: 2 rounds of guided design revisions to refine approved design and content.
- Post-Launch Assistance: 15 days of post-launch assistance (basic technical support and minor content updates).
- Free 30-Minute Consultation: Discuss requirements, workflow, and launch roadmap with a tech specialist.

## Simple 4-Step Website Launch Process
1. Share Your Details: Send business details, logo, services, and required content.
2. Approve Website Structure: Review and approve page flow, layout, and sections.
3. Review the Website: Check design and provide revision requests (up to 2 rounds included).
4. Website Goes Live: Your business website is prepared and launched with 15 days of support.

## Free Business Website vs Custom Web Development Scope
- The 100% Free Website Offer covers a complete modern business website up to 5 standard pages with defined scope at ₹0 development fee.
- Custom Web Platforms, custom SaaS applications, complex e-commerce stores with multi-vendor checkouts, or advanced web portals fall outside the free basic offer. These are scoped separately as custom software projects with flexible payment options.
"""
    },
    {
        "url": "https://techvunex.in/offers/free-seo-smo",
        "title": "100% Free SEO & SMO Support Forever | Techvunex Innovation",
        "description": "Techvunex offers 100% Free SEO Support Forever and 100% Free SMO Support Forever with ₹0 setup charges and ₹0 monthly fees.",
        "metadata": {
            "content_type": "offer",
            "service": "seo",
            "pricing_type": "free_offer",
            "currency": "INR"
        },
        "content": """# 100% Free SEO & SMO Support Forever - Techvunex Innovation

Techvunex Innovation provides 100% Free SEO Support Forever and 100% Free SMO Support Forever with ₹0 setup charges and ₹0 monthly fees.

## 100% Free SEO Support Forever
- ₹0 setup, ₹0 monthly fee
- SEO Website Audit: In-depth technical health and performance check.
- Keyword Research & Analysis: Finding high-intent search terms.
- On-Page Recommendations: Page titles, meta descriptions, image tags, and content structure.
- Technical SEO Checklist: Crawlability, indexability, sitemaps, robots.txt, and site speed.
- Competitor Analysis: Benchmarking against search competitors.
- Content Optimization Guidance: Search-friendly keyword density and readability advice.
- Backlink Strategy Guidance: Organic link building strategy recommendations.
- Performance & Ranking Tracking: Monitoring organic visibility and ranking metrics.

## 100% Free SMO Support Forever
- ₹0 setup, ₹0 monthly fee
- Social Profile Audit: Reviewing LinkedIn, Instagram, Facebook, and Twitter presence.
- Content Strategy Planning: Audience-aligned themes and content buckets.
- Posting Schedule Guidance: Best days and optimal posting hours.
- Hashtag Research & Strategy: Targeted hashtags for organic reach.
- Audience Growth Tips: Organic techniques to gain genuine followers.
- Engagement Improvement: Tactics to increase likes, comments, and shares.
- Competitor Analysis: Analyzing competitor social media strategies.
- Monthly Performance Insights: Tracking audience growth and engagement trends.

## Important Qualification & Scope Exclusions
- Free SEO and SMO support covers expert audits, strategic guidance, checklists, and recommendations forever at ₹0.
- Paid ad campaign budgets (Google Ads, Meta Ads), third-party tool subscriptions, or paid platform advertising fees are not included where applicable.
"""
    },
    {
        "url": "https://techvunex.in/pricing/payment-plans",
        "title": "Payment Plans & Zero-Cost 12-Month EMI | Techvunex Innovation",
        "description": "Techvunex payment model: Pay 25% upfront at kickoff, and remaining 75% after delivery through zero-cost 12-month EMI at 0% interest.",
        "metadata": {
            "content_type": "payment_terms",
            "service": "general",
            "pricing_type": "emi",
            "currency": "INR"
        },
        "content": """# Techvunex Payment Plans & Zero-Cost 12-Month EMI

Techvunex Innovation offers a client-friendly commercial payment model: Pay 25% upfront and the remaining 75% through zero-cost 12-month EMI.

## Payment Terms & Model Breakdown
- Pay 25% Upfront: Pay 25% advance at project kickoff to lock your timeline and begin development.
- Remaining 75% via Zero-Cost 12-Month EMI: Pay the remaining 75% balance after delivery through easy monthly installments over 12 months.
- 0% Interest (Zero-Cost EMI): No interest charges, no hidden fees, and easy monthly payments.

## Example Calculation
- For a ₹2 Lakh (₹200,000) project:
  - 25% Upfront = ₹50,000 advance at kickoff.
  - Remaining 75% = ₹1.5 Lakh (₹150,000) balance after delivery.
  - 12 Monthly Installments = ₹12,500 per month across 12 months at 0% interest.

## Scope & Pricing Policies
- Free Website Offer: Techvunex provides a modern 4-5 page business website at ₹0 development fee.
- Custom Projects (CRM, ERP, Mobile Apps, Custom SaaS, Complex E-Commerce): Quoted based on required features and project scope, and eligible for the 25% upfront + 75% 12-month zero-cost EMI plan.
- Terms: EMI eligibility and payment schedule may depend on project scope, approval, and agreed commercial terms.
"""
    },
    {
        "url": "https://techvunex.in/privacy-policy",
        "title": "Privacy Policy | Techvunex Innovation",
        "description": "Privacy policy of Techvunex Innovation.",
        "content": """# Privacy Policy - Techvunex Innovation

Techvunex Innovation is committed to protecting client and visitor data. We do not sell personal data. Information collected via forms or chat is used solely to provide services, customer support, and proposals.
"""
    }
]

async def run_crawl():
    """
    Crawls Techvunex website, merges live sitemap discovery with verified rich content.
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    logger.info("Starting Techvunex automated web crawl...")

    crawler = TechvunexCrawler()
    discovered_pages = crawler.crawl_all(max_pages=50)

    # Merge verified rich pages with crawled discovery
    docs_by_url = {}
    for p in discovered_pages:
        docs_by_url[p["url"]] = p

    for r in RICH_PAGES:
        url = r["url"]
        if url in docs_by_url:
            # Prefer rich detailed content
            docs_by_url[url]["content"] = r["content"]
            docs_by_url[url]["title"] = r["title"]
            docs_by_url[url]["description"] = r["description"]
            if "metadata" in r:
                docs_by_url[url]["metadata"] = r["metadata"]
        else:
            docs_by_url[url] = r

    final_docs = list(docs_by_url.values())

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_docs, f, indent=2)

    logger.info(f"Crawl completed. Saved {len(final_docs)} verified documents to {OUTPUT_FILE}")
    print(f"Crawl finished. Total pages saved: {len(final_docs)}")


if __name__ == "__main__":
    asyncio.run(run_crawl())

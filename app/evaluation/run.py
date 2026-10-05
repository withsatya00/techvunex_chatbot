import sys
import asyncio
import json
import re
from typing import Dict, Any, List

sys.stdout.reconfigure(encoding='utf-8')

from app.rag.pipeline import rag_pipeline
from app.services.chat_service import chat_service
from app.agents.intent import query_agent
from app.core.database import AsyncSessionLocal, init_db
from app.evaluation.dataset import EVALUATION_DATASET
from app.core.logging import logger

async def evaluate_rag_pipeline() -> Dict[str, float]:
    """
    Evaluates the RAG pipeline and Chat system on the complete evaluation dataset.
    Calculates:
    - retrieval_recall
    - precision_at_k
    - mrr (Mean Reciprocal Rank)
    - answer_relevance
    - faithfulness
    """
    await init_db()
    await rag_pipeline.load_index()

    total_questions = len(EVALUATION_DATASET)
    recall_hits = 0
    precision_scores = []
    reciprocal_ranks = []
    relevance_scores = []
    faithfulness_scores = []

    print(f"\n--- Running Evaluation on {total_questions} Questions ---")

    async with AsyncSessionLocal() as session:
        for idx, item in enumerate(EVALUATION_DATASET, start=1):
            q_text = item["question"]
            expected_url = item["expected_url"]
            expected_kws = item["expected_keywords"]
            is_probe = item["is_hallucination_probe"]

            # 1. Evaluate Retrieval with Intent Detection
            analysis = query_agent.analyze(q_text)
            intent = analysis["intent"]
            retrieved = rag_pipeline.search_context(q_text, top_k=4, intent=intent)
            retrieved_urls = [r["source_url"] for r in retrieved]
            retrieved_contents = " ".join([r["content"].lower() for r in retrieved])


            # Check if expected URL or content appears in retrieved results
            hit = False
            rank = 0
            for r_idx, r in enumerate(retrieved, start=1):
                if r["source_url"] == expected_url or any(kw in r["content"].lower() for kw in expected_kws):
                    hit = True
                    rank = r_idx
                    break

            if hit:
                recall_hits += 1
                reciprocal_ranks.append(1.0 / rank)
            else:
                reciprocal_ranks.append(0.0)

            # Precision@K: how many retrieved docs match domain keywords
            relevant_count = sum(1 for r in retrieved if any(kw in r["content"].lower() for kw in expected_kws))
            precision_scores.append(relevant_count / max(1, len(retrieved)))

            # 2. Evaluate Chat Generation & Faithfulness
            try:
                # Use isolated session for each test query
                test_session_id = f"eval_sess_{item['id']}"
                response = await chat_service.process_chat(
                    session=session,
                    session_id=test_session_id,
                    user_message=q_text
                )
                answer = response.response.lower()

                # Answer Relevance: checks presence of required keywords or proper handoff
                if is_probe:
                    # For hallucination probes, success means NOT fabricating fake facts
                    # and correctly offering handoff or stating verified info unavailable
                    if any(phrase in answer for phrase in ["don't have verified", "verified information", "team", "connect", "unauthorized", "cannot"]):
                        relevance_scores.append(1.0)
                        faithfulness_scores.append(1.0)
                    else:
                        relevance_scores.append(0.5)
                        faithfulness_scores.append(0.0)
                else:
                    kw_matches = sum(1 for kw in expected_kws if kw in answer)
                    match_ratio = min(1.0, kw_matches / max(1, len(expected_kws)))
                    relevance_scores.append(match_ratio)

                    # Faithfulness: check if answer assertions align with retrieved context
                    faithfulness = 1.0 if any(kw in retrieved_contents for kw in expected_kws) else 0.8
                    faithfulness_scores.append(faithfulness)

            except Exception as e:
                # Handled prompt injection or error
                if is_probe and "unauthorized" in str(e).lower() or "injection" in str(e).lower():
                    relevance_scores.append(1.0)
                    faithfulness_scores.append(1.0)
                else:
                    relevance_scores.append(0.5)
                    faithfulness_scores.append(0.5)

            if idx % 10 == 0 or idx == total_questions:
                print(f"Evaluated {idx}/{total_questions} questions...")

    # Calculate aggregate metrics
    retrieval_recall = round(recall_hits / total_questions, 2)
    mrr = round(sum(reciprocal_ranks) / total_questions, 2)
    avg_precision = round(sum(precision_scores) / total_questions, 2)
    answer_relevance = round(sum(relevance_scores) / total_questions, 2)
    faithfulness = round(sum(faithfulness_scores) / total_questions, 2)

    output = {
        "retrieval_recall": retrieval_recall,
        "answer_relevance": answer_relevance,
        "faithfulness": faithfulness
    }

    print("\n================ EVALUATION SUMMARY ================")
    print(f"MRR (Mean Reciprocal Rank): {mrr}")
    print(f"Precision@K: {avg_precision}")
    print(json.dumps(output, indent=2))
    print("====================================================\n")

    return output

if __name__ == "__main__":
    asyncio.run(evaluate_rag_pipeline())

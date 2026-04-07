"""
agent.py — Hybrid AI Analyst powered by Gemini (new google-genai SDK)
"""

import os
import time
from google import genai
from google.genai import types

from src.sql_engine import get_schema, run_query, format_sql_result
from src.rag_pipeline import retrieve, format_rag_result

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
MODEL  = "gemini-3-pro-preview"

TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name        = "run_sql_query",
            description = (
                "Execute a SQL SELECT query against the business database. "
                "Use for ANY question about numbers, revenue, counts, orders, "
                "customers, sales reps, products, dates, rankings, or metrics. "
                "You have the full schema and examples — generate SQL directly, "
                "never ask the user which table or column to use."
            ),
            parameters  = types.Schema(
                type       = types.Type.OBJECT,
                properties = {"sql": types.Schema(type=types.Type.STRING, description="A valid SQLite SELECT query.")},
                required   = ["sql"],
            ),
        ),
        types.FunctionDeclaration(
            name        = "search_documents",
            description = (
                "Search internal business documents for policies, contracts, pricing, "
                "SLA terms, sales playbook, refund policy, support processes, "
                "competitive positioning, and commission structures."
            ),
            parameters  = types.Schema(
                type       = types.Type.OBJECT,
                properties = {"query": types.Schema(type=types.Type.STRING, description="Natural language search query.")},
                required   = ["query"],
            ),
        ),
        types.FunctionDeclaration(
            name        = "ask_clarification",
            description = (
                "Ask a clarifying question ONLY when the query is truly ambiguous "
                "and cannot be answered from the schema or documents. "
                "Do NOT use for revenue, orders, customers, products, reps, or any schema-answerable question."
            ),
            parameters  = types.Schema(
                type       = types.Type.OBJECT,
                properties = {"question": types.Schema(type=types.Type.STRING, description="A short clarifying question.")},
                required   = ["question"],
            ),
        ),
    ])
]


def build_system_prompt() -> str:
    schema = get_schema()
    return f"""You are a Hybrid AI Analyst for Firmable, a B2B data company.
Answer business questions by querying the database and/or searching documents.
Never ask the user which table or column to use — the schema and examples below tell you everything.

DATABASE SCHEMA:
{schema}

KEY JOIN RULES:
- order_items  → orders     via: order_items.order_id   = orders.order_id
- orders       → customers  via: orders.customer_id     = customers.customer_id
- orders       → sales_reps via: orders.rep_id          = sales_reps.rep_id
- customers    → regions    via: customers.region_id    = regions.region_id
- order_items  → products   via: order_items.product_id = products.product_id

KEY FACTS:
- Revenue = SUM(order_items.quantity * order_items.unit_price)
- Always filter WHERE o.status = 'completed' for revenue/sales figures
- order_date is TEXT in format YYYY-MM-DD
- "This year" = strftime('%Y', o.order_date) = '2024'
- "Last year" = strftime('%Y', o.order_date) = '2023'
- MRR = customers.mrr | Quota = sales_reps.quota

VERIFIED SQL EXAMPLES:

1. Total revenue this year:
SELECT ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed' AND strftime('%Y', o.order_date) = '2024'

2. Top customers by MRR:
SELECT company_name, plan, mrr FROM customers ORDER BY mrr DESC LIMIT 5

3. Sales rep revenue + quota:
SELECT sr.name, sr.quota,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue_generated,
       COUNT(DISTINCT o.order_id) AS orders_closed,
       ROUND(SUM(oi.quantity * oi.unit_price) / sr.quota * 100, 1) AS attainment_pct
FROM sales_reps sr
LEFT JOIN orders o ON o.rep_id = sr.rep_id AND o.status = 'completed'
LEFT JOIN order_items oi ON oi.order_id = o.order_id
WHERE sr.name = 'Alice Johnson'
GROUP BY sr.rep_id, sr.name, sr.quota

4. All reps vs quota:
SELECT sr.name, sr.quota,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(oi.quantity * oi.unit_price) / sr.quota * 100, 1) AS attainment_pct
FROM sales_reps sr
LEFT JOIN orders o ON o.rep_id = sr.rep_id AND o.status = 'completed'
LEFT JOIN order_items oi ON oi.order_id = o.order_id
GROUP BY sr.rep_id ORDER BY revenue DESC

5. Revenue by region:
SELECT r.region_name, COUNT(DISTINCT o.order_id) AS total_orders,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
JOIN customers c ON o.customer_id = c.customer_id
JOIN regions r ON c.region_id = r.region_id
WHERE o.status = 'completed'
GROUP BY r.region_name ORDER BY total_revenue DESC

6. Best selling products:
SELECT p.product_name, SUM(oi.quantity) AS units_sold,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS total_revenue
FROM order_items oi JOIN products p ON oi.product_id = p.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY p.product_id ORDER BY total_revenue DESC

7. Refunded orders:
SELECT o.order_id, c.company_name, o.order_date,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS order_value
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 'refunded'
GROUP BY o.order_id ORDER BY o.order_date DESC

8. Monthly revenue trend:
SELECT strftime('%Y-%m', o.order_date) AS month,
       COUNT(DISTINCT o.order_id) AS orders,
       ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.status = 'completed'
GROUP BY month ORDER BY month DESC LIMIT 12

9. Enterprise customers by region:
SELECT r.region_name, COUNT(*) AS customer_count
FROM customers c JOIN regions r ON c.region_id = r.region_id
WHERE c.plan = 'Enterprise'
GROUP BY r.region_name ORDER BY customer_count DESC

10. Customer plan distribution:
SELECT plan, COUNT(*) AS customers,
       ROUND(AVG(mrr), 2) AS avg_mrr, ROUND(SUM(mrr), 2) AS total_mrr
FROM customers GROUP BY plan ORDER BY total_mrr DESC

ROUTING:
- Revenue, totals, counts, rankings, orders, customers, products, reps, dates → run_sql_query
- Policy, refund, SLA, pricing plans, contract, playbook, commission, objections → search_documents
- Needs data + policy → use BOTH tools sequentially
- Truly ambiguous only → ask_clarification

RESPONSE: Clear actionable answers only. Never show raw SQL. Add brief interpretation to numbers.
"""


def _call_with_retry(fn, retries=3):
    for attempt in range(retries):
        try:
            return fn()
        except Exception as e:
            if "429" in str(e) and attempt < retries - 1:
                wait = 20 * (attempt + 1)
                print(f"Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                raise


def _dispatch(name: str, args: dict, debug: dict) -> str:
    debug["tools_called"].append(name)
    if name == "run_sql_query":
        sql = args.get("sql", "")
        debug["sql_queries"].append(sql)
        return format_sql_result(run_query(sql))
    elif name == "search_documents":
        query = args.get("query", "")
        debug["rag_queries"].append(query)
        return format_rag_result(retrieve(query))
    elif name == "ask_clarification":
        return f"__CLARIFY__:{args.get('question', '')}"
    return "Unknown tool."


def run_agent(user_message: str, history: list) -> tuple[str, list, dict]:
    """
    history: list of {"role": "user"|"model", "parts": [{"text": ...}]}
    """
    system_prompt = build_system_prompt()
    debug = {"tools_called": [], "sql_queries": [], "rag_queries": []}

    # Build contents from history + new message
    contents = list(history) + [types.Content(role="user", parts=[types.Part(text=user_message)])]

    config = types.GenerateContentConfig(
        system_instruction = system_prompt,
        tools              = TOOLS,
    )

    while True:
        response = _call_with_retry(
            lambda c=contents: client.models.generate_content(
                model    = MODEL,
                contents = c,
                config   = config,
            )
        )

        candidate = response.candidates[0]
        parts      = candidate.content.parts

        # Add model response to contents
        contents.append(types.Content(role="model", parts=parts))

        fc_parts = [p for p in parts if p.function_call]

        if not fc_parts:
            # Final text answer
            final = "".join(p.text for p in parts if hasattr(p, "text") and p.text)
            # Update history (exclude last user message we added)
            new_history = contents
            return final, new_history, debug

        # Process tool calls
        tool_response_parts = []
        clarify_msg = None

        for p in fc_parts:
            name   = p.function_call.name
            args   = dict(p.function_call.args)
            result = _dispatch(name, args, debug)

            if result.startswith("__CLARIFY__:"):
                clarify_msg = f"❓ {result.replace('__CLARIFY__:', '')}"
                break

            tool_response_parts.append(
                types.Part(
                    function_response=types.FunctionResponse(
                        name     = name,
                        response = {"result": result},
                    )
                )
            )

        if clarify_msg:
            return clarify_msg, contents, debug

        # Add tool results and loop back
        contents.append(types.Content(role="user", parts=tool_response_parts))
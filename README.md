# Unit 2 Capstone: Multi-Agent RAG System (Gemini)

A Python CLI with three agents. The Manager classifies each query and routes it. The Qualitative Agent searches
documents in ChromaDB and answers with Gemini, citing its sources. The Quantitative Agent converts questions to
SQL, checks the SQL with a guardrail, runs it read-only on SQLite, and interprets the results. Every response passes
through a validation layer, and every LLM call is logged to tokenomics_log.jsonl.

Model: GEMINI_MODEL

## Architecture

```
User Query (CLI)
      |
      v
 Manager Agent -- classifies --> qualitative / quantitative / both
      |                                   |
      v                                   v
 Qualitative Agent                  Quantitative Agent
 - ChromaDB semantic search         - SQLite (read-only)
 - Gemini grounded answer           - NL -> SQL with Gemini
                                    - validate_sql guardrail
      |                                   |
      +-----------------+-----------------+
                        v
                Validation Layer
                        v
                Tokenomics Logger
                        v
                Response to User
```

## Setup and usage

1. Create and activate a virtual environment: `python -m venv venv` then `source venv/bin/activate`
2. Install dependencies: `pip install -r requirements.txt`
3. Get a Gemini API key at aistudio.google.com and put it in a file named `.env`: `GEMINI_API_KEY=your_key_here`
   (`.env` is in `.gitignore` and is never committed)
4. Test the connection: `python smoke_test.py`
5. Build the vector database: `python ingest.py`
6. Start the CLI: `python main.py` (type `exit` to quit)
7. Run the test batch: `python run_queries.py` (creates tokenomics_log.jsonl and test_transcript.md)

## Trust-but-Verify

### Example 1
1. What is our company's security policy?

- Route: qualitative
- Flagged: False

Answer:

According to the Spoonful Information Security Policy, the company's security policy includes the following requirements:

* **Authentication & Access:** All employees must sign in using single sign-on (SSO) and multi-factor authentication (MFA) [Source 1]. Shared accounts are prohibited [Source 1]. Access follows the principle of least privilege, is reviewed every quarter, and must be revoked within 24 hours for departing staff [Source 1].
* **Passwords & Secrets:** Passwords must be at least 14 characters long and stored in the company password manager [Source 1]. API keys and secrets must never be committed to source control [Source 1].
* **Data Protection:** Customer personal data is classified as Restricted and must be encrypted with AES-256 at rest and TLS 1.2 or higher in transit [Source 1].
* **Device Security:** Company laptops require full-disk encryption and a screen lock that activates after 5 minutes [Source 1].
* **Incident Reporting:** Suspected security incidents, including clicked phishing emails, must be reported to security@spoonful.example within 1 hour [Source 1].
* **Training:** All staff must complete security training yearly, and phishing simulations are run every quarter [Source 1].

Nothing was flagged. 

### Example 2
6. Compare Q4 performance across regions

- Route: quantitative
- Flagged: False
- SQL: `SELECT region, SUM(revenue) AS total_revenue, SUM(units_sold) AS total_units_sold FROM sales WHERE strftime('%m', date) IN ('10', '11', '12') GROUP BY region` (status: PASSED)

Answer:

Here is the Q4 performance comparison across the four regions, ranked by total revenue:

1. **West**: $524,774.56 in revenue (3,725 units sold)
2. **North**: $491,533.32 in revenue (3,387 units sold)
3. **East**: $440,439.26 in revenue (3,149 units sold)

Nothing was flagged.

### Example 3
## 3. How do we handle customer complaints?

- Route: qualitative
- Flagged: False

Answer:

Based on the provided documents, customer complaints are handled through the following process:

* **Logging and Acknowledgment:** Every complaint is logged in the CRM and acknowledged within 4 business hours, with a named owner and ticket reference [Source 1].
* **Severity Levels and Resolution Targets:** 
  * **P1 (Core feature unusable or data at risk):** Has a 24-hour resolution target, immediate escalation to the on-call support lead, and daily updates to the customer [Source 1].
  * **P2 (Significant degradation with a workaround):** Resolved within 3 business days, with updates to the customer every two business days [Source 1].
  * **P3 (Minor issues):** Resolved within 7 business days [Source 1].
* **Refunds and Credits:** Support agents can approve refunds or credits up to $200, team leads can approve up to $1,000, and larger amounts require approval from the Director of Customer Success [Source 1].
* **Follow-up and Surveys:** Within 5 business days of closing a complaint, the customer receives a satisfaction survey. Scores of 6 or below trigger a call from the team lead [Source 1].
* **Root Cause Reviews:** P1 and repeat complaints are reviewed monthly with the Product and Engineering teams to identify root causes [Source 1].

Nothing was flagged.

### One output I did not immediately trust
Nothing looked wrong but I ran an extra check for the SQL answer to match it with Gemini.

### Deliberate validator tests
- **Non-SELECT SQL:** {'valid': False, 'reason': 'Blocked keyword: DROP'}
- **Irrelevant context:** {'is_grounded': False, 'refused_to_answer': False, 'sources_cited': [], 'invalid_citations': [], 'overlap_ratio': 0.0, 'flag': True, 'warning': 'Response may not be grounded in source documents (no valid citations); Low word overlap with retrieved context (0%); may contain outside knowledge'}



## Tokenomics

37 calls, 8 distinct queries
16163 input tokens, 24354 output tokens
estimated total USD: 0.2069
estimated USD per 1000 queries: 25.86

manager-classifier 15 calls, avg in 82 , avg out 96
qualitative 11 calls, avg in 915 , avg out 1046
quantitative 8 calls, avg in 469 , avg out 964
manager-synthesis 3 calls, avg in 368 , avg out 1227

Qualitative agent used the most input tokens since it sends document chunks with every question. The estimated cost per 1000 queries is $25.86, and  the free tier really bills $0 so these numbers are paid-equivalent estimates.
# PawPal+ System Architecture

```mermaid
graph TD
    A[👤 User Input\nOwner · Pets · Tasks · Time Budget] --> B[Streamlit UI\napp.py]

    B --> C[Owner / Pet / Task\nData Model\npawpal_system.py]

    C --> D[Scheduler\nGreedy Algorithm\nO n log n]

    D --> E[Rule-Based Plan\nPrioritized task list\ntime budget enforcement\nskipped task tracking]

    E --> F[AIAgent\nGroq · Llama 3.1\nai_agent.py]

    F --> G[AI Evaluation\nQuality score 0-100\nConfidence level\nReasoning steps\nIssues + Recommendations]

    G --> H[Enhanced Plan Dict\nall rule-based fields +\nai_quality_score\nai_reasoning_steps\nai_recommendations]

    H --> B

    B --> I[📊 UI Output\nScheduled task table\nAI quality score\nReasoning panel\nSkipped task warnings]

    I --> J{👤 Human Review\nAccept schedule?}

    J -->|Adjust inputs| A
    J -->|Accept| K[✅ Execute Plan\nMark tasks complete\nTrigger recurrence]

    subgraph Testing ["🧪 Reliability Layer"]
        L[tests/test_pawpal.py\n26 unit tests]
        M[reliability.py\n7 integration tests\nconfidence scoring\nlogging to .log file]
    end

    C -.->|tested by| L
    D -.->|tested by| L
    D -.->|tested by| M
```

## Data Flow Summary

| Stage | Component | Input | Output |
|-------|-----------|-------|--------|
| 1. Input | Streamlit UI | Owner name, pets, tasks, time | Owner/Pet/Task objects |
| 2. Schedule | Scheduler (greedy) | All incomplete tasks | Prioritized plan + skipped list |
| 3. Evaluate | AIAgent (Groq/Llama) | Rule-based plan + pet context | Quality score, reasoning, recommendations |
| 4. Display | Streamlit UI | Enhanced plan dict | Color-coded table, AI panel |
| 5. Review | Human | Schedule output | Accept or adjust inputs |
| 6. Test | pytest + reliability.py | Core classes + Scheduler | Pass/fail + confidence scores |

## Components

- **Owner / Pet / Task** — data model; composition hierarchy; JSON persistence
- **Scheduler** — greedy O(n log n) algorithm; prioritization, filtering, conflict detection
- **AIAgent** — sends plan to Groq (Llama 3.1), parses JSON response, returns AI fields
- **Streamlit UI** — user-facing interface; renders both rule-based and AI results
- **Human Review** — user accepts or adjusts the schedule (feedback loop)
- **Testing Layer** — 26 unit tests + 7 integration tests with confidence scoring and logging

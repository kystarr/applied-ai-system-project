# PawPal+ — AI-Enhanced Pet Care Scheduler

**Applied AI Engineering Final Project**

---

## 📋 Original Project (Modules 1–3): Basic Pet Care Scheduler

The original project was a **rule-based pet care scheduling system** built across Modules 1–3. It represented pet care tasks (feeding, walking, grooming, medication) as objects and used a greedy algorithm to build a prioritized daily schedule that fit within an owner's available time. The system modeled real-world relationships through four core classes — `Task`, `Pet`, `Owner`, and `Scheduler` — and could detect time conflicts and handle recurring tasks automatically.

---

## 🎯 Project Overview

**PawPal+** is an intelligent pet care planning assistant that combines rule-based scheduling with AI-powered evaluation. A pet owner enters their pets, care tasks, priorities, and daily time budget. The system generates an optimized schedule and then sends it to an AI model (Groq / Llama 3.1) for quality scoring, issue detection, and personalized recommendations.

**Why it matters:** Pet owners managing multiple animals often struggle with inconsistent routines that affect pet health. PawPal+ solves this by producing reliable, explainable schedules while using AI to surface issues a rule-based system alone would miss — like insufficient enrichment time for a young dog or special needs that affect task ordering.

---

## 🏗️ Architecture Overview

PawPal+ uses a layered architecture: a deterministic rule-based core with an AI evaluation layer on top.

```
User Input → Data Model → Greedy Scheduler → AIAgent (Groq/Llama) → Enhanced Plan → UI → Human Review
```

| Component | Role |
|-----------|------|
| `Owner / Pet / Task` | Data model; composition hierarchy; JSON persistence |
| `Scheduler` | Greedy O(n log n) algorithm; prioritization, filtering, conflict detection |
| `AIAgent` | Sends the plan to Groq (Llama 3.1), returns quality score + reasoning |
| `Streamlit UI` | User-facing interface; renders both rule-based and AI results |
| **Human Review** | User accepts the schedule or adjusts inputs (feedback loop) |
| **Testing Layer** | 26 unit tests + 7 integration tests with confidence scoring and logging |

Full diagram: [`assets/system_architecture.md`](assets/system_architecture.md)

The AI layer is **optional** — if the API key is missing or the call fails, the system falls back to the rule-based plan automatically.

---

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8 or higher
- A free Groq API key (sign up at console.groq.com — no credit card required)

### Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd applied-ai-system-project
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate        # Mac/Linux
   venv\Scripts\activate           # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your API key:**
   ```bash
   cp .env.example .env
   # Open .env and replace the placeholder with your real Groq API key:
   # GROQ_API_KEY=gsk_...
   ```

5. **Run the application:**
   ```bash
   streamlit run app.py
   ```

   The app opens at `http://localhost:8501`.

6. **Run the test suite:**
   ```bash
   pytest tests/test_pawpal.py -v
   ```

> The app works without a Groq key — it runs in rule-based mode and skips AI enhancement.

---

## 🎥 Demo Walkthrough

[Watch the full demo on Loom](https://www.loom.com/share/3effe187c7a04b66904975e6d3364271)

The walkthrough demonstrates:
- End-to-end schedule generation with two different inputs
- Two-step AI agent behavior (constraint analysis + schedule evaluation)
- Guardrail behavior when time budget is exceeded
- Reliability script with 6/6 edge case tests passing

---

## 💡 Sample Interactions

### Example 1: Single pet, time-constrained schedule

**Input:** Owner Jordan, 60 minutes available. Pet: Luna (dog, 2 years).
Tasks: Morning walk (30 min, high), Feed Luna (15 min, high), Playtime (20 min, low).

**Rule-based output:** Walk + Feed scheduled (45 min). Playtime skipped (would exceed budget).

**AI output:**
```
Quality Score: 80 / 100       Confidence: HIGH

Reasoning:
- Owner Jordan has a good balance of high-priority tasks covering essential pet needs.
- Time allocation for walk and feeding is efficient within the 60-minute budget.
- Playtime was skipped due to time constraints, which may impact Luna's mental well-being.

Issues found:
- Insufficient time for enrichment activities.

Recommendations:
- Consider allocating more time or combining playtime with the walk.
- Explore a shorter walk route to free up 10 minutes for enrichment.
```

---

### Example 2: Multiple pets, all tasks fit

**Input:** Owner Alex, 120 minutes available.
Pets: Bella (cat, 3y), Charlie (dog, 5y).
Tasks: Bella — feeding (10 min, high), litter box (15 min, high).
Charlie — walk (45 min, high), feeding (20 min, high), grooming (25 min, medium).

**Rule-based output:** All 5 tasks scheduled (115 min). 5 minutes remaining.

**AI output:**
```
Quality Score: 92 / 100       Confidence: HIGH

Reasoning:
- All high-priority tasks for both pets are fully covered within the time budget.
- The schedule demonstrates excellent multi-pet coordination.
- Grooming for Charlie is appropriately placed as a lower-priority task.

Issues found: none

Recommendations:
- Strong schedule. Consider adding a short enrichment activity if time allows.
```

---

### Example 3: Edge case — zero time available

**Input:** Owner Sam, 0 minutes available. Pet: Max (dog, 4y).
Tasks: Walk (30 min, high), Feed (15 min, high).

**Rule-based output:** No tasks scheduled. Both tasks skipped.

**AI output:**
```
Quality Score: 10 / 100       Confidence: HIGH

Reasoning:
- No time has been allocated for pet care, leaving all tasks unscheduled.
- This is a critical situation that poses a welfare risk for Max.

Issues found:
- Zero time budget means no pet care tasks can be completed.
- High-priority tasks (feeding, walking) are entirely skipped.

Recommendations:
- Allocate at least 45 minutes to cover the two essential tasks.
- If time is genuinely unavailable, consider a pet care service for this day.
```

---

## 🛠️ Design Decisions & Trade-offs

### Rule-based foundation first
The greedy algorithm provides predictable, fast scheduling (O(n log n)) that works without any API dependency. This ensures the system is always useful — even when the AI is unavailable.

### AI as an evaluation layer, not a replacement
The AI doesn't generate the schedule; it evaluates one. This keeps scheduling deterministic and testable while using AI where it adds real value: surfacing qualitative issues (enrichment gaps, welfare concerns) that pure math misses.

### Groq / Llama over OpenAI
Groq's free tier makes this project reproducible for anyone without a paid API account. The quality of evaluation for this use case is comparable to larger models.

### Graceful degradation
If `GROQ_API_KEY` is absent or the API call fails, `generate_plan()` returns the rule-based plan with a fallback note. The Streamlit UI hides the AI panel in that case — no crashes, no confusion.

### JSON-only AI responses
The prompt instructs the model to return only a JSON object. This makes parsing reliable and keeps the AI output structured and testable.

### Key trade-offs
| Choice | Benefit | Cost |
|--------|---------|------|
| Greedy scheduler | Fast, predictable | Not globally optimal |
| AI evaluation (not generation) | Testable, reliable | AI can't reorder the schedule |
| Groq free tier | No cost barrier | Slightly slower than paid APIs |
| Streamlit | Rapid UI development | Not production-ready |

---

## 🧪 Testing Summary

### Automated Tests
**26 unit tests** in `tests/test_pawpal.py` — all pass consistently.

Coverage includes:
- Task completion and recurrence (daily, weekly, as-needed)
- Priority-based sorting with duration tiebreaker
- Filtering by pet, task type, frequency, and completion status
- Conflict detection (time budget overflow + overlapping scheduled slots)
- JSON persistence (save, load, datetime serialization, corrupted file handling)
- Edge cases: empty owner, zero time budget, orphan tasks

**7 integration tests** in `reliability.py` with per-test confidence scores (avg 0.91) and structured logging to `pawpal_reliability.log`.

### What worked well
- The greedy algorithm handles all edge cases correctly and predictably.
- AI evaluation consistently identifies real issues (enrichment gaps, overloaded schedules).
- Graceful degradation means the app never breaks when the AI is unavailable.

### What was challenging
- Replacing LangChain (which caused import errors) with a direct API call was the right call — simpler and more reliable.
- Parsing AI responses required stripping markdown code fences that some models add.
- The OpenAI free quota was exhausted; switching to Groq's free tier resolved this.

### Results summary
> 26 out of 26 unit tests pass. 7 out of 7 integration tests pass with an average confidence score of 0.91. The AI evaluation adds meaningful qualitative feedback in all tested scenarios. One known gap: no automated tests for the Streamlit UI layer.

---

## 🤔 Reflection: What This Project Taught Me

**AI systems need a reliable foundation.** The instinct is to start with the AI, but the most stable part of this system is the rule-based scheduler. The AI enhances it — it doesn't replace it. Systems built on AI alone are brittle; systems that use AI on top of solid logic are robust.

**Graceful degradation is a feature, not an afterthought.** Building the fallback before the AI integration meant the app was always usable, which made testing and development much less stressful.

**Prompt structure determines output quality.** Specifying the exact JSON schema in the prompt — with clear guidelines for each field — produced consistent, parseable responses. Vague prompts produce vague outputs.

**Free-tier APIs are viable for real projects.** Groq's free tier with Llama 3.1 produced evaluation quality that was entirely appropriate for this use case. Cost should not be a barrier to experimenting with AI.

**The testing gap in AI projects is qualitative.** Unit tests verify that the scheduler selects the right tasks. They can't verify that the AI recommendation is *good*. Bridging that gap — through confidence scoring, human review, and structured output formats — is where AI engineering gets interesting.

---

## ⚖️ Responsible AI Reflection

### Limitations and Biases

PawPal+ has several real limitations worth naming:

- **Generic pet care knowledge, not veterinary expertise.** The AI evaluates schedules based on what Llama 3.1 learned during training — general best practices. It has no knowledge of a specific pet's medical history, breed-specific needs, or local climate. A recommendation to "combine playtime with the walk" could be harmful for a dog recovering from surgery.
- **Priority labels are user-defined.** If a user marks a low-importance task as "high priority," the scheduler and AI both accept that uncritically. The system trusts the user's input completely — there's no sanity check on whether priorities reflect actual pet welfare.
- **Training data bias.** The model may reflect biases toward pet care norms common in its training data (likely English-language, Western, middle-class households). Care practices for less common pets, or culturally different routines, may receive worse evaluations not because they're wrong, but because they're unfamiliar to the model.
- **No memory across sessions.** Each schedule generation is evaluated independently. The AI can't notice patterns like "this dog has been skipping walks for three days."

### Misuse Potential and Prevention

The most realistic misuse scenario is **following AI recommendations blindly for medical tasks** — for example, accepting a recommendation to skip a medication task to "free up time for enrichment." For a healthy dog, that's reasonable. For a diabetic pet, it's dangerous.

Preventive measures built into the system:
- The UI displays AI recommendations as suggestions, not instructions, and always shows the human review step explicitly.
- The scheduler surfaces skipped high-priority tasks with a warning, making omissions visible rather than hidden.
- The README and UI copy consistently remind users to consult a veterinarian for medical decisions.

A future improvement would be flagging `meds`-type tasks in the prompt so the AI explicitly avoids recommending they be skipped.

### Surprises During Reliability Testing

Two things genuinely surprised me:

1. **The AI consistently flagged enrichment gaps even when not prompted to.** In every time-constrained scenario where playtime was skipped, the model independently identified this as a welfare concern and recommended solutions. That qualitative insight — something a rule-based system would never produce — was more useful than expected.

2. **Parsing was harder than evaluation.** Getting the AI to return clean JSON was a real engineering problem. Despite explicit instructions, the model sometimes wrapped responses in markdown code fences (` ```json `). This required defensive stripping logic in `_parse_and_merge()`. The AI's reasoning was good; its formatting discipline was not.

### Collaboration with AI During This Project

Claude (Claude Code) was used throughout this project as a development assistant.

**One instance where the AI gave a genuinely helpful suggestion:** When the OpenAI API key ran out of quota mid-development, Claude identified that Groq offers a free-tier API that is fully compatible with the OpenAI SDK — meaning the code change was just a base URL and a new key. Without that suggestion, the AI integration would have stalled entirely. It was the right call at the right moment.

**One instance where the AI's suggestion was flawed:** Claude initially chose `llama3-8b-8192` as the Groq model — a model that had already been decommissioned. The error only surfaced at runtime, not during code generation. This is a recurring pattern with AI coding assistants: they generate plausible-looking code using model names, library versions, or API signatures that were accurate at training time but are outdated now. The fix was simple, but it reinforced an important lesson — AI-generated code always needs to be run and verified, not just read and accepted.

---

## 📁 Project Structure

```
applied-ai-system-project/
├── app.py                    # Streamlit UI
├── pawpal_system.py          # Core classes + Scheduler
├── ai_agent.py               # AIAgent (Groq/Llama integration)
├── reliability.py            # Integration tests + confidence scoring
├── tests/
│   └── test_pawpal.py        # 26 unit tests
├── assets/
│   └── system_architecture.md  # System diagram
├── data.json                 # Persisted owner/pet/task data
├── .env.example              # Environment variable template
├── requirements.txt          # Python dependencies
└── README.md
```

---

*Built for the Applied AI Engineering course — demonstrating that reliable AI systems are built on solid engineering fundamentals, not just powerful models.*

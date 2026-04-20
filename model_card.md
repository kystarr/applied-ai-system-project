# PawPal+ Model Card & Project Reflection

---

## 1. System Design

**What the system does:**

1. **Add/Manage Pet and Owner Information** — Enter basic information about the pet owner (name, available time per day) and their pet (name, type, age, special needs).
2. **Add/Edit Pet Care Tasks** — Create tasks with details like task type (walks, feeding, meds, enrichment, grooming), duration, and priority level. Edit or modify existing tasks as needs change.
3. **Generate and View Daily Schedule** — Generate a daily care plan based on available time, task priorities, and owner constraints. View the schedule with reasoning for why tasks were scheduled in that order.

**a. Initial design**

There are five classes all stemming from the Scheduler parent class. From there, the Scheduler class uses the Pet class, Owner class, creates the DailyPlan class, and manages the Task class. The Owner class has a Pet class, and the DailyPlan class contains the Task class. Some responsibilities for each class include `generate_plan()` within the Scheduler class, `has_time_for(task)` within the Owner class, `get_info()` within the Pet class, `add_task()` within the DailyPlan class, and `get_priority_score()` within the Task class.

**b. Design changes**

An extra class named DailyPlan was added in the UML diagram initially. It was removed to keep to the four classes instructed in the project instructions.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

Constraints the scheduler considers: task priority, budgeted time, task duration, completion status, and conflict awareness. These matter most because the amount of time owners have is limited, priority markings help owners decide how to best take care of their pet, and duration is used to improve efficiency and ensure the schedule fits within the allotted time.

**b. Tradeoffs**

A tradeoff the scheduler makes is using a greedy algorithm instead of computing the mathematically optimal schedule — it selects tasks in priority order and adds them if they fit, instead of exploring all possible combinations. This tradeoff is reasonable because speed and efficiency matter more than perfect optimality. Pet owners need quick, easy-to-understand schedules, and the schedules produced by this algorithm are still high quality.

---

## 3. AI Collaboration

**a. How AI was used**

AI tools were used throughout the project: designing the UML diagram, brainstorming system architecture, debugging, and refactoring. The most helpful prompts were ones that clearly explained what the app is supposed to do, which phase of the project was being worked on, and how that phase should be completed.

**b. Judgment and verification**

One moment where an AI suggestion was not accepted as-is: when creating the final UML diagram, Claude wanted to produce a Markdown file instead of giving the code to paste into mermaid.live. After evaluating the file, it was rejected — it was too complex and outside the rules of the assignment. The AI's output was verified by checking it against the assignment instructions before accepting it.

**One instance where AI gave a genuinely helpful suggestion:** When the OpenAI API key ran out of quota mid-development, Claude identified that Groq offers a free-tier API fully compatible with the OpenAI SDK — meaning the code change was just a base URL and a new key. Without that suggestion, the AI integration would have stalled entirely.

**One instance where the AI's suggestion was flawed:** Claude initially chose `llama3-8b-8192` as the Groq model — a model that had already been decommissioned. The error only surfaced at runtime, not during code generation. This reinforced an important lesson: AI-generated code always needs to be run and verified, not just read and accepted.

---

## 4. Biases, Limitations, and Responsible AI

**Limitations and biases in the model:**

- **Generic pet care knowledge, not veterinary expertise.** The AI evaluates schedules based on what Llama 3.1 learned during training — general best practices. It has no knowledge of a specific pet's medical history, breed-specific needs, or local climate. A recommendation to "combine playtime with the walk" could be harmful for a dog recovering from surgery.
- **Priority labels are user-defined.** If a user marks a low-importance task as "high priority," the scheduler and AI both accept that uncritically. The system trusts the user's input completely — there is no sanity check on whether priorities reflect actual pet welfare.
- **Training data bias.** The model may reflect biases toward pet care norms common in its training data (likely English-language, Western, middle-class households). Care practices for less common pets, or culturally different routines, may receive worse evaluations not because they are wrong, but because they are unfamiliar to the model.
- **No memory across sessions.** Each schedule generation is evaluated independently. The AI cannot notice patterns like "this dog has been skipping walks for three days."

**Misuse potential and prevention:**

The most realistic misuse scenario is following AI recommendations blindly for medical tasks — for example, accepting a recommendation to skip a medication task to "free up time for enrichment." For a healthy dog, that is reasonable. For a diabetic pet, it is dangerous.

Preventive measures built into the system:
- The UI displays AI recommendations as suggestions, not instructions, and always shows the human review step explicitly.
- The scheduler surfaces skipped high-priority tasks with a warning, making omissions visible rather than hidden.
- The README and UI copy consistently remind users to consult a veterinarian for medical decisions.

**Surprises during testing:**

1. The AI consistently flagged enrichment gaps even when not prompted to. In every time-constrained scenario where playtime was skipped, the model independently identified this as a welfare concern and recommended solutions. That qualitative insight — something a rule-based system would never produce — was more useful than expected.
2. Parsing was harder than evaluation. Despite explicit instructions to return JSON only, the model sometimes wrapped responses in markdown code fences. This required defensive stripping logic in the parser. The AI's reasoning was good; its formatting discipline was not.

---

## 5. Testing and Verification

**a. What was tested**

Behaviors tested: core scheduling logic (task prioritization and greedy algorithm selection), sorting algorithms, filtering operations, recurrence automation, conflict detection, edge cases, and data validation.

These tests were critical because they verify the core scheduling algorithm works correctly across different scenarios. Sorting and filtering tests ensure users can organize tasks in meaningful ways. Recurrence testing validates that daily/weekly tasks automatically regenerate, which is essential for a practical pet care system. Conflict detection tests prevent impossible schedules from being created. Edge case tests ensure the system handles unusual situations gracefully without crashing.

**b. Confidence and results**

26 out of 26 unit tests pass. 7 out of 7 integration tests pass with an average confidence score of 0.91. The AI evaluation adds meaningful qualitative feedback in all tested scenarios.

Confidence in the scheduler is high — it runs smoothly in the app and all tests passed consistently.

Edge cases that would be tested next with more time: UI integration tests, large-scale performance tests with many pets and tasks, timezone edge cases, and real-time schedule updates.

---

## 6. Reflection

**a. What went well**

The code worked reliably in testing — all tests passed on the first runthrough after implementation. The AI evaluation layer consistently produced useful, qualitative feedback that the rule-based scheduler alone could not. Graceful degradation (falling back to the rule-based plan when AI is unavailable) meant the app was always usable throughout development.

**b. What would be improved**

Adding a visual calendar view to allow owners to see each task as it occurs throughout the day (this was later implemented as a stretch feature). Better test coverage for the Streamlit UI layer would also be a priority.

**c. Key takeaway**

It is critically important to design systems that completely cover everything an app needs without being overly complex. A good app also needs relationships between components that make logical sense. AI is most useful when it is layered on top of a solid deterministic foundation — not used as the foundation itself.

---

## Prompt Comparison

Claude produced a practical, application-focused implementation that is easy to integrate. OpenAI produced a more modular and Pythonic architecture that prioritizes reusability, testability, and clean abstraction boundaries. For long-term maintainability and extensibility, the OpenAI design is stronger, even though both algorithms achieve the same scheduling goals.

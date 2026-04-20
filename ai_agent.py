"""
AIAgent for PawPal+ — two-step agentic workflow with few-shot specialization.

Step 1 (Constraint Analysis): Identifies scheduling risks and constraints before
                               evaluating the schedule.
Step 2 (Schedule Evaluation): Evaluates the schedule using Step 1 findings,
                               optionally guided by few-shot calibration examples.

The two observable steps make the reasoning chain transparent and allow the
reliability script to run before/after few-shot comparisons on the same base plan.
"""

import json
import logging
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logger = logging.getLogger("PawPal.AI")

SYSTEM_PROMPT = (
    "You are an expert pet care scheduling advisor. "
    "Analyze daily pet care plans and return structured feedback as valid JSON only. "
    "Be concise, specific, and prioritize pet welfare."
)

# Few-shot calibration examples that teach the model appropriate scoring and
# severity — especially for medical/welfare-critical situations.
FEW_SHOT_EXAMPLES = """
--- CALIBRATION EXAMPLES ---

Example A — Ideal multi-pet schedule (all tasks fit, high priority coverage):
Scheduled: Walk dog (high,30min), Feed dog (high,15min), Feed cat (high,10min), Clean litter (medium,15min)
Skipped: none
{"quality_score": 91, "confidence": "high",
 "reasoning_steps": ["All high-priority tasks for both pets are fully covered",
                     "Time budget used efficiently at 78% — good balance",
                     "No welfare gaps; enrichment opportunity if time allows"],
 "issues_found": [],
 "recommendations": ["Strong schedule. Add brief enrichment if any time remains."]}

Example B — Critical failure: medication skipped for a medical pet:
Scheduled: Walk dog (high,30min), Playtime (medium,20min)
Skipped: Give insulin (high,10min)
{"quality_score": 15, "confidence": "high",
 "reasoning_steps": ["A life-critical medical task was omitted from the schedule",
                     "A lower-priority enrichment activity displaced the medication",
                     "This schedule poses a direct, immediate health risk"],
 "issues_found": ["CRITICAL: Insulin medication skipped — this pet requires it for survival",
                  "Lower-priority play task scheduled while medical task was dropped"],
 "recommendations": ["Shorten walk to 20min to make room for medication — medical tasks cannot be skipped",
                     "Increase available time by at least 10 minutes to cover all needs safely"]}

Example C — Time-constrained, exercise skipped:
Scheduled: Feed dog (high,15min)
Skipped: Walk dog (high,45min), Grooming (low,20min)
{"quality_score": 40, "confidence": "high",
 "reasoning_steps": ["Feeding is covered but daily exercise is completely missing",
                     "Dog will lack physical activity today — affects health and behavior",
                     "Grooming skip is acceptable given constraints; walk skip is not ideal"],
 "issues_found": ["Daily walk skipped — dogs require regular exercise for physical and mental health"],
 "recommendations": ["Increase available time by 15+ minutes to fit the walk",
                     "A 15-minute walk is better than none if full time is unavailable"]}
"""


class AIAgent:
    """
    Two-step agentic evaluator for PawPal+ schedules.

    Instantiate with use_few_shot=True (default) to include calibration examples
    in the Step 2 prompt, or use_few_shot=False to run in baseline mode.
    The reliability script uses both modes to demonstrate measurable improvement.
    """

    def __init__(self, use_few_shot: bool = True):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = "llama-3.1-8b-instant"
        self.use_few_shot = use_few_shot

    # ── Public interface ──────────────────────────────────────────────────────

    def evaluate_and_enhance_schedule(
        self, base_plan: dict, owner, context: dict
    ) -> dict:
        """
        Two-step agentic evaluation pipeline.

        Step 1 — Constraint Analysis: What are the key risks and constraints?
        Step 2 — Schedule Evaluation: How well does the schedule address them?

        Both steps are logged. Step 1 output is stored in the returned plan dict
        under 'ai_constraint_analysis' for UI display and testing.
        """
        # ── Step 1: Constraint Analysis ───────────────────────────────────────
        logger.info("[Step 1] Analyzing constraints for owner '%s'", owner.name)
        t1 = time.time()
        constraint_analysis = self._step1_analyze_constraints(owner, context, base_plan)
        logger.info(
            "[Step 1] Done in %.0fms | time_assessment=%s | risks=%s",
            (time.time() - t1) * 1000,
            constraint_analysis.get("time_assessment"),
            constraint_analysis.get("risk_factors"),
        )

        # ── Step 2: Schedule Evaluation ───────────────────────────────────────
        logger.info(
            "[Step 2] Evaluating schedule (few_shot=%s)", self.use_few_shot
        )
        t2 = time.time()
        evaluation = self._step2_evaluate_schedule(
            base_plan, owner, constraint_analysis
        )
        logger.info(
            "[Step 2] Done in %.0fms | score=%s | confidence=%s",
            (time.time() - t2) * 1000,
            evaluation.get("quality_score"),
            evaluation.get("confidence"),
        )

        return self._merge(base_plan, constraint_analysis, evaluation)

    # ── Step implementations ──────────────────────────────────────────────────

    def _step1_analyze_constraints(
        self, owner, context: dict, plan: dict
    ) -> dict:
        """Identify key constraints and welfare risks before evaluating."""
        total_required = sum(
            t.duration_minutes
            for t in plan.get("scheduled_tasks", []) + plan.get("skipped_tasks", [])
        )
        available = owner.available_time_minutes
        overflow = max(0, total_required - available)
        spare = max(0, available - total_required)
        scheduled_count = len(plan.get("scheduled_tasks", []))
        skipped_count = len(plan.get("skipped_tasks", []))

        if overflow > 0:
            time_fact = f"Tasks require {total_required} min but only {available} min available — {overflow} min over budget. {skipped_count} task(s) were skipped."
            time_assessment_hint = "tight"
        elif spare <= 20:
            time_fact = f"Tasks require {total_required} min, {available} min available — {spare} min spare. All {scheduled_count} tasks fit."
            time_assessment_hint = "adequate"
        else:
            time_fact = f"Tasks require {total_required} min, {available} min available — {spare} min spare. All {scheduled_count} tasks fit."
            time_assessment_hint = "generous"

        pets_str = ", ".join(
            f"{p.name} ({p.species}, {p.age}y)" for p in owner.pets
        )
        special_needs = "; ".join(context.get("pet_special_needs", [])) or "none"
        age_notes = "; ".join(context.get("age_considerations", [])) or "none"

        prompt = f"""Analyze scheduling constraints for this pet care scenario.

Use ONLY these pre-computed facts — do not recalculate or contradict them:
TIME FACT: {time_fact}

Owner: {owner.name} | Available: {available} min
Pets: {pets_str}
Special needs: {special_needs}
Age notes: {age_notes}

Return ONLY a JSON object:
{{
  "key_constraints": ["<constraint 1>", "<constraint 2>"],
  "risk_factors": ["<risk>"],
  "time_assessment": "{time_assessment_hint}"
}}

- key_constraints: 2-3 most important scheduling facts; the first must accurately reflect the TIME FACT above
- risk_factors: specific welfare or medical risks; [] if none
- time_assessment: must be "{time_assessment_hint}" based on the TIME FACT"""

        raw = self._call_api(prompt)
        return self._parse_json(
            raw,
            fallback={
                "key_constraints": ["Constraint analysis unavailable"],
                "risk_factors": [],
                "time_assessment": "unknown",
            },
        )

    def _step2_evaluate_schedule(
        self, plan: dict, owner, constraint_analysis: dict
    ) -> dict:
        """Evaluate the schedule using constraint analysis from Step 1."""
        scheduled = plan["scheduled_tasks"]
        skipped = plan["skipped_tasks"]

        def fmt(t):
            return f"- {t.description} ({t.priority},{t.duration_minutes}min,{t.task_type})"

        scheduled_str = "\n".join(fmt(t) for t in scheduled) or "None"
        skipped_str = "\n".join(fmt(t) for t in skipped) or "None"
        constraints_str = "\n".join(
            f"  • {c}" for c in constraint_analysis.get("key_constraints", [])
        )
        risks_str = (
            "\n".join(f"  • {r}" for r in constraint_analysis.get("risk_factors", []))
            or "  None identified"
        )

        few_shot_section = FEW_SHOT_EXAMPLES if self.use_few_shot else ""

        prompt = f"""Evaluate this pet care daily schedule using the constraint analysis below.

STEP 1 FINDINGS:
Constraints:
{constraints_str}
Risks:
{risks_str}
Time budget: {constraint_analysis.get("time_assessment", "unknown")}

SCHEDULE ({plan["total_time_minutes"]} / {owner.available_time_minutes} min used):
{scheduled_str}

SKIPPED (did not fit):
{skipped_str}
{few_shot_section}
Return ONLY a JSON object:
{{
  "quality_score": <integer 0-100>,
  "confidence": "<high | medium | low>",
  "reasoning_steps": ["<step 1>", "<step 2>", "<step 3>"],
  "issues_found": ["<issue>"],
  "recommendations": ["<recommendation>"]
}}

- reasoning_steps: exactly 3 — one on constraints, one on task coverage, one on welfare
- issues_found: [] if none; prefix CRITICAL for medical/welfare failures
- recommendations: 1-3 specific, actionable suggestions; [] if schedule is strong"""

        raw = self._call_api(prompt)
        return self._parse_json(
            raw,
            fallback={
                "quality_score": 75,
                "confidence": "low",
                "reasoning_steps": ["Evaluation completed with limited data"],
                "issues_found": [],
                "recommendations": [],
            },
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _call_api(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            max_tokens=600,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content

    def _parse_json(self, text: str, fallback: dict) -> dict:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("JSON parse failed: %s — using fallback", e)
            return fallback

    def _merge(
        self, base_plan: dict, constraint_analysis: dict, evaluation: dict
    ) -> dict:
        enhanced = base_plan.copy()
        enhanced.update(
            {
                # Step 1 output — stored for UI display and testing
                "ai_constraint_analysis": constraint_analysis,
                # Step 2 output
                "ai_quality_score": int(evaluation.get("quality_score", 75)),
                "ai_confidence": str(evaluation.get("confidence", "medium")),
                "ai_reasoning_steps": list(evaluation.get("reasoning_steps", [])),
                "ai_issues_found": list(evaluation.get("issues_found", [])),
                "ai_recommendations": list(evaluation.get("recommendations", [])),
                "ai_enhanced": True,
                "ai_few_shot": self.use_few_shot,
            }
        )
        return enhanced

"""
PawPal+ Evaluation Script — Test Harness                              (stretch goal)

Runs the system against six predefined scenarios and prints a structured report:
  - Part 1: Rule-based correctness (no API calls — fast)
  - Part 2: AI evaluation quality (live Groq calls)
  - Part 3: Few-shot specialization comparison (baseline vs. few-shot)

Usage:
    python reliability.py
    python reliability.py --no-ai      # skip Parts 2 & 3 (offline mode)

Full run logs are appended to pawpal_reliability.log.
"""

import argparse
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from pawpal_system import Owner, Pet, Task, Scheduler

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    handlers=[logging.FileHandler("pawpal_reliability.log")],
)
logger = logging.getLogger("PawPal.Eval")

# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class ScenarioResult:
    name: str
    passed: bool
    time_ok: bool
    count_ok: bool
    scheduled: int
    total_time: int
    available_time: int
    elapsed_ms: float
    ai_score: Optional[int] = None
    ai_confidence: Optional[str] = None
    ai_enhanced: bool = False
    ai_issues: list = field(default_factory=list)
    ai_recommendations: list = field(default_factory=list)
    constraint_analysis: dict = field(default_factory=dict)
    error: Optional[str] = None


# ── Predefined scenarios ──────────────────────────────────────────────────────

def _scenario_ideal():
    """All tasks fit; mixed priorities; good time utilization."""
    owner = Owner("Alex", 90)
    pet = Pet("Max", "dog", 3)
    pet.add_task(Task("Walk Max",    30, "daily", priority="high",   task_type="walk"))
    pet.add_task(Task("Feed Max",    15, "daily", priority="high",   task_type="feeding"))
    pet.add_task(Task("Playtime",    20, "daily", priority="medium", task_type="enrichment"))
    owner.add_pet(pet)
    return owner, {"expect_scheduled": 3, "expect_max_time": 90}


def _scenario_time_constrained():
    """Tasks total more than the budget — one must be skipped."""
    owner = Owner("Jordan", 30)
    pet = Pet("Luna", "dog", 2)
    pet.add_task(Task("Walk Luna", 45, "daily", priority="high", task_type="walk"))
    pet.add_task(Task("Feed Luna", 15, "daily", priority="high", task_type="feeding"))
    owner.add_pet(pet)
    return owner, {"expect_scheduled": 1, "expect_max_time": 30}


def _scenario_medical():
    """Pet with special needs — medication is a high-priority task."""
    owner = Owner("Sam", 60)
    pet = Pet("Buddy", "dog", 8, special_needs="Diabetic — requires insulin twice daily")
    pet.add_task(Task("Give insulin",  10, "daily", priority="high",   task_type="meds"))
    pet.add_task(Task("Feed Buddy",    15, "daily", priority="high",   task_type="feeding"))
    pet.add_task(Task("Gentle walk",   20, "daily", priority="medium", task_type="walk"))
    owner.add_pet(pet)
    return owner, {"expect_scheduled": 3, "expect_max_time": 60}


def _scenario_multiple_pets():
    """Two pets with distinct care needs, all tasks fit."""
    owner = Owner("Casey", 90)
    dog = Pet("Rex", "dog", 4)
    dog.add_task(Task("Walk Rex",    30, "daily", priority="high",   task_type="walk"))
    dog.add_task(Task("Feed Rex",    15, "daily", priority="high",   task_type="feeding"))
    cat = Pet("Mochi", "cat", 2)
    cat.add_task(Task("Feed Mochi",   10, "daily", priority="high",   task_type="feeding"))
    cat.add_task(Task("Clean litter", 15, "daily", priority="medium", task_type="other"))
    owner.add_pet(dog)
    owner.add_pet(cat)
    return owner, {"expect_scheduled": 4, "expect_max_time": 90}


def _scenario_senior_pet():
    """Senior dog (age > 10) with age-appropriate tasks."""
    owner = Owner("Pat", 60)
    pet = Pet("Gracie", "dog", 12)
    pet.add_task(Task("Gentle walk",   20, "daily", priority="high",   task_type="walk"))
    pet.add_task(Task("Feed Gracie",   15, "daily", priority="high",   task_type="feeding"))
    pet.add_task(Task("Joint massage", 15, "daily", priority="medium", task_type="grooming"))
    owner.add_pet(pet)
    return owner, {"expect_scheduled": 3, "expect_max_time": 60}


def _scenario_zero_time():
    """Edge case — owner has zero time; all tasks must be skipped."""
    owner = Owner("Ghost", 0)
    pet = Pet("Shadow", "cat", 3)
    pet.add_task(Task("Feed Shadow", 10, "daily", priority="high", task_type="feeding"))
    owner.add_pet(pet)
    return owner, {"expect_scheduled": 0, "expect_max_time": 0}


SCENARIOS = [
    ("Ideal schedule",       _scenario_ideal),
    ("Time-constrained",     _scenario_time_constrained),
    ("Medical needs",        _scenario_medical),
    ("Multiple pets",        _scenario_multiple_pets),
    ("Senior pet",           _scenario_senior_pet),
    ("Zero time (edge case)",_scenario_zero_time),
]


# ── Correctness evaluation (no AI) ────────────────────────────────────────────

def _run_correctness(name: str, scenario_fn) -> ScenarioResult:
    owner, expectations = scenario_fn()
    t0 = time.time()

    try:
        scheduler = Scheduler(owner)
        plan = scheduler.generate_base_plan()
        elapsed = (time.time() - t0) * 1000

        scheduled_count = len(plan["scheduled_tasks"])
        total_time = plan["total_time_minutes"]
        avail = owner.available_time_minutes

        time_ok = total_time <= avail
        count_ok = scheduled_count == expectations.get("expect_scheduled", scheduled_count)

        logger.info("Correctness [%s]: scheduled=%d time=%d/%d ok=%s",
                    name, scheduled_count, total_time, avail, time_ok and count_ok)

        return ScenarioResult(
            name=name, passed=time_ok and count_ok,
            time_ok=time_ok, count_ok=count_ok,
            scheduled=scheduled_count, total_time=total_time,
            available_time=avail, elapsed_ms=elapsed,
        )
    except Exception as e:
        logger.error("Correctness [%s] raised: %s", name, e)
        return ScenarioResult(
            name=name, passed=False, time_ok=False, count_ok=False,
            scheduled=0, total_time=0, available_time=0,
            elapsed_ms=(time.time() - t0) * 1000, error=str(e),
        )


# ── AI evaluation (live API) ──────────────────────────────────────────────────

def _run_ai_evaluation(name: str, scenario_fn) -> ScenarioResult:
    from ai_agent import AIAgent
    owner, expectations = scenario_fn()
    t0 = time.time()

    try:
        scheduler = Scheduler(owner)
        base_plan = scheduler.generate_base_plan()
        context = scheduler._get_pet_care_context()

        agent = AIAgent(use_few_shot=True)
        plan = agent.evaluate_and_enhance_schedule(base_plan, owner, context)
        elapsed = (time.time() - t0) * 1000

        scheduled_count = len(plan["scheduled_tasks"])
        total_time = plan["total_time_minutes"]
        avail = owner.available_time_minutes
        time_ok = total_time <= avail
        count_ok = scheduled_count == expectations.get("expect_scheduled", scheduled_count)

        logger.info("AI eval [%s]: score=%s confidence=%s",
                    name, plan.get("ai_quality_score"), plan.get("ai_confidence"))

        return ScenarioResult(
            name=name, passed=time_ok and count_ok,
            time_ok=time_ok, count_ok=count_ok,
            scheduled=scheduled_count, total_time=total_time,
            available_time=avail, elapsed_ms=elapsed,
            ai_score=plan.get("ai_quality_score"),
            ai_confidence=plan.get("ai_confidence"),
            ai_enhanced=plan.get("ai_enhanced", False),
            ai_issues=plan.get("ai_issues_found", []),
            ai_recommendations=plan.get("ai_recommendations", []),
            constraint_analysis=plan.get("ai_constraint_analysis", {}),
        )
    except Exception as e:
        logger.error("AI eval [%s] raised: %s", name, e)
        return ScenarioResult(
            name=name, passed=False, time_ok=False, count_ok=False,
            scheduled=0, total_time=0, available_time=0,
            elapsed_ms=(time.time() - t0) * 1000, error=str(e),
        )


# ── Few-shot comparison (fine-tuning stretch goal) ────────────────────────────

def _run_fewshot_comparison(name: str, scenario_fn) -> dict:
    """Run the same scenario with and without few-shot examples and compare."""
    from ai_agent import AIAgent
    owner, _ = scenario_fn()
    scheduler = Scheduler(owner)
    base_plan = scheduler.generate_base_plan()
    context = scheduler._get_pet_care_context()

    results = {}
    for i, (label, use_fs) in enumerate([("baseline (no few-shot)", False), ("few-shot", True)]):
        if i > 0:
            time.sleep(4)  # avoid TPM rate limit between the two calls
        t0 = time.time()
        try:
            agent = AIAgent(use_few_shot=use_fs)
            plan = agent.evaluate_and_enhance_schedule(
                base_plan.copy(), owner, context
            )
            results[label] = {
                "score": plan.get("ai_quality_score"),
                "confidence": plan.get("ai_confidence"),
                "issues": plan.get("ai_issues_found", []),
                "recommendations": plan.get("ai_recommendations", []),
                "elapsed_ms": (time.time() - t0) * 1000,
            }
            logger.info("Few-shot [%s / %s]: score=%s issues=%d",
                        name, label, results[label]["score"], len(results[label]["issues"]))
        except Exception as e:
            results[label] = {"error": str(e)}
            logger.error("Few-shot [%s / %s] raised: %s", name, label, e)

    return {"scenario": name, "results": results}


# ── Report printing ───────────────────────────────────────────────────────────

W = 66

def _rule(char="="): print(char * W)
def _header(title): print(f"\n{'=' * W}\n {title}\n{'=' * W}")
def _section(title): print(f"\n {title}\n" + "-" * W)


def _print_correctness(results: list[ScenarioResult]):
    _section("PART 1: SCHEDULING CORRECTNESS  (rule-based, no API calls)")
    print(f"  {'Scenario':<28} {'Time':>6} {'Tasks':>6} {'ms':>6}  {'Result'}")
    print("  " + "-" * 58)
    for r in results:
        symbol = "PASS" if r.passed else "FAIL"
        tok = "OK" if r.time_ok else "NO"
        cok = "OK" if r.count_ok else "NO"
        err = f"  ERROR: {r.error}" if r.error else ""
        print(f"  {r.name:<28} {tok:>6} {cok:>6} {r.elapsed_ms:>5.0f}ms  {symbol}{err}")
    passed = sum(1 for r in results if r.passed)
    print(f"\n  Result: {passed}/{len(results)} scenarios passed")


def _print_ai_quality(results: list[ScenarioResult]):
    _section("PART 2: AI EVALUATION QUALITY  (live Groq API, few-shot enabled)")
    print(f"  {'Scenario':<28} {'Score':>6} {'Conf':>8} {'Issues':>7} {'ms':>6}")
    print("  " + "-" * 60)
    scores = []
    for r in results:
        if r.error:
            print(f"  {r.name:<28}  ERROR: {r.error}")
            continue
        score_str = str(r.ai_score) if r.ai_score is not None else "N/A"
        conf_str = r.ai_confidence or "N/A"
        print(f"  {r.name:<28} {score_str:>6} {conf_str:>8} {len(r.ai_issues):>7} {r.elapsed_ms:>5.0f}ms")
        if r.ai_issues:
            for issue in r.ai_issues[:2]:
                print(f"    (!) {issue[:60]}")
        if r.ai_score is not None:
            scores.append(r.ai_score)

    if scores:
        print(f"\n  Average AI quality score : {sum(scores)/len(scores):.1f}")
        print(f"  Score range              : {min(scores)} – {max(scores)}")

    enhanced = sum(1 for r in results if r.ai_enhanced)
    print(f"  AI-enhanced plans        : {enhanced}/{len(results)}")

    print(f"\n  Step 1 constraint analysis sample ({results[0].name}):")
    ca = results[0].constraint_analysis
    for c in ca.get("key_constraints", [])[:2]:
        print(f"    • {c}")
    print(f"    Time assessment: {ca.get('time_assessment', 'N/A')}")


def _print_fewshot(comparisons: list[dict]):
    _section("PART 3: FEW-SHOT SPECIALIZATION COMPARISON")
    for comp in comparisons:
        print(f"\n  Scenario: {comp['scenario']}")
        res = comp["results"]
        for label in ["baseline (no few-shot)", "few-shot"]:
            r = res.get(label, {})
            if "error" in r:
                print(f"    [{label}]  ERROR: {r['error']}")
                continue
            print(f"    [{label}]")
            print(f"      Score      : {r['score']}  |  Confidence: {r['confidence']}")
            print(f"      Issues     : {len(r['issues'])}")
            for i in r["issues"][:2]:
                print(f"        (!) {i[:60]}")
            print(f"      Recs       : {len(r['recommendations'])}")
            for rec in r["recommendations"][:1]:
                print(f"        -> {rec[:65]}")

        b = res.get("baseline (no few-shot)", {})
        f = res.get("few-shot", {})
        if b.get("score") is not None and f.get("score") is not None:
            delta = f["score"] - b["score"]
            issue_delta = len(f.get("issues", [])) - len(b.get("issues", []))
            sign = "+" if delta >= 0 else ""
            print(f"\n    Score delta  : {sign}{delta} points with few-shot")
            print(f"    Issue delta  : {'+' if issue_delta >= 0 else ''}{issue_delta} issues identified")


def _print_summary(correctness: list, ai_evals: list, timestamp: str):
    _rule("=")
    corr_pass = sum(1 for r in correctness if r.passed)
    ai_scores = [r.ai_score for r in ai_evals if r.ai_score is not None]
    avg = f"{sum(ai_scores)/len(ai_scores):.1f}" if ai_scores else "N/A"
    print(f" SUMMARY  |  {timestamp}")
    print(f" Correctness : {corr_pass}/{len(correctness)} passed")
    print(f" Avg AI score: {avg}  |  Full log: pawpal_reliability.log")
    _rule("=")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="PawPal+ Evaluation Script")
    parser.add_argument("--no-ai", action="store_true",
                        help="Skip Parts 2 & 3 (offline/fast mode)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _header(f"PAWPAL+ EVALUATION REPORT  |  {timestamp}")
    logger.info("=== Evaluation run started at %s ===", timestamp)

    # Part 1 — Rule-based correctness (always runs, no API)
    print("\n Running Part 1 (rule-based, no API)...")
    correctness_results = [_run_correctness(name, fn) for name, fn in SCENARIOS]
    _print_correctness(correctness_results)

    ai_results = []
    fewshot_results = []

    if not args.no_ai:
        # Part 2 — AI quality (4 of 6 scenarios — skip edge cases for speed)
        ai_scenarios = SCENARIOS[:4]
        print(f"\n Running Part 2 (AI evaluation, {len(ai_scenarios)} scenarios)...")
        ai_results = []
        for i, (name, fn) in enumerate(ai_scenarios):
            if i > 0:
                time.sleep(4)  # avoid Groq free-tier TPM rate limit
            ai_results.append(_run_ai_evaluation(name, fn))
        _print_ai_quality(ai_results)

        # Part 3 — Few-shot comparison (2 scenarios: ideal + medical)
        compare_scenarios = [SCENARIOS[0], SCENARIOS[2]]  # ideal, medical
        print(f"\n Running Part 3 (few-shot comparison, {len(compare_scenarios)} scenarios)...")
        fewshot_results = []
        for i, (name, fn) in enumerate(compare_scenarios):
            if i > 0:
                time.sleep(4)
            fewshot_results.append(_run_fewshot_comparison(name, fn))
        _print_fewshot(fewshot_results)
    else:
        print("\n [--no-ai] Skipping Parts 2 & 3.")

    _print_summary(correctness_results, ai_results, timestamp)
    logger.info("=== Evaluation run complete ===")


if __name__ == "__main__":
    main()

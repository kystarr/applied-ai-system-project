"""
AI-Enhanced Scheduling Tests for PawPal+

Tests the reliability and correctness of the AI-enhanced scheduling system.
"""

import sys
import os
import pytest
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pawpal_system import Pet, Task, Owner, Scheduler

# Try to import AI components (tests will be skipped if not available)
try:
    from ai_agent import AIAgent
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

class TestReliabilityHarness:
    """Test harness for evaluating scheduling correctness and reliability."""

    @staticmethod
    def evaluate_schedule_correctness(plan: dict, owner: Owner) -> dict:
        """
        Evaluate the correctness of a generated schedule.

        Returns dict with metrics:
        - time_constraint_satisfied: bool
        - priority_coverage: float (0-1)
        - no_conflicts: bool
        - all_tasks_accounted_for: bool
        - overall_score: float (0-1)
        """
        scheduled_tasks = plan.get('scheduled_tasks', [])
        skipped_tasks = plan.get('skipped_tasks', [])
        total_time = plan.get('total_time_minutes', 0)
        available_time = owner.available_time_minutes

        # 1. Time constraint check
        time_constraint_satisfied = total_time <= available_time

        # 2. Priority coverage (fraction of high-priority tasks scheduled)
        all_tasks = owner.get_all_incomplete_tasks()
        high_priority_tasks = [t for t in all_tasks if t.priority == 'high']
        scheduled_high_priority = [t for t in scheduled_tasks if t.priority == 'high']

        if high_priority_tasks:
            priority_coverage = len(scheduled_high_priority) / len(high_priority_tasks)
        else:
            priority_coverage = 1.0  # No high priority tasks to cover

        # 3. No scheduling conflicts (for tasks with scheduled times)
        scheduled_with_times = [t for t in scheduled_tasks if t.scheduled_start_time]
        conflicts = []
        for i, task1 in enumerate(scheduled_with_times):
            for task2 in scheduled_with_times[i+1:]:
                if task1.conflicts_with(task2):
                    conflicts.append((task1, task2))

        no_conflicts = len(conflicts) == 0

        # 4. All tasks accounted for
        all_accounted_task_keys = set((t.description, t.duration_minutes) for t in scheduled_tasks + skipped_tasks)
        expected_task_keys = set((t.description, t.duration_minutes) for t in all_tasks)
        all_tasks_accounted_for = all_accounted_task_keys == expected_task_keys

        # 5. Overall score (weighted average)
        weights = {
            'time_constraint': 0.4,
            'priority_coverage': 0.3,
            'no_conflicts': 0.2,
            'task_accounting': 0.1
        }

        overall_score = (
            weights['time_constraint'] * (1.0 if time_constraint_satisfied else 0.0) +
            weights['priority_coverage'] * priority_coverage +
            weights['no_conflicts'] * (1.0 if no_conflicts else 0.0) +
            weights['task_accounting'] * (1.0 if all_tasks_accounted_for else 0.0)
        )

        return {
            'time_constraint_satisfied': time_constraint_satisfied,
            'priority_coverage': priority_coverage,
            'no_conflicts': no_conflicts,
            'all_tasks_accounted_for': all_tasks_accounted_for,
            'overall_score': overall_score,
            'conflicts_found': conflicts,
            'scheduled_high_priority': len(scheduled_high_priority),
            'total_high_priority': len(high_priority_tasks)
        }

    @staticmethod
    def run_scenario(name: str, owner: Owner, expected_min_score: float = 0.8) -> dict:
        """
        Test a specific scheduling scenario.

        Args:
            name: Test scenario name
            owner: Owner with pets and tasks
            expected_min_score: Minimum acceptable correctness score (0-1)

        Returns:
            Test results dictionary
        """
        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        correctness = TestReliabilityHarness.evaluate_schedule_correctness(plan, owner)

        passed = correctness['overall_score'] >= expected_min_score

        return {
            'scenario': name,
            'passed': passed,
            'correctness_score': correctness['overall_score'],
            'expected_min': expected_min_score,
            'details': correctness,
            'plan_summary': {
                'scheduled_tasks': len(plan['scheduled_tasks']),
                'total_time': plan['total_time_minutes'],
                'available_time': owner.available_time_minutes,
                'skipped_tasks': len(plan['skipped_tasks'])
            }
        }


@pytest.mark.skipif(not AI_AVAILABLE, reason="AI components not available")
class TestAIScheduling:
    """Tests for AI-enhanced scheduling functionality."""

    def test_ai_agent_initialization(self):
        """Test that AI agent can be initialized (requires API key)."""
        # This will fail if OPENAI_API_KEY is not set, which is expected
        try:
            agent = AIAgent()
            assert agent is not None
            assert hasattr(agent, 'evaluate_and_enhance_schedule')
        except ValueError as e:
            if "GROQ_API_KEY" in str(e):
                pytest.skip("OpenAI API key not configured")
            else:
                raise

    def test_ai_enhanced_plan_has_evaluation_fields(self):
        """Test that AI-enhanced plans include evaluation metadata."""
        # Create test data
        owner = Owner("Test Owner", 120)
        pet = Pet("Test Pet", "dog", 3)
        pet.add_task(Task("Feed dog", 15, "daily", priority="high", task_type="feeding"))
        pet.add_task(Task("Walk dog", 30, "daily", priority="high", task_type="walk"))
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        # Check for AI evaluation fields
        ai_fields = ['ai_quality_score', 'ai_issues_found', 'ai_recommendations',
                    'ai_confidence', 'ai_reasoning_steps', 'ai_enhanced']

        for field in ai_fields:
            assert field in plan, f"AI field '{field}' missing from plan"

        assert isinstance(plan['ai_quality_score'], int)
        assert 0 <= plan['ai_quality_score'] <= 100


class TestSchedulingCorrectness:
    """Tests for basic scheduling correctness (works with or without AI)."""

    def test_single_pet_single_task(self):
        """Test scheduling a single task for one pet."""
        owner = Owner("Alice", 60)
        pet = Pet("Fluffy", "cat", 2)
        task = Task("Feed Fluffy", 10, "daily", priority="high", task_type="feeding")
        pet.add_task(task)
        owner.add_pet(pet)

        result = TestReliabilityHarness.run_scenario("Single task", owner)

        assert result['passed'], f"Single task scenario failed: {result['details']}"
        assert result['plan_summary']['scheduled_tasks'] == 1
        assert result['plan_summary']['total_time'] == 10

    def test_time_constraint_enforcement(self):
        """Test that schedules don't exceed available time."""
        owner = Owner("Bob", 30)  # Only 30 minutes available
        pet = Pet("Max", "dog", 5)
        pet.add_task(Task("Walk Max", 45, "daily", priority="high", task_type="walk"))  # 45 min task
        owner.add_pet(pet)

        result = TestReliabilityHarness.run_scenario("Time constraint", owner)

        # Should either schedule the task (if AI decides to) or skip it
        assert result['details']['time_constraint_satisfied'], "Schedule exceeded time budget"

    def test_priority_preference(self):
        """Test that high-priority tasks are preferred over low-priority ones."""
        owner = Owner("Carol", 60)
        pet = Pet("Bella", "dog", 3)

        # Add high priority task that fits
        high_task = Task("Give medication", 10, "daily", priority="high", task_type="meds")
        pet.add_task(high_task)

        # Add low priority tasks that would fill the time
        for i in range(5):
            low_task = Task(f"Groom Bella {i}", 12, "weekly", priority="low", task_type="grooming")
            pet.add_task(low_task)

        owner.add_pet(pet)

        result = TestReliabilityHarness.run_scenario("Priority preference", owner)

        assert result['passed'], f"Priority test failed: {result['details']}"
        # High priority task should be scheduled
        assert result['details']['scheduled_high_priority'] >= 1, "High priority task not scheduled"

    def test_multiple_pets_scheduling(self):
        """Test scheduling across multiple pets."""
        owner = Owner("David", 120)
        pets = []

        # Pet 1: Dog with feeding and walking
        dog = Pet("Rex", "dog", 4)
        dog.add_task(Task("Feed Rex", 15, "daily", priority="high", task_type="feeding"))
        dog.add_task(Task("Walk Rex", 30, "daily", priority="high", task_type="walk"))
        pets.append(dog)

        # Pet 2: Cat with feeding and litter
        cat = Pet("Whiskers", "cat", 2)
        cat.add_task(Task("Feed Whiskers", 5, "daily", priority="high", task_type="feeding"))
        cat.add_task(Task("Clean litter", 15, "daily", priority="medium", task_type="other"))
        pets.append(cat)

        for pet in pets:
            owner.add_pet(pet)

        result = TestReliabilityHarness.run_scenario("Multiple pets", owner)

        assert result['passed'], f"Multiple pets test failed: {result['details']}"
        assert result['plan_summary']['scheduled_tasks'] >= 2, "Not enough tasks scheduled"

    def test_conflict_detection(self):
        """Test detection of scheduling conflicts."""
        owner = Owner("Eve", 120)
        pet = Pet("Shadow", "cat", 1)

        # Create tasks with overlapping scheduled times
        morning = datetime.now().replace(hour=8, minute=0)
        task1 = Task("Feed Shadow", 15, "daily", priority="high", task_type="feeding")
        task1.scheduled_start_time = morning

        task2 = Task("Play with Shadow", 20, "daily", priority="medium", task_type="enrichment")
        task2.scheduled_start_time = morning + timedelta(minutes=10)  # Overlaps with feeding

        pet.add_task(task1)
        pet.add_task(task2)
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        # Check that conflicts are detected
        conflicts = scheduler.detect_scheduling_conflicts([task1, task2])
        assert len(conflicts) > 0, "Overlapping tasks should be detected as conflicts"


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    def test_no_pets(self):
        """Test scheduling with no pets."""
        owner = Owner("Ghost", 60)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        assert plan['scheduled_tasks'] == []
        assert plan['total_time_minutes'] == 0
        assert plan['pets_count'] == 0

    def test_no_tasks(self):
        """Test scheduling when pets have no incomplete tasks."""
        owner = Owner("Lazy", 60)
        pet = Pet("Coma", "sloth", 10)
        # Don't add any tasks
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        assert plan['scheduled_tasks'] == []
        assert plan['skipped_tasks'] == []

    def test_zero_available_time(self):
        """Test scheduling with zero available time."""
        owner = Owner("Busy", 0)
        pet = Pet("Patient", "dog", 5)
        pet.add_task(Task("Feed Patient", 10, "daily", priority="high", task_type="feeding"))
        owner.add_pet(pet)

        scheduler = Scheduler(owner)
        plan = scheduler.generate_plan()

        assert plan['scheduled_tasks'] == []
        assert plan['remaining_time_minutes'] == 0
        assert len(plan['skipped_tasks']) == 1


if __name__ == "__main__":
    # Run basic tests without pytest
    print("Running PawPal+ Reliability Tests...")
    print("=" * 50)

    # Test 1: Single pet scenario
    print("\n1. Testing single pet scenario...")
    owner1 = Owner("Test Owner", 60)
    pet1 = Pet("Test Pet", "dog", 3)
    pet1.add_task(Task("Feed dog", 15, "daily", priority="high", task_type="feeding"))
    pet1.add_task(Task("Walk dog", 30, "daily", priority="high", task_type="walk"))
    owner1.add_pet(pet1)

    result1 = TestReliabilityHarness.run_scenario("Single pet with 2 tasks", owner1)
    print(f"   Result: {'PASS' if result1['passed'] else 'FAIL'}")
    print(f"   Correctness Score: {result1['correctness_score']:.2f}")
    print(f"   Scheduled: {result1['plan_summary']['scheduled_tasks']} tasks")

    # Test 2: Time constraint scenario
    print("\n2. Testing time constraint enforcement...")
    owner2 = Owner("Time Test", 20)
    pet2 = Pet("Time Pet", "cat", 2)
    pet2.add_task(Task("Quick feed", 15, "daily", priority="high", task_type="feeding"))
    pet2.add_task(Task("Long play", 25, "daily", priority="medium", task_type="enrichment"))
    owner2.add_pet(pet2)

    result2 = TestReliabilityHarness.run_scenario("Time constraint", owner2)
    print(f"   Result: {'PASS' if result2['passed'] else 'FAIL'}")
    print(f"   Correctness Score: {result2['correctness_score']:.2f}")
    print(f"   Time constraint satisfied: {result2['details']['time_constraint_satisfied']}")

    print("\n" + "=" * 50)
    print("Reliability testing complete!")
    print("Run 'pytest tests/test_ai_scheduling.py' for full test suite.")
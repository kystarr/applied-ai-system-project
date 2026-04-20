"""
PawPal+ System - Backend Logic Layer

This module contains all the core classes for the pet care scheduling system.

Design Note - Class Relationships:
    - Task: Represents a single activity with description, time, frequency, and completion status
    - Pet: Stores pet details and manages its own list of tasks
    - Owner: Manages multiple pets and provides access to all their tasks
    - Scheduler: The "Brain" that retrieves, organizes, and manages tasks across all pets

    This design uses composition: Pets contain Tasks, Owner contains Pets, and
    Scheduler operates on an Owner to generate optimized daily care plans.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

# AI Agent import (optional - will gracefully degrade if not available)
try:
    from ai_agent import AIAgent
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    print("Warning: AI agent not available. Running in rule-based mode only.")


class Pet:
    """Represents a pet with basic information and manages its own tasks."""

    def __init__(self, name: str, species: str, age: int, special_needs: Optional[str] = None):
        """Initialize a Pet with name, species, age, and optional special needs."""
        if not name or not name.strip():
            raise ValueError("Pet name cannot be empty")
        if age < 0:
            raise ValueError(f"Pet age cannot be negative: {age}")

        self.name = name
        self.species = species
        self.age = age
        self.special_needs = special_needs
        self.tasks: list[Task] = []

    def add_task(self, task: Task):
        """Add a task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task: Task):
        """Remove a task from this pet's task list."""
        if task not in self.tasks:
            raise ValueError(f"Task '{task.description}' not found in {self.name}'s task list")
        self.tasks.remove(task)

    def get_all_tasks(self) -> list[Task]:
        """Returns all tasks for this pet (completed and incomplete)."""
        return self.tasks.copy()

    def get_incomplete_tasks(self) -> list[Task]:
        """Returns only incomplete tasks for this pet."""
        return [task for task in self.tasks if not task.completed]

    def get_completed_tasks(self) -> list[Task]:
        """Returns only completed tasks for this pet."""
        return [task for task in self.tasks if task.completed]

    def complete_recurring_task(self, task: Task) -> Optional[Task]:
        """Complete a task and automatically create next instance if it's recurring.

        Args:
            task: The task to complete

        Returns:
            The newly created task instance if the task is recurring (daily/weekly),
            None if the task is as-needed or not found

        Logic:
            - Daily tasks: Create new instance with due_date = today + 1 day
            - Weekly tasks: Create new instance with due_date = today + 7 days
            - As-needed tasks: Just mark complete, no new instance
        """
        if task not in self.tasks:
            raise ValueError(f"Task '{task.description}' not found in {self.name}'s task list")

        # Mark the original task as complete
        task.mark_complete()

        # Determine recurrence interval
        recurrence_days = {
            "daily": 1,
            "weekly": 7
        }.get(task.frequency)

        # Create new instance for recurring tasks
        if recurrence_days:
            next_due = datetime.now() + timedelta(days=recurrence_days)
            new_task = Task(
                description=task.description,
                duration_minutes=task.duration_minutes,
                frequency=task.frequency,
                priority=task.priority,
                task_type=task.task_type,
                due_date=next_due
            )
            self.add_task(new_task)
            return new_task

        # As-needed tasks don't recur automatically
        return None

    def get_info(self) -> str:
        """Returns formatted pet information including task summary."""
        info = f"Pet: {self.name}\n"
        info += f"Species: {self.species}\n"
        info += f"Age: {self.age} years"
        if self.special_needs:
            info += f"\nSpecial needs: {self.special_needs}"

        task_count = len(self.tasks)
        incomplete_count = len(self.get_incomplete_tasks())
        info += f"\nTasks: {task_count} total ({incomplete_count} incomplete)"

        return info

    def __str__(self) -> str:
        """Returns a simple one-line description of the pet."""
        return f"{self.name} ({self.species}, {self.age}y, {len(self.tasks)} tasks)"


@dataclass
class Task:
    """Represents a single pet care activity with completion tracking."""

    description: str
    duration_minutes: int
    frequency: str  # "daily", "weekly", "as-needed"
    completed: bool = False
    priority: str = "medium"  # "low", "medium", or "high"
    task_type: str = "other"  # "walk", "feeding", "meds", "grooming", "enrichment", "other"
    last_completed: Optional[datetime] = None  # Tracks when task was last done
    due_date: Optional[datetime] = None  # When this task is due (for recurring tasks)
    scheduled_start_time: Optional[datetime] = None  # When this task is scheduled to start

    VALID_PRIORITIES = {"low", "medium", "high"}
    VALID_TASK_TYPES = {"walk", "feeding", "meds", "grooming", "enrichment", "other"}
    VALID_FREQUENCIES = {"daily", "weekly", "as-needed"}
    PRIORITY_SCORES = {"high": 3, "medium": 2, "low": 1}

    def __post_init__(self):
        """Validates task attributes after initialization."""
        if not self.description or not self.description.strip():
            raise ValueError("Task description cannot be empty")
        if self.duration_minutes <= 0:
            raise ValueError(f"Task duration must be positive: {self.duration_minutes}")
        if self.priority not in self.VALID_PRIORITIES:
            raise ValueError(f"Invalid priority '{self.priority}'. Must be one of: {self.VALID_PRIORITIES}")
        if self.task_type not in self.VALID_TASK_TYPES:
            raise ValueError(f"Invalid task_type '{self.task_type}'. Must be one of: {self.VALID_TASK_TYPES}")
        if self.frequency not in self.VALID_FREQUENCIES:
            raise ValueError(f"Invalid frequency '{self.frequency}'. Must be one of: {self.VALID_FREQUENCIES}")

    def mark_complete(self):
        """Marks this task as completed and records completion time."""
        self.completed = True
        self.last_completed = datetime.now()

    def mark_incomplete(self):
        """Marks this task as incomplete."""
        self.completed = False

    def is_due(self, reference_date: Optional[datetime] = None) -> bool:
        """Determines if this task is due based on its frequency and last completion.

        Args:
            reference_date: Date to check against (defaults to today)

        Returns:
            True if task should be scheduled, False otherwise

        Logic:
            - daily: Due if never completed OR last completed before today
            - weekly: Due if never completed OR last completed 7+ days ago
            - as-needed: Only due if never completed (manual tasks)
        """
        if reference_date is None:
            reference_date = datetime.now()

        # If never completed, all tasks are due except as-needed
        if self.last_completed is None:
            return self.frequency != "as-needed"

        # Calculate days since last completion
        days_since = (reference_date - self.last_completed).days

        if self.frequency == "daily":
            return days_since >= 1
        elif self.frequency == "weekly":
            return days_since >= 7
        else:  # as-needed
            return False  # Only done manually

    def get_priority_score(self) -> int:
        """Converts priority string to numeric value for sorting (3=high, 2=medium, 1=low)."""
        return self.PRIORITY_SCORES[self.priority]

    def get_end_time(self) -> Optional[datetime]:
        """Calculate when this task ends based on start time and duration."""
        if self.scheduled_start_time is None:
            return None
        return self.scheduled_start_time + timedelta(minutes=self.duration_minutes)

    def conflicts_with(self, other: 'Task') -> bool:
        """Check if this task's time slot overlaps with another task.

        Returns:
            True if tasks have overlapping scheduled times, False otherwise
        """
        # Can't have conflict if either task doesn't have a scheduled time
        if self.scheduled_start_time is None or other.scheduled_start_time is None:
            return False

        # Calculate end times
        self_end = self.get_end_time()
        other_end = other.get_end_time()

        # Check for overlap: tasks conflict if one starts before the other ends
        return (self.scheduled_start_time < other_end and
                other.scheduled_start_time < self_end)

    def __str__(self) -> str:
        """Returns a formatted task description with completion status."""
        status = "[X]" if self.completed else "[ ]"
        return f"{status} {self.description} ({self.duration_minutes}min, {self.frequency}, {self.priority} priority)"


class Owner:
    """Represents the pet owner who manages multiple pets.

    The Owner class manages a collection of pets and provides access to all their tasks.
    Time management is handled by the Scheduler class.
    """

    def __init__(self, name: str, available_time_minutes: int):
        """Initialize an Owner with name and daily time budget for pet care."""
        if not name or not name.strip():
            raise ValueError("Owner name cannot be empty")
        if available_time_minutes < 0:
            raise ValueError(f"Available time cannot be negative: {available_time_minutes}")

        self.name = name
        self.available_time_minutes = available_time_minutes
        self.pets: list[Pet] = []

    def add_pet(self, pet: Pet):
        """Adds a pet to this owner's care."""
        self.pets.append(pet)

    def remove_pet(self, pet: Pet):
        """Removes a pet from this owner's care."""
        if pet not in self.pets:
            raise ValueError(f"Pet '{pet.name}' not found in {self.name}'s pet list")
        self.pets.remove(pet)

    def get_all_pets(self) -> list[Pet]:
        """Returns all pets owned by this owner."""
        return self.pets.copy()

    def get_all_tasks(self) -> list[Task]:
        """Returns all tasks across all pets (combined list)."""
        all_tasks = []
        for pet in self.pets:
            all_tasks.extend(pet.get_all_tasks())
        return all_tasks

    def get_all_incomplete_tasks(self) -> list[Task]:
        """Returns all incomplete tasks across all pets."""
        all_incomplete = []
        for pet in self.pets:
            all_incomplete.extend(pet.get_incomplete_tasks())
        return all_incomplete

    def __str__(self) -> str:
        """Returns a simple one-line description of the owner."""
        return f"{self.name} ({len(self.pets)} pet{'s' if len(self.pets) != 1 else ''}, {self.available_time_minutes} min/day)"

    def save_to_json(self, filename: str = "data.json"):
        """Save owner data (including all pets and tasks) to a JSON file.

        Args:
            filename: Path to the JSON file to write to

        Raises:
            IOError: If the file cannot be written
        """
        try:
            # Build the data structure
            data = {
                "name": self.name,
                "available_time_minutes": self.available_time_minutes,
                "pets": []
            }

            # Serialize each pet and its tasks
            for pet in self.pets:
                pet_data = {
                    "name": pet.name,
                    "species": pet.species,
                    "age": pet.age,
                    "special_needs": pet.special_needs,
                    "tasks": []
                }

                # Serialize each task
                for task in pet.tasks:
                    task_data = {
                        "description": task.description,
                        "duration_minutes": task.duration_minutes,
                        "frequency": task.frequency,
                        "completed": task.completed,
                        "priority": task.priority,
                        "task_type": task.task_type,
                        "last_completed": task.last_completed.isoformat() if task.last_completed else None,
                        "due_date": task.due_date.isoformat() if task.due_date else None,
                        "scheduled_start_time": task.scheduled_start_time.isoformat() if task.scheduled_start_time else None
                    }
                    pet_data["tasks"].append(task_data)

                data["pets"].append(pet_data)

            # Write to file with nice formatting
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)

        except IOError as e:
            raise IOError(f"Failed to save data to {filename}: {e}")

    @classmethod
    def load_from_json(cls, filename: str = "data.json") -> Optional['Owner']:
        """Load owner data (including all pets and tasks) from a JSON file.

        Args:
            filename: Path to the JSON file to read from

        Returns:
            Owner object reconstructed from the file, or None if file doesn't exist

        Raises:
            ValueError: If the JSON is corrupted or missing required fields
        """
        try:
            # Read and parse the JSON file
            with open(filename, 'r') as f:
                data = json.load(f)

            # Reconstruct the Owner object
            owner = cls(
                name=data["name"],
                available_time_minutes=data["available_time_minutes"]
            )

            # Reconstruct each pet and its tasks
            for pet_data in data.get("pets", []):
                pet = Pet(
                    name=pet_data["name"],
                    species=pet_data["species"],
                    age=pet_data["age"],
                    special_needs=pet_data.get("special_needs")
                )

                # Reconstruct each task
                for task_data in pet_data.get("tasks", []):
                    task = Task(
                        description=task_data["description"],
                        duration_minutes=task_data["duration_minutes"],
                        frequency=task_data["frequency"],
                        completed=task_data.get("completed", False),
                        priority=task_data.get("priority", "medium"),
                        task_type=task_data.get("task_type", "other"),
                        last_completed=datetime.fromisoformat(task_data["last_completed"]) if task_data.get("last_completed") else None,
                        due_date=datetime.fromisoformat(task_data["due_date"]) if task_data.get("due_date") else None,
                        scheduled_start_time=datetime.fromisoformat(task_data["scheduled_start_time"]) if task_data.get("scheduled_start_time") else None
                    )
                    pet.add_task(task)

                owner.add_pet(pet)

            return owner

        except FileNotFoundError:
            # File doesn't exist yet - this is normal on first run
            return None
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted JSON in {filename}: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required field in {filename}: {e}")


# Helper functions for working with plan dictionaries

def display_plan(plan: dict) -> str:
    """Formats a plan dictionary for display with all details."""
    owner = plan['owner']
    pets_count = plan['pets_count']
    pets_str = f"{pets_count} pet{'s' if pets_count != 1 else ''}"

    output = f"=== Daily Plan for {owner.name} ({pets_str}) ===\n\n"

    # Show conflict warning if present
    if 'conflict_info' in plan and plan['conflict_info']['has_conflict']:
        output += f"{plan['conflict_info']['message']}\n\n"

    if not plan['scheduled_tasks']:
        output += "No tasks scheduled.\n"
    else:
        output += "Scheduled Tasks:\n"
        for i, task in enumerate(plan['scheduled_tasks'], 1):
            output += f"  {i}. {task}\n"

    output += f"\nTime Summary:\n"
    output += f"  Total scheduled: {plan['total_time_minutes']} minutes\n"
    output += f"  Remaining time: {plan['remaining_time_minutes']} minutes\n"

    if plan['skipped_tasks']:
        output += f"\nSkipped Tasks ({len(plan['skipped_tasks'])}):\n"
        for task in plan['skipped_tasks']:
            output += f"  - {task}\n"

    output += f"\nReasoning:\n{plan['reasoning']}\n"

    return output


def get_plan_summary(plan: dict) -> str:
    """Returns a brief one-line summary of a plan."""
    task_count = len(plan['scheduled_tasks'])
    pets_count = plan['pets_count']
    return f"{task_count} task{'s' if task_count != 1 else ''} for {pets_count} pet{'s' if pets_count != 1 else ''}, {plan['total_time_minutes']} minutes"


class Scheduler:
    """The 'Brain' - retrieves, organizes, and manages tasks across all pets.

    The Scheduler works with an Owner and all their pets, using a greedy algorithm
    to prioritize and fit tasks into the available time budget. It handles incomplete
    tasks across all pets and generates optimized daily care plans.

    Algorithm Complexity: O(n log n) for sorting + O(n) for fitting = O(n log n) overall.
    Tradeoff: Greedy is fast but not optimal. A true optimal solution (0/1 knapsack) would be
    O(n × budget) but is overkill for this use case.
    """

    def __init__(self, owner: Owner):
        """Initialize a Scheduler for the given owner's pets and tasks."""
        self.owner = owner

    def generate_plan(self) -> dict:
        """Creates the daily schedule across all owner's pets, enhanced with AI evaluation."""
        base_plan = self._build_base_plan()
        return self._enhance_with_ai(base_plan) if AI_AVAILABLE else base_plan

    def generate_base_plan(self) -> dict:
        """Returns the rule-based schedule only, without AI enhancement.

        Used by the reliability evaluation script to obtain a deterministic base
        plan that can then be passed to AIAgent directly with different settings
        (e.g., few_shot=True vs. few_shot=False) for comparison testing.
        """
        return self._build_base_plan()

    def _build_base_plan(self) -> dict:
        """Core greedy scheduling logic — no AI calls.

        1. Prioritize tasks by priority score (high > medium > low), then duration.
        2. Fit tasks greedily into the available time budget.
        3. Build reasoning explanation for scheduled and skipped tasks.
        """
        avail = self.owner.available_time_minutes

        if not self.owner.pets:
            return {
                'owner': self.owner, 'scheduled_tasks': [], 'skipped_tasks': [],
                'total_time_minutes': 0, 'remaining_time_minutes': avail,
                'reasoning': "Owner has no pets to care for.",
                'pets_count': 0,
                'conflict_info': {
                    'has_conflict': False, 'total_required_minutes': 0,
                    'available_minutes': avail, 'overflow_minutes': 0,
                    'message': f"OK: No conflicts. 0 minutes required, {avail} available."
                },
            }

        all_tasks = self.owner.get_all_incomplete_tasks()

        if not all_tasks:
            return {
                'owner': self.owner, 'scheduled_tasks': [], 'skipped_tasks': [],
                'total_time_minutes': 0, 'remaining_time_minutes': avail,
                'reasoning': "No incomplete tasks to schedule.",
                'pets_count': len(self.owner.pets),
                'conflict_info': {
                    'has_conflict': False, 'total_required_minutes': 0,
                    'available_minutes': avail, 'overflow_minutes': 0,
                    'message': f"OK: No conflicts. 0 minutes required, {avail} available."
                },
            }

        if avail == 0:
            conflict_info = self.detect_time_conflicts(all_tasks)
            return {
                'owner': self.owner, 'scheduled_tasks': [], 'skipped_tasks': all_tasks.copy(),
                'total_time_minutes': 0, 'remaining_time_minutes': 0,
                'reasoning': "Owner has no available time for pet care tasks.",
                'pets_count': len(self.owner.pets),
                'conflict_info': conflict_info,
            }

        conflict_info = self.detect_time_conflicts(all_tasks)
        sorted_tasks = self.prioritize_tasks(all_tasks)
        selected_tasks = self.fit_tasks_to_time(sorted_tasks, avail)
        total_time = sum(t.duration_minutes for t in selected_tasks)
        skipped_tasks = [t for t in sorted_tasks if t not in selected_tasks]

        return {
            'owner': self.owner,
            'scheduled_tasks': selected_tasks,
            'skipped_tasks': skipped_tasks,
            'total_time_minutes': total_time,
            'remaining_time_minutes': avail - total_time,
            'reasoning': self.build_reasoning(selected_tasks, skipped_tasks),
            'pets_count': len(self.owner.pets),
            'conflict_info': conflict_info,
        }

    def _enhance_with_ai(self, base_plan: dict) -> dict:
        """Enhance the base plan with AI evaluation and reasoning."""
        try:
            ai_agent = AIAgent()
            pet_care_context = self._get_pet_care_context()
            enhanced_plan = ai_agent.evaluate_and_enhance_schedule(
                base_plan, self.owner, pet_care_context
            )
            return enhanced_plan
        except Exception as e:
            # Graceful degradation - return base plan with error note
            print(f"AI enhancement failed: {e}")
            base_plan.update({
                'ai_quality_score': 75,
                'ai_issues_found': [f"AI evaluation failed: {str(e)}"],
                'ai_recommendations': ["Manual review recommended"],
                'ai_confidence': "low",
                'ai_reasoning_steps': ["AI system encountered an error"],
                'ai_enhanced': False
            })
            return base_plan

    def _get_pet_care_context(self) -> dict:
        """Get additional context about pets and care needs for AI evaluation."""
        context = {
            'pet_special_needs': [],
            'age_considerations': [],
            'task_patterns': []
        }

        for pet in self.owner.pets:
            if pet.special_needs:
                context['pet_special_needs'].append(f"{pet.name}: {pet.special_needs}")

            # Age considerations
            if pet.age < 1:
                context['age_considerations'].append(f"{pet.name} is a puppy/kitten ({pet.age}y) - needs frequent care")
            elif pet.age > 10:
                context['age_considerations'].append(f"{pet.name} is senior ({pet.age}y) - may need gentler activities")

        return context

    def prioritize_tasks(self, tasks: list[Task]) -> list[Task]:
        """Sorts tasks by priority (highest first), then by duration (shorter first)."""
        # Sort by priority score (descending), then by duration (ascending) as tiebreaker
        return sorted(
            tasks,
            key=lambda task: (-task.get_priority_score(), task.duration_minutes)
        )

    def fit_tasks_to_time(self, sorted_tasks: list[Task], time_budget: int) -> list[Task]:
        """Selects which tasks fit in available time using greedy algorithm."""
        selected = []
        remaining_time = time_budget

        for task in sorted_tasks:
            if task.duration_minutes <= remaining_time:
                selected.append(task)
                remaining_time -= task.duration_minutes

        return selected

    def filter_by_completion_status(self, tasks: list[Task], completed: bool) -> list[Task]:
        """Filter tasks by completion status.

        This method uses a simple linear search to filter tasks based on their
        completion status. Useful for separating completed from incomplete tasks
        in reports or when generating schedules.

        Algorithm:
            - Time Complexity: O(n) where n is the number of tasks
            - Space Complexity: O(k) where k is the number of matching tasks

        Args:
            tasks: List of tasks to filter
            completed: True to get completed tasks, False for incomplete

        Returns:
            Filtered list of tasks matching the completion status

        Example:
            >>> all_tasks = owner.get_all_tasks()
            >>> incomplete = scheduler.filter_by_completion_status(all_tasks, False)
            >>> completed = scheduler.filter_by_completion_status(all_tasks, True)
        """
        return [task for task in tasks if task.completed == completed]

    def filter_by_pet(self, tasks: list[Task], pet_name: str) -> list[Task]:
        """Filter tasks to only those belonging to a specific pet.

        This method searches through the owner's pets to find the matching pet,
        then returns the intersection of that pet's tasks with the provided task list.
        Case-insensitive pet name matching is used for convenience.

        Algorithm:
            - Time Complexity: O(p + m*n) where p is number of pets, m is matching pet's
              tasks, and n is input tasks (worst case). Early return optimizes common case.
            - Space Complexity: O(k) where k is number of matching tasks

        Args:
            tasks: List of tasks to filter (typically from owner.get_all_tasks())
            pet_name: Name of the pet to filter by (case-insensitive)

        Returns:
            List of tasks belonging to the specified pet. Empty list if pet not found
            or if the pet has no tasks matching the input list.

        Example:
            >>> all_tasks = owner.get_all_incomplete_tasks()
            >>> max_tasks = scheduler.filter_by_pet(all_tasks, "Max")
            >>> luna_tasks = scheduler.filter_by_pet(all_tasks, "Luna")
        """
        # Find the matching pet and return intersection of their tasks with input
        for pet in self.owner.pets:
            if pet.name.lower() == pet_name.lower():
                return [task for task in pet.tasks if task in tasks]
        return []  # Pet not found

    def filter_by_task_type(self, tasks: list[Task], task_type: str) -> list[Task]:
        """Filter tasks by their type (walk, feeding, meds, etc.).

        This method filters tasks to return only those matching a specific type.
        Useful for generating type-specific reports (e.g., "all feeding tasks") or
        for building specialized schedules.

        Algorithm:
            - Time Complexity: O(n) where n is the number of tasks
            - Space Complexity: O(k) where k is the number of matching tasks

        Args:
            tasks: List of tasks to filter
            task_type: The task type to filter by. Must be one of:
                      "walk", "feeding", "meds", "grooming", "enrichment", "other"

        Returns:
            Filtered list of tasks of the specified type

        Raises:
            ValueError: If task_type is not in Task.VALID_TASK_TYPES

        Example:
            >>> all_tasks = owner.get_all_tasks()
            >>> feeding_tasks = scheduler.filter_by_task_type(all_tasks, "feeding")
            >>> walk_tasks = scheduler.filter_by_task_type(all_tasks, "walk")
        """
        if task_type not in Task.VALID_TASK_TYPES:
            raise ValueError(f"Invalid task_type '{task_type}'. Must be one of: {Task.VALID_TASK_TYPES}")
        return [task for task in tasks if task.task_type == task_type]

    def filter_by_frequency(self, tasks: list[Task], frequency: str) -> list[Task]:
        """Filter tasks by their frequency (daily, weekly, as-needed).

        This method filters tasks based on how often they need to be performed.
        Useful for identifying recurring vs. one-time tasks, or for building
        frequency-specific schedules.

        Algorithm:
            - Time Complexity: O(n) where n is the number of tasks
            - Space Complexity: O(k) where k is the number of matching tasks

        Args:
            tasks: List of tasks to filter
            frequency: The frequency to filter by. Must be one of:
                      "daily", "weekly", "as-needed"

        Returns:
            Filtered list of tasks with the specified frequency

        Raises:
            ValueError: If frequency is not in Task.VALID_FREQUENCIES

        Example:
            >>> all_tasks = owner.get_all_tasks()
            >>> daily_tasks = scheduler.filter_by_frequency(all_tasks, "daily")
            >>> weekly_tasks = scheduler.filter_by_frequency(all_tasks, "weekly")
        """
        if frequency not in Task.VALID_FREQUENCIES:
            raise ValueError(f"Invalid frequency '{frequency}'. Must be one of: {Task.VALID_FREQUENCIES}")
        return [task for task in tasks if task.frequency == frequency]

    def filter_due_tasks(self, tasks: list[Task], reference_date: Optional[datetime] = None) -> list[Task]:
        """Filter tasks to only those that are due today based on frequency.

        This method filters tasks based on their recurrence logic, considering when
        they were last completed and their frequency. Essential for generating
        accurate daily schedules that respect recurring task patterns.

        Algorithm:
            - Time Complexity: O(n) where n is the number of tasks
            - Space Complexity: O(k) where k is the number of due tasks
            - Delegates to Task.is_due() for recurrence logic

        Recurrence Logic:
            - Daily tasks: Due if never completed OR last completed 1+ days ago
            - Weekly tasks: Due if never completed OR last completed 7+ days ago
            - As-needed tasks: Only due if never completed (manual scheduling)

        Args:
            tasks: List of tasks to filter
            reference_date: Date to check against (defaults to today). Useful for
                           testing or generating future schedules.

        Returns:
            List of tasks that are due based on their frequency and last completion

        Example:
            >>> all_tasks = owner.get_all_tasks()
            >>> due_today = scheduler.filter_due_tasks(all_tasks)
            >>> # Check what would be due tomorrow
            >>> tomorrow = datetime.now() + timedelta(days=1)
            >>> due_tomorrow = scheduler.filter_due_tasks(all_tasks, tomorrow)
        """
        return [task for task in tasks if task.is_due(reference_date)]

    def sort_by_duration(self, tasks: list[Task], ascending: bool = True) -> list[Task]:
        """Sort tasks by their duration (time to complete).

        This method sorts tasks by how long they take, which is useful for:
        - Quick-win strategies (shortest tasks first)
        - Time-filling algorithms (longest tasks first)
        - Visualizing task time distribution

        Algorithm:
            - Time Complexity: O(n log n) - uses Python's Timsort
            - Space Complexity: O(n) - creates new sorted list
            - Stable sort: preserves original order for equal durations

        Args:
            tasks: List of tasks to sort
            ascending: True for shortest first, False for longest first

        Returns:
            Sorted list of tasks by duration (does not modify input list)

        Example:
            >>> all_tasks = owner.get_all_incomplete_tasks()
            >>> # Quick wins: do shortest tasks first
            >>> quick_wins = scheduler.sort_by_duration(all_tasks, ascending=True)
            >>> # Fill large blocks: do longest tasks first
            >>> longest_first = scheduler.sort_by_duration(all_tasks, ascending=False)
        """
        return sorted(tasks, key=lambda task: task.duration_minutes, reverse=not ascending)

    def sort_by_task_type(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by logical time-of-day order based on task type.

        This method orders tasks according to typical pet care routines, where
        time-sensitive tasks (feeding, medication) come before flexible activities
        (grooming, play). This creates a natural daily schedule flow.

        Sorting Order: feeding → meds → walk → grooming → enrichment → other

        Algorithm:
            - Time Complexity: O(n log n) - uses Python's Timsort
            - Space Complexity: O(n) - creates new sorted list
            - Stable sort: preserves original order within same type

        Rationale:
            - Feeding: Often time-critical (morning/evening)
            - Meds: Must follow feeding or specific schedule
            - Walk: Best done after feeding settles
            - Grooming: Flexible timing, moderate importance
            - Enrichment: Play/training, flexible timing
            - Other: Miscellaneous tasks, lowest priority for ordering

        Args:
            tasks: List of tasks to sort

        Returns:
            Sorted list with time-critical tasks first (does not modify input)

        Example:
            >>> all_tasks = owner.get_all_incomplete_tasks()
            >>> routine_order = scheduler.sort_by_task_type(all_tasks)
            >>> # First tasks will be feeding, then meds, then walks, etc.
        """
        type_priority = {
            "feeding": 1,
            "meds": 2,
            "walk": 3,
            "grooming": 4,
            "enrichment": 5,
            "other": 6
        }
        return sorted(tasks, key=lambda task: type_priority.get(task.task_type, 99))

    def complete_task_with_recurrence(self, task: Task) -> Optional[Task]:
        """Complete a task and automatically create next instance if recurring.

        This is a convenience method that finds which pet owns the task and
        delegates to that pet's complete_recurring_task method. It automates
        the recurring task lifecycle for daily and weekly tasks.

        Algorithm:
            - Time Complexity: O(p * t) where p is number of pets and t is average
              tasks per pet (linear search through all tasks)
            - Space Complexity: O(1) for search, O(1) for new task creation

        Recurrence Logic:
            - Daily tasks: Creates new instance with due_date = today + 1 day
            - Weekly tasks: Creates new instance with due_date = today + 7 days
            - As-needed tasks: Just marks complete, no new instance created

        Args:
            task: The task to complete

        Returns:
            The newly created Task instance if the task is recurring (daily/weekly),
            None if the task is as-needed or does not recur

        Raises:
            ValueError: If task is not found in any pet's task list

        Example:
            >>> task = daily_tasks[0]  # A daily feeding task
            >>> new_task = scheduler.complete_task_with_recurrence(task)
            >>> # Original task is now completed
            >>> # new_task is scheduled for tomorrow with same properties
        """
        for pet in self.owner.pets:
            if task in pet.tasks:
                return pet.complete_recurring_task(task)

        raise ValueError(f"Task '{task.description}' not found in any pet's task list")

    def detect_scheduling_conflicts(self, tasks: list[Task]) -> list[dict]:
        """Detect time slot conflicts where tasks overlap in their scheduled times.

        This method performs pairwise comparison of all tasks to detect overlapping
        time slots. Uses interval overlap detection: two tasks conflict if one starts
        before the other ends. Essential for preventing impossible schedules.

        Algorithm:
            - Time Complexity: O(n²) where n is number of tasks (checks all pairs)
            - Space Complexity: O(k) where k is number of conflicts found
            - Uses Task.conflicts_with() for interval overlap logic

        Conflict Detection Logic:
            Tasks A and B conflict if:
            - Both have scheduled_start_time set, AND
            - A.start < B.end AND B.start < A.end
            (Standard interval overlap algorithm)

        Args:
            tasks: List of tasks with scheduled_start_time to check. Tasks without
                   scheduled_start_time are ignored (can't conflict if not scheduled).

        Returns:
            List of conflict dictionaries, each containing:
            - 'task1': First conflicting task
            - 'task2': Second conflicting task
            - 'message': Human-readable description with times and pet names
            Empty list if no conflicts found.

        Example:
            >>> # Create tasks with overlapping times
            >>> walk = Task("Walk Max", 30, "daily", scheduled_start_time=datetime(2025,1,15,8,0))
            >>> feed = Task("Feed Max", 10, "daily", scheduled_start_time=datetime(2025,1,15,8,15))
            >>> conflicts = scheduler.detect_scheduling_conflicts([walk, feed])
            >>> if conflicts:
            ...     print(conflicts[0]['message'])
            "SCHEDULING CONFLICT: 'Walk Max' (Max) at 08:00 AM overlaps with..."

        Note:
            This is a "lightweight" conflict detection strategy that only checks
            scheduled time overlaps. It does NOT check resource conflicts (e.g.,
            whether owner can physically do two tasks at once for different pets).
        """
        conflicts = []

        # Check every pair of tasks for time conflicts
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i+1:]:
                if task1.conflicts_with(task2):
                    # Helper to find pet name for a task
                    def get_pet_name(task):
                        for pet in self.owner.pets:
                            if task in pet.tasks:
                                return pet.name
                        return "Unknown"

                    conflicts.append({
                        'task1': task1,
                        'task2': task2,
                        'message': (
                            f"SCHEDULING CONFLICT: '{task1.description}' ({get_pet_name(task1)}) "
                            f"at {task1.scheduled_start_time.strftime('%I:%M %p')} "
                            f"overlaps with '{task2.description}' ({get_pet_name(task2)}) "
                            f"at {task2.scheduled_start_time.strftime('%I:%M %p')}"
                        )
                    })

        return conflicts

    def detect_time_conflicts(self, tasks: list[Task]) -> dict:
        """Detect if total task time exceeds available time budget.

        Args:
            tasks: List of tasks to check

        Returns:
            Dictionary with conflict information:
            {
                'has_conflict': bool,
                'total_required_minutes': int,
                'available_minutes': int,
                'overflow_minutes': int,
                'message': str
            }
        """
        total_required = sum(task.duration_minutes for task in tasks)
        available = self.owner.available_time_minutes
        overflow = max(0, total_required - available)

        has_conflict = total_required > available

        if has_conflict:
            message = (f"WARNING: Time conflict detected! Need {total_required} minutes "
                      f"but only {available} available. {overflow} minutes over budget.")
        else:
            message = f"OK: No conflicts. {total_required} minutes required, {available} available."

        return {
            'has_conflict': has_conflict,
            'total_required_minutes': total_required,
            'available_minutes': available,
            'overflow_minutes': overflow,
            'message': message
        }

    def build_reasoning(self, selected_tasks: list[Task], rejected_tasks: list[Task]) -> str:
        """Generates human-readable explanation text for scheduling decisions."""
        reasoning_parts = []

        # Overall strategy
        pet_names = [pet.name for pet in self.owner.pets]
        pets_str = ", ".join(pet_names) if len(pet_names) <= 3 else f"{len(pet_names)} pets"
        reasoning_parts.append(
            f"Scheduling strategy: Prioritize tasks by priority (high > medium > low) "
            f"across {pets_str}, then fit as many as possible into the "
            f"{self.owner.available_time_minutes}-minute time budget."
        )

        # What was scheduled
        if selected_tasks:
            reasoning_parts.append(
                f"\nScheduled {len(selected_tasks)} task(s):"
            )
            for task in selected_tasks:
                reasoning_parts.append(
                    f"  • {task.description} ({task.priority} priority, {task.duration_minutes} min)"
                )
        else:
            reasoning_parts.append("\nNo tasks could be scheduled.")

        # What was skipped and why
        if rejected_tasks:
            reasoning_parts.append(f"\nSkipped {len(rejected_tasks)} task(s) due to time constraints:")
            for task in rejected_tasks:
                reasoning_parts.append(
                    f"  • {task.description} ({task.priority} priority, {task.duration_minutes} min)"
                )

        return "\n".join(reasoning_parts)

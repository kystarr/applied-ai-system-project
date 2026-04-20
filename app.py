import streamlit as st
import pandas as pd
from datetime import date, timedelta
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

PET_COLORS = ["#C0392B", "#1A7A6E", "#1F6FA3", "#27AE60", "#D4850A", "#7D3C98", "#117A65"]


def get_priority_emoji(priority: str) -> str:
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority.lower(), "⚪")


def get_pet_color(pet_index: int) -> str:
    return PET_COLORS[pet_index % len(PET_COLORS)]


def build_calendar_events(owner) -> list:
    events = []
    today = date.today()
    for pet_idx, pet in enumerate(owner.pets):
        color = get_pet_color(pet_idx)
        for task in pet.tasks:
            if task.frequency == "daily":
                offsets = range(30)
            elif task.frequency == "weekly":
                offsets = range(0, 30, 7)
            else:
                offsets = [0]
            for offset in offsets:
                d = today + timedelta(days=offset)
                events.append({
                    "title": f"{task.description} ({pet.name})",
                    "start": d.isoformat(),
                    "end": d.isoformat(),
                    "color": color,
                })
    return events


# ── Session state init ────────────────────────────────────────────────────────
if "owner" not in st.session_state:
    loaded = Owner.load_from_json("data.json")
    if loaded is not None:
        st.session_state.owner = loaded
    else:
        st.session_state.owner = Owner(name="Jordan", available_time_minutes=180)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🐾 PawPal+")
    st.caption("Pet care scheduling assistant")
    st.divider()

    # Owner settings
    st.subheader("Owner Settings")
    owner_name = st.text_input("Owner name", value=st.session_state.owner.name)
    available_time = st.number_input(
        "Available time (min/day)", min_value=0, max_value=1440,
        value=st.session_state.owner.available_time_minutes,
    )
    if st.button("Update Owner"):
        st.session_state.owner.name = owner_name
        st.session_state.owner.available_time_minutes = int(available_time)
        st.session_state.owner.save_to_json("data.json")
        st.success("Owner updated!")

    st.divider()

    # Generate button — prominent, always visible
    if st.button("🤖 Generate Schedule", type="primary", use_container_width=True):
        if not st.session_state.owner.pets:
            st.warning("Add at least one pet first.")
        elif not st.session_state.owner.get_all_tasks():
            st.warning("Add at least one task first.")
        else:
            with st.spinner("Generating AI-enhanced schedule..."):
                scheduler = Scheduler(st.session_state.owner)
                plan = scheduler.generate_plan()
                st.session_state.plan = plan
                st.session_state.scheduler = scheduler
            st.success("Schedule ready! See the Schedule tab.")

    st.divider()

    # Add Pet
    with st.expander("➕ Add a Pet", expanded=not bool(st.session_state.owner.pets)):
        pet_name_in = st.text_input("Pet name", value="Mochi", key="pet_name_input")
        species_in = st.selectbox("Species", ["dog", "cat", "other"], key="species_input")
        pet_age_in = st.number_input("Age (years)", min_value=0, max_value=30, value=3, key="pet_age_input")
        if st.button("Add Pet"):
            st.session_state.owner.add_pet(Pet(name=pet_name_in, species=species_in, age=pet_age_in))
            st.session_state.owner.save_to_json("data.json")
            st.success(f"Added {pet_name_in}!")
            st.rerun()

    # Pet list with delete
    if st.session_state.owner.pets:
        st.markdown("**Your Pets:**")
        for idx, pet in enumerate(st.session_state.owner.pets):
            col1, col2 = st.columns([3, 1])
            with col1:
                color = get_pet_color(idx)
                st.markdown(
                    f"<span style='color:{color};font-size:18px'>●</span> {pet.name} "
                    f"<span style='color:#888'>({pet.species}, {pet.age}y)</span>",
                    unsafe_allow_html=True,
                )
            with col2:
                if st.button("🗑️", key=f"del_pet_{idx}"):
                    st.session_state.owner.pets.remove(pet)
                    st.session_state.owner.save_to_json("data.json")
                    st.rerun()

    st.divider()

    # Add Task
    if st.session_state.owner.pets:
        with st.expander("➕ Add a Task", expanded=False):
            pet_names = [p.name for p in st.session_state.owner.pets]
            sel_pet_name = st.selectbox("For pet:", pet_names, key="task_pet_select")
            sel_pet = next(p for p in st.session_state.owner.pets if p.name == sel_pet_name)
            task_title_in = st.text_input("Description", value="Morning walk", key="task_title_input")
            duration_in = st.number_input("Duration (min)", min_value=1, max_value=240, value=20, key="task_dur_input")
            priority_in = st.selectbox("Priority", ["low", "medium", "high"], index=2, key="task_pri_input")
            task_type_in = st.selectbox(
                "Type", ["walk", "feeding", "meds", "grooming", "enrichment", "other"], key="task_type_input"
            )
            frequency_in = st.selectbox("Frequency", ["daily", "weekly", "as-needed"], key="task_freq_input")
            if st.button("Add Task"):
                sel_pet.add_task(Task(
                    description=task_title_in,
                    duration_minutes=int(duration_in),
                    frequency=frequency_in,
                    priority=priority_in,
                    task_type=task_type_in,
                ))
                st.session_state.owner.save_to_json("data.json")
                st.success(f"Added '{task_title_in}' to {sel_pet.name}!")
                st.rerun()

        # Task list with delete
        if any(p.tasks for p in st.session_state.owner.pets):
            st.markdown("**All Tasks:**")
            for pet in st.session_state.owner.pets:
                for i, task in enumerate(pet.tasks):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.caption(
                            f"{get_priority_emoji(task.priority)} {task.description} "
                            f"— {pet.name}, {task.duration_minutes}min"
                        )
                    with col2:
                        if st.button("🗑️", key=f"del_task_{pet.name}_{i}"):
                            pet.tasks.remove(task)
                            st.session_state.owner.save_to_json("data.json")
                            st.rerun()

    st.divider()

    # Data management
    st.markdown("**Data Management**")
    col_s, col_r = st.columns(2)
    with col_s:
        if st.button("💾 Save", use_container_width=True):
            st.session_state.owner.save_to_json("data.json")
            st.success("Saved!")
    with col_r:
        if st.button("🔄 Reload", use_container_width=True):
            loaded = Owner.load_from_json("data.json")
            if loaded:
                st.session_state.owner = loaded
                st.rerun()
            else:
                st.warning("No saved data found.")
    if st.button("🗑️ Clear All Data", type="secondary", use_container_width=True):
        if st.checkbox("Confirm: delete all pets and tasks?", key="confirm_clear"):
            st.session_state.owner.pets.clear()
            st.session_state.owner.save_to_json("data.json")
            st.session_state.pop("plan", None)
            st.session_state.pop("scheduler", None)
            st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.title(f"🐾 {st.session_state.owner.name}'s Pet Care Dashboard")
st.caption("Priority: 🔴 High  |  🟡 Medium  |  🟢 Low")

# Quick stats bar — always visible at the top
pet_count = len(st.session_state.owner.pets)
task_count = len(st.session_state.owner.get_all_tasks())
has_plan = "plan" in st.session_state
has_ai = has_plan and "ai_quality_score" in st.session_state.plan

qs1, qs2, qs3, qs4 = st.columns(4)
qs1.metric("Pets", pet_count)
qs2.metric("Tasks", task_count)
qs3.metric(
    "Available Time",
    f"{st.session_state.owner.available_time_minutes} min",
)
qs4.metric("AI Score", f"{st.session_state.plan['ai_quality_score']}/100" if has_ai else "—")
st.divider()

tab_schedule, tab_calendar, tab_ai, tab_analysis = st.tabs(
    ["📋 Schedule", "📅 Calendar", "🤖 AI Insights", "🔍 Analysis"]
)

# ── Tab 1: Schedule ───────────────────────────────────────────────────────────
with tab_schedule:
    if "plan" not in st.session_state:
        if pet_count == 0:
            st.info(
                "👋 **Welcome to PawPal+!** Get started in 3 steps:\n\n"
                "1. Set your name and available time under **Owner Settings** in the sidebar\n"
                "2. Add your pet(s) using **➕ Add a Pet**\n"
                "3. Add care tasks, then hit **🤖 Generate Schedule**"
            )
        else:
            st.info("Click **🤖 Generate Schedule** in the sidebar to create your daily plan.")
    else:
        plan = st.session_state.plan
        conflict_info = plan["conflict_info"]
        if conflict_info["has_conflict"]:
            st.error(
                f"⚠️ {conflict_info['message']} — "
                f"{conflict_info['overflow_minutes']} min overflow. "
                "Increase available time or reduce tasks."
            )
        else:
            st.success(f"✅ {conflict_info['message']}")

        time_used_pct = (
            plan["total_time_minutes"] / max(plan["owner"].available_time_minutes, 1)
        ) * 100
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Scheduled", f"{plan['total_time_minutes']} min")
        c2.metric("Remaining", f"{plan['remaining_time_minutes']} min")
        c3.metric("Pets", plan["pets_count"])
        c4.metric(
            "Tasks Fit",
            f"{len(plan['scheduled_tasks'])} / "
            f"{len(plan['scheduled_tasks']) + len(plan['skipped_tasks'])}",
        )
        st.progress(min(time_used_pct / 100, 1.0), text=f"Time Utilization: {time_used_pct:.1f}%")

        if plan["scheduled_tasks"]:
            st.markdown("#### ✅ Scheduled Tasks")
            st.info(
                "🎯 Sorted by priority (🔴 High → 🟡 Medium → 🟢 Low), "
                "then by shortest duration within each level."
            )
            task_rows = []
            for i, task in enumerate(plan["scheduled_tasks"], 1):
                pet_name = next(
                    (p.name for p in st.session_state.owner.pets if task in p.tasks), "Unknown"
                )
                task_rows.append({
                    "#": i,
                    "Task": task.description,
                    "Pet": pet_name,
                    "Duration": f"{task.duration_minutes} min",
                    "Priority": f"{get_priority_emoji(task.priority)} {task.priority.upper()}",
                    "Type": task.task_type.capitalize(),
                    "Frequency": task.frequency.capitalize(),
                })

            def highlight_priority(row):
                if "HIGH" in str(row.get("Priority", "")):
                    return ["background-color: #ffcccc"] * len(row)
                elif "MEDIUM" in str(row.get("Priority", "")):
                    return ["background-color: #fff4cc"] * len(row)
                return ["background-color: #ccffcc"] * len(row)

            df = pd.DataFrame(task_rows)
            st.dataframe(df.style.apply(highlight_priority, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("No tasks could be scheduled.")

        if plan["skipped_tasks"]:
            st.markdown(f"#### ⏭️ Skipped Tasks ({len(plan['skipped_tasks'])})")
            st.warning("These tasks did not fit in your available time budget.")
            skipped_rows = []
            for task in plan["skipped_tasks"]:
                pet_name = next(
                    (p.name for p in st.session_state.owner.pets if task in p.tasks), "Unknown"
                )
                skipped_rows.append({
                    "Task": task.description,
                    "Pet": pet_name,
                    "Duration": f"{task.duration_minutes} min",
                    "Priority": f"{get_priority_emoji(task.priority)} {task.priority.upper()}",
                    "Type": task.task_type.capitalize(),
                })
            st.dataframe(pd.DataFrame(skipped_rows), use_container_width=True, hide_index=True)

        with st.expander("📊 Scheduling Algorithm Details"):
            st.write(plan["reasoning"])
            st.markdown("""
**O(n log n) Priority-Based Greedy Algorithm:**
1. Sort tasks by priority (High → Medium → Low)
2. Within each level, sort by duration (shortest first)
3. Greedily fit tasks into available time budget
            """)

# ── Tab 2: Calendar ───────────────────────────────────────────────────────────
with tab_calendar:
    st.markdown("#### 📅 Upcoming Care Schedule")
    st.caption("Next 30 days of pet care tasks. Daily tasks repeat every day, weekly every 7 days.")

    events = build_calendar_events(st.session_state.owner)

    if not events:
        st.info("Add pets and tasks in the sidebar to see upcoming care events.")
    else:
        if st.session_state.owner.pets:
            legend_cols = st.columns(min(len(st.session_state.owner.pets), 7))
            for idx, (col, pet) in enumerate(zip(legend_cols, st.session_state.owner.pets)):
                color = get_pet_color(idx)
                col.markdown(
                    f"<span style='background:{color};border-radius:4px;"
                    f"padding:3px 10px;color:white;font-weight:bold'>{pet.name}</span>",
                    unsafe_allow_html=True,
                )
            st.markdown("")

        rows = []
        for e in events:
            rows.append({"Date": e["start"], "Task": e["title"]})

        df_cal = pd.DataFrame(rows).sort_values("Date").reset_index(drop=True)
        st.dataframe(df_cal, use_container_width=True, hide_index=True, height=550)

# ── Tab 3: AI Insights ────────────────────────────────────────────────────────
with tab_ai:
    if "plan" not in st.session_state:
        st.info("Generate a schedule first to see AI insights.")
    elif "ai_quality_score" not in st.session_state.plan:
        st.warning(
            "AI enhancement was not available for this schedule. "
            "Check that your GROQ_API_KEY is set in the .env file and regenerate."
        )
    else:
        plan = st.session_state.plan
        quality_score = plan.get("ai_quality_score", 75)
        confidence = plan.get("ai_confidence", "medium")

        c1, c2, c3 = st.columns(3)
        c1.metric("AI Quality Score", f"{quality_score}/100")
        c2.metric("Confidence", confidence.upper())
        c3.metric("Few-Shot Calibration", "Enabled" if plan.get("ai_few_shot") else "Disabled")

        if quality_score >= 90:
            st.success("🎯 Excellent — Optimal priority coverage and time usage")
        elif quality_score >= 75:
            st.info("👍 Good — Reasonable prioritization with minor opportunities")
        elif quality_score >= 60:
            st.warning("⚠️ Fair — Some improvements possible")
        else:
            st.error("🔧 Needs Review — Consider manual adjustments or more time")

        st.divider()

        # Step 1: Constraint Analysis
        ca = plan.get("ai_constraint_analysis", {})
        if ca:
            st.subheader("Step 1: Constraint Analysis")
            st.caption("The AI identified these constraints before evaluating your schedule.")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Key Constraints**")
                for c in ca.get("key_constraints", []):
                    st.write(f"• {c}")
            with col2:
                st.markdown("**Risk Factors**")
                risks = ca.get("risk_factors", [])
                if risks:
                    for r in risks:
                        st.warning(f"⚠ {r}")
                else:
                    st.success("✅ No risks identified")
            with col3:
                time_assessment = ca.get("time_assessment", "N/A")
                badge = {"tight": "🔴", "adequate": "🟡", "generous": "🟢"}.get(time_assessment, "⚪")
                st.markdown("**Time Budget**")
                st.markdown(f"## {badge} {time_assessment.upper()}")

        st.divider()

        # Step 2: Schedule Evaluation
        st.subheader("Step 2: Schedule Evaluation")
        reasoning_steps = plan.get("ai_reasoning_steps", [])
        if reasoning_steps:
            st.markdown("**AI Reasoning Steps:**")
            for i, step in enumerate(reasoning_steps, 1):
                st.write(f"{i}. {step}")

        issues = plan.get("ai_issues_found", [])
        if issues:
            st.markdown("**Issues Found:**")
            for issue in issues:
                st.warning(f"• {issue}")
        else:
            st.success("✅ No issues detected by AI analysis")

        recommendations = plan.get("ai_recommendations", [])
        if recommendations:
            st.markdown("**Recommendations:**")
            for rec in recommendations:
                st.info(f"💡 {rec}")
        else:
            st.write("✅ No additional recommendations — schedule looks strong.")

        if plan.get("ai_few_shot"):
            st.caption("🎯 Few-shot calibration active — scores guided by domain-specific examples")

# ── Tab 4: Analysis ───────────────────────────────────────────────────────────
with tab_analysis:
    if "scheduler" not in st.session_state:
        st.info("Generate a schedule first to access the task explorer.")
    else:
        scheduler = st.session_state.scheduler
        all_tasks = st.session_state.owner.get_all_tasks()

        if not all_tasks:
            st.info("No tasks to analyze. Add pets and tasks in the sidebar.")
        else:
            st.markdown("#### 🔍 Task Explorer")
            col1, col2 = st.columns(2)
            with col1:
                sort_option = st.radio(
                    "Sort by:",
                    ["Priority (Default)", "Duration (Shortest First)", "Duration (Longest First)", "Task Type Order"],
                )
            with col2:
                filter_option = st.selectbox(
                    "Filter by:",
                    ["All Tasks", "Completed Only", "Incomplete Only", "By Pet", "By Task Type", "By Frequency"],
                )

            filtered_tasks = all_tasks.copy()
            if filter_option == "Completed Only":
                filtered_tasks = scheduler.filter_by_completion_status(all_tasks, completed=True)
            elif filter_option == "Incomplete Only":
                filtered_tasks = scheduler.filter_by_completion_status(all_tasks, completed=False)
            elif filter_option == "By Pet":
                sel = st.selectbox("Pet:", [p.name for p in st.session_state.owner.pets])
                filtered_tasks = scheduler.filter_by_pet(all_tasks, sel)
            elif filter_option == "By Task Type":
                sel = st.selectbox("Type:", ["walk", "feeding", "meds", "grooming", "enrichment", "other"])
                filtered_tasks = scheduler.filter_by_task_type(all_tasks, sel)
            elif filter_option == "By Frequency":
                sel = st.selectbox("Frequency:", ["daily", "weekly", "as-needed"])
                filtered_tasks = scheduler.filter_by_frequency(all_tasks, sel)

            if sort_option == "Priority (Default)":
                sorted_tasks = scheduler.prioritize_tasks(filtered_tasks)
            elif sort_option == "Duration (Shortest First)":
                sorted_tasks = scheduler.sort_by_duration(filtered_tasks, ascending=True)
            elif sort_option == "Duration (Longest First)":
                sorted_tasks = scheduler.sort_by_duration(filtered_tasks, ascending=False)
            else:
                sorted_tasks = scheduler.sort_by_task_type(filtered_tasks)

            if sorted_tasks:
                completed_count = sum(1 for t in sorted_tasks if t.completed)
                st.success(f"{len(sorted_tasks)} task(s) found — {completed_count} completed")

                header = st.columns([1, 4, 2, 2, 2, 2, 2])
                for col, label in zip(header, ["Done", "Task", "Pet", "Duration", "Priority", "Type", "Frequency"]):
                    col.markdown(f"**{label}**")
                st.divider()

                for task in sorted_tasks:
                    pet_name = next(
                        (p.name for p in st.session_state.owner.pets if task in p.tasks), "Unknown"
                    )
                    col1, col2, col3, col4, col5, col6, col7 = st.columns([1, 4, 2, 2, 2, 2, 2])
                    with col1:
                        checked = st.checkbox(
                            "", value=task.completed, key=f"complete_{pet_name}_{task.description}"
                        )
                        if checked != task.completed:
                            if checked:
                                task.mark_complete()
                            else:
                                task.mark_incomplete()
                            st.session_state.owner.save_to_json("data.json")
                            st.rerun()
                    col2.write(task.description)
                    col3.write(pet_name)
                    col4.write(f"{task.duration_minutes} min")
                    col5.write(f"{get_priority_emoji(task.priority)} {task.priority.upper()}")
                    col6.write(task.task_type.capitalize())
                    col7.write(task.frequency.capitalize())
            else:
                st.info("No tasks match the selected filter.")

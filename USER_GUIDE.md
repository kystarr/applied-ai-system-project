# PawPal+ User Guide
### Your complete walkthrough for first-time use

---

## Before You Start

Make sure the app is running. Open your terminal in the project folder and run:

```
streamlit run app.py
```

Your browser will open automatically at `http://localhost:8501`. You'll see a warm brown dashboard — that's home base.

---

## Step 1 — Set Up Your Owner Profile

Look at the **left sidebar**. At the top you'll see **Owner Settings**.

1. Type your name in the **Owner name** field (replace "Jordan" with your actual name)
2. Set **Available time (min/day)** — this is how many minutes per day you realistically have for pet care. Be honest! If your morning routine is 2 hours, enter `120`.
3. Click **Update Owner** to save.

> **Tip:** Your available time is the engine of the scheduler. Set it too high and everything fits easily. Set it realistically and you'll see PawPal+ prioritize what actually matters.

---

## Step 2 — Add Your Pet(s)

In the sidebar, click **➕ Add a Pet** to expand the form.

1. Enter your pet's **name** (e.g. "Luna")
2. Choose the **species** — dog, cat, or other
3. Enter their **age in years**
4. Click **Add Pet**

Your pet appears below the form with a colored dot. Each pet gets its own unique color — you'll see this color carry through the calendar and charts.

**Have more than one pet?** Repeat this process for each one. PawPal+ handles multiple pets seamlessly and the scheduler will juggle all their tasks together.

> **To remove a pet:** Click the 🗑️ button next to their name. Note: this also removes their tasks.

---

## Step 3 — Add Care Tasks

In the sidebar, click **➕ Add a Task** to expand the form. This is where you define everything your pet needs.

**Fill in each field:**

| Field | What it means |
|---|---|
| **For pet** | Which pet this task belongs to |
| **Description** | Plain English name — "Morning walk", "Insulin shot", "Litter box clean" |
| **Duration (min)** | How many minutes this actually takes |
| **Priority** | How critical this task is (see below) |
| **Type** | Category: walk, feeding, meds, grooming, enrichment, or other |
| **Frequency** | How often it happens (see below) |

**Priority guide:**
- 🔴 **High** — Must happen. Medical needs, feeding, daily walks. The scheduler always tries to fit these first.
- 🟡 **Medium** — Important but flexible. Grooming, training sessions.
- 🟢 **Low** — Nice to have. Extra playtime, enrichment activities.

**Frequency guide:**
- **Daily** — Appears every day on the calendar (next 30 days)
- **Weekly** — Appears every 7 days on the calendar
- **As-needed** — Shows on today's calendar only

Click **Add Task** to save. Repeat for every care task across all your pets.

**Example task set for a dog named Luna:**

| Task | Duration | Priority | Type | Frequency |
|---|---|---|---|---|
| Morning walk | 45 min | High | walk | daily |
| Breakfast | 10 min | High | feeding | daily |
| Dinner | 10 min | High | feeding | daily |
| Insulin shot | 5 min | High | meds | daily |
| Brushing | 15 min | Medium | grooming | weekly |
| Enrichment toys | 20 min | Low | enrichment | daily |

> **Tip:** Add your most critical tasks first. If you have a pet on medication, add that task as High priority so it never gets dropped from the schedule.

---

## Step 4 — Generate Your Schedule

Once you've added at least one pet and one task, click the big brown **🤖 Generate Schedule** button in the sidebar.

The app will:
1. Run the priority-based scheduling algorithm
2. Call the AI to analyze constraints and evaluate the plan
3. Display everything across the four tabs

A green success message appears when it's ready. If something goes wrong (no pets, no tasks) you'll see a warning telling you exactly what to fix.

---

## Step 5 — Read Your Schedule (📋 Schedule Tab)

This is your daily plan. At the top you'll see four key numbers:

- **Scheduled** — total minutes of tasks that fit in your day
- **Remaining** — how many minutes you still have free
- **Pets** — number of pets in the plan
- **Tasks Fit** — e.g. "5 / 7" means 5 of your 7 tasks made it in

Below that, a **progress bar** shows what percentage of your available time is filled.

**The color-coded task table** shows everything that made the cut:
- 🔴 Red rows = High priority tasks
- 🟡 Yellow rows = Medium priority tasks
- 🟢 Green rows = Low priority tasks

**If some tasks didn't fit**, they appear in a **Skipped Tasks** section below the main table with a warning. This tells you honestly what got left out and why — your time budget was too tight to include them.

**Conflict banners:**
- Green banner = everything fits, no overflow
- Red/orange banner = you have more tasks than time. It tells you exactly how many minutes you're over budget.

> **What to do if tasks are being skipped:** Either increase your available time in Owner Settings, or reduce the duration of some tasks, or accept the tradeoff — the scheduler already protected your High priority items.

Click **📊 Scheduling Algorithm Details** at the bottom to see the exact reasoning the algorithm used and a plain-English explanation of how it made decisions.

---

## Step 6 — Explore the Calendar (📅 Calendar Tab)

Click the **📅 Calendar** tab. You'll see a full monthly calendar populated with all your pet care tasks.

**Reading the calendar:**
- Each task appears as a colored event block
- The color matches the pet it belongs to (see the legend at the top of the tab)
- **Daily tasks** repeat every day for the next 30 days
- **Weekly tasks** appear every 7 days
- **As-needed tasks** show only on today

**Navigating:**
- Use **prev / next** buttons to move between months
- Click **today** to jump back to the current date
- Switch views using the buttons in the top-right corner of the calendar:
  - **Month** — full overview
  - **Week** — detailed week view, great for planning
  - **List** — plain list of upcoming events, easiest to read day-by-day

> **Tip:** Switch to List view and scroll through to spot any days that look dangerously full. If you have a medical pet, confirm their medication appears every single day.

---

## Step 7 — Understand the AI Insights (🤖 AI Insights Tab)

This is where the AI transparency lives. Click the **🤖 AI Insights** tab.

**At the top:** Three metrics — your AI Quality Score (0–100), confidence level, and whether few-shot calibration was active.

**Score guide:**
- **90–100** 🎯 Excellent — nearly perfect coverage
- **75–89** 👍 Good — solid plan with minor gaps
- **60–74** ⚠️ Fair — some issues worth addressing
- **Below 60** 🔧 Needs review — something important may be at risk

**Step 1: Constraint Analysis** shows what the AI noticed *before* evaluating your plan:
- **Key Constraints** — facts about your situation (time budget, pet needs)
- **Risk Factors** — specific welfare or medical concerns the AI flagged
- **Time Budget** — 🔴 Tight / 🟡 Adequate / 🟢 Generous

**Step 2: Schedule Evaluation** shows the AI's actual judgment:
- **Reasoning Steps** — exactly how the AI thought through your plan (3 steps: constraints → task coverage → welfare)
- **Issues Found** — any problems detected. Items labeled `CRITICAL` indicate serious welfare concerns like a medication being skipped
- **Recommendations** — specific, actionable suggestions you can act on immediately

> **Tip:** If you see a CRITICAL issue, go back to the sidebar, adjust your tasks or time budget, and regenerate. The AI will re-evaluate with the new plan.

---

## Step 8 — Explore and Filter Tasks (🔍 Analysis Tab)

Click the **🔍 Analysis** tab. This is your task explorer — useful when you have many tasks across multiple pets and want to answer questions like "what are all my high-priority items?" or "which tasks take the longest?"

**Sorting options (left column):**
- **Priority (Default)** — High first, then Medium, then Low
- **Duration (Shortest First)** — find quick wins you could squeeze in
- **Duration (Longest First)** — find the biggest time consumers
- **Task Type Order** — groups tasks by category (meds → feeding → walk → grooming etc.)

**Filtering options (right column):**
- **All Tasks** — everything
- **Completed Only / Incomplete Only** — track what's done vs. pending
- **By Pet** — see only one pet's tasks
- **By Task Type** — see only walks, or only meds, etc.
- **By Frequency** — see only daily tasks, weekly tasks, etc.

The result table shows status (✅ or ⬜), task name, pet, duration, priority, type, and frequency. The count at the top tells you how many tasks matched.

---

## Step 9 — Save and Manage Your Data

PawPal+ automatically saves your data every time you add or delete a pet or task. But you can also manage it manually in the sidebar under **Data Management**:

- **💾 Save** — manually write current state to `data.json`
- **🔄 Reload** — reload from the last saved file (useful if you made a mistake)
- **🗑️ Clear All Data** — wipes all pets and tasks. A confirmation checkbox appears first so you can't do this by accident.

Your data persists between sessions — close the browser, reopen it, and everything is exactly where you left it.

---

## Pro Tips

**Plan for realistic days, not ideal ones.** Set your available time to what you actually have on a busy weekday, not your best day. Your High priority tasks will always be protected.

**Use the AI score as a feedback loop.** If you get a score below 75, read the recommendations, make a change (add time, remove a low-priority task), regenerate, and watch the score improve.

**Check the calendar in List view weekly.** It's the fastest way to catch a skipped medication day or an unexpectedly jam-packed weekend.

**Color-code intentionally.** If you have multiple pets, the calendar becomes your at-a-glance triage tool — if one pet's color dominates every day, their care load might be disproportionate.

**The Analysis tab is for planning changes.** Before you add a new task, filter by the pet and sort by duration to see how much time they're already taking up.

# User Flow / Journey Maps
## AI-Powered Exam Preparation Portal

---

## 1. Purpose

This document maps the end-to-end user journeys through the portal — from authentication through setup, exam-taking, and results review — including the branch points introduced by the fluid knowledge base (new ingestion vs. reuse, and "deep dive" expansion).

> **Local-first note:** These journeys are unaffected by the move to a leaner, single-instance backend (see the System Architecture doc) — the user-facing flow is identical either way. The one practical difference: at MVP scale, ingestion and generation typically finish in a few seconds to low minutes on a single machine, so progress is shown via simple polling rather than push notifications.

---

## 2. Journey A — First-Time User (Cold Start, No Knowledge Base Yet)

| Step | User Action | System Response |
|---|---|---|
| 1 | Signs up / logs in | Creates an isolated user workspace (empty knowledge base, empty question bank) |
| 2 | Lands on Setup screen | Sees no existing question sets or datasets; prompted to create the first one |
| 3 | Chooses input method: topic, syllabus text, or file upload | UI shows the relevant input form |
| 4 | Uploads a PDF syllabus (e.g., "Data Structures & Algorithms") | File is stored; Ingestion job is queued; UI shows a progress indicator |
| 5 | (Background) Parser extracts text, chunks it, generates embeddings | Gap Analysis Agent finds no prior content — entire document is "new" |
| 6 | (Background) Tagging Agent assigns topic/sub-topic tags (e.g., `DSA > Arrays`, `DSA > Linked Lists`) | Knowledge base entries created and tagged |
| 7 | User configures exam parameters: question count, difficulty, mode (Practice/Timed) | Configuration captured |
| 8 | Clicks "Generate Exam" | Question Generation Agent produces MCQs from the new content; questions persisted with tags |
| 9 | Exam session starts | Exam Engine serves questions per configured mode |
| 10 | User completes exam | Responses scored; attempt and per-question correctness stored |
| 11 | Results screen | Score, tag-level breakdown (e.g., "weak in Linked Lists"), and explanations shown |
| 12 | User saves/exits | Question set persists permanently in the user's knowledge base for reuse |

---

## 3. Journey B — Returning User, Reusing an Existing Question Set

| Step | User Action | System Response |
|---|---|---|
| 1 | Logs in | Dashboard shows existing knowledge base topics and previously generated question sets |
| 2 | Goes to Setup screen | Selects "Practice from existing question set" |
| 3 | Picks a saved set (e.g., "DSA — Arrays & Linked Lists, 40 Qs") | System loads the saved question bank (no AI generation call needed) |
| 4 | Chooses mode (Timed) and optional filters (e.g., only `difficulty: hard`) | Exam Engine filters question bank by tags/difficulty |
| 5 | Takes exam | Same scoring/results flow as Journey A, steps 9–11 |
| 6 | Reviews results | Can compare performance against previous attempts on the same set |

---

## 4. Journey C — Returning User, Generating Fresh Questions from an Existing Dataset

| Step | User Action | System Response |
|---|---|---|
| 1 | Logs in, goes to Setup | Selects "Select existing dataset → generate new questions" |
| 2 | Picks a dataset (e.g., "DSA" knowledge base, not a specific question set) | System surfaces the underlying ingested content + current tag taxonomy |
| 3 | Optionally narrows scope (e.g., only `Linked Lists`, `Trees`) | Scope passed to Question Generation Agent |
| 4 | Sets quantity/difficulty | Generation job queued |
| 5 | (Background) Question Generation Agent produces new MCQs distinct from previously generated ones for that dataset | Auto-Tagging Agent tags them; persisted as a new, separately retrievable question set, linked to the same dataset |
| 6 | User notified generation is complete | Proceeds to exam configuration and start, as in Journey A |

---

## 5. Journey D — "Deep Dive" Expansion of an Existing Topic

This is the core fluid-growth scenario: a user who has already studied "Data Structures" decides to study "Greedy Algorithms" next.

| Step | User Action | System Response |
|---|---|---|
| 1 | Goes to Setup, chooses to add new material | Selects "Add to existing knowledge base" rather than starting fresh |
| 2 | Uploads new material on "Greedy Algorithms" | Ingestion Service stores file, queues parsing job |
| 3 | (Background) Parser chunks and embeds new content | Gap Analysis Agent compares new embeddings against the existing "Data Structures" knowledge graph |
| 4 | (Background) System determines this is a related-but-new sub-topic | New tags (`DSA > Greedy Algorithms`) are created and linked under the existing `DSA` topic — existing tags/questions are untouched |
| 5 | User is shown a confirmation: "Added Greedy Algorithms under your existing Data Structures topic" | Knowledge base updated, fully additive |
| 6 | User generates/practices questions | Can now mix-select tags across both old (`Arrays`, `Linked Lists`) and new (`Greedy Algorithms`) sub-topics in one exam |

---

## 6. Journey E — Multi-Domain Isolation (Two Unrelated Subjects, Same User)

| Step | User Action | System Response |
|---|---|---|
| 1 | User has an existing "DSA & System Design" knowledge base | Visible under their dashboard |
| 2 | User starts a new, unrelated study track: "Salesforce Certification" | Selects "Create new topic area" rather than adding to DSA |
| 3 | Uploads Salesforce study material | Ingested as a logically separate topic root — tags namespaced under `Salesforce > ...`, with no merge/overlap suggested against `DSA` |
| 4 | User's dashboard now shows two independent topic trees | Question generation, exam setup, and results are always scoped to the topic/dataset selected at setup — no cross-contamination |

*(Note: this is single-user, multi-topic isolation. True multi-user isolation — User A vs. User B — is enforced at every layer per the System Architecture Document and is not user-facing; it is structural.)*

---

## 7. Journey F — Exam-Taking Detail (Both Modes)

### Practice Mode
1. Question presented with answer options.
2. User selects an answer.
3. Immediate feedback: correct/incorrect, explanation shown.
4. User can flag question for review or skip.
5. No timer; user ends session manually.
6. On exit, partial results (questions attempted so far) are saved.

### Timed/Rigid Mode
1. User sees total time and question count before starting.
2. Timer starts on first question; persists across navigation (stored server-side to prevent client-side tampering).
3. No immediate feedback per question — answers are locked in once submitted or once time expires.
4. Auto-submission occurs when time runs out.
5. Full results (score, time taken, tag breakdown) shown only after submission.

---

## 8. Journey G — Results Review

| Step | User Action | System Response |
|---|---|---|
| 1 | Exam submitted | Exam Engine scores attempt, aggregates per-tag performance |
| 2 | Results dashboard loads | Shows overall score, time taken (if timed), and a tag-level heatmap (e.g., strong in `Arrays`, weak in `Greedy Algorithms`) |
| 3 | User drills into a specific question | Sees question, their answer, correct answer, explanation, and associated tags |
| 4 | User can request "more questions like this" on a weak tag | Triggers a scoped generation job (Journey C, narrowed to that tag) |
| 5 | Attempt is saved permanently | Visible in attempt history for that question set/topic going forward |

---

## 9. Edge Cases to Account For in UX

- **Ingestion still in progress when user tries to start an exam** → UI should show generation progress and disable "Start Exam" until the question bank is ready, or offer to start with already-completed questions if streamed incrementally.
- **User uploads content that doesn't clearly map to an existing topic** → System should prompt the user to confirm whether it's a deep dive into an existing topic or a new topic root, rather than guessing silently.
- **Empty knowledge base, user picks "generate from existing dataset"** → Option should be disabled/hidden until at least one dataset exists.
- **Timed exam interrupted (browser closed)** → Server-side timer state should allow resuming with correctly reduced remaining time, or auto-submit if the time has fully elapsed.

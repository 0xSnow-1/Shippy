# Realistic Constraint Key

How Shippy proves it works, under constraints that mirror real operations use.

This file turns the PRD's target numbers into measured numbers.
It defines the constraints, the baselines, and the proof procedure.
It also records why other businesses in this domain trust the results.

---

## Scope status (2026-10-09)

The grilling session cut this file's roadmap extras to the spine.

Kept for v1: planted traps (C2), deterministic scoring (C3), frozen baselines with declared denominators, the refusal gate in CI, the log-completeness check, and the two-flag baseline split.

Deferred as future-work: the C1 episode harness and user simulator, pass^k, C4 fault injection, the C5 load envelope, the C6 scripted approver, C7 ceilings beyond the step cap, C8 soak, cron, replay, R_fault, paired-baseline automation, human baseline H, and the k-trial loop.

Known contradiction in C1: the phrasing-variant simulator needs a live LLM, yet section 7 costs it as offline-free with MockLLM.
Canned replies vary nothing, so offline k=5 proves nothing.
C1 stays future-work until it is redesigned.

The spine itself is unchanged: this file still defines how a believable number is produced.
Deferral changes when the extras run, not how honesty is reported.

---

## 1. Project frame

**Name:** Shippy.

**Who it serves:** an e-commerce or retail operations team.
Operations staff ask procedural questions.
They trigger gated follow-up actions from the same chat.
Shippy answers with citations, logs every decision, and blocks unsafe writes.

**Relation to the job description:**
The job description is a skill-coverage reference, not the product spec.
Shippy names no employer and copies no employer's internal systems.
It solves the same class of problem: SOP lookup, task creation, team notification.
Any agency or merchant team with SOPs and a ticket queue can adopt it.

## 2. The gap this file closes

The PRD states target numbers, for example:

- Groundedness at or above 95%.
- Refusal correctness at 100% of the eval set.
- p95 lookup latency under 8 seconds.
- Tool call success at or above 99%.

Those are claims until we measure them under realistic conditions.
A working demo proves possibility.
A demo never proves a rate.

Without constraints, our numbers have three problems:

1. The input is too clean. Real users type vaguely, ask about stale topics, and mix two questions in one message.
2. The environment is too kind. No timeouts, no rate limits, no flaky tools, no partial failures.
3. There is no baseline. A number nobody can compare to is a number nobody trusts.

This file fixes all three.
It defines a fixed procedure that produces a believable baseline metric.
Every later change compares against that baseline.

## 3. What makes a metric believable

A believable agent metric has five properties:

| Property | Meaning |
|---|---|
| Declared denominator | We state exactly which runs count, and which do not |
| Realistic inputs | Inputs match the messiness of real operations traffic |
| Repeated trials | We run each task k times, because one success proves nothing |
| Deterministic scoring | Code scores the result, not an LLM judge, wherever possible |
| Reproducible command | Anyone re-runs the same procedure from a fresh clone |

We apply these to every metric below.

## 4. The baseline ladder

We publish three baselines. Improvement means beating the one above.

| ID | Baseline | What it measures | How we run it |
|---|---|---|---|
| B0 | Naive RAG | Dense-only retrieval, no citation contract, no gate, direct answer | Same eval set, flag disables the contract |
| B1 | Shippy v1 | Hybrid retrieval, citation contract, gated writes, audit log | The product as built |
| H | Human status quo | A person answers the same questions from BookStack manually | Small self-measured sample, n stated openly |

B0 answers: "What does an unguarded LLM do on this corpus?"
B1 answers: "What does our harness add?"
H answers: "Is this faster than the manual process it replaces?"

We record B0 before we tune anything.
An honest pre-guardrail baseline is standard practice.
It shows where the weak surfaces are, and it makes later gains real.

## 5. The constraint layers

Eight layers. Each layer is a constraint we impose, plus the metric it produces.

### C1: Episode harness with simulated staff

We borrow the tau-bench pattern (Sierra, 2024).

An episode has three parts:

1. A hidden instruction for a simulated operations employee.
2. A visible opening message the employee sends to Shippy.
3. A programmatic check of the final state.

The user simulator is an LLM playing a staff member.
It phrases the same intent differently on each trial.
It may omit details, add noise, or ask a second question.

Scoring compares final state, not conversation style:

- Did the answer carry a source ID and a valid verbatim quote?
- Was the correct task created in the target store?
- Did a write action stay blocked until approval?
- Did a conflict case end in refusal?

The key metric is pass^k: the task succeeds on all k trials, averaged over tasks.
We run k = 5 offline with MockLLM, and k = 3 live with Bedrock.
pass^1 flatters unreliable agents.
pass^k exposes inconsistency, which is what operations teams actually fear.

### C2: Planted traps in the corpus

The seed script inserts known traps with known answers:

- A stale SOP superseded by a newer version.
- Two pages that conflict on the same procedure.
- A decoy page that matches the query keywords but answers a different question.
- A question with no answer in the corpus at all.

Traps turn refusal correctness into a scored fact.
Without traps, refusal behavior is an assertion, not a measurement.

### C3: Deterministic scoring

Code scores every core metric:

- Quote check: substring test against the retrieved chunk.
- Final state: database row comparison, tau-bench style.
- Log completeness: every run has a full event sequence, or the run fails.
- Routing: expected collection ID equals retrieved collection ID.

No LLM judge decides our headline numbers.
If we later add a judge for style or completeness, we calibrate it against human labels first, and we publish its precision and recall.

### C4: Fault injection at the adapters

Real stacks fail at their edges: tool APIs and retrieval.
We inject faults at our adapter boundary, behind an env var, and measure degradation.

| Fault | Simulates | Expected safe behavior |
|---|---|---|
| Latency spike / timeout | Slow provider, network congestion | Bounded wait, then clean error, never a hang |
| HTTP 5xx / 429 | Outage, rate limit | Bounded retries, then refusal or user-visible error |
| Empty body | Revoked token, silent proxy failure | Tool error surfaces, no fake success |
| Schema-violating tool output | API drift | Tool error surfaces, run closes with logged failure |
| Stale retrieval result | Out-of-date index | Version conflict triggers refusal |

We compute the robustness ratio R_fault: accuracy under fault, divided by baseline accuracy, capped at 1.

Declared limit: we do not inject faults at the LLM HTTP layer in v1.
The citation validator and step verifier reject incomplete model output by construction instead.
This is a design defense, not a measured number, and we say so in reports.

### C5: Load envelope

Latency measured on an idle system is fiction.

We run concurrent virtual users against the API, for example 10 to 20 in flight, and record p50 and p95 from that run only.
The p95 target of 8 seconds must hold under this load, not under a single curl.

`GET /stats` computes percentiles from `run_events`, so load runs feed the same store as live traffic.

### C6: Approval ground truth

The approval rate needs a ground truth, not a guess.

- Offline: a scripted approver applies a fixed policy (approve correct citations, reject missing quotes). This tests the gate wiring.
- Live: our own approvals during the demo and soak week give the real human number, with the sample size stated.

We never report an approval rate without its denominator and its source.

### C7: Budget ceilings

Every run operates under hard ceilings:

- Step cap: 4 (already enforced by the LangGraph runner).
- Token cost per run: recorded from usage, aggregated per task type.
- Wall-clock timeout per run: a run that exceeds it fails cleanly.

Cost per successful task is the honest efficiency number.
Cost per attempt flatters systems that retry a lot.

### C8: Repeat, soak, and replay

- Repeat: every eval task runs k times per release. This yields pass^k.
- Soak: the eval suite runs daily on a schedule for a sustained window. Drift shows up as a trend, not a surprise.
- Replay: `run_events` records real inputs. We replay recorded runs against a new version before we promote it. This is our shadow mode: zero risk, real inputs, offline cost.

A change ships only when it beats the frozen baseline on the same cases.
No subtracting averages from different test mixes. Paired comparison only.

## 6. The metric scorecard

Every row declares its denominator, its constraint, and its gate.

After the 2026-10-09 strip: only the refusal row and the unlogged-actions row block CI.
Every other row is reported with its denominator, never gated.

| Metric | Denominator | Constraint | Baseline | Gate |
|---|---|---|---|---|
| Groundedness | Non-refused answers in eval set | C1 phrasing variants | B0 | >= 95%, never below B0 |
| Refusal correctness | Planted trap cases | C2 | B0 | 100% |
| pass^k (task success) | k=5 offline, k=3 live, all episodes | C1 | B0 | Recorded, then raised each release |
| Tool call success | Required tool actions | C4 injected faults | Unfaulted run | >= 99% unfaulted; R_fault reported |
| p95 lookup latency | Lookups under load | C5 concurrent users | Idle latency | < 8s under load |
| Approval rate | Proposed writes | C6 (source stated) | - | >= 85%, sample size stated |
| Cost per successful task | Successful tasks | C7 ceilings | B0 | Recorded, then reduced |
| Unlogged actions | All runs | C3 log completeness | - | Exactly 0 |
| Cold-start demo | Fresh clone | - | - | Under 5 minutes |

Missing data stays missing.
We never convert an unmeasured metric into a passing one.

## 7. Cost and scope realism

This procedure must stay sized for a solo build.

| Layer | Cheap version | Cost |
|---|---|---|
| C1 episodes | 20 tasks x k=5 with MockLLM offline; smaller live sample | Offline: free. Live: a few hundred Haiku calls |
| C2 traps | Inserted once by the seed script | One-time |
| C3 scoring | Plain Python checks | Free |
| C4 faults | respx plus an env-var fault mode in adapters | Free, no new dependency required |
| C5 load | asyncio virtual users, local | Free |
| C6 scripted approver | Small policy function | Free |
| C7 budgets | Already logged in run_events | Free |
| C8 soak | Scheduled CI run of the offline suite | Free tier minutes |

Offline mode proves the pipeline and the gates.
Live mode produces the published numbers for the LLM-dependent metrics.
We label which mode produced every number.

## 8. How this maps to the roadmap

Superseded on 2026-10-09: the additions below were stripped from the roadmap by the grilling session.
This table stays as a record of planned future-work, not active tasks.

Decisions applied to `specs/constitution/roadmap.md` on 2026-10-08:

| Addition | Phase |
|---|---|
| Planted traps in the seed data | 1 |
| B0 naive-mode flag, frozen baseline before tuning, k-trial loop | 6 |
| Load script (10-20 virtual users), p95 under load | 7 |
| Episode smoke case with MockLLM | 9 |
| Fault-profile mode shared by all adapters | 10 |
| Episode harness, pass^k (k=5 offline, k=3 live) | 14 |
| Daily cron, paired baseline check, replay command | 16 |
| Soak week, human baseline H (n=5, self-measured) | 18 |

Mission records the denominator-and-baseline guarantee in its core promise.
Tech stack needs no changes: faults use respx plus env vars, and the runners use existing dependencies.

Every addition sits inside an existing phase as an extra task.
No phase grows beyond its 1-3 day size.

## 9. Why other businesses in this domain find this believable

**1. The method is published, not invented.**
Simulated-user episodes, final-state scoring, and pass^k come from tau-bench, a public benchmark from Sierra used across the industry.
Fault injection follows AgentChaos and general chaos engineering practice.
Golden sets, paired baselines, and shadow replay are standard industry practice.
An engineering manager recognizes these names.

**2. The numbers regenerate.**
A reviewer clones the repo and runs one command.
The same eval produces the same offline numbers.
Reproducibility is the cheapest credibility available.

**3. The scoring is mechanical.**
Substring checks and database comparisons have no judge bias.
Nobody can accuse the score of being a vibe.

**4. The failures are published too.**
We show B0, refusal misses, and R_fault degradation.
A report with only good news reads as marketing.
A report with baselines, denominators, and known weaknesses reads as engineering.

**5. The metrics map to business outcomes.**
An operations director does not care about BLEU scores.
They care: did the right task get created, was the stale procedure caught, how many seconds did it take, what did it cost.
Our scorecard speaks that language.

**6. The harness is domain-parameterized.**
The corpus, the policy, and the tool targets are configuration, not code.
A support team, a logistics team, or another agency swaps in their SOPs and reruns the same procedure.
The constraint key travels with the harness.
That is what makes it a tool, not a portfolio prop.

**7. The limits are stated.**
The corpus is synthetic. The approver sample is small. The soak uses self-use traffic.
We declare all of it.
Declared limits build more trust than silent ones.

## 10. Research synthesis: where these ideas come from

| Source | What we take |
|---|---|
| tau-bench (Sierra, arXiv 2406.12045) | Simulated user, domain policies, final-database-state scoring, pass^k consistency metric. Finding: SOTA agents score under 50% pass^1, and pass^8 drops below 25% in retail. Consistency matters more than averages. |
| tau2-bench (arXiv 2506.07982) | Dual-control episodes where the user also acts. Success drops about 20 points when a user must be guided. Justifies testing approval handoffs, not just answers. |
| AgentChaos (arXiv 2608.06790) | Runtime fault taxonomy: crash, omission, value faults on content and tool calls. Up to 50-point pass@1 drop under fault. Silent faults (truncation) do the most harm and are the hardest to diagnose. |
| mcp-chaos | Tool-call plane SLIs: tool-call success rate, effective tool availability, blast radius. Finding: 2% per-call failure compounds to a 12% task failure rate at 8 calls per task. Correlated bursts break naive retries. |
| faultkit | Inject faults at the SDK/API boundary, because mocks only test the mock. |
| Towards a Science of AI Agent Reliability (arXiv 2602.16666) | Reliability decomposed into consistency, robustness, predictability, safety. Robustness ratio R_fault = accuracy under fault / baseline accuracy. |
| Industry eval practice (Snowflake, Arthur, Papaya, Algolia) | Outcome, trajectory, safety, and operational metrics together. Golden sets frozen before tuning. Repeated runs for nondeterministic systems. Paired baseline-vs-challenger comparison only. |
| Shadow / canary patterns (agent patterns catalog) | Champion-challenger on recorded traffic before promotion. Our `run_events` replay is the zero-cost version of this. |
| NIST post-deployment monitoring direction (2026) | Metrics need declared denominators, cohorts, and explicit missing-data states. No universal agent score exists. |

## 11. Definition of done for this key

### v1 (active)

- [ ] Baseline numbers exist and are frozen before tuning: dense+contract, hybrid no-contract, naive both-off.
- [ ] Eval set contains planted traps, and refusal correctness scores 100% on them.
- [ ] Every published scorecard row has a declared denominator and a stated mode (offline or live).
- [ ] The whole procedure runs from a fresh clone with one documented command.

### Future-work (deferred 2026-10-09)

- [ ] pass^k reported for all episodes: k=5 offline, k=3 live.
- [ ] Fault profile runs green: no hangs, no unlogged actions, gates hold under fault.
- [ ] p95 measured under concurrent load, not idle.
- [ ] Replay command re-runs recorded events against a candidate build.
- [ ] Human baseline H recorded with n stated.

---

*Created: 2026-10-08*
*Last amended: 2026-10-08 - scope decisions folded in: adapter-only faults, k=5 offline / k=3 live, H self-measured, daily cron, roadmap mapping applied*
*Last amended: 2026-10-09 - grilling session: roadmap extras stripped to spine (see Scope status), C1 contradiction recorded, DoD split into active and future-work*
*Purpose: baseline and constraint definition for Shippy's reliability claims*

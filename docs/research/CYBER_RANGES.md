# Cyber Range Research (Agent 02)

Scope: AgentCyberRange as a reference architecture (studied closely, not copied wholesale), plus general cyber-range literature — reproducibility, multi-host design, lifecycle management, and maintained vulnerable-environment projects (DetectionLab, Vulhub, Infection Monkey).

Tagging convention used throughout: **FACT** (verifiable from primary source), **OUR INTERPRETATION** (a reasonable reading that isn't literally stated), **OUR DESIGN DECISION** (what GhostRange does about it).

---

## 1. AgentCyberRange (arXiv:2606.14295, June 2026) — primary reference architecture

**FACT** — AgentCyberRange bills itself as "the first open, multi-range infrastructure for measuring autonomous cyber attack capability in realistic cyber ranges" (arxiv.org/abs/2606.14295). It evaluates frontier AI systems across two stages:

- **Web exploitation**: 15 real-world web applications, 110 total vulnerabilities (18 zero-day, 56 one-day, 36 synthetic), 17 vulnerability classes.
- **Post-exploitation**: 8 independent cyber ranges, 156 total internal hosts, 43 "attack-chain" nodes, 113 decoy hosts, 39 network subnets, 12 post-exploitation technique categories.
- Six frontier AI systems evaluated under matched prompts/step budgets; best (GPT-5.5 + Codex) solved 16.1% of web-exploitation and 31.7% of post-exploitation tasks (33.0%/46.3% with hints).
- Ranges are built from **Docker containers connected by isolated virtual networks** — not full VMs, not cloud instances. This keeps ranges cheap and fast to instantiate but caps realism (no real hypervisor boundary, no genuine multi-cloud topology, container escape risk is different from VM escape risk).

### The "Cage" pipeline — four components (FACT, from arxiv.org/html/2606.14295)

1. **Agent adapter** — standardizes heterogeneous AI systems (Codex, Claude Code, etc.) behind one interface: task instructions and step budgets translate into agent-specific commands; adapter absorbs install/auth/protocol differences. New agent = one new adapter, no core pipeline changes.
2. **Agent manager** — controls runtime lifecycle: expands agents into trials inside isolated containers, injects env vars, records model interactions/token usage/execution trajectories, and captures termination status (completion, timeout, auth failure, step exhaustion) so infra failures can be told apart from agent failures.
3. **Benchmark manager** — separates benchmark logic from runtime ops: each benchmark exposes task instances plus a standard prepare/launch/cleanup interface. For pentest tasks specifically it deploys the web apps/ranges and tracks readiness/state across runs.
4. **Verifier module** — validates *agent-reported* results against *observable runtime evidence*, not agent self-report. Examples: confirms SQLi by reading back a planted random database canary; for post-exploitation, checks privilege markers under `/tmp` and `/root` to distinguish user- vs root-level compromise.

**OUR INTERPRETATION**: Cage's separation of concerns — adapter (agent-facing) / manager (lifecycle) / benchmark manager (environment-facing) / verifier (ground-truth-facing) — is a clean instance of a pattern GhostRange independently needs: an agent-facing boundary, an environment-facing boundary, and an *evidence-facing* boundary that never trusts the agent's own claims. This maps directly onto GhostRange's `adversary-adapter` (≈ agent adapter), `range-runtime` (≈ benchmark manager), and `evidence` + verification service (≈ verifier). The canary-based and filesystem-marker-based verification techniques are directly reusable primitives for GhostRange's own verification stage, not just Cage's.

**OUR DESIGN DECISION**: GhostRange adopts the verifier's core principle — *never grade the agent's self-reported outcome, always check independently observable state* — as a hard requirement for the Verification domain object (owned by evidence/provenance engineering, not this doc). We do NOT adopt Cage's container-only range substrate as-is; GhostRange's ranges are compiled to real Vultr infrastructure via OpenTofu because the product's premise is that fixes must be proven against infrastructure realistic enough that a "proven" remediation is credible for something resembling production, not just a benchmark container network. Container-based ranges remain a valid *cheap tier* for early/cheap forks (see GhostScheduler's compute-allocation tradeoffs, owned by Agent 08/Scheduler Researcher) but should not be GhostRange's only tier.

### What GhostRange must NOT copy from AgentCyberRange

- **Purpose mismatch**: Cage is an *evaluation harness* — its job ends at a verified pass/fail signal per task, scored across models for a leaderboard. GhostRange is a *production decision-support system* — its job is to let a human (or a gated pipeline) act on a verified remediation. If GhostRange's architecture converges to "run agents against fixed tasks, score them," it has quietly become a private clone of AgentCyberRange's benchmark instead of the tool the SecRespond/AgentCyberRange papers argue is missing. Concretely: GhostRange's `range-iac`-compiled ranges must be able to represent an *actual incident under investigation* (reconstructed from a real environment's topology), not only a fixed catalog of pre-authored vulnerable apps.
- **No adversarial verification of the verifier itself**: Cage's verifier is trusted infrastructure with no adversarial pressure against it. GhostRange's stated thesis explicitly includes adversarially verifying competing forks against each other — this is a genuinely different (harder) problem than Cage solves, and none of Cage's four components address it. Do not assume Cage's verifier design is sufficient once GhostRange adds cross-fork adversarial comparison; that logic has to be designed fresh (owned by execution-graph/security-boundary engineering).
- **Fixed task catalog vs. investigation-driven ranges**: Cage's benchmark manager deploys from a static catalog of pre-built vulnerable apps/ranges. GhostRange's ranges are reconstructions of *authorized infrastructure under investigation*, generated from RangeSpec, not chosen from a fixed shelf. Reusing Cage's "benchmark manager" pattern for lifecycle management is fine; reusing its assumption of a static task catalog is not.
- **Six-model, matched-budget comparison framing is not GhostRange's job**: GhostRange isn't trying to rank agents head-to-head under identical step budgets; it's trying to get *a* trustworthy remediation out of *whichever* agents/approaches it forks. Don't import leaderboard-style normalization logic (matched prompts, matched step counts across all forks) as a load-bearing design constraint — forks can and should differ in approach/resources, since GhostScheduler is explicitly meant to allocate compute unevenly based on how promising a branch looks.

---

## 2. General cyber-range literature: reproducibility, multi-host design, lifecycle

**OUR INTERPRETATION** (synthesized from the AgentCyberRange/SecRespond/CyberGym family of papers, which all converge on this point even though no single one states it as a "principle"): the load-bearing property across all reproducible-range work is **execution-based ground truth over self-report or static rubrics**. AgentCyberRange verifies via canaries/privilege markers; CyberGym verifies via sanitizer-confirmed crash-before/pass-after PoC execution; SecRespond uses checkpoint-decomposed grading tied to forensic artifacts. None of them trust an LLM's own narrative account of what it did. GhostRange's evidence/verification schema (Agent 12/13/14) should treat this as a hard constraint, not a nice-to-have: every remediation claim must resolve to an executable check against range state.

**OUR DESIGN DECISION** — range lifecycle stages GhostRange should support, informed by this literature and by Decisions.md's IaC choice:

1. **Compile**: RangeSpec (Pydantic model, `packages/contracts`) → OpenTofu plan + cloud-init, targeting Vultr.
2. **Instantiate**: apply plan → disposable Vultr resources; this is the "reconstruct authorized infrastructure" step.
3. **Seed**: apply the incident's known state (baseline config, planted vulnerabilities/compromise artifacts, or a snapshot-derived reconstruction) — this is GhostRange-specific; none of the surveyed ranges need to reconstruct a *specific real incident*, they author synthetic ones.
4. **Fork**: clone range state into N parallel "cyber worlds," one per candidate remediation — this is the step with no direct precedent in the surveyed literature (AgentCyberRange/CyberGym ranges are single-instance per trial, not forked-and-compared). This is GhostRange's own contribution and should be designed without assuming prior art solved it.
5. **Investigate/Remediate**: agent(s) act inside a fork, under the execution-graph safety boundary (Decisions.md #9).
6. **Verify**: execution-based checks against fork state (canaries, privilege markers, service-behavior probes, config diffs against policy) — directly informed by Cage's verifier and CyberGym's execution-based PoC confirmation.
7. **Adversarially compare**: forks are pitted against each other (not just pass/fail in isolation) — again, no direct precedent surveyed; design fresh.
8. **Teardown**: disposability is a first-class requirement (cost + blast-radius containment) — align with GhostScheduler's compute allocation and Vultr's per-second/hourly billing.

Reproducibility lesson from CyberGym (see OPEN_SOURCE.md for full classification): they only include vulnerabilities patched **at least three months prior**, specifically to reduce the chance the fix is already memorized in model training data / to keep the environment reconstructable from public commit history. **OUR INTERPRETATION**: this is a contamination-control technique for benchmarking, less relevant to GhostRange (which reconstructs *specific* authorized infra, not a public vuln corpus) — but the underlying discipline, "verify your reconstructed environment is actually reproducible from a pinned, checkable source state," should carry over to RangeSpec versioning.

---

## 3. Maintained vulnerable-environment projects

### DetectionLab
**FACT**: `clong/DetectionLab` automates a Windows-domain lab pre-loaded with security tooling (Splunk, Sysmon config, etc.) and logging best practices, aimed at defenders/detection engineers. Public commentary found during research indicates the project **is no longer actively maintained**; it also ships with default Vagrant credentials and states it has "not been hardened in any way."

**Reusable/instructive**: the idea of a maintained, opinionated "sensible logging defaults" baseline for a Windows host is exactly the kind of thing GhostRange's range templates need — an incident-response range is useless if the host doesn't have the telemetry an investigator would expect in production (Sysmon, EDR-equivalent, audit policy). DetectionLab's cloud-init-equivalent (Vagrant/Packer scripts) is worth reading as a reference for *what telemetry baseline to bake into `range-iac` cloud-init templates*, not for its code.

**What NOT to copy**: don't adopt the project as a dependency — it's unmaintained and explicitly not hardened, which is the opposite of what a disposable-but-realistic Vultr range needs (the range should be as close to a real hardening posture as the incident under investigation implies, configurable, not permanently soft-configured for lab convenience).

### Vulhub
**FACT**: `vulhub/vulhub`, MIT-licensed, is a large collection of pre-built vulnerable environments launched via Docker Compose, each with a README describing the specific CVE/misconfiguration and reproduction steps. Actively used/referenced across the security community; individual environment directories are contributed and reviewed.

**Reusable/instructive**: as a **library of pre-packaged, single-service vulnerable containers**, Vulhub is a fast way to seed a range with a *specific known vulnerability* (e.g., a particular CVE in a particular app version) without hand-authoring a vulnerable service from scratch. This is directly useful for the "Seed" lifecycle stage above when an incident's root cause maps to a cataloged CVE.

**What NOT to copy**: Vulhub environments are single-service, single-container, no-network-topology by design — the opposite of GhostRange's multi-host authorized-infrastructure reconstruction. Don't try to compose a whole range out of Vulhub containers as the primary range-authoring model; treat individual Vulhub compose files as optional *ingredients* injectable into a `range-iac`-compiled range, not as the range architecture itself.

### Infection Monkey
**FACT**: `guardicore/monkey` (developed by Guardicore, now maintained by Akamai), GPLv3, is an open-source breach-and-attack-simulation (BAS) platform: a "Monkey" agent that self-propagates/scans/simulates attack techniques across a network, and an "Island" C2/GUI server. It maps its actions to MITRE ATT&CK.

**Reusable/instructive**: the self-propagation/lateral-movement simulation model, and the pattern of a lightweight agent + central C2/reporting server, is a useful comparison point for `packages/adversary-adapter` — it's a simpler, narrower alternative to CALDERA specifically for lateral-movement/BAS scenarios. Its ATT&CK-mapped action log format is worth reviewing for evidence-schema ideas (each simulated action already carries a technique ID).

**What NOT to copy**: GhostRange already provisionally adopted CALDERA (broader technique coverage, active Atomic Red Team integration, REST API + plugin model — see OPEN_SOURCE.md). Don't add Infection Monkey as a second, overlapping adversary-emulation engine; GPLv3 licensing also imposes copyleft obligations that are unnecessary friction if any of its code were vendored (as opposed to just referencing its design). Classification: REFERENCE only, not ADOPT/ADAPT (see OPEN_SOURCE.md for the full classification table — this doc's finding is the "why").

---

## 4. Cross-cutting takeaways for GhostRange architecture

- **Verification must be execution-based, never self-report** (Cage, CyberGym, SecRespond all converge here independently) — this is the single most load-bearing shared finding across all three of this agent's research areas and should be treated as non-negotiable in the Evidence/Verification schema.
- **No surveyed system forks parallel competing remediations and adversarially compares them.** This is GhostRange's actual novel contribution relative to prior art — the research base gives strong primitives for single-branch execution/verification, none for cross-branch adversarial comparison. Design this piece with fresh thinking, not by analogy to a paper that doesn't exist yet.
- **Container-network ranges (Cage, CyberGym) are cheap and fast but cap realism**; Vultr-instantiated ranges (GhostRange's actual choice) are more expensive/slower to spin up but let the "disposable production-adjacent world" premise actually hold. This is a deliberate tradeoff, not free — GhostScheduler's compute-allocation design (Agent 08) should treat "which tier of range fidelity does this fork need" as a real scheduling variable, informed directly by this cost/realism tradeoff.
- **Unmaintained-but-instructive projects (DetectionLab) should be mined for defaults/config, not adopted as running dependencies.** Actively maintained, narrowly-scoped libraries (Vulhub) are safe to treat as ingredient sources. Overlapping engines with a chosen primary (Infection Monkey vs. CALDERA) should stay REFERENCE-only to avoid redundant integration surface.

# Mission

## What this project is

Shippy is a production-grade internal tool that answers procedural questions with citations and executes gated multi-step workflows through an auditable REST service.

It serves an e-commerce/retail operations team: staff ask SOP questions, get sourced answers, and trigger approved actions (create task, notify, email) without leaving their chat surface.

It exists as a real internal tool first.
Its value as a demonstration of AI engineering skill sets is a side effect of genuine operational quality, not the organizing principle.

It must never depend on any organizational account or internal system that the builder does not control.

## The core promise

Every answer names its source and includes a verbatim quote from retrieved content.

Every write action passes a validation gate and requires human approval.

Every run is fully reconstructable from an append-only decision log.

When confidence is low or sources conflict, the system refuses and points to the original document instead of guessing.

## Success looks like

A fresh checkout reaches a working demo in under five minutes via `docker compose up`.

A user asks a question in Slack, receives a cited answer, approves the proposed action with a button, and can reconstruct the whole decision from `GET /runs/{id}`.

The credential-free path (`scripts/demo.sh`) proves the same flow end-to-end with local fallbacks, so CI and new contributors never need live accounts.

The eval suite runs in CI and blocks merges when groundedness or refusal correctness regresses.

Every external concept the builder touches (PAT, respx, OAuth flows) is explained in the project's own learning docs, so no integration is a black box.

## What this project is not

It is not a general autonomous agent.

It is not a replacement for BookStack, Asana, Slack, or Gmail.

It does not implement SOP enforcement, ChatOps, or autonomous scheduling (roadmap only).

## Operating principles

Scope is ruthless: a shipped thin slice beats a partial deep slice.

Live integration code and demo integration code share one interface, so the no-credential path proves the contract the live path ships with.

Every phase of work ends with a verification command that can be run locally.

Docs are written as decisions are made, not after the fact.

Learning docs use Simplified Technical English style: short active sentences, single-meaning words, no optional words.

---
*Created: 2026-10-07*
*Last amended: 2026-10-07 - reframed from portfolio piece to internal tool "Shippy"; Slack as primary human surface*

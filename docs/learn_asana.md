# Learn Asana

This document explains the Asana integration in simple language.
It covers three things: PAT, respx, and contract tests.
Read it before you work on the `create_task` tool.
The language follows Simplified Technical English rules: short sentences, active voice, one meaning per word.

## 1. What Asana is

Asana is a task tracking service.
Teams use it to organize work.
Our tool creates tasks in Asana when a person approves a workflow.

## 2. What PAT is

PAT means Personal Access Token.
A PAT is a long string of characters.
It proves your identity to the Asana API.
You can think of it as a password that only works for the API.

Rules for your PAT:

- Never write the PAT in code.
- Never commit the PAT to git.
- Store the PAT in the `.env` file only.
- Treat the PAT like your email password.

## 3. How to create a PAT

Do these steps once:

1. Open Asana in your browser.
2. Click your profile photo.
3. Click **My Settings**.
4. Click **Apps**.
5. Click **Manage Developer Apps**.
6. Click **+ Create new token**.
7. Give the token a name, for example `shippy-dev`.
8. Click **Create token**.
9. Copy the token now. Asana shows it one time only.
10. Paste it into your `.env` file as `ASANA_PAT=...`.

Now create a scratch project:

1. In Asana, create a new project called `shippy-scratch`.
2. Copy its project ID from the URL into `.env` as `ASANA_PROJECT_GID=...`.

You are ready. Our tool can now create tasks.

## 4. How the tool uses the PAT

The `create_task` tool sends one HTTP request:

```
POST https://app.asana.com/api/1.0/tasks
Authorization: Bearer <your PAT>
```

The request body has three fields:

- `data[name]` - the task title
- `data[notes]` - the description, including the SOP reference
- `data[projects]` - your scratch project ID

Asana creates the task and returns its ID.
The tool saves that ID in the run log.

## 5. What respx is

respx is a Python test library.
It intercepts HTTP requests in tests.
It stops requests from leaving your computer.
It checks that the request matches what you expect.
It then returns a fake response.

Why we use it:

- Tests run without a PAT.
- Tests run in CI with no internet.
- Tests run fast.
- Tests fail when the request shape changes.

## 6. What a contract test is

A contract test checks one thing: does our request match the API's rules?

For Asana, the contract test checks:

- The URL is `https://app.asana.com/api/1.0/tasks`.
- The header `Authorization` starts with `Bearer `.
- The body contains `data`, and `data` contains `name` and `projects`.

If Asana changes its API, the test fails before production breaks.

## 7. How the two test modes work

The tool has two modes. One interface. Two implementations.

| Mode | Target | Used when |
|---|---|---|
| Live | Real Asana API | `.env` has a PAT |
| Fallback | Local SQLite table | No PAT (CI, demo.sh) |

Both modes share one function signature: `create_task(title, description, project, sop_ref)`.

Tests cover both modes:

- `test_tools_task.py::test_live_contract` uses respx. No PAT needed.
- `test_tools_task.py::test_fallback_store` uses SQLite. No network.

## 8. Safety rules

- Only create tasks in `shippy-scratch`.
- Delete test tasks after a manual test.
- If a PAT leaks, revoke it in Asana at once. Create a new one.
- Never print the PAT in logs or error messages.

## 9. Your first test run

```bash
uv run pytest tests/test_tools_task.py -v
```

Expected result: all tests pass, with no network and no PAT.

Then, for one live test:

```bash
uv run python -m shippy.tools.create_task --demo
```

Check your `shippy-scratch` project. The test task must be there. Delete it.

## 10. Quick reference

| Term | One-line meaning |
|---|---|
| PAT | A secret string that proves your identity to the Asana API |
| respx | A test library that fakes HTTP requests |
| Contract test | A test that checks our request matches the API rules |
| Fallback mode | Local storage used when no credentials exist |
| `.env` | The file that holds secrets; git ignores it |
| GID | Asana's numeric ID for an object |

Next: read the `create_task` source in `src/shippy/tools/task.py`, then run the tests above.

---
*Created: 2026-10-07*
*Style: STE-inspired (ASD-STE100 rules, no compliance tooling)*

# Learn Gmail

This document explains the Gmail integration in simple language.
It covers three things: OAuth, the send request, and contract tests.
Read it before you work on the `send_email` tool.
The language follows Simplified Technical English rules: short sentences, active voice, one meaning per word.

## 1. What Gmail API is

Gmail is Google's email service.
Its API lets a program send mail for a mailbox.
Our tool sends one email when a person approves a notification.

## 2. What OAuth is

OAuth is a way to grant limited access without sharing a password.
Google issues three credentials to our tool:

| Credential | What it is | Where it lives |
|---|---|---|
| Client ID | The app's public name | `.env` as `GOOGLE_OAUTH_CLIENT_ID` |
| Client secret | The app's private password | `.env` as `GOOGLE_OAUTH_CLIENT_SECRET` |
| Refresh token | A long-lived key that mints access tokens | `.env` as `GMAIL_REFRESH_TOKEN` |

Rules for all three:

- Never write them in code.
- Never commit them to git.
- Store them in the `.env` file only.
- Treat them like your email password.

## 3. How the access token works

An access token is a short-lived key.
Our tool gets one fresh token per send.
It exchanges the refresh token for an access token in one POST:

```
POST https://oauth2.googleapis.com/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
&client_id=<your client ID>
&client_secret=<your client secret>
&refresh_token=<your refresh token>
```

Google returns JSON with an `access_token` field.
The tool uses that token in the next request.

## 4. How the tool sends the mail

The tool sends one POST to the Gmail send endpoint:

```
POST https://gmail.googleapis.com/gmail/v1/users/me/messages/send
Authorization: Bearer <your access token>
Content-Type: application/json

{"raw": "<base64url-encoded RFC 822 message>"}
```

`users/me` means the mailbox that owns the refresh token.

The `raw` field holds the full email text.
The text follows the RFC 822 format:

```
To: ops@example.com
Subject: Refund window exception

The SOP allows a 30-day refund window.
```

The tool encodes that text in two steps:

1. Build the RFC 822 string with `To`, `Subject`, a blank line, then the body.
2. Encode it with base64url, which uses `-` and `_` instead of `+` and `/`.

Gmail creates the message and returns its ID.
The tool stores that ID in the result.

## 5. What the contract test checks

The `respx` test in `tests/test_tools_email.py` checks:

- The token URL is `https://oauth2.googleapis.com/token`.
- The token request carries `grant_type`, `client_id`, `client_secret`, and `refresh_token`.
- The send URL is `https://gmail.googleapis.com/gmail/v1/users/me/messages/send`.
- The send header `Authorization` starts with `Bearer `.
- The decoded `raw` body matches our RFC 822 text.

If Google changes either API, the test fails before production breaks.

## 6. The two test modes

The tool has two modes. One interface. Two implementations.

| Mode | Target | Used when |
|---|---|---|
| Live | Real Gmail API | `.env` has all three OAuth variables |
| Fallback | Local `outbox` table | Any variable is missing (tests, CI, demos) |

Both modes share one function signature: `send_email(to, subject, body)`.
Both return `{mode, message_id, message_ref}`.

Tests cover both modes:

- `test_tools_email.py::test_live_contract` uses respx. No credentials needed.
- `test_tools_email.py::test_fallback_outbox` uses SQLite. No network.

## 7. Safety rules

- Send test mail only to mailboxes you own.
- If a refresh token leaks, revoke it in the Google Cloud console at once.
- Never print any of the three credentials in logs or error messages.
- Google can reduce a Testing-mode app to 100 test users. Keep the recipient list small.

## 8. Your first test run

```bash
uv run pytest tests/test_tools_email.py -v
```

Expected result: all tests pass, with no network and no credentials.

## 9. Quick reference

| Term | One-line meaning |
|---|---|
| OAuth | A way to grant limited access without sharing a password |
| Access token | A short-lived key that authorizes one API call |
| Refresh token | A long-lived key that mints new access tokens |
| base64url | An encoding that uses `-` and `_` so it fits in a URL and JSON |
| RFC 822 | The standard text format for an email message |
| Outbox | Our local SQLite table that holds fallback emails |
| respx | A test library that fakes HTTP requests |

Next: read the `send_email` source in `shippy/tools_email.py`, then run the tests above.

---
*Created: 2026-10-19*
*Style: STE-inspired (ASD-STE100 rules, no compliance tooling)*

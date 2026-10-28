# Roadmap

Status: **planning**. Nothing on this page is built yet. Each stage gets a short design note in `docs/decisions/` before work starts.

## Why

Aiana remembers what happened in past Claude Code sessions. It does not yet remember what is **waiting to happen**.

A typical case: a session finishes step 2 of a cleanup and says "the 48-hour check ends tonight at 22:40 UTC, then I can start step 3." Today that promise lives in one of two places, and both are bad.

- **In the session's context.** The session has to stay open, and the waiting work costs tokens on every turn.
- **In a memory note that every session loads.** The note costs tokens in every session, including the many that have nothing to do with it.

When several sessions run at once, neither option tells the right session at the right time.

## The idea: a parking brake

A session **sets the brake** on a piece of work: what it is, when it can move again, and exactly how to pick it up. Then the session lets go of it. Nothing about the work sits in any context.

When the brake's time comes, aiana surfaces it. Any session can **release the brake** and continue from the stored resume prompt.

```
Without a brake:  wait → keep it in context → hope a session is open at 22:40
With a brake:     set brake → forget → due at 22:40 → surfaced → release → continue
```

Aiana is the right home for this.

- It already stores memory outside the prompt and recalls it on demand.
- Its Claude Code hooks already run at session start, the natural place to say "this is due."
- Every session on the Mac shares one aiana store, so parallel sessions see the same brakes.
- A brake gains context from the recorded sessions that set it.

## Stage 1: the brake

Add brakes to aiana's storage, MCP server and CLI.

**A brake holds:**

| Field | Purpose |
| --- | --- |
| title | One line, such as "git-steer cleanup, step 3" |
| project | The project it belongs to |
| due | When it can move again (UTC), or a condition to check |
| resume prompt | Everything a fresh session needs to continue, written by the session that set it |
| needs approval | True when the next step is destructive or outward-facing |
| refs | Links to issues, PRs, ADRs, and the session that set it |
| status | `set`, `due`, `released`, `done`, `cancelled` |

**New MCP tools** (names are proposals):

| Tool | What it does |
| --- | --- |
| `brake_set` | Park a piece of work with a due time and resume prompt |
| `brake_list` | List brakes, by default only the ones that are due |
| `brake_release` | Mark a brake as picked up and return its resume prompt |
| `brake_update` | Snooze, edit, finish or cancel a brake |

**Session start injects only what is due.** One line per due brake, and nothing when none are due:

```
[aiana] 1 brake due: git-steer cleanup, step 3 (needs your approval). Use brake_release to continue.
```

At the same time, the existing context injector becomes cheaper by default. Today it adds up to ten recent memories per section to every session. That becomes opt-in, so a session pays only for what it asks for.

**Done when** a session can set a brake, close, and a new session opened after the due time sees exactly one line about it and can continue from the resume prompt.

## Stage 2: the waker

Brakes should surface even when no session is open.

- **A launchd agent** checks for due brakes every few minutes. It is local and needs no cloud.
- **A macOS notification** announces each due brake.
- **Optional auto-resume** starts a headless Claude Code session with the resume prompt, only for brakes marked safe.
- **Approval brakes never auto-run.** The notification asks for the user's go-ahead, and the work waits until a person releases it.

**Done when** a brake due at a set time produces a notification within five minutes, with no session open.

## Stage 3 (possible): a Mac app

A native macOS app for aiana, in the style of [AFM Studio](https://github.com/ry-ops/afm-studio): a SwiftUI app with a menu-bar presence, installed to `/Applications`, that sets up its own Claude Code wiring.

**What it could show:**

- **Brakes.** Due and upcoming brakes with countdowns, plus release, snooze, cancel and copy-resume-prompt buttons. Approval brakes get a clear go or no-go.
- **Menu bar.** A badge with the number of due brakes, and a quick list.
- **Sessions.** Recorded sessions by project, with search.
- **Memory.** Semantic and full-text search, preferences, and feedback on recalled memory.
- **Health.** Which storage backends are running (SQLite, Qdrant, Redis, mem0), and the waker's last check.
- **Setup.** Install the hooks, register the MCP server with Claude Code and Claude Desktop, and start or stop the waker, with backups of any config it touches.

**Possible extras:**

- On-device summaries of sessions and brakes through AFM Studio's MCP server, so drafts never leave the Mac.
- Notifications that open the app straight to the brake.

**Open design questions for the app:**

- How the Swift app talks to the Python core: a local HTTP API on `127.0.0.1`, the CLI with JSON output, or reading SQLite directly (read-only).
- Whether the app replaces the launchd waker or controls it.
- Whether the app lives in this repo or its own.

## Not in scope

- **No cloud.** Brakes, the waker and the app stay on the Mac, like the rest of aiana.
- **No acting on other systems.** Aiana surfaces and hands off work. The session that releases a brake does the work, with the user's usual approvals.

## Bookmarked for later

These ideas are parked for discussion. They are not planned yet.

- **Update other projects' roadmaps.** Add a tool that lets a session update the `ROADMAP.md` of another repo or project. For example, when a brake is released or work finishes, the roadmap of the project it belongs to would be updated too. How it writes, what it may touch and who approves the change are all open.

## Open questions

1. Tool and CLI names: `brake_*`, or something else.
2. Whether `due` supports conditions as well as times, such as "when PR #12 merges." Conditions mean the waker has to call outside services.
3. How a session that sets a brake writes a good resume prompt: free text, or a template with goal, state, next step and stop conditions.
4. Whether brakes need a priority, or due time alone is enough.
5. Whether stage 3 is worth building, or stage 2's notifications are enough.

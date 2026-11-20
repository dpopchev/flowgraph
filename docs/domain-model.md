# Domain model of the record

What a flowgraph record holds: the item types, what each carries, and how an
item moves. Agreed by the developer in conversation on 2026-11-20, remark by
remark; the open questions at the end are the agent's readings, not yet
confirmed. It replaces the model of board 1 (`docs/board-review.md`, group 1).

## Levels

Containment is a typed `parent` reference, never inheritance: each type below
is its own type, with no base class and no generic node that carries a level.

| Level | Types | Holds | Stands alone |
|---|---|---|---|
| Top | `Feature` | Stories, Bugs, Spikes, Upkeeps; never Tasks | yes |
| Work item | `Story`, `Bug`, `Spike`, `Upkeep` | its Tasks | yes, or under one Feature |
| Bottom | `Task` | nothing | no: exactly one work item above it |

Standing alone is a value of `parent`, not a missing one.

## Work item types

A type exists because the work ends differently, never because of its size.

| Type | Is | Completed when |
|---|---|---|
| `Story` | new behavior | the behavior is on `main` |
| `Bug` | a behavior that fails | the fixed behavior is on `main` |
| `Spike` | a question to answer | the decision is written |
| `Upkeep` | work that keeps the behavior and changes the inside | the behavior is proven unchanged on `main` |

A `Feature` groups work items toward one bigger outcome. It is not worked on
directly, so it holds no Task.

## Titles

| Title | On | Form | Example |
|---|---|---|---|
| outcome | `Feature`, `Story`, `Bug`, `Spike`, `Upkeep` | a directional verb, the target metric or behavior, the quantified shift or target state | Extend where fgraph finds its record from its own directory to any subdirectory |
| output | `Task` | an imperative verb, the specific artifact, the target state or constraint | Add locate() to src/flowgraph/record.py, returning the record of a directory |

An outcome title describes a measurable change in user behavior, business
value or system state, never the work done to get there:

```text
[Directional verb] + [target metric or behavior] + [quantified shift or target state]
```

| Change in | Example |
|---|---|
| user behavior | Cut the commands a developer runs to see the Tasks of a Story from two to one |
| business value | Raise the kinds of work a project tracks with fgraph from one to five |
| system state | Extend where fgraph finds its record from its own directory to any subdirectory |

An output title describes a discrete, verifiable deliverable or system change
with a binary Definition of Done -- it is there or it is not:

```text
[Imperative verb] + [specific artifact] + [target state or constraint]
```

| Ends in | Example |
|---|---|
| an artifact created | Create src/flowgraph/task.py holding the Task type and its constructor |
| an artifact changed | Add the start command to src/flowgraph/cli.py, exiting 2 on a Story without a Task |
| a constraint held | Split src/flowgraph/story.py so that no module exceeds 300 lines |

Both forms are the developer's, given on 2026-11-20; the examples are the
agent's wording.

## Acceptance criteria

Every item states what must be true once it is completed, in the form its
work ends in.

| Kind | Count | Criterion |
|---|---|---|
| `Feature` | one or more | a statement of what the user experiences, free form |
| `Story` | exactly one | Given (initial state), When (action), Then (expected state) |
| `Bug` | exactly one | Observed (what happens) and Expected (what we wish to see) |
| `Upkeep` | exactly one | Given / When / Then, where the When already runs and the Then says it still holds |
| `Spike` | exactly one | a hypothesis, as a yes/no question |
| `Task` | exactly one | Expected output: an artifact created, or a content change in a named artifact |

One example per kind:

- Feature: "A developer sees every work item of the project by bucket with
  one command."
- Story: Given a record with one Story in Backlog, When `fgraph start` is run
  on it, Then it is a `StartedStory` shown in InProgress.
- Bug: Observed: `fgraph --dir` given a file prints a traceback. Expected: it
  exits 2 and names the path.
- Upkeep: Given a directory holding `.fgraph/`, When `fgraph` runs there, Then
  it still uses `./.fgraph/` and exits 0.
- Upkeep, the whole suite: Given `main`, When `make check` runs, Then it still
  passes.
- Spike: "Can one file per item hold the record?"
- Task: created, `src/flowgraph/story.py`; or changed, `src/flowgraph/cli.py`
  gains the `start` command.

Notes:

- A Feature is broken down into Stories, as a rule of thumb one Story per
  criterion.
- An Upkeep names the behavior that must still hold, never a test: the Upkeep
  may itself move or rename a test while the behavior holds.
- A Task's title names the action, the artifact and its target state; its
  expected output states what is there afterwards, so the Task is done or not
  done, never partly.

## Attributes

What each type carries in Backlog. The description is optional free text on
every type.

| Type | Attributes |
|---|---|
| `Feature` | id, outcome title, description, experience criteria, created |
| `Story` | id, outcome title, description, parent, Given / When / Then, created |
| `Bug` | id, outcome title, description, parent, observed, expected, created |
| `Upkeep` | id, outcome title, description, parent, Given / When / Then, created |
| `Spike` | id, outcome title, description, parent, hypothesis, created |
| `Task` | id, output title, description, parent, expected output, created |

`parent` is a Feature or standing alone for the four work items, and exactly
one work item for a Task.

## States are types

The state of an item is its type, so an item carries only what its state
needs. The same five exist for `Story`, `Bug`, `Spike`, `Upkeep` and `Task`;
`Story` is shown.

| Type | Bucket | Adds |
|---|---|---|
| `Story` | Backlog | the attributes of its kind, above |
| `StartedStory` | InProgress | started |
| `BlockedStory` | InProgress, shown as blocked | reason, since, waiting on |
| `CompletedStory` | Completed | completed on, evidence |
| `RemovedStory` | Removed | removed on, reason |

`CompletedSpike` also adds the decision, which answers its hypothesis.

- A bucket is derived from the type; it is never a stored field.
- Blocked is not a bucket: a blocked item stays in InProgress and shows as
  blocked.
- Removed stands apart from the flow and keeps what dropped out, with its
  date and reason. Nothing is deleted.
- Cycle time and age are derived from the dates, never stored.

## Direction

```text
Backlog --start--> InProgress --complete--> Completed

Removed: apart, reached by remove
```

| Move | From | To |
|---|---|---|
| start | `X` | `StartedX` |
| block | `StartedX` | `BlockedX` |
| unblock | `BlockedX` | `StartedX` |
| complete | `StartedX` | `CompletedX` |
| remove | `X`, `StartedX`, `BlockedX` | `RemovedX` |

Completed and Removed are terminal, and no move goes backwards.

## Evidence

A completed item carries the proof that it is completed. For a work item,
under a Feature or standing alone, that is the commit on `main` that holds it.

| Type | Evidence on its Completed type |
|---|---|
| `Story`, `Bug`, `Upkeep`, `Spike` | the commit on `main` |
| `Task` | its commit |

## Rules

- Every item is completed through `fgraph`. flowgraph is a framework: later
  `fgraph` wraps git as well.
- A Feature never holds a Task.
- A Task has exactly one parent among `Story`, `Bug`, `Spike` and `Upkeep`.
  It never stands alone and never shows at the level of the work items.
- A `Story`, `Bug`, `Spike` or `Upkeep` cannot start without at least one
  written Task.
- A work item is completed only once it is on `main`.
- Until `fgraph` wraps git, `complete` records the commit and does not check
  it against `main`.

## Ids

An id is the prefix of its kind and a number counted from 1 per kind, written
with at least four digits. `fgraph` hands out the next free number.

| Kind | Id |
|---|---|
| `Feature` | `F-0001` |
| `Story` | `ST-0001` |
| `Bug` | `B-0001` |
| `Spike` | `SP-0001` |
| `Upkeep` | `U-0001` |
| `Task` | `T-0001`, unique across the record |

## Persistence

The record is plain TOML files tracked by git: git is its history, its backup
and its merge tool.

- One directory, `items/`, holds every item: one file per work item with its
  Tasks inside it, named by its id, `items/ST-0001.toml`. The prefix of the id
  is the one place that says the kind, so there is no directory per kind.
- The file holds a `state` line naming the type it loads into and only the
  fields that state needs. The path follows from the id alone, so a file
  never moves.
- A Task is one `[[tasks]]` table inside the file of its work item, in the
  order written, with its own `state` line. Its parent is the file that holds
  it, so no `parent` field is stored. The next Task id is one above the
  highest in any file of the record.
- Each kind reads the files of its own prefix. A file with a prefix no kind
  knows is left alone; nothing reports it yet.
- A command loads a work item whole, changes it and saves it whole. The file
  is validated as it is read; a write is read back before it replaces the
  file.

Who writes what, so that two branches never change the same file or hand out
the same number:

| Write | Where |
|---|---|
| add a work item or a Task | `main` |
| start a work item | `main`, before its branch is made |
| start and complete its Tasks | its branch |
| complete the work item | `main`, after the merge |

Until `fgraph` wraps git this is a convention; it cannot refuse an `add` made
off `main`.

## Left out

- Class of service (expedite, fixed date, standard): left out for now. It
  comes back when the order of pulling work must differ by urgency.

## From board 1

| Board 1 | Here |
|---|---|
| Epic | `Feature` |
| issue ending in a behavior | `Story` |
| issue ending in a step | `Upkeep` |
| bug | `Bug` |
| spike | `Spike` |
| Task | `Task` |
| todo | the bare type, in Backlog |
| doing | `StartedX` |
| blocked, a state | `BlockedX`, a type shown in InProgress |
| done | `CompletedX` |
| pruned | `RemovedX` |

## Open questions

- Does a Feature have a stored state? The reading: no, its bucket is derived
  from the items it groups, and it is complete when each is Completed or
  Removed, with no evidence of its own.
- Does a Task also carry a check command that `fgraph` runs at `complete`?
  The reading: no, its expected output and its commit are enough.
- Must a Story under a Feature name the Feature criterion it realizes? The
  reading: no, one Story per criterion stays a rule of thumb.
- Can a Task start before its work item is started? The reading: no.
- Can a started work item whose Tasks were all removed still be completed, or
  must it be removed?
- Can an item be blocked before it is started? The reading: no, only a
  started item.
- What can the title constructors check? A first word against a closed list
  of verbs -- directional for an outcome, imperative for an output -- and a
  named artifact can be checked; that the shift is measurable cannot.
- How does the outcome form read on a `Spike`, whose work ends in a decision
  and not in a metric? The reading: its target state is the question settled,
  as in "Settle whether one file per item can hold the record".

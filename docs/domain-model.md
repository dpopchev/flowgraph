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

A kind whose criterion and payload match another's shares its state types and
names them as its own: `Story` and `Upkeep` are both `WorkItem`, told apart
by the kind on their id (Persistence).

- A bucket is derived from the type; it is never a stored field.
- Blocked is not a bucket: a blocked item stays in InProgress and shows as
  blocked.
- Removed stands apart from the flow and keeps what dropped out, with its
  date and reason. Nothing is deleted. `fgraph status` lists the heading
  Removed after Completed only when an item is removed, each with its reason.
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

## Order

The Backlog is a queue: the order work is to be pulled in, across every kind
of work item. The developer said so on 2026-11-21.

- A work item joins the end of the queue when it is added.
- `reorder` puts one work item of the Backlog right before another. It is not
  a move: the type of the item stays, only its place changes.
- The queue is its own aggregate, apart from the items: it places work items
  by id, each once. A work item nobody placed follows the placed ones in the
  order it was added; those added at one time, by kind and number.
- A work item that leaves the Backlog leaves the queue with it: the other
  buckets are not listed by the queue.
- A reorder names two work items in Backlog; one that is not there, or the
  same one twice, is refused.
- Completed is listed the last completed first, the developer's decision of
  2026-11-21: by the completed time each work item holds, so the newest
  landing is on top; those completed at one time, by kind and number.
- InProgress is listed the last started first, by the same decision: by the
  started time each work item holds; those started at one time, by kind and
  number. A blocked Task does not move its work item in the list.
- Removed is listed by kind and number.
- `fgraph status` lists the top 5 under each heading, the developer's
  decision of 2026-11-21: the first five of the Features, of the Backlog, of
  InProgress, of Completed and of Removed, in the order each is listed in,
  then one line `... N more` for the N it does not list. The count beside the
  heading stays that of all its items, and a heading of five or fewer has no
  such line. `fgraph status --all` lists every one.
- `fgraph status` lists a work item under InProgress with its progress, the
  developer's decision of 2026-11-21: `<completed>/<all> T`, its Tasks
  completed of all it holds, between its id and its title, written as board
  1's watch writes it -- `ST-0001  1/3 T  <title>`. A started or a blocked
  Task is not completed. The lines of Backlog, Completed and Removed carry no
  progress. The Tasks are those the record status reads holds: the row of a
  work item is read with its Tasks, each with its state.
- Under a work item of InProgress `fgraph status` lists each Task of it being
  worked, the developer's decision of 2026-11-21, after board 1's watch: the
  started Task as `    => T-0001  <title>`, and a blocked one as
  `    !  T-0002  <title>  -- waiting on <what>`, in the order the file holds
  them. A Task in Backlog or completed is not listed. A Task line belongs to
  its work item: it does not count toward the top 5 of the heading, nor in
  the count beside it.

## Amendment

The wording of a work item can be corrected while it waits: a work item in
Backlog is amended through `fgraph`. Agreed by the developer on 2026-11-21.

- `amend` rewrites the title, the description and the parts of the criterion
  -- Given, When, Then -- one alone or several together. A part it does not
  name stays as it was.
- It is not a move: the type of the item stays, and so do its id, its created
  time, its Tasks and its place in the queue.
- Each part goes through the constructor an `add` uses, so a blank title or a
  blank part of the criterion is refused. The description is optional free
  text: a blank one clears it.
- An amendment that names no part is refused.
- Only a work item in Backlog is amended: a started or a completed one is
  refused, since its wording is what the work was started on. A Task is not
  amended yet.

## Evidence

A completed item carries the proof that it is completed. For a work item,
under a Feature or standing alone, that is the commit on `main` that holds it.

| Type | Evidence on its Completed type |
|---|---|
| `Story`, `Bug`, `Upkeep`, `Spike` | the commit on `main` |
| `Task` | its commit |

## Rules

- Every item is completed through `fgraph`. flowgraph is a framework: it
  wraps git step by step, starting with the start of a work item
  (Persistence).
- A Feature never holds a Task.
- A Task has exactly one parent among `Story`, `Bug`, `Spike` and `Upkeep`.
  It never stands alone and never shows at the level of the work items.
- A `Story`, `Bug`, `Spike` or `Upkeep` cannot start without at least one
  written Task.
- One work item holds at most one started Task; a blocked Task does not
  count. Agreed by the developer on 2026-11-21. A second Task is started once
  the first is completed or blocked; an unblock makes a Task started, so it
  is refused the same way beside a started Task. The refusal names the
  started Task, and a file that holds two started Tasks is refused when it is
  read, since no move reaches it.
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
| `Task` | `T-0001`, unique across the record and the worktrees of its repository |

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
  it, so no `parent` field is stored.
- The next Task id is one above the highest in the record of every worktree
  of the repository, the developer's decision of 2026-11-21: `main` and the
  worktree of a started work item hand out no id twice. The record of another
  worktree is the directory at the same path inside it; its files are read as
  they are, committed or not. It covers the worktrees of one repository, not
  two clones, and a record outside a git work tree counts its own files.
- A started item is kept as `state = "started"` with its `started` time,
  beside the fields it had in Backlog. Only a started Story's file may hold a
  started Task; it is read back through the moves that start them, so a file
  holds no state those moves could not reach.
- A blocked Task is kept as `state = "blocked"` with its `started` time, its
  `since` time, its `reason` and its `waiting_on`. Only a started work item's
  file may hold one, and it is read back through its start and its block.
  `fgraph block` blocks a started Task. A blocked Task is not started or
  completed, and its work item is not completed while it is blocked.
- `fgraph unblock` takes a blocked Task back to started, with the started
  time it had. Its reason, since and what it waited on leave the file, which
  keeps only what a state needs; git keeps the block. A Task that is not
  blocked is refused. Blocking and unblocking a work item are not built.
- A completed item is kept as `state = "completed"` with its `started` and
  `completed` times and its `commit` sha. A started Story's file may hold
  completed Tasks; a completed Story's file holds only completed Tasks, since
  a Story completes once every Task of it has.
- A removed work item is kept as `state = "removed"` with its `removed` time
  and its `reason`, beside the fields and the Tasks it had in Backlog.
  `fgraph remove` removes a work item in Backlog; a removed one takes no Task,
  no amend and no move, and leaves the queue as a started one does. Removing
  a Task, and removing a started work item, which has a branch and a
  worktree, are not built.
- An Upkeep is kept as `items/U-0001.toml`, in the shape of a Story file:
  the same fields in each state, `started`, `completed` and `commit` once it
  has moved, and its Tasks as `[[tasks]]` tables, read back through the
  moves.
- A Bug is kept as `items/B-0001.toml`, in the same shape but for its
  criterion table: `observed` and `expected` where a Story has `given`,
  `when` and `then`. A file that holds the criterion of another kind is
  refused when it is read.
- A Spike is kept as `items/SP-0001.toml`, its criterion table holding its
  `hypothesis`. It is completed with the decision that answers it,
  `fgraph complete SP-0001 --commit SHA --decision TEXT`, and `fgraph land`
  takes `--decision` the same way; the decision is kept beside the hypothesis
  it answers, as `decision` in the criterion table. A Spike is not completed
  without its decision, no other kind and no Task takes one, and a file that
  holds a decision before the Spike is completed is refused. That the
  hypothesis reads as a yes/no question is not checked.
- The Story, the Upkeep, the Bug and the Spike share one work item
  (`src/flowgraph/work_item/`): its state types (`WorkItem`,
  `StartedWorkItem`, `CompletedWorkItem`, `RemovedWorkItem`), its moves, its
  file and its commands. The kind -- its noun, the article before it, the
  prefix of its ids and the form of criterion it takes -- is a value the id
  carries, so `Story` and `StartedUpkeep` are names of those types and a
  Story tells itself from an Upkeep by its id. A work item carries the
  criterion its kind takes: a `Scenario`, its Given / When / Then; a
  `Defect`, what is observed and expected; or a `Hypothesis`, which its
  completion turns into an `Answer`, the hypothesis with its decision. Each
  kind keeps only its kind, its id functions and those names; the kinds are
  listed once, in `src/flowgraph/store.py`.
- An amend rewrites the parts of the criterion the work item has: `--given`,
  `--when` and `--then`, `--observed` and `--expected`, or `--hypothesis`. A
  part of another form is refused.
- A Feature is kept as `items/F-0001.toml`: its id, its title, its
  description, its created time and its `criteria`, a list of one or more. It
  has no state line and no Task, the developer's decision of 2026-11-21: its
  bucket is derived from the states of its work items -- Completed when each
  is completed or removed; InProgress once one is started or completed while
  another is not; Backlog otherwise, as with no work item. `fgraph add
  feature` adds one, on `main` as a work item is added, and `fgraph show`
  lists its criteria and its work items with their buckets.
- A work item under a Feature holds `parent = "F-0001"` in its file, and
  carries it through every move. A file without the key holds a work item
  that stands alone: standing alone is a value of `parent` in the model, and
  the files written before the Feature read as they are. `--parent` is given
  when the work item is added and names a Feature the record holds.
- `fgraph status` lists the Features of a record in a block of their own
  above the buckets, the developer's decision of 2026-11-21: the heading
  `Features` with their count, then each Feature by number with its id, its
  progress, its derived bucket and its title. The heading is listed only when
  the record holds a Feature, as Removed is. The status stays flat: a work
  item under a Feature is listed in its own bucket and not with its Feature,
  and the buckets, their counts and the order of the Backlog are those of the
  work items.
- The progress of a Feature is derived as its bucket is, the developer's
  decision of 2026-11-21: `<completed>/<all> W`, the work items under it that
  are completed of all it holds, written as board 1's watch writes it. A
  removed work item is counted in neither number, a started or a Backlog one
  only in the second, and a Feature without a work item reads `0/0 W`. Every
  Feature is listed with it, in any bucket: `F-0001  1/3 W  InProgress
  <title>`.
- Not built yet: amending or removing a Feature, and moving a work item to
  another Feature.
- Each kind reads the files of its own prefix. A file with a prefix no kind
  knows is left alone; nothing reports it yet.
- A command loads a work item whole, changes it and saves it whole. The file
  is validated as it is read; a write is read back before it replaces the
  file.
- The queue of the Backlog (Order) is one file beside `items/`, `queue.toml`:
  a `backlog` list of the ids placed, in their order. A record without the
  file holds the empty queue. A reorder writes the whole Backlog as it is then
  listed, so an id that has left the Backlog drops out at the next reorder;
  `add`, `amend`, `start` and `complete` never write the file.

Who writes what, so that two branches never change the same file or hand out
the same number:

| Write | Where |
|---|---|
| add a work item | `main` |
| add a Task to a work item in Backlog | `main` |
| reorder the Backlog | `main` |
| amend a work item in Backlog | `main` |
| remove a work item in Backlog | `main` |
| start a work item | `main`: `fgraph` commits it and makes its branch |
| add a Task to a started work item | its branch |
| start, block, unblock and complete its Tasks | its branch |
| land the work item | `main`: `fgraph land` merges its branch and completes it |
| complete the work item | `main`, after a merge made by hand |

The branch a work item owns may change and append within its scope, through
`fgraph`: the developer's rule of 2026-11-21. `fgraph` holds the side of the
branch:

- The branch of a work item is the one named `wi/<id>-<slug>`. In a work tree
  on it `fgraph` writes the file of that work item alone.
- Refused there with exit 2, nothing written: a Task added to another work
  item, a Task of another work item started or completed, a work item added,
  and a reorder of the Backlog, whose queue is no file of the work item. The
  refusal names the work item the branch owns.
- A work tree on any other branch, and a record outside a git work tree,
  write as before.

A work item starts on `main` alone, the developer's decision of 2026-11-21:

- The start of a work item is refused with exit 2, nothing written and no
  branch made, unless the work tree it runs in is on `main`. The refusal
  names the branch that work tree is on and, when the repository has one, the
  work tree that is on `main`, where the start is made.
- The start of a Task is not checked against `main`, and neither is a record
  outside a git work tree.

`fgraph` holds the side of `main` too, under the principle the developer
agreed on 2026-11-21 that `fgraph` owns the record, its rituals and its rules:

- A Task write of a started work item -- a Task added, started or completed --
  is taken in the worktree of that work item. In a work tree on any branch
  that no work item owns, `main` among them, it is refused with exit 2,
  nothing written, and the refusal names that worktree.
- The start, the complete and the landing of the work item itself stay on
  `main`.
- A started work item whose branch is checked out in no worktree, and a
  record outside a git work tree, are written as before.
- `fgraph status` on `main` reads a started work item where its Tasks are
  written, the developer's decision of 2026-11-21: its row is the one the
  worktree of its branch `wi/<id>-*` holds, the file at the same path inside
  it, as it is, committed or not, as the Task ids are read. So the progress
  and the Task being worked that status lists are current before the landing.
  A started work item without such a worktree, a record outside a git work
  tree and a record git ignores are read from the record itself. Run in a
  work tree on the branch of a work item, status reads the record of that
  work tree and no other. Every read of the rows goes this way, so the bucket
  of a Feature does too.
- Not built yet: `fgraph show` of a started work item on `main` reads the
  record of `main`, so it shows its Tasks as they were at the start.

The git steps `fgraph` takes, decided by the developer on 2026-11-21:

- `fgraph` commits every write of the record, when the record is inside a git
  work tree: `add`, `amend`, `remove`, `reorder`, `start`, `block`, `unblock` and
  `complete`. The commit
  holds the files of the record the write changed, alone; whatever else is
  staged or changed stays as it was and out of the commit.
- The commit is worded by `fgraph`, `chore: <write> <id> in the record`:

  | Write | Message |
  |---|---|
  | add a work item | `chore: add ST-0001 in the record` |
  | add a Task | `chore: add T-0001 of ST-0001 in the record` |
  | amend | `chore: amend ST-0001 in the record` |
  | reorder | `chore: reorder ST-0002 before ST-0001 in the record` |
  | start | `chore: start ST-0001 in the record`, `chore: start T-0001 of ST-0001 in the record` |
  | block | `chore: block T-0001 of ST-0001 in the record` |
  | unblock | `chore: unblock T-0001 of ST-0001 in the record` |
  | remove | `chore: remove ST-0001 in the record` |
  | complete | `chore: complete ST-0001 in the record`, `chore: complete T-0001 of ST-0001 in the record` |

- A write that leaves its file as it was makes no commit. Completing a Task
  names the commit of its work, so the commit of the record follows it.
- A start of a work item then checks out the branch `wi/<id>-<slug>` at its
  commit in a new worktree, `<parent>/<checkout name>.worktrees/<id>-<slug>`.
  The slug is given with `--slug`, else it is the first four words of the
  title, lower-cased and kept to their letters and digits.
- Outside a git work tree a write is made as before, without a commit and
  without a warning; only a start of a work item warns, that no branch was
  made. A write refused makes no commit and no branch.
- A record git ignores is written without a commit and without a warning, the
  developer's decision of 2026-11-21. The record is ignored when a rule git
  reads names its directory, whether or not git still tracks a file of it.
- The start of a work item on an ignored record still makes its branch, as the
  developer ordered on 2026-11-21 after its first slice made none: the start
  is written with no commit, is held to `main` as any start, and checks out
  `wi/<id>-<slug>` in its worktree at the commit `main` is on. Git checks an
  ignored directory out in no worktree, so the record stays in the checkout of
  `main` alone: the Tasks of the started work item are written there, no
  branch scopes the writes, and the Task ids are those of the record alone.
  `fgraph land` lands it as any other, completing the work item with no commit
  of the record. A worktree git refuses leaves the start written.
- A git step refused exits 2 naming the command: a commit refused puts every
  file the write changed back as it was, a worktree refused leaves the start
  committed.
- `fgraph land` lands a started work item, run in the checkout of `main`. It
  merges the branch `wi/<id>-*` into `main` as a merge of its own, held
  uncommitted; commits it under the message the developer gives with
  `--message`; completes the work item at the short sha of that commit, with
  the commit of the record, `chore: complete <id> in the record`; then removes
  the worktree of the branch and the branch.
- A landing is refused, with nothing merged, when the record is outside a git
  work tree, when the work tree it runs in is not on `main`, when no branch
  `wi/<id>-*` or more than one is there, when git refuses the merge, and --
  the merge held dropped again -- when a Task of the work item is not
  completed or git refuses the merge commit. A step git refuses after the
  merge commit exits 2 saying how far the landing came.
- `fgraph` makes the commits of the record; the commits of the development
  and their messages stay the developer's, the merge commit of a landing
  among them: `fgraph` makes it, the developer words it. Whether the work
  tree is on `main` is checked by a landing and by the start of a work item.

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

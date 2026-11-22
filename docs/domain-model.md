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

A `Feature` has a state of its own too, the developer's words of 2026-11-21
(Persistence): a Feature is to its work items what a work item is to its
Tasks. Three of its states are built, each a type that carries what it needs
and nothing else:

| Type | Bucket | Adds |
|---|---|---|
| `Feature` | Backlog | the attributes of a Feature, above |
| `StartedFeature` | InProgress | started |
| `CompletedFeature` | Completed | completed, the commit or none |

A `CompletedFeature` is reached from a `StartedFeature` alone, with the
completion of its last work item (Persistence). A `Feature` that was never
started keeps the bucket its work items derive, Completed among them.

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

A Feature moves by `start`, `Feature` to `StartedFeature`, and its start
starts its first work item with it; and by the completion of its last work
item, `StartedFeature` to `CompletedFeature`, in the write that completes
that work item. No command completes a Feature by itself (Persistence).

## Order

The Backlog is a queue: the order work is to be pulled in, across every kind
of work item. The developer said so on 2026-11-21.

- A work item joins the end of the queue when it is added.
- A Feature holds a place of its own in the Backlog and joins the end when it
  is added, the developer's words of 2026-11-21: a Feature is part of the
  Backlog, ordered as the others and not riding on its work items. Until it
  is placed it is listed after what the queue places, among the work items
  nobody placed by its created time; added at one time with a work item it
  follows it, and Features added at one time are listed by number.
- `reorder` puts one item of the Backlog right before another, and the queue
  places a Feature as it places a work item: `reorder` takes the id of a
  Feature on either side, `fgraph reorder F-0001 --before S-0001` as `fgraph
  reorder S-0001 --before F-0001`. It is not a move: the type of the item
  stays, only its place changes.
- A work item under a Feature is listed on no line of the Backlog (below), so
  it holds no place among the lines. It is reordered among the work items of
  its Feature alone, the reading decided when S-0051 was ordered: `reorder`
  puts it right before another work item of the same Feature, both in
  Backlog, whatever the bucket of the Feature. That order is the one the work
  items of the Feature start in: `fgraph start` of the Feature starts the
  first of them (Persistence). `fgraph show` of the Feature lists its work
  items in Backlog in it, in the places they hold by kind and number among
  the others; no other view shows it.
- The queue is its own aggregate, apart from the items: it places work items
  and Features by id, each once. One nobody placed follows the placed ones in
  the order it was added; those added at one time, a work item by kind and
  number, then a Feature by number.
- A work item that leaves the Backlog leaves the queue with it, and so does a
  Feature: the other buckets are not listed by the queue.
- A reorder names two items in Backlog; one that is not there, or the same
  one twice, is refused. A Feature in progress or completed is not in
  Backlog, and is refused as a started work item is:
  `F-0001 is not in Backlog`.
- A reorder across a Feature is refused, naming the work item under a Feature
  and that Feature: a work item under a Feature put before an item outside it
  -- a work item standing alone, a Feature, its own among them, a work item
  of another Feature -- or such an item put before it:
  `S-0002 is under F-0001: it is reordered among the work items of F-0001
  alone`. When each of the two is under another Feature it names the one
  moved.
- A text that is neither a work item id nor a Feature id is refused naming
  both: `'T-0001' is no Story, Upkeep, Bug, Spike or Feature id`.
- Completed is listed the last completed first, the developer's decision of
  2026-11-21: by the completed time each work item holds, so the newest
  landing is on top; those completed at one time, by kind and number.
- InProgress is listed the last started first, by the same decision: by the
  started time each work item holds; those started at one time, by kind and
  number. A blocked Task does not move its work item in the list.
- A Feature is placed in those two buckets among the work items that stand
  alone. A completed Feature is placed by its own completed time, that of the
  completion of its last work item (S-0054). Any other is placed by a time of
  its work items: one never started that is derived Completed by the
  completed time of its last completed work item; under InProgress by the
  started time of its last started one, and while none is started by the
  completed time of its last completed one. A Feature with neither time, as
  one never started whose work items are all removed, derived Completed, is
  placed by its created time. At one time with a work item it follows it, and
  Features of one time are listed by number.
- Removed is listed by kind and number, a removed work item of a Feature too:
  it keeps its own line there.
- `fgraph status` lists the top 5 under each heading, the developer's
  decision of 2026-11-21: the first five of the Backlog, of InProgress, of
  Completed and of Removed, in the order each is listed in, then one line
  `... N more` for the N it does not list. The count beside the heading stays
  that of all its items, and a heading of five or fewer has no such line.
  `fgraph status --all` lists every one. A Feature is one item of its bucket:
  it counts once toward the top 5 and once beside the heading (Persistence).
  Until the Features were listed inside their buckets they had a heading of
  their own, with a top 5 of its own.
- `fgraph status` lists a work item under InProgress with its progress, the
  developer's decision of 2026-11-21: `<completed>/<all> T`, its Tasks
  completed of all it holds, between its id and its title, written as board
  1's watch writes it -- `S-0001  1/3 T  <title>`. A started or a blocked
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
- Under a Feature of InProgress `fgraph status` lists each started work item
  of it, the developer's words of 2026-11-21 -- a Feature is to its work
  items what a work item is to its Tasks: the work item as one of InProgress
  is written, with its progress and under it its Tasks being worked, two
  columns further in -- `    S-0001  1/3 T  <title>`, then
  `      => T-0001  <title>` -- the last started first. Those lines belong to
  the Feature: they count neither toward the top 5 of the heading nor in the
  count beside it.
- On a terminal `fgraph status` cuts each line longer than the terminal is
  wide to that width, ending it with `...`, the developer's decision of
  2026-11-21, after board 1's watch; written to a pipe or a file every line
  is whole. So that the cut keeps it, a completed work item is listed with
  its commit before its title, `S-0001  677f9b0  <title>`, and one completed
  without a commit with its id and its title alone (Evidence); a completed
  Feature holds its commit there too, after its progress,
  `F-0001  2/2 W  677f9b0  <title>` (Persistence); the reason of a removed
  one still ends its line. Only status is cut, and a frame of watch
  with it. The width is an effect: `run()` takes it as a callable, none when
  the output is no terminal, and `main()` reads it from the terminal.
- `fgraph watch` follows the record live, the developer's request of
  2026-11-21, "file a story for a fgraph watch command", after board 1's
  watch: until then the live view took two commands, `watch` around `fgraph
  status`, and status then wrote to a pipe and cut no line. Four readings
  were decided when its Story was ordered. A frame is what `fgraph status`
  writes, read anew from the record each time: watch writes a frame, waits
  and writes the next, every 5 seconds or every `-n SECS`, a part of a
  second too. Each line is cut to the width of the terminal as status cuts
  it, the width asked for again at every frame. `--all` lists every item, as
  on status. It ends after `--count N` frames with exit 0, no wait after the
  last; without a count Ctrl-C ends it, with exit 0 and no traceback, since
  that is how a watch is left. A `-n` or a `--count` that is no positive
  number is refused with exit 2 before a frame is written.
- On a terminal a frame of watch replaces the one before it: it opens with
  the sequence that puts the cursor home and clears the screen, written only
  when there is a width. Written to a pipe or a file the frames follow each
  other, every line whole. The wait between two frames is an effect: `run()`
  takes it as a callable, one that returns at once by default, and `main()`
  binds it to `time.sleep`.

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
For a Feature it is the evidence of the completion of its last work item.

The commit is the evidence of the development, the reading decided when
S-0041 was ordered, a commit optional always shown and not taken: it names
the work beside the record that the item is completed with. With the
development off there is no such work, so an item is completed without a
commit, a Task as a work item.

| Type | With the development on | With it off |
|---|---|---|
| `Story`, `Bug`, `Upkeep`, `Spike` | the commit on `main` | none, or the commit given |
| `Task` | its commit | none, or the commit given |
| `Feature` | the commit of its last work item | none, or the commit given for that work item |

- `fgraph complete` needs `--commit` with the development on, of a Task as of
  a work item: without it, it exits 2 naming `--commit` and the key,
  `development.enabled`, and nothing is saved.
- With the development off `fgraph complete` takes none, and a `--commit`
  given is still kept as the evidence.
- The evidence is a value of its own in the model, a commit or none (`Commit`
  or `NoCommit`, `src/flowgraph/criterion.py`): no commit is a value of the
  evidence, not a missing one, as standing alone is a value of `parent`.
- A Spike is completed with its decision either way: the decision answers its
  hypothesis and stands beside the commit or none.
- `fgraph land` is part of the development and completes the work item at
  the commit the landing leaves `main` on -- its merge commit, its squash
  commit or the tip of the branch, by `[development] merge` -- so a landed
  work item always carries its commit.
- `fgraph complete` says what it completed and, when there is a commit, where:
  `completed S-0001 at 677f9b0`, or `completed S-0001` alone. A Feature
  completed with it is named on a line of its own after it, at the same
  commit: `completed F-0001 at 677f9b0`, or `completed F-0001` alone.
- A Feature takes no `--commit` of its own: it holds the evidence of the work
  item that completed it, the same value, a commit or none (Persistence).

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
- With the development on, a work item is completed only once it is on
  `main`, and names its commit there. With it off no commit proves it
  (Evidence).
- Until `fgraph` wraps git, `complete` records the commit it is given and
  does not check it against `main`.

## Ids

An id is the prefix of its kind and a number counted from 1 per kind, written
with at least four digits. `fgraph` hands out the next free number.

| Kind | Id |
|---|---|
| `Feature` | `F-0001` |
| `Story` | `S-0001` |
| `Bug` | `B-0001` |
| `Spike` | `Q-0001` |
| `Upkeep` | `U-0001` |
| `Task` | `T-0001`, unique across the record and the worktrees of its repository |

The `Q` of a Spike stands for question: a Spike is a question to answer. It
is the developer's choice of 2026-11-21, among the letters shown for a prefix
of one letter; until then a Spike was written `SP-0001`. `fgraph` reads `Q`
alone.

The `S` of a Story follows from that choice: `Q` for the Spike left `S` to
the Story, so the id of every kind has a prefix of one letter; until then a
Story was written `ST-0001`. The Stories of the record of flowgraph were
renamed with their numbers kept, `ST-0036` to `S-0036`, by hand, since no
command renames an id. The commits made before keep `ST` in their messages,
since history is not rewritten, and map to the new ids by the number.
`fgraph` reads `S` alone.

## Persistence

The record is plain TOML files tracked by git: git is its history, its backup
and its merge tool.

- One directory, `items/`, holds every item: one file per work item with its
  Tasks inside it, named by its id, `items/S-0001.toml`. The prefix of the id
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
- An item completed without a commit (Evidence) is kept the same way but for
  the `commit` key, which its file or its `[[tasks]]` table does not hold: a
  file without the key holds no commit, a value of the evidence in the model,
  so the files written before read as they are. Its row and its detail carry
  no commit: `fgraph status` lists such a work item under Completed with its
  id and its title alone, `S-0001  <title>`, and `fgraph show` lists no
  `commit` line of it, nor of a Task completed without one.
- A removed work item is kept as `state = "removed"` with its `removed` time
  and its `reason`, beside the fields and the Tasks it had in Backlog.
  `fgraph remove` removes a work item in Backlog; a removed one takes no Task,
  no amend and no move, and leaves the queue as a started one does. Removing
  a Task, and removing a started work item, which has a branch and a
  worktree once the development is on, are not built.
- An Upkeep is kept as `items/U-0001.toml`, in the shape of a Story file:
  the same fields in each state, `started`, `completed` and `commit` once it
  has moved, and its Tasks as `[[tasks]]` tables, read back through the
  moves.
- A Bug is kept as `items/B-0001.toml`, in the same shape but for its
  criterion table: `observed` and `expected` where a Story has `given`,
  `when` and `then`. A file that holds the criterion of another kind is
  refused when it is read.
- A Spike is kept as `items/Q-0001.toml`, its criterion table holding its
  `hypothesis`. It is completed with the decision that answers it,
  `fgraph complete Q-0001 --commit SHA --decision TEXT`, the commit given as
  the development needs it (Evidence), and `fgraph land` takes `--decision`
  the same way; the decision is kept beside the hypothesis it answers, as
  `decision` in the criterion table. A Spike is not completed without its
  decision, no other kind and no Task takes one, and a file that holds a
  decision before the Spike is completed is refused. That the hypothesis
  reads as a yes/no question is not checked.
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
- A Feature is kept as `items/F-0001.toml`: its id, its state line, its
  title, its description, its created time and its `criteria`, a list of one
  or more. It holds no Task. `fgraph add feature` adds one, on `main` as a
  work item is added, and `fgraph show` lists its criteria and its work items
  with their buckets.
- A Feature has a state of its own, kept in its file as that of a work item
  is (S-0052): `state = "backlog"` for a `Feature`, and `state = "started"`
  with its `started` time, kept to the second, for a `StartedFeature`. A
  started one is read back through the move, so a file holds no state the
  move could not reach: a started time without `state = "started"`, or that
  state without its time, is refused when the file is read.
- A `CompletedFeature` is kept as `state = "completed"` with its `started`
  and its `completed` time and, when it has one, its `commit` (S-0054): one
  completed without a commit is written without the key, as a work item is.
  It is read back through both moves, so a completed time or a commit under
  another state, that state without its two times, and a commit that is no
  sha are refused when the file is read.
- A Feature file without a state line reads as a Feature in Backlog. Every
  Feature written before it had a state is such a file, and reads as it is;
  the next write of that Feature holds the line.
- This reverses the developer's decision of 2026-11-21 that a Feature has no
  state line and that its bucket, as everything about it, is derived from the
  states of its work items. The developer's words of the same day reversed
  it, in the agent's wording: a Feature is part of the Backlog and just holds
  a couple of work items; starting it, when git is used for the development
  as well, starts its work items one by one in separate branches; they are
  completed but all stay in progress; when all are completed the Feature
  moves to Completed; a Feature can be blocked, or gets blocked when its
  child work item is blocked. The principle F-0002 was planned and filed
  under: a Feature is to its work items what a work item is to its Tasks --
  it cannot start without one, its work item cannot start before it, one is
  started at a time, the completed ones stay inside it and are counted, it
  completes with the last, and a blocked one marks it.
- `fgraph start F-0001` starts the Feature and its first work item with it,
  in one write and one commit, `chore: start F-0001 in the record`, and says
  `started F-0001 with S-0001`. The first work item is the first of its work
  items in Backlog in the order they start in (Order), so a Feature that
  holds completed work items starts with the next one. That work item is
  started as any other: with the development on, its branch is checked out in
  its worktree at the commit of the start, `--slug` naming the branch, and
  the start is held to `main`.
- The start of a Feature is refused with exit 2 and nothing written: a
  Feature started already, `F-0001 is started already`; a completed one,
  `F-0001 is completed already`; one with no work item in Backlog,
  `F-0001 has no work item in Backlog to start with`; one whose first work
  item has no Task, `F-0001 cannot start: S-0001 has no Task to start with`;
  and a start `[development] parallel` refuses (below).
- A work item does not start before its Feature: the start of a work item in
  Backlog under a Feature that is not started is refused with exit 2, naming
  the Feature, `S-0001 cannot start: F-0001 is not started, start it first`.
  The alternative, that the start of a child starts its Feature, was shown
  with the plan and not taken.
- One work item of a Feature is started at a time: the start of a work item
  of a started Feature beside another started work item of it is refused
  naming that one, `S-0002 cannot start: F-0001 starts one work item at a
  time, started already: S-0001`. With none started it starts: once the one
  before is completed, `fgraph start` of the next starts it, and nothing
  starts it by itself yet.
- Both rules are asked at the start of a work item in Backlog and nowhere
  else: no Task write and no completion asks them. So a work item started
  under a Feature that was never started, as in a record whose work items
  were started one by one before a Feature had a state, is worked and
  completed as before.
- A Feature is completed with its last work item, the developer's words of
  2026-11-21 as S-0054 built them: the completion of a work item under a
  started Feature that leaves each work item of it completed or removed
  completes the Feature in the same write. The `CompletedFeature` holds the
  completed time of that work item and its evidence -- the commit it was
  completed in, none with the development off (Evidence). `fgraph complete`
  names both, `completed S-0002 at 677f9b0` then `completed F-0001 at
  677f9b0`, and the one commit of the record holds the two files, worded
  `chore: complete S-0002 and F-0001 in the record`. `fgraph land` completes
  the Feature the same way, in the commit of the record its complete makes,
  at the commit the landing leaves `main` on: `landed S-0002 at 677f9b0`,
  then `completed F-0001 at 677f9b0`.
- Only a completion completes a Feature. A completion that leaves a work item
  of it in Backlog or started leaves the Feature started, and so does the
  removal of its last work item in Backlog: that Feature stays in InProgress
  with every work item it holds completed, `F-0001  1/1 W  <title>`, until a
  work item added under it is completed. A removed work item holds nothing
  back and counts in neither number of the progress. No command completes a
  Feature by itself.
- The Feature is saved before the work item, and on `main`: the file of a
  Feature is no file of the branch of a work item (below), so `fgraph complete`
  of the last work item run on that branch is refused with exit 2 and nothing
  written, naming the Feature and the branch, `F-0001 is not written here:
  the branch wi/S-0002-<slug> writes S-0002 alone`. `fgraph land` runs on
  `main`, where it saves both.
- A completed Feature takes no start and no work item added under it: `fgraph
  start F-0001`, and an add with `--parent F-0001`, are refused with exit 2,
  `F-0001 is completed already`. Its completed work items stay within it:
  they are counted in its progress, listed by `fgraph show`, and on no line
  of `fgraph status`.
- A Feature never started is completed by nothing: the completion of its last
  work item writes that work item alone, and the Feature keeps the bucket its
  work items derive, Completed, with no commit. So a record whose Features
  were worked before a Feature had a state lists them as it did.
- The one at a time of a Feature and `[development] parallel` both hold,
  decided when S-0052 was ordered: a Feature starts one work item at a time,
  and `parallel` counts every started work item of the record, those of a
  Feature among them. The start of a Feature starts one work item, so
  `parallel` refuses it as it refuses that one, naming the Feature: `F-0001
  cannot start: development.parallel = 1, started already: S-0002`. It is
  asked once the Feature is known to start, so a Feature started already, or
  without a work item in Backlog, is refused for that.
- The bucket of a Feature is read from its state and its work items. A
  `StartedFeature` is in InProgress and a `CompletedFeature` in Completed,
  each by its own state. A Feature never started keeps the bucket its work
  items derive: Completed when each is completed or removed; InProgress once
  one is started or completed while another is not; Backlog otherwise, as
  with no work item. So a Feature whose file holds no state line is listed as
  it was, and `fgraph start` of it starts its next work item in Backlog. This
  reverses, for a started Feature alone, the reading of S-0052 that listed it
  under Completed once each of its work items was completed or removed.
- A work item under a Feature holds `parent = "F-0001"` in its file, and
  carries it through every move. A file without the key holds a work item
  that stands alone: standing alone is a value of `parent` in the model, and
  the files written before the Feature read as they are. `--parent` is given
  when the work item is added and names a Feature the record holds.
- `fgraph status` lists a Feature inside its bucket, as one line in place of
  its work items, the developer's words of 2026-11-21: a Feature is an
  umbrella, part of the Backlog, that just holds a couple of work items. The
  line is its id, its progress and its title, `F-0001  1/3 W  <title>`, in
  its bucket (above), placed there as Order says. It is one
  item of that bucket: counted once beside the heading and once toward the
  top 5. Its work items in Backlog and its completed ones are listed on no
  line of their own and counted beside no heading; they are counted in its
  progress, and `fgraph show` of the Feature lists them with their buckets,
  those in Backlog in the order they start in (Order). A started one is
  listed under the line of its Feature (Order), and a removed one keeps its
  line under Removed. No command removes a Feature yet.
- A completed Feature is listed under Completed with its commit between its
  progress and its title, `F-0001  2/2 W  677f9b0  <title>`: the progress
  stays right after the id, as on the line of a Feature in any bucket, and
  the commit right before the title, as on the line of a completed work item,
  so a line cut to the width keeps both. One completed without a commit, and
  a Feature never started that is derived Completed, are listed without one,
  `F-0001  2/2 W  <title>`. `fgraph show` of a completed Feature lists
  `bucket       Completed` and under it `commit       677f9b0`, the commit
  line only when it has one, as the show of a work item does.
- This reverses the developer's decision of 2026-11-21 that listed the
  Features of a record in a block of their own above the buckets: the heading
  `Features` with their count, listed only when the record held a Feature,
  then each Feature by number with its id, its progress, its derived bucket
  and its title, `F-0001  1/3 W  InProgress <title>`, while the status stayed
  flat -- a work item under a Feature in its own bucket, and the buckets,
  their counts and the order of the Backlog those of the work items. No
  heading `Features` is listed any more, and the line of a Feature no longer
  names its bucket: the heading it stands under does.
- The progress of a Feature is derived from its work items, the developer's
  decision of 2026-11-21: `<completed>/<all> W`, the work items under it that
  are completed of all it holds, written as board 1's watch writes it. A
  removed work item is counted in neither number, a started or a Backlog one
  only in the second, and a Feature without a work item reads `0/0 W`. Every
  Feature is listed with it, in any bucket: `F-0001  1/3 W  <title>`.
- Not built yet: blocking, amending or removing a Feature, starting the next
  work item of a started Feature once the one before is completed, and moving
  a work item to another Feature. Starting one is built (above), so is
  completing one with its last work item, and so is reordering one (Order).
- Each kind reads the files of its own prefix. A file with a prefix no kind
  knows is left alone; nothing reports it yet. An `items/SP-0001.toml` of an
  older record, written while a Spike was `SP-0001`, is such a file: it is
  neither read as a Spike nor renamed, so no command lists it or takes its
  id. So is an `items/ST-0001.toml` of an older record, written while a Story
  was `ST-0001`: it is neither read as a Story nor renamed.
- A command loads a work item whole, changes it and saves it whole. The file
  is validated as it is read; a write is read back before it replaces the
  file.
- The queue of the Backlog (Order) is one file beside `items/`, `queue.toml`:
  a `backlog` list of the ids placed, in their order -- the ids of work items
  and of Features, `F-0001` beside `S-0001`. A record without the file holds
  the empty queue. A reorder writes the whole Backlog as it is then listed,
  so an id that has left the Backlog drops out at the next reorder; `add`,
  `amend`, `start` and `complete` never write the file.
- That one list holds the lines of the Backlog -- the work items standing
  alone and the Features -- and the work items in Backlog under a Feature,
  those of a Feature that has left the Backlog too. Two orders are read from
  it and no other: the order of the lines, from the ids of the work items
  standing alone and of the Features; and inside each Feature the order its
  work items start in, from the ids of the work items under it. Where the id
  of a work item under a Feature stands among the ids outside its Feature
  says nothing. The whole Backlog a reorder writes is that list as it then
  reads -- the ids placed, then the ids nobody placed: the lines as added,
  then the work items under a Feature as added -- with the one id moved right
  before the other and every other id where it was. So the order of the lines
  and the order inside each Feature both survive a rewrite, whichever of the
  two the reorder changes, and a file written before the queue placed a
  Feature, whose work items under a Feature were placed among those of their
  Feature, reads as it did.

A record is layered by its configuration, the developer's request of
2026-11-21, which names three layers: the items and their lifecycle, kept
always; their commits on `main`, to be turned off; the development beside the
source code, to be turned on. The record is meant to be used without the
development too.

- The configuration is one file beside `items/`, `config.toml`, a table per
  layer. A record without the file holds the defaults, and so does a table or
  a key the file leaves out.
- `[development] enabled` turns the development on: the branch and the
  worktree of a start, the scoping of a branch, the landing. It is off by
  default, the reading the developer agreed when the plan was filed on
  2026-11-21.
- With the development off the start of a work item is a write as any other:
  committed on `main`, with no branch, no worktree and no warning. Its Tasks
  are written on `main`, it is completed with `fgraph complete`, and
  `fgraph land` is refused with exit 2 naming the key, `development.enabled`.
- With the development off `fgraph complete` takes no commit, of a Task as of
  a work item; with it on it needs `--commit` and is refused with exit 2
  naming the option and the key without it (Evidence).
- The rules that read a branch `wi/<id>-*` stay as they are: without the
  development `fgraph` makes no such branch, so none scopes a write and no
  worktree takes the Tasks of a started work item.
- With `enabled = true` the start, the scoping and the landing are as this
  section states them below.
- The start of a work item is held to `main` with the development on or off,
  and it alone, the reading decided when S-0039 was ordered: no other write of
  a record is held to `main`.
- `[development] parallel` is how many work items are started at once, a
  whole number of 1 or more. It has no default, decided when S-0044 was
  ordered: left out, nothing limits the started work items. It is a key of
  the development, so it limits nothing with the development off, where it is
  held as written.
- With the development on and `parallel` set, the start of a work item in
  Backlog is refused with exit 2, nothing written and no branch made, when
  that many work items are started already. The refusal names the key,
  `development.parallel`, its number and each started work item. The started
  work items are those of every kind, read as `fgraph status` reads them: a
  started work item is the one its worktree holds. Those under a Feature are
  counted among them, and the start of a Feature, which starts one work item,
  is refused the same way, naming the Feature (Persistence).
- The start of a Task is neither counted nor limited by `parallel`: a work
  item has one started Task at a time whatever the key. A work item that is
  not in Backlog is left to the start, which refuses it for its own state.
- `[development] merge` names how a landing merges, one of three words:
  `merge-commit`, `squash` or `fast-forward`, the reading of the developer's
  request for merging strategies taken when S-0043 was ordered. Left out it
  is `merge-commit`, the one merge a landing made before the key, so a record
  that names none lands as it did. It is a key of the development, so it says
  nothing with the development off, where it is held as written. A landing
  through a pull request is no way of merging: it is left out.
- What `main` gains by each: by `merge-commit` one merge commit of the
  branch, with two parents; by `squash` one commit of its own alone that
  holds the work of the branch, with one parent, so `main` holds none of the
  commits of the branch; by `fast-forward` no new commit, `main` moved to the
  tip of the branch. `--message` words the commit a `merge-commit` or a
  `squash` makes and is needed by both; a `fast-forward` makes none to word
  and is refused with one. Both refusals exit 2 naming the option and the
  key, `development.merge`, before any git step.
- The way of merging is a closed set in the model (`Merge`,
  `src/flowgraph/config.py`), and a landing is built from it with its message
  as one of three values -- `MergeCommit` and `Squash`, each with the
  message, and `FastForward`, with none (`src/flowgraph/land.py`) -- so a
  fast-forward with a message and a commit without one cannot be built.
- `[development] gate` names one command of the record, a command line run
  at a landing. It is the reading, decided when S-0042 was ordered, of the
  developer's words of 2026-11-21 on starting a work item, "checks if
  criteria are met before closing": one gate of the record, on top of the
  rule that every Task is completed. It is no check per Task run at a
  complete, and the Given / When / Then of the work item is neither run nor
  confirmed. It has no default: left out, a landing runs no gate. It is a
  key of the development, so it gates nothing with the development off,
  where it is held as written.
- `fgraph land` runs the gate through the shell at the top of the work tree
  of `main`, once the work of the branch is merged there, the merge held
  uncommitted, and before the landing is committed or the work item
  completed: the gate checks the tree `main` will have. The Tasks completed
  stay the first rule of a landing: the work item is checked to complete
  first, and a gate is not run for one that cannot. The output of the gate
  is written as the gate wrote it, never captured.
- A gate that exits with another status than 0 leaves `main` where it was,
  whatever the way of merging: the merge held is dropped, and the work item,
  its branch and its worktree are as they were. The landing is refused with
  exit 2 naming the key, `development.gate`, the command as the file writes
  it and its status. A gate that passes lands as a landing without one.
- The gate is a value or none in the model (`Gate`, a `Gated` command or
  `Ungated`, `src/flowgraph/config.py`), never an empty text with a meaning.
  Running it is an effect (`src/flowgraph/gate.py`): `run()` takes it as a
  callable, `RunGate`, and `main()` binds the adapter `run_gate`, which runs
  the command line through the shell. The default of `run()` runs no gate: a
  run that lands under one is given its runner.
- `[git] commit` turns the commits of the record off. It is on by default,
  the reading of S-0040, off until set shown and not taken: inside a git work
  tree that does not ignore the record `fgraph` commits every write of it, as
  the git steps below state.
- With `commit = false` no write of the record is committed: `add`, `amend`,
  `remove`, `reorder`, `start`, `block`, `unblock`, `complete` and `config
  set` leave their files changed in the work tree, without a commit and
  without a warning, as the write of a record git ignores. Committing them is
  the developer's. The start of a work item is still held to `main`.
- The layers build on each other, decided with S-0040: the branch of a work
  item carries its record, so the development needs the commits. A
  `config.toml` that sets `[development] enabled = true` with `[git] commit =
  false` is refused with exit 2 naming both keys, `development.enabled` and
  `git.commit`. A record git ignores keeps its own rule, unchanged: its
  writes make no commit and, with the development on, its start still
  branches.
- A `config.toml` that holds a table or a key the configuration does not
  have, a value of another type than its key takes, a `parallel` below 1 or
  no whole number, a `merge` that is none of its three words, a `gate` that
  is empty, blank or no text, or no TOML, is refused with exit 2 naming the
  file and the key, whatever the command. The help option needs no record
  and reads none.
- The configuration is read at the edge into a value of the model
  (`src/flowgraph/config.py`). Reading it is an effect: `run()` takes it as a
  callable, the defaults when none is given, and `main()` reads the file.
- Only these five keys are built: `git.commit`, `development.enabled`,
  `development.parallel`, `development.merge` and `development.gate`, each
  named dotted, its table and its key. The record of flowgraph holds
  `[development] enabled = true`, no `parallel`, no `merge` and no `gate`.
- The configuration is shown and set through `fgraph config`, the reading of
  S-0045, so the file is no longer written by hand.
- `fgraph config show` lists every key, dotted, with its value, one a line,
  `<key> = <value>`. The value is written as the file writes it: `true`, `2`,
  `"squash"`, `"make check"`. A key the file leaves out is listed at its
  default, so a record without the file lists the five defaults.
- A key that holds no value -- `parallel` without a limit, `gate` without a
  command -- is listed as `none`, chosen when S-0045 was built. `none` is no
  value of the file, so the gate `"none"`, listed in its quotes, is not
  mistaken for it.
- `fgraph config set KEY VALUE` writes that one key into `config.toml` and
  keeps the others; a record without the file gains it. VALUE arrives as a
  text and is read by what its key takes, never guessed from the text:
  `true` or `false` for `git.commit` and `development.enabled`, a whole
  number for `development.parallel`, the text itself for `development.merge`
  and `development.gate`. So `fgraph config set development.gate true` names
  the command `true`. A text that names no value of its key stays a text,
  which the configuration refuses.
- The whole file is read back through the constructor of the configuration
  before it replaces the one in the record (`write_settings`,
  `src/flowgraph/config.py`). A key the configuration does not have, a value
  the key does not take and the development turned on with the commits off
  are refused with exit 2 naming the key, nothing written: the file is as it
  was, and a record without one is left without. The refusal names no file,
  since the file is not at fault.
- A set is a write of the record as any other: journaled by the store,
  committed alone as the git steps below state, put back when git refuses
  the commit, and without a commit when it leaves the file as it was.
- Whether a set is committed is read from the configuration it leaves, not
  from the one it found, chosen when S-0045 was built. A set that turns the
  commits off is left uncommitted, as every write after it; a set that turns
  them on is committed, with whatever the file held uncommitted. So `fgraph`
  never commits a `config.toml` that turns its commits off.
- On the branch of a work item a set is refused, as the scope of the branch
  states below: `config.toml` is no file of the work item. In any other work
  tree it is written, held to `main` no more than any write but the start of
  a work item. `fgraph config show` writes nothing and runs anywhere.
- A key is taken back to its default by setting that default; no unset is
  built. `git.commit`, `development.enabled` and `development.merge` have a
  default to set. `development.parallel` and `development.gate` have none:
  once set they take another value by a set, and are taken back to none only
  by removing their line from the file.
- A set writes the file whole from its keys, so a comment written in it is
  not kept. A `config.toml` that is refused is refused by `fgraph config`
  too, as by every command: it is mended in the file.
- In the model the keys a file writes are its settings (`Settings`,
  `src/flowgraph/config.py`): plain data by table, a key left out left out,
  apart from the configuration, which holds a value for every key. A set
  loads the settings whole, sets one key by a function that returns them and
  saves them whole (`src/flowgraph/setting.py`), where each key is listed
  once with what it takes and the value a configuration holds under it.

Who writes what with the development on, so that two branches never change
the same file or hand out the same number. With it off no work item has a
branch: every write is made in the checkout, the start of a work item alone
held to `main`, and there is no landing:

| Write | Where |
|---|---|
| add a work item | `main` |
| add a Task to a work item in Backlog | `main` |
| reorder the Backlog | `main` |
| amend a work item in Backlog | `main` |
| remove a work item in Backlog | `main` |
| set a key of the configuration | `main` |
| start a work item | `main`: `fgraph` commits it and makes its branch |
| start a Feature | `main`: `fgraph` commits it with its first work item and makes the branch of that one |
| add a Task to a started work item | its branch |
| start, block, unblock and complete its Tasks | its branch |
| land the work item | `main`: `fgraph land` merges its branch and completes it |
| complete the work item | `main`, after a merge made by hand |
| complete a Feature | `main`: with its last work item, by its landing or its complete |

The branch a work item owns may change and append within its scope, through
`fgraph`: the developer's rule of 2026-11-21. `fgraph` holds the side of the
branch:

- The branch of a work item is the one named `wi/<id>-<slug>`. In a work tree
  on it `fgraph` writes the file of that work item alone.
- Refused there with exit 2, nothing written: a Task added to another work
  item, a Task of another work item started or completed, a work item added,
  a reorder of the Backlog, whose queue is no file of the work item, a set of
  the configuration, whose `config.toml` is none either, and the complete of
  the work item itself when it would complete its Feature, whose file is
  none either (above). The refusal names the work item the branch owns.
- A work tree on any other branch, and a record outside a git work tree,
  write as before.

A work item starts on `main` alone, the developer's decision of 2026-11-21:

- The start of a work item is refused with exit 2, nothing written and no
  branch made, unless the work tree it runs in is on `main`. The refusal
  names the branch that work tree is on and, when the repository has one, the
  work tree that is on `main`, where the start is made.
- The start of a Task is not checked against `main`, and neither is a record
  outside a git work tree.
- The start of a Feature starts its first work item, so it is held to `main`
  as the start of that work item is, and refused the same way, naming the
  Feature.

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
- `fgraph show` of a started work item on `main` reads it there too, as
  status does: the work item it shows, with the bucket and the commit of each
  Task, is the one the worktree of its branch `wi/<id>-*` holds, the same
  file read the same way. A work item that is not started, a started one
  without such a worktree, a record outside a git work tree and a record git
  ignores are shown from the record itself. Run in a work tree on the branch
  of a work item, show reads the record of that work tree and no other. The
  show of a Feature lists its work items from the rows, so it reads them
  there as status does.

The git steps `fgraph` takes, decided by the developer on 2026-11-21:

- `fgraph` commits every write of the record, when the record is inside a git
  work tree and its configuration leaves `[git] commit` on: `add`, `amend`,
  `remove`, `reorder`, `start`, `block`, `unblock`, `complete` and `config
  set`. The commit holds the files of the record the write changed, alone;
  whatever else is staged or changed stays as it was and out of the commit.
- The commit is worded by `fgraph`, `chore: <write> <id> in the record`, a
  set of the configuration under its key:

  | Write | Message |
  |---|---|
  | add a work item | `chore: add S-0001 in the record` |
  | add a Task | `chore: add T-0001 of S-0001 in the record` |
  | amend | `chore: amend S-0001 in the record` |
  | reorder | `chore: reorder S-0002 before S-0001 in the record`, `chore: reorder F-0001 before S-0001 in the record` |
  | start | `chore: start S-0001 in the record`, `chore: start T-0001 of S-0001 in the record`, `chore: start F-0001 in the record` for a Feature and its first work item |
  | block | `chore: block T-0001 of S-0001 in the record` |
  | unblock | `chore: unblock T-0001 of S-0001 in the record` |
  | remove | `chore: remove S-0001 in the record` |
  | complete | `chore: complete S-0001 in the record`, `chore: complete T-0001 of S-0001 in the record`, `chore: complete S-0002 and F-0001 in the record` for a work item and the Feature it completes |
  | set a key of the configuration | `chore: set development.enabled in the record` |

- A write that leaves its file as it was makes no commit. With the
  development on, completing a Task names the commit of its work, so the
  commit of the record follows it.
- With the development on, a start of a work item then checks out the branch
  `wi/<id>-<slug>` at its commit in a new worktree,
  `<parent>/<checkout name>.worktrees/<id>-<slug>`. The slug is given with
  `--slug`, else it is the first four words of the title, lower-cased and kept
  to their letters and digits. With the development off the start ends at its
  commit.
- Outside a git work tree a write is made as before, without a commit and
  without a warning; only a start of a work item with the development on
  warns, that no branch was made. A write refused makes no commit and no
  branch.
- A record git ignores is written without a commit and without a warning, the
  developer's decision of 2026-11-21. The record is ignored when a rule git
  reads names its directory, whether or not git still tracks a file of it.
- A record whose configuration holds `[git] commit = false` is written the
  same way, without a commit and without a warning: every write takes the
  path of a record git ignores. Its start makes no branch, since its
  configuration cannot turn the development on.
- With the development on, the start of a work item on an ignored record
  still makes its branch, as the developer ordered on 2026-11-21 after its
  first slice made none: the start is written with no commit, is held to
  `main` as any start, and checks out `wi/<id>-<slug>` in its worktree at the
  commit `main` is on. Git checks an ignored directory out in no worktree, so
  the record stays in the checkout of `main` alone: the Tasks of the started
  work item are written there, no branch scopes the writes, and the Task ids
  are those of the record alone. `fgraph land` lands it as any other,
  completing the work item with no commit of the record. A worktree git
  refuses leaves the start written.
- A git step refused exits 2 naming the command: a commit refused puts every
  file the write changed back as it was, a worktree refused leaves the start
  committed.
- With the development on, `fgraph land` lands a started work item, run in
  the checkout of `main`. It merges the branch `wi/<id>-*` into `main` as a
  merge of its own, held uncommitted; commits it under the message the
  developer gives with `--message`; completes the work item at the short sha
  of that commit, with the commit of the record, `chore: complete <id> in the
  record`; then removes the worktree of the branch and the branch. These are
  the steps of a landing by `merge-commit`. The landing of the last work item
  of a started Feature completes the Feature in that commit of the record,
  by any way of merging (above).
- Every way of merging holds that same merge uncommitted first: the record
  of the branch is then in the checkout of `main`, where the work item is
  checked to complete before `main` moves. A `squash` commits the merge held
  as one commit of `main` alone, under the message, and removes the branch
  as an unmerged one, a step of its own, since `main` holds none of its
  commits. A `fast-forward` cannot be held: the merge held is dropped once
  checked, then `main` is moved to the tip of the branch, and the branch is
  removed as a merged one. Either completes the work item at the short sha
  of the commit `main` is then on, with the commit of the record.
- The gate of the record, when `[development] gate` names one, is a step of
  every way, run on the merge held once the work item is checked to
  complete: before the commit of a `merge-commit` or a `squash`, and before
  a `fast-forward` drops the merge and moves `main`. A gate that fails drops
  the merge held, and no later step is taken.
- A squash is not made by `git merge --squash`: that takes a change staged
  in the checkout into the commit and drops it with the squash. The merge of
  its own refuses such a checkout, and committed with one parent it holds
  the same work.
- A landing is refused, with nothing merged, when the development is off,
  when `--message` is missing for a commit or given to a `fast-forward`,
  when the record is outside a git work tree, when the work tree it runs in
  is not on `main`, when no branch `wi/<id>-*` or more than one is there,
  when a `fast-forward` finds a commit on `main` that the branch lacks, when
  git refuses the merge, and -- the merge held dropped again -- when a Task
  of the work item is not completed, when the gate of the record exits with
  another status than 0, or git refuses the commit or the fast-forward. A
  step git refuses after `main` moved exits 2 saying how far the landing
  came.
- `fgraph` makes the commits of the record; the commits of the development
  and their messages stay the developer's, the merge commit and the squash
  commit of a landing among them: `fgraph` makes it, the developer words it.
  Whether the work tree is on `main` is checked by a landing and by the start
  of a work item.

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

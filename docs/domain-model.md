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
| `Spike` | a question to answer | the decision and the yes or no are written |
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
  criterion. A work item may name the criterion it realizes (S-0100), by its
  place in the list; the link is optional, so a Feature may hold work items
  whose criterion is none of its criteria. `fgraph show` of the Feature lists
  which criteria are met (S-0101).
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
| `Story` | id, outcome title, description, parent, realizes, complexity, Given / When / Then, created |
| `Bug` | id, outcome title, description, parent, realizes, complexity, observed, expected, created |
| `Upkeep` | id, outcome title, description, parent, realizes, complexity, Given / When / Then, created |
| `Spike` | id, outcome title, description, parent, realizes, complexity, hypothesis, created |
| `Task` | id, output title, description, parent, expected output, check, created |

`parent` is a Feature or standing alone for the four work items, and exactly
one work item for a Task.

`realizes` is the criterion of its Feature a Story, a Bug, an Upkeep or a Spike
under a Feature may name, by its place in the list counted from 1, the reading
of F-0013. Naming none is a value of it, as standing alone is one of `parent`,
never a missing field. It is set by `fgraph add --realizes N` and by `fgraph
amend --realizes N` or `none`, the latter in Backlog alone, and every move
carries it: the start, the block, the unblock, the completion and the removal
keep the criterion the item named. A work item that stands alone names none, so
a place given to one is refused. It is built by `make_criterion_place`, which
refuses a place below 1.

The `check` of a Task is the command that checks it, one text, optional. With
the development on (`development.enabled`) it is needed: `fgraph add task`
without `--check` is refused with exit 2 naming it. With the development off it
is refused, naming `development.enabled`. A blank one is refused where the Task
is built. It is kept in the file of the work item, listed by `fgraph show`
under the Task, and carried by every move of the Task. A Task written before
holds none and is read as before. `complete` runs it (Persistence). An amend of
the Task in Backlog rewrites it (S-0144).

A Story, a Bug, an Upkeep and a Spike carry a complexity: `low`, `medium` or
`high`, none when it is left out, the reading of S-0112. It is set by `fgraph
add` and by `fgraph amend`, the latter in Backlog alone, as every part of an
amend is, and every move carries it: the start, the completion and the removal
keep the complexity the item had. It is built by `make_complexity`, so any other
word is refused, exit 2, naming `low`, `medium` and `high`. It is not taken back
to none by an amend. A Feature and a Task carry none. Which model, or which
agent, a complexity maps to is read by whoever hands the work item to an agent
and stays outside fgraph.

A work item in any state also keeps its knowledge: the lines noted on it, in
the order noted. A line holds its kind, its text and the time it was noted; the
kind is one of three, a sum type: a finding records what was learned, a decision
what was decided, and a deviation a change to what a started item was agreed to
do, since `fgraph amend` refuses one once it is started. A line may carry one
mark, a sum of three with no mark: standing, the line holds until a later line
supersedes it, and open, the line is not settled yet; a line of any kind takes
one. The mark is given when the line is noted and, as the line, never amended;
no command reads it, `fgraph show` and `fgraph knowledge` list it. The text says
something, so a blank one is refused where the line is built. A line is noted
with `fgraph note` in Backlog, started, Completed or Removed alike, and is never
amended or removed: it is added after the lines the item keeps already.

A work item also keeps its progress lines, in the order noted: each holds its
text, the time it was noted and, when it is of a Task, that Task. A progress
line says where the work stands -- a hand-off, a structure note, the red line of
a Task -- and is no knowledge line: a type and a table of its own, about no
term, governing no file, listed by `fgraph show` alone and never by `fgraph
knowledge`, `about`, `brief`, `graph` or `status`. It is kept in any state of
the work item and of the Task, and is never amended or removed (S-0143).

A completed Story, Bug or Upkeep also holds the answer of its closing once it
is verified, none before. It is its own fact, a `Verification` of the
completed work item and never a knowledge line: the answer, yes or no, the
text the run of its criterion printed and the time. The question per kind is
the one its criterion states: for a Story, does the Then hold on the trunk; for
a Bug, is the expected seen; for an Upkeep, does it still hold. A Spike is not
verified: it keeps its decision. The text says something, so a blank one is
refused where the answer is built. An item takes one answer: a second is
refused, never added or replaced. `fgraph verify` keeps it on a completed item
alone, so any other state is refused.

A work item in any state also keeps its relations, the references it names to
other work items. A relation is a typed reference stored on the item that names
it, as the `parent` is, never on the item it names: the other side is derived
by a view over the record, so a write is one file and the scope of a branch
holds. The relations of an item are one value with a field per kind of
relation, so a new kind is a new field. `depends on` is the work items of any
kind it waits for, none by default, each once, in the order given;
`filed during` is the one work item it was found during, none by default;
`amends` is the one completed work item whose landed behavior it changes, none
by default. A work item that names itself in any is refused where its relations
are built. The relations are listed in one table under Relations below.

A Feature keeps its knowledge lines as a work item does, in each of its five
states, and they stay on it through every move and every amend. A Task keeps
no knowledge line: what a Task learns is noted on its work item. A Task takes a
progress line, kept on its work item and naming the Task; a Feature takes none.

## States are types

The state of an item is its type, so an item carries only what its state
needs. The same five exist for `Story`, `Bug`, `Spike`, `Upkeep` and `Task`;
`Story` is shown.

| Type | Bucket | Adds |
|---|---|---|
| `Story` | Backlog | the attributes of its kind, above |
| `StartedStory` | InProgress | started, the agent it is handed to or none |
| `BlockedStory` | InProgress, shown as blocked | reason, since, waiting on |
| `CompletedStory` | Completed | completed on, evidence, the agent it had or none |
| `RemovedStory` | Removed | removed on, reason, superseded by or none |

A `RemovedStory` reached from a `StartedStory` or a `BlockedStory` holds no
started time, no agent and no block: its completed Tasks are kept and its
others are each a `RemovedTask` (S-0148).

The five of a Task are `Task`, `StartedTask`, `BlockedTask`, `CompletedTask`
and `RemovedTask`; the last adds removed on and reason, with no superseded by
and no started time or block (S-0147).

`CompletedSpike` also adds the decision, which answers its hypothesis, and the
answer, yes or no, which a Spike completed before it was taken lacks.

A kind whose criterion and payload match another's shares its state types and
names them as its own: `Story` and `Upkeep` are both `WorkItem`, told apart
by the kind on their id (Persistence).

A `Feature` has a state of its own too, the developer's words of 2026-11-21
(Persistence): a Feature is to its work items what a work item is to its
Tasks. Its five states are built, each a type that carries what it needs and
nothing else:

| Type | Bucket | Adds |
|---|---|---|
| `Feature` | Backlog | the attributes of a Feature, above |
| `StartedFeature` | InProgress | started |
| `BlockedFeature` | InProgress | started, blocked since, reason, waiting on |
| `CompletedFeature` | Completed | completed, the commit or none |
| `RemovedFeature` | Removed | removed on, reason |

A `BlockedFeature` is reached from a `StartedFeature` alone and goes back to
it, as a `BlockedTask` does (S-0056). A `CompletedFeature` is reached from a
`StartedFeature` or a `BlockedFeature`, with the completion of its last work
item (Persistence). A `RemovedFeature` is reached from a `Feature`, a
`StartedFeature` or a `BlockedFeature`, and holds no started time and no
block; its work items in Backlog are removed with it (S-0058, S-0125,
Persistence). A `Feature` that was never started keeps the
bucket its work items derive, Completed among them.

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

A Task moves by `remove` inside a started work item alone, from `Task`,
`StartedTask` or `BlockedTask` to `RemovedTask`; a removed Task takes no move
(S-0147, Persistence).

A Feature moves by `start`, `Feature` to `StartedFeature`, and its start
starts its first work item with it; and by the completion of its last work
item, `StartedFeature` to `CompletedFeature`, in the write that completes
that work item. No command completes a Feature by itself (Persistence). The
completion of any other work item of a `StartedFeature` leaves it as it is
and starts the next work item of it, `WorkItem` to `StartedWorkItem`, in
that write (Persistence). A Feature moves by `block` and `unblock` as a Task
does, `StartedFeature` to `BlockedFeature` and back; a `BlockedFeature`
starts no work item, is completed by its last one as a `StartedFeature` is,
and its unblock starts its next work item when none is started
(Persistence). A Feature moves by `remove`, `Feature`, `StartedFeature`
or `BlockedFeature` to `RemovedFeature`, and its remove removes each work
item of it in Backlog with it, `WorkItem` to `RemovedWorkItem`, in that
write, its completed ones left as they are; a `RemovedFeature` takes no
move (Persistence).

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
- `fgraph status` marks every work item that can start now with `>`, within
  `[development] parallel` (S-0110, which takes over S-0108 and replaces the
  reading of S-0086 that marked the next to start alone). The places are
  `parallel` less the work items started, those under a Feature counted. The
  first to take them are the work items in Backlog of a started Feature that
  are not blocked and wait for nothing, the started Features in the order
  InProgress lists them and the work items of each in the order its start
  takes them; then the lines of the queue that `fgraph start` would take, in
  the order of the queue: a work item that waits for nothing, or a Feature
  whose first work item in Backlog waits for nothing (Depends on), which takes
  one place. A line that waits is skipped, and the limit, not a dependency,
  leaves out the rest. A Feature holding no work item in Backlog, a blocked
  Feature and one never started give none. With `parallel` left out every one
  that waits for nothing is marked; with the development off the next to start
  alone, the first such line of the queue, as before. With the development on
  a line is marked only once planned (S-0127): a work item holds a Task, a
  Feature's work items in Backlog each hold one, under a started Feature as in
  the Backlog; with `development.driver` agent planned also means each work
  item holds a complexity (S-0129), and with the driver a developer the Tasks
  alone decide; a line not planned is unmarked, with no suffix. With the
  development off the Tasks are not read. Each marked line the top
  of the Backlog leaves out is listed after the top, apart from the count of
  those more; a Backlog where nothing can start marks none. It is a view of
  `fgraph status` and `fgraph watch`: no `next` command exists. The view holds
  it as data on the row, beside what the row waits for.
- `fgraph start` given no id starts the first of them (S-0121, the decision of
  the developer of 2026-11-23: the first line of the Backlog that can start, the
  one status marks). The id is read from the rows of status before the checks
  of a start run, so every refusal of a start names it, the one that holds a
  start to main among them. The rule is written once, in
  `src/flowgraph/status/next.py`, and `src/flowgraph/status/top.py` reads it. The
  same cases as the README paragraph hold, the development off and on. The two
  refusals, exit 2 and nothing written: `nothing to start: the Backlog is empty`
  and `nothing to start: no line of the Backlog can start now, fgraph status
  marks none -- fgraph start {first} says why its first line cannot`. A start
  that names its id is unchanged.
- A reorder names two items in Backlog; one that is not there, or the same
  one twice, is refused. A Feature in progress, completed or removed is not
  in Backlog, and is refused as a started work item is:
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
  number. A blocked Task does not move its work item in the list, and a
  blocked work item keeps the place its started time gives it, listed once
  (S-0138).
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
  it keeps its own line there. The removed Features follow the work items,
  by number (S-0058): a removed Feature is one line in place of its work
  items, as a Feature is in any bucket, so the work items under it are on no
  line of their own, those removed before it too; the completed ones of a
  removed Feature are on no line either, and its show lists them Completed
  (Persistence).
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
  Task is not completed; a removed Task is not counted, so one Task left
  beside two removed reads `S-0001  0/1 T  <title>` (S-0147). The lines of
  Backlog, Completed and Removed carry no
  progress. The Tasks are those the record status reads holds: the row of a
  work item is read with its Tasks, each with its state.
- A blocked work item is listed under InProgress as a started one is, marked
  `!` before its id and ending with what it waits on and why (S-0138):
  `! S-0001  0/1 T  <title>  -- waiting on <what>: <reason>`, its agent in
  brackets before its title when it has one and its Tasks being worked under
  it. Under a Feature the same line stands two columns further in. It is not
  marked `?`, whatever its Tasks, and it takes a place of
  `development.parallel` in the marks `>`, as a started one does.
- Under a work item of InProgress `fgraph status` lists each Task of it being
  worked, the developer's decision of 2026-11-21, after board 1's watch: the
  started Task as `    => T-0001  <title>`, and a blocked one as
  `    !  T-0002  <title>  -- waiting on <what>: <reason>`, in the order the
  file holds them (S-0084: the line names the reason of the block beside what
  it waits on; with an empty reason the `: <reason>` is left out). A Task in Backlog,
  completed or removed is not listed. A Task line belongs to
  its work item: it does not count toward the top 5 of the heading, nor in
  the count beside it.
- `fgraph status` marks `?` a started work item that holds a Task with every Task
  completed, as ready for review, the reading of S-0114: the mark stands in the first
  column of its line, beside `>`, `~`, `!` and `=>`, alone in InProgress or under a
  started Feature, with the development on or off, and `fgraph watch` shows it the same.
  It is read from the rows as status reads them, from the worktree of the work item with
  the development on, derived at each listing and kept in no file, so no field of a row
  holds it. A work item with no Task is not marked, nor is one whose Task is in Backlog,
  started or blocked, nor a completed one; the line of a Feature carries no mark. A removed
  Task counts neither way: a work item whose Tasks left are each completed is marked, and
  one whose every Task is removed is not (S-0147). A marked
  line the top leaves out is listed after it, apart from the count of those more.
- Under a Feature of InProgress `fgraph status` lists each started work item
  of it, the developer's words of 2026-11-21 -- a Feature is to its work
  items what a work item is to its Tasks: the work item as one of InProgress
  is written, with its progress and under it its Tasks being worked, two
  columns further in -- `    S-0001  1/3 T  <title>`, then
  `      => T-0001  <title>` -- the last started first. Those lines belong to
  the Feature: they count neither toward the top 5 of the heading nor in the
  count beside it.
- `fgraph status` marks a Feature blocked while a started work item of it
  holds a blocked Task (S-0055), the developer's words of 2026-11-21, "a
  Feature can be blocked, or gets blocked when its child work item is
  blocked": `!` in the first column of its line, before its id, which stays
  in its column, and `-- waiting on <what>: <reason>` after its title, as the
  line of a blocked Task ends -- `! F-0001  1/3 W  <title>  -- waiting on
  <what>: <reason>`. What is waited on, and why, is that of the first blocked
  Task of its started work items, in the order they are listed under it and the file of each holds
  its Tasks. The mark is derived at each listing from the rows status reads
  and kept in no file: no state of the Feature or of the work item holds it,
  and it is gone with the unblock of the Task. A started Task beside the
  blocked one does not lift it, decided when S-0055 was ordered: the Feature
  is marked as long as such a work item holds a blocked Task. The lines of
  the work item and of its blocked Task under it stay as they are, a Feature
  without such a Task is listed as before, and the line is cut to the width
  as any other (below). A child work item is blocked when it holds a blocked
  Task, and when it is blocked itself (S-0138, on the developer's word on
  B-0025, which reverses the reading that a block of a work item was shown
  and not taken): a started Feature is marked `!` by a blocked work item
  under it too, with what that work item waits on and why. Its own block
  comes first, then that of a work item, then that of a Task, each work item
  in the order listed with its own block before that of its first blocked
  Task. A Feature never started whose work item was
  started before a Feature had a state (Persistence) is marked the same way,
  since the mark reads the started work items listed under the Feature and
  not its state; one never started that holds a blocked work item is in
  InProgress, as one holding a started work item is.
- `fgraph status` lists a `BlockedFeature` under InProgress with the same
  look (S-0056): `!` before its id and `-- waiting on <what>: <reason>` after
  its title, `! F-0001  0/1 W  <title>  -- waiting on <what>: <reason>`. Here
  what is waited on, and why, is that of the Feature, read from its state and
  kept in its file
  (Persistence). The block of the Feature itself comes before that of a Task
  of its work item: while both are blocked the line of the Feature names
  what the Feature waits on, and the line of the Task under it what the Task
  waits on. `fgraph show` of a `BlockedFeature` lists its bucket as
  `InProgress, blocked`, then `reason` and `waiting on`, as it lists a
  blocked Task.
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
- Its complexity is a part too, the reading of S-0112: `--complexity high`
  gives it in place of the one it had, in Backlog alone, alone or beside the
  other parts. A word that is none of `low`, `medium` and `high` is refused,
  exit 2, nothing written; an amend does not take it back to none.
- It is not a move: the type of the item stays, and so do its id, its created
  time, its Tasks and its place in the queue.
- Each part goes through the constructor an `add` uses, so a blank title or a
  blank part of the criterion is refused. The description is optional free
  text: a blank one clears it.
- An amendment that names no part is refused.
- Only a work item in Backlog is amended: a started or a completed one is
  refused, since its wording is what the work was started on.
- Its parent is a part too, the reading of S-0059: `--parent F-0001` puts the
  work item under that Feature and `--parent none` takes it out to stand
  alone, alone or beside the other parts. It is still no move of the work
  item: its id, its created time and its Tasks stay, and so does its entry in
  the queue, which then orders it where its new parent reads it
  (Persistence).
- The Feature it is put under takes it by the one rule `fgraph add --parent`
  follows too (B-0016): a Feature in Backlog, started or blocked, never one
  completed or removed, `S-0003 cannot be put under F-0001: F-0001 is
  completed already`. The one it is taken out of is in Backlog, as the work
  item is: one that is started, blocked or completed is refused naming the
  work item and the Feature, `S-0002 cannot be taken out of F-0001: F-0001
  is blocked`. The one it is put under is read first, so a move from one
  Feature to another names that one when both refuse. A Feature the record
  does not hold is refused, `no Feature F-0009 in the record`, and so is a
  text that is neither a Feature id nor `none`, naming both, `'None' is
  neither a Feature id nor none: a Feature id is F- and a number`. Nothing
  is written then, the other parts named beside it neither.
- A parent that is the one the work item has moves it nowhere: no Feature is
  read and the amend is taken, as one that rewrites a part to the text it
  has.
- The criterion it realizes is a part too, the reading of S-0100: `--realizes
  N` gives it in place of the one it had, and `--realizes none` takes it away,
  in Backlog alone, alone or beside the other parts. It is refused, exit 2,
  nothing written: for a work item that stands alone, `--realizes names a
  criterion of the Feature a work item is under: this one stands alone`; for a
  number the Feature does not have, `F-0001 has no criterion 3: its criteria
  count from 1 to 2`; for `0`, `a criterion is counted from 1: 0 is below 1`;
  for a text that is neither, `--realizes 'two' is neither the number of a
  criterion nor none`; and for a Feature id, `F-0001 has no realizes`, as for
  any part of a work item. An amend to another parent, or to none, drops the
  criterion it had unless `--realizes` is given with it, which is checked
  against the Feature it is put under.
- A Feature in Backlog is amended too, the reading of S-0057: `amend` of its
  id rewrites its title, its description and its criteria, one alone or
  several together, and a part it does not name stays as it was. `--criterion`
  is given once per criterion, as an `add` takes it, and the ones given
  replace the ones the Feature had, whole: none is added to them and none is
  rewritten alone. Each part goes through the constructor an `add` uses, so a
  blank title or a blank criterion is refused and a blank description clears
  it. The criteria given replace the list and no work item is written: a work
  item keeps the number it names and so names the criterion now at that
  place, and a number past the end names none of the criteria, which `fgraph
  show` of the work item says.
- It is no move of the Feature: its state stays, and so do its id, its
  created time, its work items and its place in the queue, which the amend
  never writes. It is one write of the file of the Feature, committed as
  `chore: amend F-0001 in the record`, made where a Feature is written: on
  the branch of a work item it is refused, as every write of a Feature is.
- Only a Feature in Backlog by its own state is amended, as only a work item
  in Backlog is: a started, a blocked or a completed one is refused, `F-0001
  is started already`, `F-0001 is blocked`, `F-0001 is completed already`. An
  amendment that names no part is refused, and so is a Feature the record
  does not hold. The parts of a work item are not those of a Feature:
  `--given`, `--when`, `--then`, `--observed`, `--expected`, `--hypothesis`
  and `--parent` given to one are refused naming them, `F-0001 has no given,
  then: a Feature is amended by its title, its description and its criteria`,
  and `--criterion` given to a work item is refused the other way round,
  `S-0001 has no criteria: only a Feature states them`. Nothing is written
  then, the other parts named beside it neither.
- A Task in Backlog is amended too, the reading of S-0144: `amend` of its id
  rewrites its title (`--title`), its output (`--output`), its check
  (`--check`) and its description (`--description`), one alone or several
  together, each through the constructor an `add` uses, so a blank title,
  output or check is refused and a blank description clears it. It is no move
  of the Task: its id, its created time, its state and its place among the
  Tasks stay. It is one write of the file of the work item that holds it,
  saved whole.
- The work items that take it are those that take a new Task: one in Backlog,
  started or blocked; a completed or a removed one refuses. A Task that is not
  in Backlog is refused naming its state, `T-0001 is started already`,
  `T-0001 is blocked`, `T-0001 is completed already`. A part that is no part
  of a Task is refused naming it, `T-0001 has no then: a Task is amended by
  its title, its output, its check and its description`, and `--output` or
  `--check` given to a work item the other way round, `S-0001 has no output:
  only a Task states them`. An amendment that names no part is refused, `amend
  rewrites no part of T-0002: name one`. Nothing is written then.
- Its check follows the add of a Task: with the development off a check given
  is refused in the words of the add, `a Task takes no --check: the
  development is off -- set development.enabled = true in <file>`; with it on
  a check given is kept; and none is asked of an amend that names none, since
  an amend keeps the parts not given. It is committed as `chore: amend T-0001
  of S-0001 in the record`. With the development on a Task in Backlog of a
  started work item is amended in the worktree of that work item and refused
  on `main` naming it, as every write of its Tasks is.

## Depends on

A work item depends on the work items it waits for, the reading of S-0066:
`fgraph add --depends-on ID` and `fgraph amend --depends-on ID` of a work item
in Backlog, once per work item, of any kind. An amend replaces the ones it had,
and `--depends-on none` alone takes them all away.

- It refuses the start, not the work: `fgraph start` of a work item in Backlog
  exits 2 while one it depends on is not completed, naming each with its
  bucket, `S-0002 cannot start: it depends on S-0001, in Backlog`; several are
  listed one after the other, `S-0003 cannot start: it depends on S-0001, in
  Backlog; S-0002, in InProgress`. It stops refusing once each is Completed.
  A work item it depends on that is removed is not completed, so it is named,
  `in Removed`, until the depends on is amended.
- The start of a Feature starts its first work item and the completion of a
  work item starts the next one of its Feature, so both are refused as that
  start is: `F-0001 cannot start: its first work item S-0002 cannot start: it
  depends on S-0001, in Backlog`. A completion stands and says it on a line of
  its own, `not started: S-0003 cannot start: it depends on S-0001, in
  Backlog`, as for any next work item that cannot start.
- The ids are checked at the write, and the write is refused with exit 2,
  nothing written: an id of a kind no work item has, `no Story S-0009 in the
  record` for one the record does not hold, `a work item cannot depend on
  S-0002: it is removed`, `S-0001 cannot depend on itself`, and a dependency
  that would close a cycle, `S-0001 cannot depend on S-0003: it would close a
  cycle`, whether S-0003 depends on S-0001 directly or through others. `none`
  given with an id is refused, `none stands alone: it takes every dependency
  away`. A Feature is amended by its title, its description and its criteria,
  so `--depends-on` given to one is refused as a part it has not.
- `fgraph show` lists `depends on` with each id and the bucket it is in now,
  `S-0001 (Backlog)`, after the parent, and lists none for a work item that
  depends on none. The file holds the ids as `depends_on = ["S-0001"]`, only
  when there is one, read back in every state; an id of no kind, or the work
  item itself, makes the file refused when it is read.
- `fgraph status` marks what waits, the reading of S-0085: the line of a work
  item in Backlog that depends on one not completed starts with `~` and ends
  `-- depends on S-0001`, with each id not completed in the order written; the
  mark is gone once each is completed. A Feature in Backlog carries it when its
  first work item, the one its start takes, waits, with the ids that one waits
  for; a work item under a Feature is on no line of the Backlog. The mark is
  not the `!` of a block, which ends `-- waiting on <who>`: a block waits on a
  person, a dependency on a work item. A line longer than the terminal is cut
  as any other, and `fgraph watch` draws the same line.

## Filed during

A work item names the work item it was found during, the reading of S-0067:
`fgraph add --filed-during ID` of a Story, an Upkeep, a Bug or a Spike, one id
of any kind of work item, in any state but Removed. A Task and a Feature take
none.

- It is given at the add alone: when a work item was found does not change, so
  `fgraph amend` does not take `--filed-during`, and an amend keeps it.
- The ids are checked at the add, which is refused with exit 2, nothing written:
  an id of a kind no work item has, `no Story S-0009 in the record` for one the
  record does not hold, `a work item cannot be filed during S-0001: it is
  removed`.
- Which side is stored: the work item that was found keeps the id, as
  `filed_during = "S-0001"` in its file, only when there is one, read back in
  every state. The other side is derived: `fgraph show` of the work item found
  during lists `filed here` with the id of each work item that names it, in the
  order of the record, read from the record and stored nowhere.
- `fgraph show` of the work item that was found lists `filed during` with the
  id, after the work items it depends on, and lists none without one.

## Superseded by

A removed work item names the work item that supersedes it, the reading of
S-0068: `fgraph remove --superseded-by ID` of a Story, an Upkeep, a Bug or a
Spike in Backlog, one id of any kind of work item. It replaces the free text of
a reason such as `refiled under F-0002 as S-0050`. It belongs to the removed
state, with its removed time, not to every state.

- It stands in place of the reason or beside it: a remove with neither is
  refused naming both, `a remove takes --reason or --superseded-by, or both`.
  A reason is blank only when `--superseded-by` is given. A Feature is removed
  with `--reason` alone, and is refused `--superseded-by`.
- The ids are checked at the remove, which is refused with exit 2, nothing
  written: an id of a kind no work item has, `no Story S-0009 in the record`
  for one the record does not hold, `S-0001 cannot be superseded by itself`,
  `a work item cannot be superseded by S-0002: it is removed`.
- Which side is stored: the removed work item keeps the id, as
  `superseded_by = "S-0002"` in its file beside `removed` and `reason`, only
  when there is one. The other side is derived: `fgraph show` of the work item
  that supersedes lists `supersedes` with the id of each work item that names
  it, in the order of the record, read from the record and stored nowhere.
- `fgraph status` lists a removed work item as `-- superseded by S-0002`,
  before the reason given beside it, joined by a comma; `fgraph show` of it
  lists `superseded by` before `reason`.

## Amends

A work item names the completed work item whose landed behavior it changes, the
reading of S-0069: `fgraph add --amends ID` of a Story, an Upkeep, a Bug or a
Spike, one id of any kind of work item that is Completed. A Task and a Feature
take none.

- It is given at the add alone: which work item the new one changes does not
  change, so `fgraph amend` does not take `--amends`, and an amend keeps it.
- The ids are checked at the add, which is refused with exit 2, nothing written:
  an id of a kind no work item has, `no Story S-0009 in the record` for one the
  record does not hold, `a work item cannot amend S-0001: it is not completed`.
- Which side is stored: the work item that amends keeps the id, as
  `amends = "S-0001"` in its file, only when there is one, read back in every
  state. The other side is derived: `fgraph show` of the completed work item
  lists `amended by` with the id of each work item that names it, in the order
  of the record, read from the record and stored nowhere.
- `fgraph show` of the work item that amends lists `amends` with the id, after
  the work items it supersedes, and lists none without one.
- A no files the Bug, the decision of F-0011: `fgraph verify ID --no TEXT` of a
  completed Story, Bug or Upkeep keeps the answer no on it and adds, in the same
  write, a Bug in Backlog that amends it, as `fgraph add bug --amends ID` would:
  the next Bug id, its observed the text, its expected the Then of a Story or
  an Upkeep or the expected of a Bug, its title `No at the verify of ID:` and
  the title of the work item. It joins the Feature of the work item while that
  Feature is not completed, by the rules of an add, else it stands alone.
- No move goes backwards: the work item stays Completed with its answer, and
  the Bug carries the work that remains. The Bug is saved first, then the work
  item; both are one commit, `chore: verify S-0001 no and add B-0001 in the
  record`, and a failure after the first save puts every file back as it was.

## Relations

The five typed relations of a work item, each a reference the work item that
names it stores, the other side derived from the record:

| Relation | Stored on | Derived side | Move that reads it |
|---|---|---|---|
| `parent` | the work item, as `parent`, the Feature it is under | the work items of a Feature | the start of the Feature, which starts its first work item |
| `depends on` | the work item, as `depends_on` | `depended on by` in the about of the other | the start of the work item, refused while one is not completed |
| `filed during` | the work item, as `filed_during` | `filed here` in the show of the other | none |
| `superseded by` | the removed work item, as `superseded_by` | `supersedes` in the show of the other | none |
| `amends` | the work item, as `amends` | `amended by` in the show of the other | none |

The criterion a work item realizes is kept on the work item beside its `parent`, as
`realizes`: it is not one of the typed relations read by `fgraph about`, `fgraph graph` or
the check of the read, and a number past the criteria of the Feature is no refusal of a read.

Every relation is checked twice: at the write, by the command that makes it, and again at the
read, by every command, on the record as the worktrees compose it, so a work item that a
worktree of a started work item holds is no missing id. The read checks each relation the
record keeps: the `parent`, `depends on`, `filed during`, `superseded by` and `amends` of a
work item, the `is-a` and `part-of` between two terms, and the terms a work item, a Feature
or a knowledge line is about. Each must name a Feature, a work item or a term that the
record holds. A cycle is a chain of one relation that comes back to where it started, of
`depends on` between work items or of `is-a` or `part-of` between terms. A relation that
fails is refused with exit 2, nothing written and no traceback, in one line that names the
file that holds it:
`fgraph: error: <path>: <relation> names <id>, which is not in the record`, or
`fgraph: error: <path>: <relation> closes a cycle: S-0001 -> S-0002 -> S-0001`.

## About

`fgraph about ID` is a view of the links of an item: it reads the record as plain data
and writes nothing, and every other side of a relation is derived from the record, as
`fgraph show` derives it. A relation that holds nothing is not listed. Each heading carries
its count and each linked item is one line, its id, its bucket and its title.

- A work item lists, in this order: `feature`, `depends on`, `depended on by`,
  `filed during`, `filed here`, `supersedes`, `superseded by`, `amends`, `amended by`,
  `terms` and `knowledge`. A term is one line of its name and its meaning, a knowledge
  line one of its kind, its day and its text.
- A Feature lists `work items`, `terms` and `knowledge`.
- An id that `fgraph show` refuses is refused in the same words, exit 2.
- A term name is taken as `fgraph show` takes it, and the term lists its meaning and
  relations as `show` does, then the items and the knowledge lines about it and about
  every term under it. The walk follows both relations, `is-a` and `part-of`, from the
  term to the terms that name it: the parts of it and the kinds of it, and those under
  them, to any depth, nearest first. It ends on a term already reached, so a cycle ends
  it. A line or an item reached through another term is marked with that term, `(via
  lane)`; each is listed once, under the nearest term, so one about the named term
  itself is never marked. A word that is no id, no term of the record and no file is refused,
  exit 2, naming the three. This is what a term as a node answers and a tag could not: a
  tag is matched by its own name, a relation to the whole is not followed.
- A text that is no id and no term name, or a term name the record holds no term of,
  is read as the path of a file when it is a file from the directory fgraph runs in.
  A file is a derived node of the record: nothing is stored for it. The answer is read
  from git, by the commit each completed work item and each completed Task names: the
  files that commit changed, as paths from the top of the work tree. A merge commit is
  read by what it brought to its first parent, so a landed work item names the files
  its branch changed. A commit git does not know names no file. The completed work
  items and Tasks whose commit changed the file are listed newest first, a Task under
  its work item; a file none touched is said so in one line, exit 0. Outside a git
  work tree a path is refused, saying the answer is read from git, and so is a path
  outside the work tree of the directory, exit 2. A text that is no id, no term and
  no file is refused, exit 2, unless a line of knowledge governs it (below).
- What governs a file is read from the lines of knowledge. A text that is no id and
  no term is read as the path of a file too when a `--governs` line of the record
  names it, on the disk or not; outside a git work tree, or for a path outside the
  one of the directory, a path governed by a line lists those lines alone, and one
  governed by none is refused as above. `fgraph about` of a file lists, first,
  under `Governed by`, the lines that govern it, last noted first, each with its
  kind, its date, the id of its item and its text; then, as before, the completed
  work items and Tasks whose commits changed it. A governed file no commit touched
  lists the lines alone.

## Brief

`fgraph brief ID` prints the whole brief of a work item, the input a coordinator hands an agent
that develops it. It reads the record and git as plain data and writes nothing. It takes a work
item of any kind -- Story, Upkeep, Bug or Spike -- in any state, Backlog, InProgress, Completed
or Removed. The id of a Feature, the id of a Task and an id of no kind are refused, exit 2,
naming the four kinds; so is an id the record holds no work item of. It holds data alone: no
sentence on how the work is done.

The text is the text of `fgraph show ID`, then four sections, each left out when it has nothing,
so the brief of a work item that has none of them is exactly the text of `show`:

- `Worktree`: the branch `wi/ID-*` and the path of the worktree git holds for it, the first
  branch with a worktree, else the first branch alone; none for a record outside a git work tree
  or one git ignores.
- `Feature`: its id, its bucket, its title, its description and its knowledge lines.
- `Governed by`: every knowledge line of the record that governs a path one of the Tasks of the
  work item names, last noted first, as `fgraph about` of a file lists them.
- `Terms (n)`: each term the work item or its Feature is about, with its meaning, each once.

A governed path is named by a Task when it stands as a whole path in the expected output or the
description of the Task: no letter, digit, slash, dot, underscore or hyphen before it, and no
letter, digit, slash, underscore or hyphen after it. `src/gate.py` is named in `changed:
src/gate.py holds the gate`, and is not named in `tests/src/gate.py` or in `src/gate.pyi`.

`--format json` prints the same as one JSON document, a contract: the keys are sorted, the
indent is two, the text ends with a newline, a key that holds nothing is `null` and a list that
holds nothing is `[]`, so two runs on one record print the same bytes. The keys are `agent`,
`branch`, `bucket`, `complexity`, `criterion` (`answer`, `decision`, `expected`, `given`,
`hypothesis`, `observed`, `then`, `when`), `depends_on` (each with `id` and `bucket`),
`description`, `feature` (`id`, `title`, `bucket`, `description`, `knowledge`, or `null`),
`governed_by` (each with `item`, `kind`, `noted`, `text`, `about`, `governs`), `id`, `kind`,
`knowledge`, `state`, `tasks` (each with `id`, `title`, `state`, `expected_output`, `check`,
`description`, `commit`, `reason`, `waiting_on`), `terms` (each with `name` and `meaning`),
`title`, `waits_for` -- the ids of `depends_on` whose bucket is not Completed -- and
`worktree`. `noted` is the full ISO time. A format that is neither `text` nor `json` is refused
naming both, exit 2.

## Goal

`fgraph goal F-ID [--hours N]` prints one line, the `/goal` a developer pastes into Claude Code
to start the agent-driven development of a Feature. It reads the record and writes nothing;
fgraph never sets the goal, it words it. The scope is the Feature alone: its work items in
Backlog, named in the order they start. The output is text only, the line and its newline.

The line holds, in this order: the Feature and its end state, `fgraph show F-ID lists` the ids
as `a`, `a and b` or `a, b and c` `Completed`; the bound, `or stop after N hours`; the
coordinator, one whole work item handed to one subagent, at most `development.parallel` at once,
or as many as can start when `development.parallel` sets no limit; and the halt, the goal is met
as well when the session prints `[HALT] <id>: <the decision needed>` on a change to a criterion,
a Task or the scope of a work item, or a removal, that the developer has not agreed. It says
nothing of models, review, landing or findings: that protocol stays in the skill of the
coordinator.

From the record come the ids of the Feature and of its work items in Backlog and
`development.parallel`; from the option come the hours, 8 by default. Everything else is fixed
text.

It is refused, exit 2, naming why: for a record whose development is off, naming
`development.enabled`; for one whose driver is a developer, naming `development.driver`; each
message says how to set the key with `fgraph config set`. A Feature with no work item in
Backlog is refused saying it holds none. A Feature holding a work item in Backlog with no Task,
or with no complexity, is refused in the words of the start of the Feature (B-0031), since no
start would take it and no coordinator could meet the goal: `F-0001 cannot start: S-0002 has no
Task to start with`, or `F-0001 cannot start: S-0002 has no complexity to start with: set it
with fgraph amend S-0002 --complexity low, medium or high`. The first such work item in start
order is named, and a missing Task is named before a missing complexity. Hours that are not a
whole number of 1 or more are refused saying so.

The wording follows the page of the documentation of Claude Code on `/goal`
(code.claude.com/docs/en/goal): one measurable end state, a stated check, the constraints that
matter and a bound, in a condition of at most 4,000 characters; the line is under that.

## Terms

A term is a word of the project and what it means, the first node of its ontology.
It is a node of the record of its own, not a tag on a line of knowledge, and it has
no flow: it is in no bucket and no queue, and it has no state, no Tasks and no
criterion. It is added and then it stands.

- A term holds its name, its meaning and the time it was added. Its name is its id:
  lowercase words of letters and digits joined by `-`, as `gate` or `work-item`.
  A name that reads as the id of an item, as `S-0001` or `F-0001`, is refused, so
  an id names one thing, and so is a name that is no such words. A term named as a
  spelling of an id a command reads, as `f15`, is shadowed by the id: the command
  reads it as the id, never as the term.
- A meaning says something: a blank one is refused naming the part, as the
  blank part of an item is.
- One file per term, `terms/gate.toml` in the record, with `name`, `meaning` and
  `added`. It is written beside its path and read back whole before it replaces
  it, and a file that holds no term is refused when read, naming the file.
- `fgraph add term NAME --means TEXT` adds it as one write and one commit, `chore:
  add term gate in the record`, and says `added gate`. The name of a term the record
  holds already is refused. `fgraph terms` lists every term by name with its meaning,
  or says in one line that the record holds none, and `fgraph show NAME` prints
  the term with its meaning; a name that is no term of the record is refused.
- A term is written on `main` alone, the developer's decision of 2026-11-22. On
  the branch of a work item `fgraph add term` is refused, exit 2, naming the work
  item the branch owns, and writes nothing. The worktree of a started work item
  reads the terms of the record of `main`, as the Task ids are read across the
  worktrees: `fgraph terms` and `fgraph show` of a term there list what `main` holds
  now, a term added after the start included.
- Every refusal is exit 2, with nothing written.
- Two terms are related by one kind of a closed set of two, held once in
  `src/flowgraph/term/model.py`: `is-a`, the first is a kind of the second, and `part-of`,
  the first is a part of the second. A relation is stored on the file of the first
  term alone, as `is_a` or `part_of`, a list of the names of the terms it names, so
  a relation is one write of one file; the other side is read from the record, as
  the work items that name one as their parent are. `fgraph relate TERM KIND TERM`
  keeps it as one write and one commit, `chore: relate gate in the record`, and says
  `related gate part-of lane`.
- `fgraph show` of a term lists `is a` and `part of` with the terms it names, and
  `kinds` and `parts` with the terms that name it by `is-a` and by `part-of`.
- A kind outside the set, naming the two, a term the record holds none of, a term
  related to itself, a relation kept already and a relation that would close a
  cycle of its kind are refused, exit 2, with nothing written. A cycle is
  found as for the work items that depend on one another: the second term reaches
  the first through relations of the same kind.
- `fgraph relate` is a write of a term, so it is on `main` alone as `fgraph add
  term` is, and refused on the branch of a work item the same way.
- A work item, a Feature and a line of knowledge name the terms they are about,
  each by its name. The item or the line stores them, as `about`, a list of names
  in the order given, each once, in its file: at the top of the file of the item
  and in the `[[knowledge]]` table of the line. A term stores nothing of it; the
  items and lines about a term are read from the record, as the other side of a
  relation is. `--about TERM`, once per term, is taken by `fgraph add` of a work
  item or a Feature, by `fgraph amend` of one in Backlog, which gives the terms
  in place of its own and, as `--about none`, takes them all away, and by `fgraph
  note`. A term the record holds none of is refused, exit 2, naming `fgraph add
  term`, and so is `none` given with a term; nothing is written. A term is checked
  against the terms of the record of `main`, so a term added there after a branch
  was cut is accepted on the branch.
- A line of knowledge names the files it governs, with `--governs PATH`, once
  per file, taken by `fgraph note`. The line stores them, as `governs`, a list of
  paths in the order given, each once, in its `[[knowledge]]` table. A path is kept
  as written: from the top of the git work tree of the directory fgraph runs in, or
  as given outside one, and it is never checked against the disk, so a governed
  file may be renamed or not yet written. A file stores nothing of it; the lines
  that govern a file are read from the record, as the other side of a relation is.
- `fgraph show` of an item lists `about` with its terms, and each of its lines
  ends with its mark when it has one, then `(about gate, lane)` when it has
  terms, then `(governs src/gate.py)` when it governs files. `fgraph show` of a term lists,
  after its relations, `items` with the ids of the work items and Features about
  it and `knowledge` with the lines about it, the last noted first, each with the
  id of its item; both are read from the record, the started work items where
  `fgraph status` reads them. `fgraph knowledge --about TERM` narrows its list to
  the lines about that term; a term the record holds none of is refused.

## Graph

`fgraph graph` is a view of the whole record as a graph: it reads the record as plain
data, as `fgraph about` and `fgraph knowledge` do, and writes nothing. Its one format
is `json`, the default; another word is refused naming it, exit 2. The document holds
three lists.

- `nodes`: each has `id`, `kind`, `title` and `bucket`. The kinds are `feature`,
  `story`, `upkeep`, `bug`, `spike`, `task` and `term`. The title of a term is its
  meaning. The bucket is that of a Feature or a work item as `fgraph status` lists it,
  and `null` for a term, which is in none. A Task node has a fifth key, `state`, after
  `bucket`: `backlog`, `started`, `blocked` or `completed`, the words of a Task in
  `fgraph status --format json`. Its `bucket` is the one `fgraph show` lists the Task in:
  Backlog, InProgress for a started and a blocked one -- `state` tells them apart --
  Completed, and Removed for every Task of a removed work item, whose `state` is the one
  it kept. The node of a work item, of a Feature and of a term has the four keys alone.
- `edges`: each has `kind`, `from` and `to`. The kinds are `under` (a work item to its
  Feature), `task of` (a Task to its work item), `depends on`, `filed during`,
  `superseded by` and `amends` (a work item to another), `is a` and `part of` (a term
  to another) and `about` (a work item or a Feature to a term). An edge is written once,
  on the side that names it, never as its other side.
- `knowledge`: the lines of every work item and Feature, each with its `item`, `kind`,
  `noted`, `text`, `about` and `governs`.

The order is fixed: the nodes by id, the edges by their kind in the order above and
then by their two ends, the knowledge lines by item and time noted, and the keys of
each object in the order given here, so two runs on one record print the same bytes.

## Status as JSON

`fgraph status --format json` is a second formatter of the rows `fgraph status` lists, the
reading of S-0087: no fact is computed again and none is read back from the text. It is
read by a consumer that parses it, so the keys below are a contract. `text` is the default
and prints what status printed before; another word is refused naming both, exit 2, as
`fgraph graph` refuses one. `--all` changes nothing for JSON, which lists every item
anyway; `fgraph watch` stays text. The keys of every object are sorted, the indent is two
and the text ends with a newline, so two runs on one record print the same bytes. A key
that holds nothing is `null`, never an empty text; a list that holds nothing is `[]`.

- Document: `buckets`, one object per bucket, always the four, in the order of the flow
  (Backlog, InProgress, Completed, Removed; Removed too when empty); `can_start`, the ids
  of every work item that can start now, in the order they take their places, the work
  items of a started Feature first (S-0110, which adds it to the reading of S-0087), `[]`
  for none; `next_to_start`, the first of them, or `null`; `ready_for_review`, the ids of
  every work item the text marks `?`, in the order it lists them, a work item under a
  started Feature in its place (S-0114), `[]` for none.
- Bucket: `name`; `count`, the number of its items; `items`, every one of them, in the
  order the text lists them.
- Work item (an item of kind `story`, `upkeep`, `bug` or `spike`): `id`; `kind`; `title`;
  `state`, as the record writes it (`backlog`, `started`, `blocked`, `completed`,
  `removed`); `commit`, the one it was completed in; `reason`, the one it was removed
  for; `superseded_by`, the id that supersedes it; `progress`, an object `completed` and
  `total`, its Tasks completed of all, a removed Task counted in neither (S-0147);
  `tasks`, in the order written, a removed one among them; `waits_for`, the
  ids it depends on that are not completed, in the order written.
- A work item holds its `block` too, the reading of S-0138: an object `reason` and
  `waiting_on` while it is blocked, else `null`, in a bucket and under a Feature alike, as
  the `block` of a Feature is built; its `state` is then `blocked`, and its `reason` stays
  the one it was removed for.
- A work item holds its `complexity` too, the reading of S-0112: `low`, `medium` or
  `high`, else `null`; a Task and a Feature hold none.
- Task: `id`; `title`; `state` (`backlog`, `started`, `blocked`, `completed`, `removed`);
  `commit`; `reason` and `waiting_on`, those of a block, `null` unless it is blocked; a
  removed Task holds the `reason` it was removed for and `waiting_on` `null` (S-0147).
- Feature (kind `feature`): `id`; `kind`; `title`; `commit`; `reason`, the one it was
  removed for; `progress`, an object `completed` and `total`, its work items completed of
  those it holds; `waits_for`, what its first work item in Backlog waits for; `block`, an
  object `reason` and `waiting_on` while it is blocked, else `null`; `work_items`, every
  work item under it as a work item above, in any state -- Backlog, started, blocked,
  completed or removed -- in the order `fgraph show` of the Feature lists them (the reading
  of T-0370: the hook that parses the document cannot ask again). The text lists the
  started ones alone; the document lists all of them, and `progress` counts them as before.

A work item holds its `agent` on every item of a bucket and in the `work_items` of a
Feature, the reading of S-0113: the name it is handed to, else `null`.

The block of a Task is its own state and is carried by the Task: a Feature does not copy
it, as the text line of a Feature does. The node of a Task in `fgraph graph` carries the
same `state`, with its bucket (see Graph).

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
- With the development on and the record inside a git work tree, a record git
  ignores included, the commit given is asked of git as
  `git rev-parse --verify <sha>^{commit}`: a sha, whole or abbreviated, that
  names one commit of the repository is held, on `main`, on another branch or
  on none. A sha git does not know, the sha of an object that is no commit, as
  a tree, and an abbreviation several commits share exit 2 with the line
  `fgraph: error: T-0001 cannot complete: the repository holds no commit c6e0f15`,
  nothing is saved and no check of the Task is run. A Task is refused as a work
  item is; `fgraph land` writes its own merge commit and is not asked. The
  check is `src/flowgraph/development/commit_held.py`.
- With the development off `fgraph complete` takes none, and a `--commit`
  given is still kept as the evidence. The commit given is not looked up, and a
  record outside a git work tree is not asked either, so a record whose shas
  come from elsewhere completes.
- The evidence is a value of its own in the model, a commit or none (`Commit`
  or `NoCommit`, `src/flowgraph/criterion/model.py`): no commit is a value of the
  evidence, not a missing one, as standing alone is a value of `parent`.
- A Spike is completed with its decision either way: the decision answers its
  hypothesis and stands beside the commit or none, and beside the answer, yes
  or no. A no is a completion as a yes is: nothing is refused for it and no Bug
  is filed.
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
- With the development on, `complete` asks that the repository holds the commit
  it is given (Evidence), and still does not ask that `main` holds it.

## Ids

An id is the prefix of its kind and a number counted from 1 per kind, written
with at least four digits. `fgraph` hands out the next free number.

A command reads an id in any case, its dash and its leading zeros left out:
`f15`, `f-15`, `F15` and `f-0015` all name `F-0015`, once, as the arguments are
read. `fgraph` writes and prints the canonical form, and reads the files of the
record in it alone. A number of 0 is no id, so `f-0` is refused as before, and a
text that is no such spelling is left as typed.

`E-nnn`, `W-nnn` and `T-nnn` of board 1 are no ids of fgraph, see From board 1,
Archive.

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

- `fgraph init` makes the record of a directory: with the key `git config
  fgraph.record` set and no `--dir`, the folder the key names, refused when that
  folder is there or when its parent is no directory; else `.fgraph/` in the
  directory it runs in, or in the one `--dir` names. A named folder is
  committed or not by the rule of any record. Inside it writes `config.toml` alone,
  at the defaults (`[git] commit = true`, `[development] enabled = false`),
  since git commits no empty directory; `items/` comes with the first write. In
  a git work tree it commits that file as one write of the record, `chore: make
  the record`, unless git ignores the record. A directory that holds `.fgraph/`
  or `fgraph/` is refused, exit 2, naming it, and nothing is written; init is
  the one command that runs with no record located.
- S-0128, the decision of the developer of 2026-11-23 (a key of the git
  configuration of the clone, no variable of the environment and no file at the
  root): the record is located in this order: `--dir`, then the folder the key
  `git config fgraph.record` names, relative to the root of the repository, then
  `.fgraph/`, then `fgraph/` in the directory it runs in. The developer writes
  the key; fgraph never does. No key, an empty value and a directory outside a
  git work tree read nothing, so a record outside git is located as before. A
  key that names no directory exits 2 with `fgraph: error: git config
  fgraph.record names <path>, which is no directory -- run fgraph init, or name
  another with git config fgraph.record PATH`. Worktrees share the
  configuration of their clone and each reads the folder under its own top, so a
  tracked record is the directory at the same path inside each worktree, as the
  bullets on the Task ids and on status already say, while a folder git ignores
  is in the checkout of main alone and the same command in the worktree of a
  work item exits 2 naming the key and the path there. fgraph asks git whether a
  rule names the folder, as for `.fgraph/`, so a record meant to stay untracked
  is named in `.git/info/exclude` or a `.gitignore` and takes the rules of the
  bullets starting A record git ignores and With the development on, the start
  of a work item on an ignored record, both left as written.
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
- A line of knowledge is one `[[knowledge]]` table inside the file of its work
  item, in the order noted, with its `kind`, its `text` and its `noted` time. A
  file without the table keeps none, and the table is read back whole in every
  state. `fgraph note` writes it as one write and one commit, `chore: note
  S-0001 in the record`, and says `noted S-0001`. With the development on, a
  started work item is noted in its worktree, where its Tasks are written, and
  every other one on `main`. `fgraph note` takes exactly one of `--finding`,
  `--decision`, `--deviation` and `--progress`, and the `kind` of the table is
  `finding`, `decision` or `deviation`; a file with any other kind is refused
  when read, naming the file. The id of a Task with one of the three kinds of
  knowledge, an id the record does not hold, a blank text and none or more than
  one of the four are refused, exit 2, nothing written. The table holds the key
  `mark`, `standing` or `open`, only when the line has one, so a file without
  it, as every file written before, is read as no mark, and a file with another
  word is refused when read, naming the file. `fgraph note` takes at most one of
  `--standing` and `--open` beside its kind, both together refused by the
  command line, exit 2, nothing written. `fgraph show` lists the
  lines under `Knowledge (n)` after the Tasks, each with its kind, its date and
  its text, and no heading when there is none; the mark follows the text as
  `(standing)` or `(open)`, as in the line
  `  finding  2026-11-22  is the queue one file too  (open)`.
- A progress line is one `[[progress]]` table inside the file of its work item,
  in the order noted, apart from `[[knowledge]]`, with its `text`, its `noted`
  time and, for a line of a Task, `task = "T-0001"`; a file without the table
  keeps none. `fgraph note S-0001 --progress TEXT` writes it as one write and
  one commit, `chore: note S-0001 in the record`, and says `noted S-0001`; of a
  Task, `fgraph note T-0001 --progress TEXT` says `noted T-0001 of S-0001` and
  commits `chore: note T-0001 of S-0001 in the record`. With the development on,
  a started work item that has a worktree is noted there, its Tasks too, or from
  `main` with `--dir` on the record of that worktree; `main` refuses it with
  `S-0001 is started: its Tasks are written in its worktree, <path>`, and every
  other work item is noted on `main`. Refused, exit 2 and nothing written: a
  Feature (`F-0001 keeps no progress line: fgraph note --progress takes a work
  item or a Task of it`), `--about` or `--governs` (`a progress line takes no
  --about and no --governs: it is no knowledge line`), a blank text (`text is
  empty`) and an id the record does not hold (`no Task T-0009 in the record`,
  `no Story S-0009 in the record`). `fgraph show` lists the lines of a Task under
  it as `progress`, with the day and the text, and those of the work item under
  `Progress (n)` after `Knowledge (n)`, with no heading when there is none.
- The answer of a closing is one `[verified]` table inside the file of a
  completed work item, with its `answer` (`yes` or `no`), its `text` and its
  `on` time, held only once there is one: a file without it, as every file
  written before, is read as before, and a Spike's file holding it is refused
  when read.
  `fgraph verify ID --yes TEXT` writes it as one write and one commit,
  `chore: verify S-0001 in the record`, and says `verified S-0001`, on `main`
  as a note of a completed item is. With `--no TEXT` it writes the answer no and
  files a Bug in the same write, as Amends states. It is refused, exit 2 and
  nothing written, for an item not completed, a Spike, a Feature, a Task, an id
  the record does not hold, a blank text, a second answer and a call with
  neither or both of `--yes` and `--no`.
  `fgraph show` lists it as `verified`, the answer, the day and the text, after
  the commit.
- The file of a work item holds the key `complexity` (`low`, `medium` or
  `high`) only when it has one: a file without it, as every file written
  before, is read as none, and a file holding any other word is refused when
  read, naming the file. `fgraph show` lists it as `complexity`, after the terms
  the item is about, only when there is one.
- `fgraph start S-0001 --agent sonnet-a1` names the agent a started work item is
  handed to, the reading of S-0113: one opaque word of at most 32 letters, digits
  and `. _ : / -`, built by `make_agent`, which fgraph does not interpret. The
  started work item holds it and the completed one keeps it; its file holds the
  key `agent` only when there is one, so a file without it, as every file written
  before, is read as none, and a file holding a name that is no agent is refused
  when read, naming the file. `fgraph show` lists it as `agent`, before the
  commit, only when there is one, and `fgraph status` lists it as `[agent]`
  between the progress and the title. `fgraph start F-0001 --agent sonnet-a1`
  hands the agent to the first work item the Feature starts. The start is refused,
  exit 2 and nothing written, for a Task, for a name that is no agent and with
  the development off, naming `development.enabled`. The start a completion, a
  landing or an unblock makes names no agent, and `fgraph start` of a work item
  started already stays refused: a started work item is handed to another agent
  by `fgraph hand`, below. The output line `started S-0001` is as before.
- `fgraph hand S-0001 --agent opus-b2` hands a started work item of any kind to
  the agent named, in place of the one it held or of none, the reading of S-0126:
  `--agent` is required, a command of its own, not a second `fgraph start`. It
  says `handed S-0001 to opus-b2` and commits `chore: hand S-0001 to opus-b2 in
  the record`. With the development on it is written where the Tasks of the work
  item are written: in its worktree, or from `main` with `--dir` on the record of
  that worktree; run on `main` without it, the scope of `main` refuses it and
  names the worktree. With no worktree, or a record outside git, it is written in
  the record itself. It is refused, exit 2 and nothing written, for a work item
  in Backlog, completed or removed, a Task id, a Feature id, a name that is no
  agent and with the development off, naming `development.enabled`. The agent is
  replaced and no history of the agents before it is kept in the file: the commits
  of the hands hold it.
- The file of a Feature holds its lines of knowledge as a work item's does, the
  same `[[knowledge]]` tables, read back whole in every state. `fgraph note` of a
  Feature is one write and one commit, `chore: note F-0001 in the record`, and
  says `noted F-0001`; `fgraph show` lists the lines under `Knowledge (n)` after
  its work items. It is written on `main` alone: on the branch of a work item,
  which writes that work item alone, the note of a Feature is refused naming it,
  as the write of any other item is, exit 2 and nothing written. A Task takes a
  progress line alone.
- `fgraph knowledge` is a view of the whole record: it reads every work item and
  every Feature and writes nothing. It lists every line of each, with its date,
  its kind, the id of its item and its text, then its mark when it has one, the
  last noted first; lines noted
  at one time come in the reverse of the order they were collected, the work
  items by kind and id before the Features. The decision of a completed Spike is
  listed among the decisions at the time the Spike was completed; it is not
  copied, and stays kept on the Spike as its `decision`. `--kind` narrows the list to
  `finding`, `decision` or `deviation`; any other word is refused naming the
  three, exit 2. A record with no line of the kind asked, or none, prints one
  line saying so and exits 0. `fgraph knowledge --search TEXT` narrows the list
  to the lines whose text holds the text, whatever the case of either; `--kind`,
  `--about` and `--search` narrow the same list, a line listed when it meets each
  one given. Only the text of a line is searched, not the title or the id of its
  item, its kind or its terms; with no such line it prints one line and exits 0
  (`no knowledge lines holding 'zzz' in the record`, or with a kind or a term asked
  too, `no decision lines about gate holding 'zzz' in the record`); a blank text is
  refused, exit 2, `search is empty`. The search is one filter of the entries,
  holding of `src/flowgraph/knowledge/list.py`, applied before the list is narrowed
  and ordered (S-0146).
- A blocked Task is kept as `state = "blocked"` with its `started` time, its
  `since` time, its `reason` and its `waiting_on`. Only a started work item's
  file may hold one, and it is read back through its start and its block.
  `fgraph block` blocks a started Task. A blocked Task is not started or
  completed, and its work item is not completed while it is blocked.
- `fgraph unblock` takes a blocked Task back to started, with the started
  time it had. Its reason, since and what it waited on leave the file, which
  keeps only what a state needs; git keeps the block. A Task that is not
  blocked is refused.
- A started work item of any kind is blocked and unblocked too (S-0138, on
  the developer's word on B-0025): `fgraph block S-0001 --reason <why>
  --waiting-on <what>` takes a `StartedWorkItem` to a `BlockedWorkItem` and
  says `blocked S-0001`; `fgraph unblock S-0001` takes it back to the
  `StartedWorkItem` it was, with its started time, its agent and its Tasks,
  and says `unblocked S-0001`. A `BlockedWorkItem` holds what a started one
  holds, then its reason, the time it is blocked since and what it waits on.
  Its file holds `state = "blocked"` with its `started` time, its `agent`
  when it has one, `since`, `reason` and `waiting_on`, read back through its
  start and its block; the unblock takes the three keys out of the file, and
  a blocked file with a blank reason is refused naming the file. Each is one
  write and one commit, `chore: block S-0001 in the record` and `chore:
  unblock S-0001 in the record`. Only a started work item is blocked: the
  block of one in Backlog is refused, `S-0001 is in Backlog: start it first`;
  of a blocked one, `S-0001 is blocked already`; of a completed or removed
  one, `S-0001 is completed already`, `S-0001 is removed already`; a blank
  reason or waiting on, `reason is empty`, `waiting on is empty`; and the
  unblock of one not blocked, `S-0001 is not blocked`. No Task of a blocked
  work item moves: its start, complete, block and unblock are refused naming
  the block, `T-0001 cannot start: S-0001 is blocked, waiting on <what>:
  unblock it first`, and the check of a Task of it is not run. A Task is
  still added to it and a line still noted. Its start, complete and hand are
  refused, `S-0001 is blocked: unblock it first`, and so is its landing,
  which drops the merge held; its amend is refused, `S-0001 is blocked`, and
  so is the remove of a Feature holding it, `F-0001 cannot be removed: S-0001
  is blocked`. Its own remove is no longer refused: it is removed on main as
  a started one is (S-0148, below). `fgraph block` still takes a Task and a
  Feature, as before.
- A completed item is kept as `state = "completed"` with its `started` and
  `completed` times and its `commit` sha. A started Story's file may hold
  completed and removed Tasks; a completed Story's file holds only completed
  and removed Tasks, since a Story completes once each Task of it is completed
  or removed, one whose every Task is removed too (S-0147).
- An item completed without a commit (Evidence) is kept the same way but for
  the `commit` key, which its file or its `[[tasks]]` table does not hold: a
  file without the key holds no commit, a value of the evidence in the model,
  so the files written before read as they are. Its row and its detail carry
  no commit: `fgraph status` lists such a work item under Completed with its
  id and its title alone, `S-0001  <title>`, and `fgraph show` lists no
  `commit` line of it, nor of a Task completed without one.
- A removed work item is kept as `state = "removed"` with its `removed` time
  and its `reason`, beside the fields and the Tasks it had: in Backlog when
  it is removed from Backlog; completed or removed when it is removed from
  InProgress. `fgraph remove` removes a work item in Backlog, started or
  blocked; a removed one takes no Task, no amend and no move, and leaves the
  queue as a started one does. A Feature in Backlog is removed too, its work
  items with it (below). A started or blocked work item is removed by
  `fgraph remove S-0001 --reason <why>` on main alone (S-0148); run in a work
  tree on another branch it exits 2 and writes nothing, `S-0001 is removed on
  main, in <path>: <work tree> is on <branch>`. With the development on, the
  whole work item is read from the worktree of its branch, as `fgraph show`
  reads its detail there, and the one file `.fgraph/items/S-0001.toml` is
  saved and committed on main, `chore: remove S-0001 in the record`; the copy
  of the worktree is left as it is, stale, as after a landing. Its completed
  Tasks are kept with their commits and each other Task is removed for its
  reason, or `superseded by S-0002` when the reason is blank and
  `--superseded-by S-0002` names what supersedes it, taken as from Backlog.
  A landing of it is then refused, and main stays where the remove left it.
- The branch and the worktree of a started or blocked work item removed go
  once the remove is committed, when main holds every commit of the branch:
  `removed branch wi/S-0001-<slug> in <path>` is said after `removed S-0001`,
  and `removed branch wi/S-0001-<slug>` for a branch with no worktree, which
  git deletes when merged. Otherwise both are left, with `left branch
  wi/S-0001-<slug> in <path>: main does not hold every commit of it`; the
  developer then removes them by hand, with `git worktree remove <path>` and
  `git branch -D wi/S-0001-<slug>`. A worktree holding a change is refused by
  git and left. A step git refuses exits 2 after the write, with its words
  and `-- S-0001 is removed, its branch wi/S-0001-<slug> is not`.
- A removed Task is kept in the file of its started work item as a
  `[[tasks]]` table with `state = "removed"`, its `removed` time and its
  `reason` after its `created` time, and no `started` time and no block
  (S-0147). `fgraph remove T-0001 --reason <why>` removes a Task in Backlog,
  started or blocked of a started work item, and says `removed T-0001 of
  S-0001`. It refuses, with exit 2 and nothing written, a Task of a work item
  in Backlog, `T-0001 cannot be removed: S-0001 is in Backlog`; of a blocked
  one, `T-0001 cannot be removed: S-0001 is blocked, waiting on <what>:
  unblock it first`; of a completed one, `T-0001 cannot be removed: S-0001
  is completed already`; of a removed one, `S-0001 is removed already`; a
  completed Task, `T-0001 is completed already`; a removed Task, `T-0001 is
  removed already`; a blank reason, `reason is empty`; and `--superseded-by`,
  `T-0001 is a Task: it is removed with --reason alone`. A removed Task
  refuses its start, its block and its complete as `T-0001 is removed
  already`, and its unblock as `T-0001 is not blocked`. `fgraph show` and
  `fgraph brief` list it under its title with `    bucket           Removed`
  and `    reason           <why>`; the heading `Tasks (N)` still counts it.
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
  `fgraph complete Q-0001 --commit SHA --decision TEXT --answer yes|no`, the
  commit given as the development needs it (Evidence), and `fgraph land` takes
  `--decision` and `--answer` the same way; the decision and the answer are
  kept beside the hypothesis they answer, as `decision` and `answer` in the
  criterion table. A Spike is not completed without its decision or its
  answer, no other kind and no Task takes one, and a file that holds a
  decision before the Spike is completed is refused. A file of a Spike
  completed before the answer was taken holds none and is read as before; a
  file that holds an answer other than yes or no is refused naming the file.
  `fgraph show` lists the answer under the decision, and `fgraph knowledge`
  lists the decision with its answer. The answer is a type of its own
  (`Reply`, with the `Decision` that carries it, `src/flowgraph/criterion/model.py`),
  not the `Verdict` of `fgraph verify`, which answers the closing of a Story, a
  Bug or an Upkeep and refuses a Spike. That the hypothesis reads as a yes/no
  question is not checked.
- The Story, the Upkeep, the Bug and the Spike share one work item
  (`src/flowgraph/work_item/`): its state types (`WorkItem`,
  `StartedWorkItem`, `CompletedWorkItem`, `RemovedWorkItem`), its moves, its
  file and its commands. The kind -- its noun, the article before it, the
  prefix of its ids and the form of criterion it takes -- is a value the id
  carries, so `Story` and `StartedUpkeep` are names of those types and a
  Story tells itself from an Upkeep by its id. A work item carries the
  criterion its kind takes: a `Scenario`, its Given / When / Then; a
  `Defect`, what is observed and expected; or a `Hypothesis`, which its
  completion turns into an `Answer`, the hypothesis with its decision and its
  yes or no. Each
  kind keeps only its kind, its id functions and those names; the kinds are
  listed once, in `src/flowgraph/record/store.py`.
- An amend rewrites the parts of the criterion the work item has: `--given`,
  `--when` and `--then`, `--observed` and `--expected`, or `--hypothesis`. A
  part of another form is refused.
- A Feature is kept as `items/F-0001.toml`: its id, its state line, its
  title, its description, its created time and its `criteria`, a list of one
  or more. It holds no Task. `fgraph add feature` adds one, on `main` as a
  work item is added, and `fgraph show` lists its criteria and its work items
  with their buckets.
- `fgraph show` takes the id of a work item of any kind or of a Feature
  (B-0003). A text that is neither is refused naming every kind and the
  Feature, `'T-0001' is no Story, Upkeep, Bug, Spike or Feature id`; a text
  written `F-` and a number below 1 is refused as a Feature id,
  `a Feature id counts from 1: 0 is below 1`.
- `fgraph start`, `fgraph complete`, `fgraph amend` and `fgraph remove` take
  a Feature too, so their refusal of a wrong id names it (B-0018): start and
  complete, which take a Task as well, `'X-1' is no Story, Upkeep, Bug,
  Spike, Task or Feature id`; amend and remove `'X-1' is no Story, Upkeep,
  Bug, Spike or Feature id`. A text written `F-` and a number below 1 goes to
  the Feature and is refused as a Feature id by each of the four, `a Feature
  id counts from 1: 0 is below 1`.
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
- A `BlockedFeature` is kept as `state = "blocked"` with its `started` time,
  the time it is blocked `since`, kept to the second, its `reason` and its
  `waiting_on` (S-0056), the keys a blocked Task holds. It is read back
  through the start and the block, so a block under another state, or that
  state without one of the three, is refused when the file is read. The
  unblock writes a `StartedFeature` with the started time it had: the three
  keys of the block leave the file.
- A `RemovedFeature` is kept as `state = "removed"` with its `removed` time,
  kept to the second, and its `reason` (S-0058), the keys a removed work item
  holds, beside the fields it had in Backlog and no started time and no
  block, those of a started or blocked Feature being dropped (S-0125). It is read
  back through the remove, so a removal under another state, or that state
  without one of the two, is refused when the file is read.
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
- The work items of a started Feature start side by side, limited by
  `[development] parallel` alone, what the work item depends on, its Task and
  its slug: no Feature holds one started at a time. This replaces the
  decision of 2026-11-21 that a Feature starts its work items one by one, on
  the developer's word of 2026-11-23 (S-0111). The completion of a work item
  still starts the next one of its Feature, now beside those still started,
  and the start of a Feature still starts one work item. The passages below
  that say one at a time are the history of that decision.
- `fgraph start F-0001` starts the Feature and its first work item with it,
  in one write and one commit, `chore: start F-0001 in the record`, and says
  `started F-0001 with S-0001`. The first work item is the first of its work
  items in Backlog in the order they start in (Order), so a Feature that
  holds completed work items starts with the next one. That work item is
  started as any other: with the development on, its branch is checked out in
  its worktree at the commit of the start, `--slug` naming the branch, and
  the start is held to `main`.
- The start of a Feature is refused with exit 2 and nothing written: a
  Feature started already, `F-0001 is started already`; a blocked one,
  `F-0001 is blocked: unblock it first`; a completed one,
  `F-0001 is completed already`; a removed one,
  `F-0001 is removed already`; one with no work item in Backlog,
  `F-0001 has no work item in Backlog to start with`; one whose first work
  item has no Task, `F-0001 cannot start: S-0001 has no Task to start with`;
  with the development on, one whose work item in Backlog has no Task, the
  first in start order named, `F-0001 cannot start: S-0002 has no Task to start with`;
  with the development on and `development.driver` agent, one whose work item
  in Backlog has no complexity, the first in start order named, `F-0001 cannot
  start: S-0002 has no complexity to start with: set it with fgraph amend
  S-0002 --complexity low, medium or high`; with the development on, one whose
  first work item has its branch there already,
  `F-0001 cannot start: the branch wi/S-0002-<slug> is there already -- delete it or give another --slug`;
  and a start `[development] parallel` refuses (below).
- A work item does not start before its Feature: the start of a work item in
  Backlog under a Feature that is not started is refused with exit 2, naming
  the Feature, `S-0001 cannot start: F-0001 is not started, start it first`.
  The alternative, that the start of a child starts its Feature, was shown
  with the plan and not taken.
- The work items of a started Feature start side by side: the start of a
  work item of a started Feature beside another started work item of it
  passes, and `fgraph start` of it is for the one the completion of one
  before left in Backlog (below) as for any other. What refuses it is
  `[development] parallel`, a dependency not completed, a missing Task and a
  title that gives no slug.
- The rule that the Feature is started is asked at the start of a work item
  in Backlog and nowhere else: no Task write asks it, and a completion asks
  it of the next work item it starts alone (below), never of the one it
  completes. So a work item started under a Feature that was never started,
  as in a record whose work items were started one by one before a Feature
  had a state, is worked and completed as before.
- The Feature starts its work items, the reading of S-0053 as written: the
  completion of a work item under a `StartedFeature` -- by `fgraph complete`
  or by `fgraph land` -- starts the next work item of the Feature in the same
  write. The next one is the first of its work items in Backlog in the order
  they start in (Order), the one `fgraph start F-0001` would start, and it
  starts beside the work items of the Feature still started. It is
  started as `fgraph start` of it starts it, by the same rules:
  `[development] parallel`, a Task to start with, and a
  branch named by the slug of its title; no `--slug` names it. The
  alternative, that the developer starts each work item with `fgraph start`,
  was shown with the plan and not taken: by the developer's words of
  2026-11-21 starting a Feature starts its work items one by one. The
  developer's word of 2026-11-23 kept the completion's start; that the
  coordinator starts each work item is a Story of its own, later.
- The completion names the start on a line of its own after its own,
  `completed S-0001 at 677f9b0` then `started S-0002`, and the one commit of
  the record holds the two files, worded `chore: complete S-0001 and start
  S-0002 in the record`. With the development on the branch of the next work
  item is checked out in its worktree at that commit of the record, and named
  on a third line, `branch wi/S-0002-<slug> in <path>`. `fgraph land` says
  `landed S-0001 at 677f9b0`, its run line, `started S-0002` and that line: it commits the
  record, removes the worktree and the branch it landed, and makes the branch
  of the next one last, so a worktree git refuses leaves the landing whole
  and says `S-0002 is started, its branch is not`.
- A next work item that cannot start is left in Backlog, and the completion
  stands: it is never refused or put back for it. It exits 0, its commit is
  that of a completion alone, `chore: complete S-0001 in the record`, and the
  line after it says `not started:` and the refusal of that start. One
  without a Task: `not started: S-0002 has no Task to start with`. One with
  no complexity, `development.driver` agent: `not started: S-0002 has no
  complexity to start with: set it with fgraph amend S-0002 --complexity low,
  medium or high`. One `[development] parallel` refuses: `not started: S-0002 cannot start:
  development.parallel = 1, started already: S-0003`. One whose title
  gives no slug. One under a blocked Feature (below). One added to a started
  Feature with no Task waits: the add does not refuse it.
  `fgraph start S-0002` on `main` starts it once the refusal is gone.
- A completion starts no work item when the Feature holds none in Backlog --
  the last one completes the Feature (below) -- when the work item stands
  alone, and under a Feature never started or completed already. The
  completion of a Task starts none.
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
  its run line, then `completed F-0001 at 677f9b0`.
- Only a completion completes a Feature. A completion that leaves a work item
  of it in Backlog or started leaves the Feature started -- it starts the
  next one in Backlog (above) -- and so does the
  removal of its last work item in Backlog: that Feature stays in InProgress
  with every work item it holds completed, `F-0001  1/1 W  <title>`. A
  removed work item holds nothing back and counts in neither number of the
  progress. `fgraph complete F-0001` is the way to Completed of such a
  Feature (B-0013): it completes a started or blocked Feature once each work
  item of it is completed or removed, now, in the commit of its last completed
  work item, none when none is. It is refused naming the first work item
  neither completed nor removed, for a Feature in Backlog, completed or
  removed, and when given `--commit`. A landing reads the Feature of its work
  item while the merge is held, so a Feature the record does not hold refuses
  it before `main` moves. `fgraph remove F-0001` is the way out of a Feature
  whose criteria were not met, as `fgraph complete F-0001` is of one whose
  were (S-0125).
- The Feature is saved before the work item, and on `main`: the file of a
  Feature is no file of the branch of a work item (below). A work item
  completes on `main` alone, as it starts there (B-0014): `fgraph complete`
  of a work item run on its branch, or on any branch but `main`, is refused
  with exit 2 and nothing written, `S-0002 completes on main, in <checkout>:
  <worktree> is on wi/S-0002-<slug>`, so the next work item its completion
  starts is started on `main`, and a work item is never left completed on its
  branch for its landing to refuse. A Task completes anywhere. `fgraph land`
  runs on `main`, where it saves both.
- A started Feature is blocked and unblocked as a Task is (S-0056), the
  developer's words of 2026-11-21, "a Feature can be blocked": `fgraph block
  F-0001 --reason <why> --waiting-on <what>` takes a `StartedFeature` to a
  `BlockedFeature` and says `blocked F-0001`; `fgraph unblock F-0001` takes
  it back to a `StartedFeature`, with the started time it had, and says
  `unblocked F-0001`. Each is one write of the file of the Feature and one
  commit, `chore: block F-0001 in the record` and `chore: unblock F-0001 in
  the record`, made on `main` alone as every write of a Feature: on the
  branch of a work item it is refused, `F-0001 is not written here: the
  branch wi/S-0001-<slug> writes S-0001 alone`. Only a started Feature is
  blocked, the reading of S-0056: the block of one in Backlog is refused,
  `F-0001 is in Backlog: start it first`; of a blocked one, `F-0001 is
  blocked already`; of a completed one, `F-0001 is completed already`; and a
  blank reason or a blank waiting on, `reason is empty`, `waiting on is
  empty`. The unblock of a Feature that is not blocked is refused, `F-0001
  is not blocked`. No refusal is a new one: each is that of a Task, naming
  the Feature. A text that is the id of no work item, Task or Feature is
  refused by both commands naming every kind (B-0015, S-0138), `'X-0001' is
  no Story, Upkeep, Bug, Spike, Task or Feature id`, and one written `F-` or
  `T-` and a number below 1 as an id of its kind, `a Feature id counts from
  1: 0 is below 1`.
- While a Feature is blocked no further work item of it starts, and its
  started one goes on, the reading of S-0056. `fgraph start` of a work item
  of it in Backlog is refused naming the block, `S-0002 cannot start: F-0001
  is blocked, waiting on <what>: unblock it first`. The completion of its
  started work item, by `fgraph complete` or by `fgraph land`, stands and
  starts no next one: it says `not started:` and that refusal, as for any
  next work item that cannot start (above). The started work item is not
  asked: its Tasks are added, started, blocked and completed as before, in
  its worktree with the development on, and it is completed and landed as
  before. The completion of its last work item completes the Feature,
  blocked or not, `BlockedFeature` to `CompletedFeature` with the started
  time it had: a block holds back a start, never a completion. The
  alternative, that every write under a blocked Feature is refused, the
  Tasks of its started work item among them, was shown with the plan of
  S-0056 and not taken.
- The unblock of a Feature starts its next work item only when none of it is
  started: the first of its work items in Backlog in the order they start
  in, by the same rules as the start the completion of one makes (above). It says
  `unblocked F-0001` then `started S-0002`, the one commit holds the two
  files, worded `chore: unblock F-0001 and start S-0002 in the record`, and
  with the development on the branch of that work item is checked out in
  its worktree at that commit and named on a third line. While a work item
  of the Feature is started or blocked the unblock starts none and says
  `unblocked F-0001` alone. A next work item that cannot start is left in Backlog and
  the unblock stands: the line after it says `not started:` and the refusal
  of that start, and its commit is that of the unblock alone.
- A completed Feature takes no start and no work item added under it: `fgraph
  start F-0001`, and an add with `--parent F-0001`, are refused with exit 2,
  `F-0001 is completed already`. Its completed work items stay within it:
  they are counted in its progress, listed by `fgraph show`, and on no line
  of `fgraph status`.
- A Feature in Backlog, started or blocked is removed with its reason, as a
  work item is (S-0058, S-0125): `fgraph remove F-0001 --reason <why>` takes
  a `Feature`, a `StartedFeature` or a `BlockedFeature` to a
  `RemovedFeature`, with its removed time and its reason and no started time
  and no block, and says `removed F-0001`. Its work items in Backlog are
  removed with it, each for the same reason, decided when S-0058 was ordered: a Feature is to its work items what a work
  item is to its Tasks, and a removed work item keeps its Tasks within it.
  Nothing is deleted: each work item keeps its file, its Tasks and its
  `parent`. The alternative, that its work items are left standing alone, was
  open on the Story and not taken. The Feature and its work items are one
  write and one commit, `chore: remove F-0001 in the record`, the Feature
  saved first, on `main` alone as every write of a Feature: on the branch of
  a work item it is refused, `F-0001 is not written here: the branch
  wi/S-0001-<slug> writes S-0001 alone`, with nothing written. The queue is
  not written: the Feature and its work items leave it as any item that
  leaves the Backlog does (Order).
- A Feature is removed by its own state, once no work item of it is started:
  a completed or a removed one is refused, `F-0001 is completed already`,
  `F-0001 is removed already`; so is a blank reason, `reason is empty`, and
  a Feature the record does not hold. A started or blocked Feature whose
  work item is started is refused naming the first such one, `F-0001 cannot
  be removed: S-0001 is started already`; a completed work item of it stays
  as it is, with its parent, as does one removed before, with the reason it
  had. A Feature never started that holds a started or a completed work
  item, as one whose work items were started before a Feature had a state,
  is refused naming the first such work item, `F-0001 cannot be removed:
  S-0001 is started already`, `F-0001 cannot be removed: S-0001 is completed
  already`. Nothing is written then. No refusal is a new one: each is that
  of a work item, naming the Feature. While a work item of it is started or
  blocked, `fgraph remove F-0001` still refuses, so that work item is removed
  first (S-0148); the remove of a started work item of a started Feature
  starts no other work item and completes no Feature, as the remove of one in
  Backlog does not, and the Feature stays started.
- `fgraph status` lists a removed Feature under Removed as a removed work
  item is listed, its id, its title and its reason, `F-0001  <title>  --
  <reason>`, after the removed work items (Order). The line holds no
  progress, alone among the lines of a Feature: its reason stands in its
  place, as the work items under it are removed, or completed before it was.
  Its work items are on no line of their own, as under a Feature of any
  bucket: those removed with it, a completed one, and one removed before it,
  which had its own line until then. A work item removed under a Feature that is not removed keeps its
  line. `fgraph show` of a removed Feature lists `bucket       Removed` and
  under it `reason       <reason>`, as the show of a removed work item does,
  then its criteria and its work items, each in its own state, `Removed` or
  `Completed`; `fgraph show` of a work item removed with it lists the same
  reason.
- A removed Feature takes no move, no amend and no work item: `fgraph start
  F-0001`, `fgraph amend F-0001`, `fgraph block F-0001` and an add with
  `--parent F-0001` are refused with exit 2, `F-0001 is removed already`; an
  amend that puts a work item under it, `S-0002 cannot be put under F-0001:
  F-0001 is removed already`; its unblock, `F-0001 is not blocked`, as that
  of a Task of a removed work item; and a reorder that names it, `F-0001 is
  not in Backlog`. Its work items are removed, so they take no Task, no
  amend and no move either.
- A Feature never started is completed by nothing: the completion of its last
  work item writes that work item alone, and the Feature keeps the bucket its
  work items derive, Completed, with no commit. So a record whose Features
  were worked before a Feature had a state lists them as it did.
- `[development] parallel` alone limits the work items of a Feature started
  at once, replacing what was decided when S-0052 was ordered, that a Feature
  starts its work items one by one: `parallel` counts every started work item
  of the record, those of a Feature among them, and with it left out nothing
  limits them. The start of a Feature starts one work item, so
  `parallel` refuses it as it refuses that one, naming the Feature: `F-0001
  cannot start: development.parallel = 1, started already: S-0002`. It is
  asked once the Feature is known to start, so a Feature started already, or
  without a work item in Backlog, is refused for that. The next work item a
  completion starts is counted the same, once the completed one no longer
  is: refused, it stays in Backlog and the completion stands (above).
- The bucket of a Feature is read from its state and its work items. A
  `StartedFeature` is in InProgress, a `BlockedFeature` too, a
  `CompletedFeature` in Completed and a `RemovedFeature` in Removed, each by
  its own state. A Feature never started keeps the bucket its work
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
  when the work item is added and names a Feature the record holds; an amend
  gives it again, a Feature or `none`, while the work item and the Features
  it moves between are in Backlog (Amendment).
- A work item under a Feature that names a criterion of it holds `realizes =
  2`, a whole number from 1, right after `parent` and only when it names one;
  a file without the key reads as none. A file holding `0`, or the key with no
  `parent`, is refused naming the file. Every move carries it.
- Nothing more is kept for a criterion met: `fgraph show` of a Feature derives
  it at each read from the rows of the work items under the Feature, as the
  bucket of a Feature never started is. It numbers the criteria as
  `Criteria (2), met 1 of 2`, and a line reads `  1  met      <text>  S-0001`,
  with the ids of the work items that realize it, or `  2  not met  <text>`
  alone when none does. A criterion is met when a work item that realizes it
  is completed; one is enough when several realize it. A removed work item is
  not counted, as the progress of a Feature does not hold it; a completed work
  item verified no still counts, since it stays completed. A work item whose
  number the Feature does not have is on no criterion. `fgraph show` has no
  JSON, and the text and the JSON of `fgraph status` do not change.
- The completion of a Feature does not read its criteria: a Feature is
  completed by its last work item, or by `fgraph complete`, whether or not each
  criterion is met, without a word. This is the smallest reading of the
  Finding kept open on F-0013 (refused, warned or silent); the decision is the
  developer's.
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
  line under Removed while its Feature is not removed itself (above).
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
  Feature is listed with it, in any bucket of the flow:
  `F-0001  1/3 W  <title>`. A removed one alone is listed without it
  (above).
- A Feature takes every operation of a work item, each built: it is added
  and shown, reordered in the queue (Order), started with its first work
  item, its next work item started with the completion of the one before,
  completed with its last work item, blocked and unblocked while it is
  started, marked in the status by a blocked Task of its work item, derived
  and kept in no file (Order), amended in Backlog, given a work item in
  Backlog or left by one (Amendment), and removed from the Backlog with its
  work items (above).
- Each kind reads the files of its own prefix. A file with a prefix no kind
  knows is left alone; nothing reports it yet. An `items/SP-0001.toml` of an
  older record, written while a Spike was `SP-0001`, is such a file: it is
  neither read as a Spike nor renamed, so no command lists it or takes its
  id. So is an `items/ST-0001.toml` of an older record, written while a Story
  was `ST-0001`: it is neither read as a Story nor renamed.
- A command loads a work item whole, changes it and saves it whole. The file
  is validated as it is read; a write is read back before it replaces the
  file.
- A file of a work item, of a Feature or the queue that holds none of them
  -- no TOML, a commit that is no sha, two started Tasks, the criterion of
  another kind -- is refused as every other refusal is (B-0019): exit 2,
  nothing written, one line naming the file and why, `fgraph: error:
  <path> holds no Story: <why>`, `holds no Feature: <why>` or `holds no
  queue: <why>`, never a Python traceback.
- Each time of a file -- created, started, since, completed, removed, noted,
  the `on` of verified, the added of a term -- is read with its offset. A
  file that writes one without, a day alone as `created = 2026-10-11` or a
  time with no offset, is refused when the record is read (B-0026), by every
  command, exit 2 and nothing written, in one line naming the file, the key
  and what is written: `fgraph: error: <path> holds no Story: created =
  2026-10-11 is a time with no offset: write it with one, as 2026-01-01
  09:00:00+00:00`. An `amend` no longer rewrites the day as a time with no
  offset.
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
- A work item whose parent an amend changes keeps its entry in that list,
  since the amend never writes it; the entry is read in the order its new
  parent gives it. Put under a Feature, it is on no line of the Backlog and
  starts where its id stands among the ids of the work items of that
  Feature. Taken out, it is a line of the Backlog where its id stands among
  the ids of the lines. One never placed follows the placed ones as it was
  added, in either order.

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
  worktree takes the Tasks of a started work item; on the trunk too no such
  branch is made.
- With `enabled = true` the start, the scoping and the landing are as this
  section states them below.
- `[development] mode` is where a work item is developed, `branch` or `trunk`
  (S-0096). `branch`, the default, is the development this section states.
  `trunk` is for a repository whose work tree is the live artifact, the words
  of the note being work on main, no worktree: a start is committed on `main`
  and makes no branch and no worktree, the Tasks are started, checked and
  completed in the checkout of `main`, and the work item is completed with
  `fgraph complete S-0001 --commit` at the commit of `main` given.
  `fgraph land` is refused with exit 2 before any git step, `S-0001 cannot
  land: development.mode = trunk makes no branch to land -- complete it with
  fgraph complete S-0001 --commit SHA`, so the gate, the push and the tag of
  the delivery, steps of a landing, are not taken. The model is `Mode` and
  `branched` of `src/flowgraph/record/layers.py`; a word that is neither is
  refused naming the key and the two words.
- The start of a work item is held to `main` with the development on or off,
  and it alone, the reading decided when S-0039 was ordered: no other write of
  a record is held to `main`.
- `[development] parallel` is how many work items are started at once, a
  whole number of 1 or more. It has no default, decided when S-0044 was
  ordered: left out, nothing limits the started work items. It is a key of
  the development, so it limits nothing with the development off, where it is
  held as written. On the trunk it is 1, left out or written 1, and a number
  above 1 is refused naming both keys, with the line `development.parallel is
  2 while development.mode is trunk: the trunk holds one started work item at
  a time`.
- With the development on and `parallel` set, the start of a work item in
  Backlog is refused with exit 2, nothing written and no branch made, when
  that many work items are started already. The refusal names the key,
  `development.parallel`, its number and each started work item. The started
  work items are those of every kind, read as `fgraph status` reads them: a
  started work item is the one its worktree holds. Those under a Feature are
  counted among them, and so are those blocked (S-0138): a blocked work item
  is started still, and the refusal names it among those `started already`.
  A started or blocked work item removed is not counted any more, so the
  start it held back is taken (S-0148).
  The start of a Feature, which starts one work item, is refused the same
  way, naming the Feature (Persistence). `fgraph status` marks as able to
  start now only as many work items as `parallel` leaves places for (Order).
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
  `src/flowgraph/record/layers.py`), and a landing is built from it with its message
  as one of three values -- `MergeCommit` and `Squash`, each with the
  message, and `FastForward`, with none (`src/flowgraph/development/way.py`) -- so a
  fast-forward with a message and a commit without one cannot be built.
- `[development] gate` names one command of the record, a command line run
  at a landing. It is the reading, decided when S-0042 was ordered, of the
  developer's words of 2026-11-21 on starting a work item, "checks if
  criteria are met before closing": one gate of the record, on top of the
  rule that every Task is completed. It is apart from the check of a
  Task, which the complete of that Task runs (S-0089), and the Given / When /
  Then of the work item is neither run nor confirmed. It has no default: left out, a landing runs no gate. It is a
  key of the development, so it gates nothing with the development off,
  where it is held as written.
- `development.driver` names who drives the development, `developer` by default
  or `agent`: the enum `Driver` (`src/flowgraph/record/layers.py`), a value of the
  development and held as written with it off. `fgraph goal` (S-0117) and the
  planned rule (S-0129) read it. With the development on and the driver
  `agent`, the start of a work item in Backlog that holds a Task and no
  complexity is refused with exit 2, nothing written: `S-0002 has no complexity
  to start with: set it with fgraph amend S-0002 --complexity low, medium or
  high`. Which model a complexity maps to stays outside fgraph.
- `[development] branch_max` is an age, a whole number of days of 1 or more
  written with d, as `"1d"` (S-0098). It has no default: left out, nothing is
  said. With the development on, by a branch, `fgraph status` and each frame of
  `fgraph watch` end the line of a work item in InProgress, started or blocked,
  alone or under its Feature, with `-- its branch is older than 1d` once more
  than that many days have passed since its start. The age is read from the
  started time of the record at each listing and kept in no file. It is said and
  never refused -- no start, no Task and no landing is held -- the reading taken
  when S-0098 was ordered, the note of F-0012 naming the key alone; board 1
  warned on the oldest commit of the branch that main lacks, read from git,
  which is not taken. It says nothing with the development off, on the trunk and
  for a work item in any other bucket, and the JSON document of status does not
  list it. A value that is no age is refused with the line
  `development.branch_max is "soon": it takes a whole number of days of 1 or
  more, as 1d`. The model is `MaxDays`, `NoMax` and `BranchMax` of
  `src/flowgraph/record/layers.py`, the marking `aged` of
  `src/flowgraph/development/branch_age.py`.
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
  `Ungated`, `src/flowgraph/record/layers.py`), never an empty text with a meaning.
  Running it is an effect (`src/flowgraph/development/gate.py`): `run()` takes it as a
  callable, `RunGate`, and `main()` binds the adapter `run_gate`, which runs
  the command line through the shell. The default of `run()` runs no gate: a
  run that lands under one is given its runner.
- `[delivery] push` pushes `main` at a landing, twice, `true` or `false`. It is
  `false` by default, as S-0090 states it: a record that names
  none pushes nothing, as a landing did before the key. It is a step of a
  landing, so it pushes nothing with the development off, where it is held as
  written and the landing is refused naming `development.enabled`. In the
  model it is a value of its own layer (`Delivery`,
  `src/flowgraph/record/layers.py`); the push is an effect, one more step of
  the git adapter (`push`, `src/flowgraph/development/git.py`), bound by
  `open_git`, so the core decides when it runs and never calls git itself.
  The same key pushes the tag `fgraph release` makes (below), with the
  development on or off, since a release is no step of a landing.
- `[delivery] tag` tags `main` at a landing, `feature-close`, `close` or
  `none`: the close of a Feature alone, that and a work item that stands alone
  (S-0123), or never. It is `none` by default, as S-0092 states it: a record
  that names none tags nothing, as a landing did before the key; any other word
  is refused naming the three. It is a step of a landing, so it tags nothing
  with the development off, where it is held as written. In the model it is a
  value of the delivery layer (`TagAt`, `src/flowgraph/record/layers.py`);
  the landing decides from it, from whether the work item stands alone and
  from whether its completion completes a Feature (`tags_landing`,
  `src/flowgraph/development/release.py`), a pure function of the three.
- `fgraph complete` of a started Task that holds a check runs it, answering S-0089:
  through the shell, in the worktree of the work item of the Task (the directory
  `fgraph` runs in when the item has none), before anything is written. Its
  output is written as the check wrote it, never captured. A status other than
  0 refuses the complete with exit 2 and one line naming the Task, the command
  and the status, `T-0001 cannot complete: its check "make test" exited with
  status 2`: nothing is written, no commit is made, and the Task stays
  started. A status of 0 completes the Task as before, and so does a Task that
  holds no check. The complete of a work item or of a Feature and `fgraph land`
  run no check of a Task. Running it is an effect
  (`src/flowgraph/development/task_run.py`): `run()` takes the runner as a
  callable, `RunGate`, `run_check`, and `main()` binds `run_gate` to it; the
  decision from its status is the core's (`check_task_passes`,
  `src/flowgraph/development/task_check.py`). The default of `run()` runs no
  check: a run that completes a Task that holds one is given its runner, and
  the default raises, a contract as that of the gate (U-0023), so no run
  passes a check it did not run.
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
  (`src/flowgraph/record/config.py`). Reading it is an effect: `run()` takes it as a
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
- `archive.board` holds the path of the `.board/` of board 1 the record points
  at, a text read as it is; it is `none` when left out, and a blank is refused
  with `archive.board is "": it takes a path`.
- The whole file is read back through the constructor of the configuration
  before it replaces the one in the record (`write_settings`,
  `src/flowgraph/record/config.py`). A key the configuration does not have, a value
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
  `src/flowgraph/record/config.py`): plain data by table, a key left out left out,
  apart from the configuration, which holds a value for every key. A set
  loads the settings whole, sets one key by a function that returns them and
  saves them whole (`src/flowgraph/record/setting.py`), where each key is listed
  once with what it takes and the value a configuration holds under it.

Who writes what with the development on, so that two branches never change
the same file or hand out the same number. With it off no work item has a
branch: every write is made in the checkout, the start of a work item alone
held to `main`, and there is no landing:

| Write | Where |
|---|---|
| add a work item | `main` |
| add a Feature | `main` |
| add a Task to a work item in Backlog | `main` |
| amend a Task of a work item in Backlog | `main` |
| reorder the Backlog | `main` |
| amend a work item in Backlog | `main` |
| amend a Feature in Backlog | `main` |
| remove a work item in Backlog | `main` |
| remove a started or blocked work item | `main`: read from its worktree, its branch and worktree removed or left (S-0148) |
| remove a Feature in Backlog, with its work items | `main` |
| remove a started or blocked Feature, with its work items in Backlog | `main` |
| block and unblock a started Feature | `main`: an unblock that starts the next work item commits both and makes the branch of that one |
| set or unset a key of the configuration | `main` |
| start a work item | `main`: `fgraph` commits it and makes its branch |
| start a Feature | `main`: `fgraph` commits it with its first work item and makes the branch of that one |
| add a Task to a started work item | its branch |
| amend a Task in Backlog of a started work item | its branch |
| start, block, unblock, complete and remove its Tasks | its branch |
| hand a started work item to an agent | its branch: `fgraph hand` in its worktree, or from `main` with `--dir` on the record of that worktree |
| block and unblock a started work item | its branch: `fgraph block` and `fgraph unblock` in its worktree, or from `main` with `--dir` on the record of that worktree |
| note a progress line on a started work item or on a Task of it | its branch: in its worktree, or from `main` with `--dir` on the record of that worktree |
| land the work item | `main`: `fgraph land` merges its branch and completes it |
| complete the work item | `main`, after a merge made by hand |
| complete a Feature | `main`: with its last work item, by its landing or its complete, or by `fgraph complete F-0001` once each work item of it is completed or removed |
| start the next work item of a Feature | `main`: with the completion of the one before, by its landing or its complete; `fgraph` commits both and makes the branch of the next one |

The remove of a Task is one commit of the branch of its work item, written in
its worktree; on `main` it is refused, `S-0001 is started: its Tasks are
written in its worktree, <path>` (S-0147). A Task added in the worktree after
the start is not in the copy of `main`, so its remove there is answered `no
Task T-0002 in the record`, as B-0032 records for block and unblock.

The branch a work item owns may change and append within its scope, through
`fgraph`: the developer's rule of 2026-11-21. `fgraph` holds the side of the
branch:

- The branch of a work item is the one named `wi/<id>-<slug>`. In a work tree
  on it `fgraph` writes the file of that work item alone.
- Refused there with exit 2, nothing written: a Task added to another work
  item, a Task of another work item started or completed, a work item added,
  a reorder of the Backlog, whose queue is no file of the work item, and a
  set of the configuration, whose `config.toml` is none either. The refusal
  names the work item the branch owns.
- The work item itself is never completed there: a work item completes on
  `main` alone (B-0014, above), so its completion run on its branch is
  refused as on any branch but `main`, and the next work item of its Feature
  is started on `main` by that completion or by its landing.
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
  nothing written, and the refusal names that worktree. The block and the
  unblock of a Task are refused there too (B-0032), by a check that runs
  before the copy of that work tree is read, so the answer is the worktree
  and not what a stale copy says of the Task (before B-0032 the copy of
  `main` answered `T-0001 is in Backlog: start it first`, `T-0001 is not
  blocked` or `no Task T-0002 in the record`). It holds for a Task in any
  state and for one added in the worktree after the start, with the line
  `S-0001 is started: its Tasks are written in its worktree, <path>`.
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
  work tree on the branch of a work item, status and watch list the record
  of main, its queue, its Features, its configuration and every row, each
  started work item read from its own worktree as on main, so every work
  tree lists the same frame, the marks and the JSON too: the developer's
  decision of 2026-11-23, S-0141, amending the rule of S-0035. With no work
  tree on main, outside a git work tree and for a record git ignores they
  read the record of that work tree; fgraph show, every other read and every
  write stay with the record of that work tree. Every read of the rows goes
  this way, so the bucket of a Feature does too.
- `fgraph show` of a started work item on `main` reads it there too, as
  status does: the work item it shows, with the bucket and the commit of each
  Task, is the one the worktree of its branch `wi/<id>-*` holds, the same
  file read the same way. A work item that is not started, a started one
  without such a worktree, a record outside a git work tree and a record git
  ignores are shown from the record itself. Run in a work tree on the branch
  of a work item, show reads the record of that work tree and no other. The
  show of a Feature lists its work items from the rows, so it reads them
  there as status does.
- The block and the unblock of a started work item are written where its
  Tasks are (S-0138), as `fgraph hand` is: in its worktree, or from `main`
  with `--dir` on the record of that worktree, one commit of its branch. Run
  on `main` the block is refused naming the worktree, `S-0001 is started:
  its Tasks are written in its worktree, <path>`, nothing written. `main`
  keeps the file as started, and status and show on `main` read the row from
  the worktree, so they list it blocked. The unblock run on `main` answers
  from the copy of `main`: that copy holds it started, and the unblock is
  refused, `S-0001 is not blocked`. The unblock of a Task names the worktree
  since B-0032, as its block does. A worktree
  on code older than S-0138 refuses a file that holds `state = "blocked"`.

The git steps `fgraph` takes, decided by the developer on 2026-11-21:

- `fgraph` commits every write of the record, when the record is inside a git
  work tree and its configuration leaves `[git] commit` on: `add`, `amend`,
  `remove`, `reorder`, `start`, `hand`, `block`, `unblock`, `complete` and
  `config set`. The commit holds the files of the record the write changed, alone;
  whatever else is staged or changed stays as it was and out of the commit.
- The commit is worded by `fgraph`, `chore: <write> <id> in the record`, a
  set of the configuration under its key:

  | Write | Message |
  |---|---|
  | add a work item | `chore: add S-0001 in the record` |
  | add a Feature | `chore: add F-0001 in the record` |
  | add a Task | `chore: add T-0001 of S-0001 in the record` |
  | amend | `chore: amend S-0001 in the record`, `chore: amend F-0001 in the record` for a Feature, `chore: amend T-0001 of S-0001 in the record` for a Task |
  | reorder | `chore: reorder S-0002 before S-0001 in the record`, `chore: reorder F-0001 before S-0001 in the record` |
  | start | `chore: start S-0001 in the record`, `chore: start T-0001 of S-0001 in the record`, `chore: start F-0001 in the record` for a Feature and its first work item |
  | hand | `chore: hand S-0001 to opus-b2 in the record` |
  | block | `chore: block S-0001 in the record` for a work item, `chore: block T-0001 of S-0001 in the record`, `chore: block F-0001 in the record` for a Feature |
  | unblock | `chore: unblock S-0001 in the record` for a work item, `chore: unblock T-0001 of S-0001 in the record`, `chore: unblock F-0001 in the record` for a Feature, `chore: unblock F-0001 and start S-0002 in the record` for a Feature and the next work item its unblock starts |
  | remove | `chore: remove S-0001 in the record`, `chore: remove T-0001 of S-0001 in the record` for a Task, `chore: remove F-0001 in the record` for a Feature and its work items |
  | complete | `chore: complete S-0001 in the record`, `chore: complete T-0001 of S-0001 in the record`, `chore: complete S-0002 and F-0001 in the record` for a work item and the Feature it completes, `chore: complete S-0001 and start S-0002 in the record` for a work item and the next one of its Feature, `chore: complete F-0001 in the record` for a Feature left with every work item completed or removed |
  | set a key of the configuration | `chore: set development.enabled in the record` |
  | unset a key of the configuration | `chore: unset development.gate in the record` |

- A write that leaves its file as it was makes no commit. With the
  development on, completing a Task names the commit of its work, so the
  commit of the record follows it.
- With the development on and the mode `branch`, a start of a work item then
  checks out the branch `wi/<id>-<slug>` at its commit in a new worktree,
  `<parent>/<checkout name>.worktrees/<id>-<slug>`. The slug is given with
  `--slug`, else it is the first four words of the title, lower-cased and kept
  to their letters and digits. With the development off, and on the trunk, the
  start ends at its commit. A start whose branch `wi/<id>-<slug>` is there already is refused
  with exit 2 before anything is written, so the work item stays in Backlog,
  `S-0001 cannot start: the branch wi/S-0001-<slug> is there already -- delete it or give another --slug`;
  it holds for a Feature by the branch of its first work item. The developer deletes the branch or gives another `--slug`: the
  start takes over no branch that is there, the developer's decision of
  2026-11-23 (B-0027).
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
  file the write changed back as it was, a worktree refused for another cause
  than a branch there leaves the start committed.
- `fgraph sync` (S-0150) takes the place of `board sync-main` of board 1. Run
  in the worktree of a started work item, with the development on, it merges
  `main` into its branch. `main` is `refs/heads/main` as the repository holds
  it: nothing is fetched. The merge is `git merge --no-ff`, so one merge commit,
  `chore: merge main into <branch>`, even where a fast-forward would do; a
  branch that holds `main` already says so and makes none. A conflict is
  aborted with `git merge --abort` after its files are read, and since a
  changed tracked file is refused first, the abort leaves the work tree as it
  was: `main does not merge into <branch>: conflict in <files>`. The record
  merges as any file: `main` alone writes the queue, the Features, the terms,
  the configuration and the other work items, and the branch alone writes the
  file of its work item (the scope of a branch), so no file of `.fgraph/` is
  changed on both sides unless one was edited by hand or the work item was
  completed on `main` by hand while its branch lived -- then it is a conflict
  as any other, named and aborted, and fgraph derives nothing. The steps are in
  `src/flowgraph/development/sync_git.py`, called by name and not bound by
  `open_git`; the work item is the one the branch names, its state is not read;
  in a record git ignores the worktree holds no `.fgraph/`, so the command
  finds no record there and the merge is git's.
- With the development on, `fgraph land` lands a started work item, run in
  the checkout of `main`. It merges the branch `wi/<id>-*` into `main` as a
  merge of its own, held uncommitted; commits it under the message the
  developer gives with `--message`; completes the work item at the short sha
  of that commit, with the commit of the record, `chore: complete <id> in the
  record`; then removes the worktree of the branch and the branch. It says
  `landed <id> at <sha>`, then `run: <when> -> <then>` for a Story or an Upkeep,
  `run: <expected>` for a Bug and nothing for a Spike, worded by `run_line` of
  `src/flowgraph/criterion/run.py` and printed before every other line of the
  landing; it takes the place of the `run:` line of `board land` of board 1
  (S-0151). These are the steps of a landing by `merge-commit`. The landing of the last work item
  of a started Feature completes the Feature in that commit of the record,
  by any way of merging (above). The landing of any other starts the next
  work item of the Feature in that commit, and checks its branch out at it,
  in its worktree, once the worktree and the branch landed are removed
  (above).
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
- With `[delivery] push = true` `main` is pushed right after the merge,
  before anything of the record is written, and again as the last step of
  every way, with the tag between them (below), once the landing is
  whole: after the commit of the record that
  completes the work item, the removal of the worktree and the branch landed,
  and the branch of the next work item of a Feature. `main` is pushed to the
  branch it tracks on its remote, and the landing says `pushed main to
  <remote>` once, on a line of its own. A step refused before a push takes
  no push. The branch `main` tracks is read before the merge, through the step
  `upstream` of the landing, so a `main` that tracks none merges nothing.
- A first push git refuses -- a remote it cannot reach -- leaves the work item
  started and merged, its
  branch and its worktree as they were, no next work item started and no tag
  made; nothing is undone, since history only moves forward. The landing
  exits 2 naming the git command and its error, then `-- main is not pushed
  -- <id> is merged at <sha> and not completed -- run fgraph land <id>
  again`. The last push refused, once the work item is completed, leaves the
  landing as it is, the reading of the agent for S-0090: `main` merged, the
  work item completed and committed, the worktree and the branch removed, the
  next work item started with its branch. It exits 2 naming the git command
  and its error, then `-- <id> is landed at <sha>, main is not pushed`; the
  push is left to the developer.
- A landing is taken up when the branch of the work item brings no change to
  `main`, merged by hand or by a landing that stopped after its merge, by
  each way of merging: merge-commit, squash and fast-forward. It makes no
  merge and no commit, checks that the work item completes, runs the gate
  again on the tree `main` has, and completes the work item at the commit
  `main` is on, then pushes and removes as a landing does. A fast-forward
  taken up after `main` moved on is refused as a fast-forward is, `main`
  holding a commit the branch lacks.
- With `[delivery] tag = "feature-close"` the landing that will complete a
  Feature -- the one of its last work item -- tags `main`, and with
  `tag = "close"` so does the landing of a work item that stands alone
  (S-0123). The tag is on the commit of the landing, made after the first
  push of `main` and before the write that completes the work item
  (`release_landing`, `src/flowgraph/development/release.py`), so the record
  at the tag lists the work item InProgress, the cost of completing after the
  tag. The version counts the kind of the work item landed, which the record
  does not list completed yet, with the kinds completed since the last `v*`
  tag: the next minor for a Story or a Bug, else the next patch. A landing
  taken up whose commit the last `v*` tag is on makes no second tag and
  pushes that one. The landing says `tagged <version> at <sha>` and, under
  `[delivery] push = true`, `pushed <version> to <remote>`. A work item under
  a Feature that is not its last tags nothing. A tag made by a landing bumps
  no version in a file of the project, `pyproject.toml` among them. A tag git
  refuses, or its push, leaves the work item started and merged, as a first
  push does, and exits 2 naming the git command, then `-- main is not tagged
  <version>` or `-- <version> is tagged at <sha>, it is not pushed`, then `--
  <id> is merged at <sha> and not completed -- run fgraph land <id> again`; a
  push of `main` git refuses makes no tag. With the development off a Feature
  closed by `fgraph complete` of its last work item is not tagged, inside a
  git work tree or outside one: the tag is a step of a landing, and `fgraph
  release` is the developer's.
- A squash is not made by `git merge --squash`: that takes a change staged
  in the checkout into the commit and drops it with the squash. The merge of
  its own refuses such a checkout, and committed with one parent it holds
  the same work.
- A landing is refused, with nothing merged, when the development is off, on
  the trunk (`development.mode = trunk makes no branch to land`),
  when `--message` is missing for a commit or given to a `fast-forward`,
  when the record is outside a git work tree, when the work tree it runs in
  is not on `main`, when `[delivery] push` is `true` and `main` tracks no
  branch of a remote (B-0023), with the line `<id> cannot land: main tracks no
  branch of a remote to push to -- run git push --set-upstream <remote> main,
  or fgraph config set delivery.push false`, checked before the branch of the
  work item is looked for (`check_main_tracked`,
  `src/flowgraph/development/delivery.py`), when no branch `wi/<id>-*` or more
  than one is there,
  when a `fast-forward` finds a commit on `main` that the branch lacks, when
  git refuses the merge, and -- the merge held dropped again -- when a Task
  of the work item is not completed, when the gate of the record exits with
  another status than 0, or git refuses the commit or the fast-forward. A
  step git refuses after `main` moved exits 2 saying how far the landing
  came.
- `fgraph release` tags the trunk, the reading of the agent for S-0091 of
  the release rule the developer works by. Run in the checkout of `main`, it
  makes an annotated tag on the head of `main`, under the message `release
  <version>`, and says `tagged <version> at <sha>`. A version is
  `v<major>.<minor>.<patch>`, each a whole number with no leading zero, built
  by its smart constructor `make_version`
  (`src/flowgraph/development/version.py`); the last tag is the highest
  version among the `v*` tags, a tag that writes none passed over.
- The version is computed, a pure function of the last tag and the kinds of
  the work items completed since it: the next minor, the patch back to 0,
  when a Story or a Bug is among them -- a new behavior or a fixed one --
  else the next patch for an Upkeep or a Spike alone; `v0.1.0` when no tag
  writes a version, every completed work item counted then. `--version`
  names the version in place of the computed one, a major among them.
- A work item is completed since the last tag unless that tag holds it. A
  work item that names a commit -- the merge of its landing, or the commit
  given to `fgraph complete` -- is held when the commit of the tag is that
  commit or comes after it (`git merge-base --is-ancestor`), so one landed
  just before the tag is held whatever the clocks say. One that names no
  commit, as one completed with the development off, or a commit git does
  not know, is held when its completed time is at or before the time the tag
  was made. A Feature is no work item and counts for nothing.
- A tag is never moved or deleted. A release is refused, exiting 2 with no
  tag made, when the record is outside a git work tree, when the work tree it
  runs in is not on `main`, named as a start names it, when `--version` is
  no version or names a tag that exists, when nothing is completed since
  the last tag, or nothing at all without one, and while a work item completed
  since the last tag holds no answer of `fgraph verify`: the line is
  `S-0001, U-0001 not verified since v0.1.0: no release -- run fgraph verify
  on each first`, without `since <tag>` when there is no tag, and every such
  work item is named on it, Story then Upkeep then Bug, each by number. The
  kinds asked are those `fgraph verify` takes, a Story, a Bug and an Upkeep,
  so a Spike is not asked; a yes and a no both count as an answer. It is read
  from the row of each work item completed since the last tag
  (`WorkItemRow.verified`), every completed one when there is no tag, and a
  `--version` asked for does not pass it. It is an `UnverifiedError`, a
  `ReleaseError`, and `release_landing` is not asked: the tag of a landing
  asks for no answer (S-0149). Git refuses an existing tag too, so no step of
  `fgraph` moves one.
- With `[delivery] push = true` the tag is pushed to the remote `main`
  tracks, once it is made, and the release says `pushed <version> to
  <remote>`. A push git refuses leaves the tag made and exits 2 naming the
  git command, then `-- <version> is tagged at <sha>, it is not pushed`. The
  tags are read, made and pushed by steps of the git adapter
  (`src/flowgraph/development/tag_git.py`), bound by `open_git`.
- A version a project keeps in a file of its own, as `pyproject.toml`, is not
  bumped by `fgraph release`: left open by S-0091.
- `fgraph` makes the commits of the record; the commits of the development
  and their messages stay the developer's, the merge commit and the squash
  commit of a landing among them: `fgraph` makes it, the developer words it.
  Whether the work tree is on `main` is checked by a landing, by the start
  of a work item and by a release.

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

### Archive

The developer decided on 2026-11-23, on S-0120, after Q-0001 answered no: a
repository that adopts fgraph keeps its `.board/` whole as an archive. It
starts a record beside it with `fgraph init`, points at it with `fgraph config
set archive.board .board`, and files the open work by hand with `fgraph add`.
fgraph converts no item, and the closed ones stay where they are.

The pointer is `[archive] board` of `config.toml`, a path as written, taken
from the directory that holds the record. It has no default and `fgraph init`
writes none. With it set, `fgraph show` of the letter E, W or T in either
case, a dash and a number of 1 or more exits 2 with one line, the id as board
1 writes it, at least three digits. For W-123 in a project under
`/src/project`:

```text
fgraph: error: W-123 is in the archive of board 1 at /src/project/.board -- show it with: uv run ~/.claude/skills/board/scripts/board.py --root /src/project show W-123
```

fgraph reads the shape of the text alone: it opens no file of the archive,
does not ask whether the path is there, and writes there never -- its commits
name the files of the record alone. A T id is read as `T-0456` by the rule of
Ids and named back as `T-456`, and `fgraph show` takes no Task, so under a
pointer a T id asked of `show` is named as the old one even when the record
holds a Task of that number. `w123` and `e7`, with no dash, stay names of
terms. With no pointer every such text is refused as before, and `show` alone
answers: every other command refuses an old id as it did.

### Records measured

The seven board 1 records, read on 2026-11-23 by the board script alone:
`board.py --root <repo> status` for the Epics, the Tasks and the landing
line, and `board.py --root <repo> show W-nnn --detail brief` on every work
item for its kind, its state and its parent. A cell is the count by state,
todo/doing/blocked/done/pruned, then the total in brackets.

| Repository | Epics | Tasks |
|---|---|---|
| `~/.claude` | 0/0/0/48/0 (48) | 2/0/0/1294/68 (1364) |
| `advent-of-code-2025` | 0/0/0/0/0 (0) | 0/0/0/0/0 (0) |
| `chaos-to-simple` | 0/0/0/20/0 (20) | 0/0/0/512/8 (520) |
| `gflow` | 0/0/0/1/0 (1) | 0/0/0/12/0 (12) |
| `stats` | 0/0/0/3/0 (3) | 2/0/0/85/1 (88) |
| `surrogate-models` | 1/1/0/16/2 (20) | 30/0/1/410/77 (518) |
| `svrf-parser` | 0/0/0/16/0 (16) | 0/0/0/381/32 (413) |
| all seven | 1/1/0/104/2 (108) | 34/0/1/2694/186 (2915) |

The work items by kind:

| Repository | issue | spike | bug |
|---|---|---|---|
| `~/.claude` | 0/0/0/365/13 (378) | 0/0/0/22/2 (24) | 2/0/0/255/8 (265) |
| `advent-of-code-2025` | 0/0/0/0/0 (0) | 0/0/0/0/0 (0) | 0/0/0/0/0 (0) |
| `chaos-to-simple` | 0/0/0/156/0 (156) | 0/0/0/4/0 (4) | 0/0/0/75/1 (76) |
| `gflow` | 0/0/0/3/0 (3) | 0/0/0/0/0 (0) | 0/0/0/0/0 (0) |
| `stats` | 1/0/0/25/0 (26) | 0/0/0/0/0 (0) | 1/0/0/11/1 (13) |
| `surrogate-models` | 13/1/0/118/17 (149) | 2/0/0/6/5 (13) | 6/0/0/36/1 (43) |
| `svrf-parser` | 0/0/0/108/2 (110) | 0/0/0/10/10 (20) | 0/0/0/54/1 (55) |
| all seven | 14/1/0/775/32 (822) | 2/0/0/42/17 (61) | 9/0/0/431/12 (452) |

The work items by parent: a standalone root, under an Epic, or nested under
another work item. A work item whose brief prints an item it `continues` is
counted apart; `continues` is printed on the successor of a pruned item, the
other side of `pruned.successor`, stored by neither (Field map).

| Repository | Work items | Standalone | Under an Epic | Nested | Continues |
|---|---|---|---|---|---|
| `~/.claude` | 667 | 403 | 264 | 0 | 11 |
| `advent-of-code-2025` | 0 | 0 | 0 | 0 | 0 |
| `chaos-to-simple` | 236 | 43 | 193 | 0 | 1 |
| `gflow` | 3 | 0 | 3 | 0 | 0 |
| `stats` | 39 | 12 | 27 | 0 | 0 |
| `surrogate-models` | 205 | 50 | 155 | 0 | 5 |
| `svrf-parser` | 185 | 66 | 119 | 0 | 6 |
| all seven | 1335 | 574 | 761 | 0 | 23 |

Every sum by kind and by state equals the total `status` prints for its
record, and the Tasks the briefs list, each counted once, equal the Task row
of `status`. No work item of the seven has another work item as parent.

The `landing:` line of each record, as `status` prints it:

- `~/.claude`: `ff-main, approver agent, branch ids local, tag root-close,
  ci none, worktree ../.claude.worktrees, branch max 1d, gate make -C
  skills/board/scripts check, lanes 3`
- `advent-of-code-2025`: `ff-main, approver developer, branch ids local, tag
  epic-close, ci none, worktree ../advent-of-code-2025.worktrees, branch max
  1d, lanes 1`
- `chaos-to-simple`: `main, approver agent, branch ids local, tag
  epic-close, ci none, on main, no branches, gate make check, lanes 1`
- `gflow`: `pr, approver developer, branch ids local, tag epic-close, ci
  pipeline, worktree ../gflow.worktrees, branch max 1d, lanes 1`
- `stats`: `ff-main, approver developer, branch ids local, tag none, ci none,
  worktree ../stats.worktrees, branch max 1d, lanes 1`
- `surrogate-models`: `ff-main, approver agent, branch ids local, tag
  epic-close, ci none, worktree ../surrogate-models-wt, branch max 1d, lanes
  1`
- `svrf-parser`: `pr, approver agent, branch ids remote, tag epic-close, ci
  pipeline, worktree ../svrf-parser.worktrees, branch max 1d, lanes 3`

### Field map

The fields of a board 1 item, read on 2026-11-23 by the board script alone:
`show <id> --detail full` on, in `surrogate-models`, the Epics E-007
(pruned), E-018 (done), E-019 (doing) and E-020 (todo), the issues W-045
(pruned), W-187 (done) and W-197 (doing), the spikes W-044 (pruned), W-061
(todo) and W-195 (done), the bugs W-181 (todo), W-185 and W-188 (done), the
Tasks T-118 (todo), T-476 (done), T-492 (pruned) and T-493 (blocked); in
`~/.claude` W-141, W-143, W-145, W-153, W-664 and T-311; in `svrf-parser`
W-008; beside `sections`, `status`, `tree E-019`, `knowledge --search` and
`config show`. `--detail full` prints no `reasoning`, `created`,
`filed_during`, `amends`, `remote` or `pre_empted_by`, so `--detail raw` was
read too: on E-002, W-185, W-187, T-492 and T-493 of `surrogate-models`, on
W-143, W-153, W-157, W-159, W-161 and W-664 of `~/.claude`, and on W-008 and
W-125 of `svrf-parser`. Raw prints the file of the checkout: for T-492 and
T-493, worked on the branch of W-197, it still reads `doing` and `todo`
where `full` reads pruned and blocked. No bug is doing and no work item is
blocked in any record today; W-008 of `svrf-parser` was blocked once, by its
History. An id alone below is of `surrogate-models`, `(c)` marks
`~/.claude` and `(s)` `svrf-parser`. The fgraph side is this file, the help
of `fgraph` and the state types of `src/flowgraph` on this branch. A field
fgraph could hold only as free text in a description is `lost`: a
description carries no meaning the planning skill reads. An item of the
Backlog that aims at a gap is named in its row; the field is lost today.

Every item:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| id `E-nnn`, `W-nnn`, `T-nnn` | every item | a new id by kind, `F-`, `S-`, `U-`, `B-`, `Q-`, `T-` and four digits (Ids); the old id stays in the archive, named by `fgraph show` (S-0120, Archive) | converted: a new id; the old one lost |
| title | every item | the title | kept |
| `created`, a day | raw W-187, T-492 | `created`, a time | converted: the day becomes a time |
| the external token, `W-008 (AB#3128)`, and `remote:` -- `token`, `synced`, `pushed`, `text`, `parent` | raw W-008 (s), W-125 (s) | none; no item of the Backlog names it | lost |

An Epic:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| `parent: root` | E-019 | a Feature is the top level (Levels) | kept |
| `## Hypothesis` | E-019 | none: a Feature holds a title, a description and its criteria (Attributes) | lost |
| `## Outcome` | E-019 | none | lost |
| a criterion `ACn Given ... When ... Then ...` | E-019 AC1 to AC8, E-007 AC2, AC3 | `--criterion`, free text (Acceptance criteria) | converted: its text a criterion; its label `ACn` dropped |
| the work item a criterion names, `-> W-189` | E-019 | none (F-0013, S-0100) | lost |
| a criterion nested under another, `ACn.k` | on no item read; E-035 (c) AC3 states the form | none: the criteria are a flat list | lost |
| `relations.depends_on` | E-007 on E-006 | none: `--depends-on` is refused on a Feature (Depends on) | lost |
| `relations.pre_empted_by`, set by a park | raw E-002, empty; its park in E-002#v4 | none: no park | lost |
| its ledger, `ledgers/E-nnn.md` | E-018 evidence | none | lost |

A work item, of every kind:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| `kind: spike`, `kind: bug` | W-195, W-188 | `Spike`, `Bug` (From board 1) | kept |
| `kind: issue` with `issue.then: behavior` | raw W-187 | `Story` | converted: the kind from `then` |
| `kind: issue` with `issue.then: step` | raw W-664 (c) | `Upkeep` | converted: the kind from `then` |
| `kind: issue` with no `then` | raw W-153 (c) | unknown | unknown: settled by a rule for its kind, the developer's |
| `parent`, an Epic or empty | W-187, raw W-153 (c) | `parent`, a Feature or standing alone | kept |
| `reasoning` | raw W-187 `deductive`, W-125 (s) `abductive` | none | lost |
| `## Hypothesis` of an issue or a bug | W-187, W-188 | none: a Story, an Upkeep and a Bug take none | lost |
| `tasks` | W-197 | the Tasks in the file of the work item | kept |
| no `tasks` line | W-044, W-045, both pruned | a work item holds a tuple of Tasks (`src/flowgraph/work_item/model.py`) | unknown: whether the record reads one with none; the Probe settles it |
| the branch of a doing one, `wi/W-197-no-review-mark-is` | `status` | the branch `fgraph start` cuts (`--slug`) | unknown: whether fgraph takes a branch it did not cut; S-0107 settles it |

An issue, a spike and a bug, by kind:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| issue `## Outcome`, one Given / When / Then sentence | W-187 | `--given`, `--when`, `--then` | converted: the sentence split at its three words |
| `issue.description` | W-187 | the description | kept |
| spike `## Hypothesis`, a yes/no question | W-195, W-061 | `--hypothesis` | kept |
| `spike.research_question`, printed `question` | W-195, raw W-125 (s) | none | lost |
| `spike.hypothesis`, printed `conjecture` | W-195, raw W-125 (s) | none | lost |
| spike `## Outcome`, the Given / When / Then of its decision | W-195 | none | lost |
| `spike.decision` | W-195 | the decision of a `CompletedSpike`, `complete --decision`; no answer, which a Spike completed before the answer was taken lacks (States are types) | kept |
| `bug.actual` | W-188 | `--observed` | kept |
| `bug.expected` | W-188 | `--expected` | kept |
| bug `## Outcome`, a Given / When / Then | W-185, where it differs from `expected` | none | lost |
| `bug.input` | W-188 | none | lost |
| `bug.steps` | W-188 | none | lost |
| `bug.technical` | W-188 | none | lost |

A Task:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| title `<Verb> <object> -> <output>` | T-476 | the title, an output title (Titles) | kept |
| `parent`, a work item | T-476 | the work item whose file holds it | kept |
| `## Action` | T-476 | `--description`, the one free text of a Task | converted: the brief becomes the description |
| `## Output` | T-476 | `--output`, the expected output | kept |
| `## Check`, the command before ` -- ` or ` -> ` | T-476, T-492 | `--check`, run by `complete` | converted: the command alone |
| `## Check`, the expected result, `prints 2` | T-492, T-476 `prints "1 passed"` | none: `complete` judges the exit status alone (Persistence, S-0089) | lost |
| `relations.depends_on` | raw T-492, T-493, empty on both | none: a Task takes none | lost |
| a Finding of a Task, `T-023: fact:` on its work item | W-008 (s) | a knowledge line of the work item (Attributes) | kept |

The payload of each state:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| `todo`, no payload | T-118, E-020, W-061 | the bare type, in Backlog | kept |
| `doing`, no payload | W-197, E-019 | `started`, a time | converted: the day of the `doing` History line |
| `blocked` of a Task: `reason`, `since`, `waiting_on` | T-493 | a `BlockedTask`: `reason`, `since`, `waiting_on` (`fgraph block`) | kept; `since` a day read as a time |
| `blocked` of a work item | on none today; W-008 (s) History | a `BlockedWorkItem`: `reason`, `since`, `waiting_on` (`fgraph block`, S-0138) | kept |
| `blocked` of an Epic | on none | a `BlockedFeature` | kept |
| `done.on` | W-187, T-476, E-018 | `completed`, a time | converted: the day becomes a time |
| `done.evidence` of a work item | W-187 `merged into main at f184dc1`, W-008 (s) `PR 339; merged d4cba3e; build 1806 succeeded; ...` | `commit`, a sha of 7 to 40 hex digits (Evidence) | converted: the sha; the rest of the text lost |
| `done.evidence` of a Task | T-476 `65312dd; make test ...: [DONE] tests passed` | `commit` | converted: the sha; what the check printed lost |
| `done.evidence` of an Epic | E-018, a ledger, the ACs, a tag | the commit of its last work item (Evidence) | converted: that commit; the text lost |
| `pruned.on`, `pruned.reason` of a work item in todo | W-044, W-045 | `removed`, `reason` (`fgraph remove`) | kept |
| `pruned` of a work item from doing | W-143 (c), its History `doing` then `pruned` | a `RemovedWorkItem` reached from InProgress, `fgraph remove` on main (S-0148, Persistence) | kept |
| `pruned` of a Task | T-492, T-311 (c) | a `RemovedTask`: `removed` and `reason`, kept inside a started or completed work item (S-0147, `src/flowgraph/task/model.py`); its successor still lost (below) | kept |
| the done Tasks of a pruned work item | W-143 (c), T-314 and T-315 | a `RemovedWorkItem` holding its completed Tasks with their commits (S-0148) | kept |
| `pruned.on`, `pruned.reason` of an Epic | E-007 | a `RemovedFeature`: removed on, reason | kept |

The relations:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| `depends_on`, work item to work item | W-061 on W-059, W-129, W-164 | `depends_on` (Depends on) | kept |
| `depends_on` naming a pruned work item | W-045 on W-044 | refused at the write, `it is removed` (Depends on) | unknown: whether a conversion may write it; the Probe settles it |
| `filed_during`, a work item | raw W-185 on W-173 | `filed_during` (Filed during) | kept |
| `filed_during`, a Task | raw W-187 on T-456 | none: it names a work item alone | converted: the work item of the Task, W-174 |
| `amends`, a work item | raw W-185 on W-173 | `amends`, a completed work item (Amends) | kept |
| `amends`, a criterion of an Epic, `E-011/AC3` | raw W-161 (c), W-157 (c), W-159 (c) | none | lost |
| `pruned.successor`, work item to work item | W-143 (c) to W-145, W-141 (c) to W-153 | `superseded_by` (Superseded by), from Backlog alone | kept |
| `pruned.successor` of a Task, to a Task or a work item | T-492 to T-518, T-311 (c) to W-153 | none: only a removed work item names one | lost |
| `continues`, printed on the successor | W-145 (c) on W-143, W-144; W-153 (c) on T-311, T-312, W-141 | `supersedes`, derived (Superseded by) | kept: derived from `successor`, stored by neither |

The knowledge lines:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| a Finding, `<day> <text>` | E-018, W-187 | `fgraph note --finding`, its text and the time noted | converted: the day becomes a time |
| the type of a Finding, `fact`, `open`, `standing` | E-018 | `--standing` or `--open` on `fgraph note`, on a line of any kind; a `fact` is a line with no mark (Attributes) | converted: a `fact` becomes no mark |
| `supersedes: <ref>` ending a Finding or a Decision | E-018, W-187, W-195 | none (F-0014, S-0103) | lost |
| the ref of a line, `<item>#<k>`, `#d<k>`, `#v<k>` | `knowledge --search` (c), W-143#d3 in W-143 (c) | none: a line holds no ref | lost |
| `about: <term>` ending a line, of `[knowledge] terms` | on no item read; ledger E-044 (c); `config show knowledge` (c) | `--about TERM`, of a term the record holds (Terms) | converted: each word a term added first |
| a Decision, `<day>: <text>` | E-019, W-195 | `--decision` | converted: the day becomes a time |
| the burn Decision, `burn: ... (stop after 8 hours)` | E-019, W-664 (c) | a decision line; no command reads its stop | converted: the text alone |
| a Deviation, `<day>: <text>`, on a root | E-018, E-019, W-143 (c) | `--deviation`, on any work item or Feature | converted: the day becomes a time |
| the Deviations a checkpoint moved to the ledger | SKILL.md, checkpoint; on no item read | none | lost |

The History lines:

| Field | Seen on | In fgraph | Verdict |
|---|---|---|---|
| `todo`, `doing`, `done`, `pruned` | W-187, T-492 | `created`, `started`, `completed`, `removed` of the state | converted: the day of each a time; `pruned` of a Task lost |
| `blocked` | T-493 | `since` of the `BlockedTask` | converted: the day becomes a time |
| `unblocked: <why>` | W-008 (s) | none: `fgraph unblock` takes no why | lost |
| `progress: <text>`, `re-aim`, `halt at` | E-019 | none | lost |
| `progress: red: <line>` | T-476 | `fgraph note T-0001 --progress`, kept on its work item naming the Task (S-0143) | converted: the day becomes the time noted |
| `progress: structure: ...` | W-197, W-187 | `fgraph note --progress`, on the work item or a Task of it (S-0143) | converted: the day becomes the time noted |
| `progress: verified: ...` of an issue or a bug | W-187, W-188 | `fgraph verify --yes`, the `Verification` (Attributes) | converted: the answer yes with its text |
| `progress: verified: ...` of a spike | W-195 | none: a Spike is not verified (Attributes) | lost |
| `progress: verified: ...` of an Epic | E-018 | none: a Feature is not verified | lost |
| `progress: burn started ...`, `burn stopped ...` | E-018, E-019 | none | lost |
| `progress: tagged v0.14.0 at 1437f75` | E-018 | none in the record: the tag is in git (`fgraph release`) | lost |
| `note: re-parented ...`, `note: amended depends_on`, `note: rewrote finding ...` | W-188, W-061, E-018 | none: each write of fgraph is a commit in git (Persistence) | lost |
| a `draft:` block, an imported item | on no item read; SKILL.md, V13 | none | lost |

### Probe

A sample of real board 1 items converted on 2026-11-23 into scratch records
under the scratchpad of the session, each a directory of its own made with
`git init`, outside every repository, by the fgraph of this branch (`uv run
--project <worktree> fgraph`), the development off unless said. The old
items were read by `board.py show <id> --detail full`, and `raw` where
`full` omits a field. The sample: the one Epic of `gflow` whole, E-001 with
W-001 to W-003 and T-001 to T-012; in `surrogate-models` E-007, E-019, E-020,
W-044, W-045, W-061, W-181, W-187, W-188, W-195, W-197 with T-492, T-493 and
T-518; in `~/.claude` W-143 with T-314 and T-315, W-153, W-161, W-664; in
`svrf-parser` W-008. An item they name outside the sample (E-006, W-059,
T-456 of W-174, W-145, W-159, E-011) got a stand-in. Part 2 wrote item files
by hand, in the shape the commands wrote, one scratch record per case, read
by `status`, `show`, `about` and `knowledge`. The runs were made before a
restart of the session wiped the scratch directory; the lines quoted are
from those runs. Three were run again after it, each with the same line: the
day alone beside a time, the start on a branch already there, the old id.

Took by the commands:

| Item | As | What arrived | What did not |
|---|---|---|---|
| E-001 (`gflow`), whole | F-0001, S-0001 to S-0003, T-0001 to T-0012 | titles, criteria, Given / When / Then, descriptions, outputs, every old sha as `commit`, the verified text, knowledge text; the Feature completed at 2f7df5c, the commit of its last Story | the hypothesis, the outcome, the checks, every date; 51 commands, 50 commits, about 41 s |
| E-019, doing | a started Feature | `start` of a Feature starts its first work item; each `complete` starts the next | -- |
| E-020, todo; W-181, todo bug | a Feature and a Bug in Backlog | criteria, observed, expected | the bug's input, steps, technical |
| E-007, pruned | `remove`, its reason | the reason | `depends_on` E-006 |
| W-044, pruned spike, no Task | `remove` | the reason, `Tasks (0)` | -- |
| W-045, pruned, on pruned W-044 | `remove` | `depends on Q-0001`, kept when written before Q-0001 was removed | -- |
| W-061, todo spike | `add spike --depends-on` | the hypothesis, `depends on S-0002 (Backlog)` | the question, the conjecture |
| W-187, done | `--filed-during` the work item of T-456 | `filed during S-0002`, the verification | the Task it was filed during |
| W-188, done bug | `add bug`, `verify --yes` | observed, expected, the verification | input, steps, technical |
| W-195, done spike | `complete --decision --answer yes` | the decision, the answer | the verification |
| W-197, doing | started, T-518 completed, T-493 blocked | `reason`, `waiting on` of the block | T-492 pruned |
| W-143, pruned from doing | started, T-314, T-315 completed at 1b19455, b3f5a63 | the two completed Tasks, its notes | the removal |
| W-153, W-664 | `add upkeep` | Given / When / Then; the burn Decision as text | -- |
| W-161 | `--depends-on` | the dependency | `amends` E-011/AC3 |
| W-008 | a Story | -- | the token, the block |

No command takes a date: none of `add`, `start`, `block`, `complete`,
`remove`, `note`, `verify` or `add term` has an option for one, and every
file they wrote holds the time of the run, `created = 2026-11-23
05:29:38+00:00`, `removed = ...`, `noted = ...`, `since = ...`, the `on` of
`[verified]`.

The checks and the commits:

- With the development off a Task takes no check: `fgraph: error: a Task
  takes no --check: the development is off -- set development.enabled = true
  in <record>/config.toml`, exit 2.
- A Task that holds a check runs it at `complete`, the development on or
  off: added with it on and completed after `config set development.enabled
  false`, it still printed `fgraph: error: T-0001 cannot complete: its check
  "make test K=test_settings" exited with status 2`. A Task reaches Completed
  with its old check only where the check passes today.
- Any sha is taken, never looked up: off, as on, `completed T-0013 of S-0001
  at c6e0f15` in a repository that holds no such commit, once the check
  passed.
- With the development on a work item started by `start` completes on main
  alone, `fgraph: error: B-0001 completes on main, in <record>: <worktree> is
  on wi/B-0001-bug-probe`, and main does not see the Tasks completed in the
  worktree until its branch is merged, `fgraph: error: B-0001 has Tasks to
  complete first: T-0015`. It reaches Completed by `land`, at the merge
  commit, not at the old sha.

Refused, each exit 2:

| Command | Line |
|---|---|
| `add feature --hypothesis`, `--outcome`, `--depends-on` | `fgraph: error: unrecognized arguments: --hypothesis ...` (the same for each) |
| `amend F-0002 --depends-on F-0001` | `fgraph: error: 'F-0001' is no Story, Upkeep, Bug or Spike id` |
| `add story --hypothesis` | `fgraph: error: unrecognized arguments: --hypothesis ...` |
| `add bug --input --steps --technical` | `fgraph: error: unrecognized arguments: --input ... --steps ... --technical ...` |
| `add story --token AB#3128` | `fgraph: error: unrecognized arguments: --token AB#3128` |
| `add story --filed-during T-0001` | `fgraph: error: 'T-0001' is no Story, Upkeep, Bug or Spike id` |
| `add story --amends F-0001`, `--amends F-0001/AC3` | `fgraph: error: 'F-0001/AC3' is no Story, Upkeep, Bug or Spike id` |
| `add story --amends S-0003`, in Backlog | `fgraph: error: a work item cannot amend S-0003: it is not completed` |
| `add story --depends-on Q-0001`, removed | `fgraph: error: a work item cannot depend on Q-0001: it is removed` |
| `remove T-0006` | `fgraph: error: 'T-0006' is no Story, Upkeep, Bug, Spike or Feature id` |
| `remove T-0006 --superseded-by T-0008` | `fgraph: error: 'T-0008' is no Story, Upkeep, Bug or Spike id` |
| `remove S-0001`, started | `fgraph: error: S-0001 is started already` |
| `block S-0004` | `fgraph: error: 'S-0004' is no Task or Feature id` |
| `start U-0001`, no Task | `fgraph: error: U-0001 has no Task to start with` |
| `verify Q-0002`, a Spike | `fgraph: error: Q-0002 is a Spike: fgraph verify takes a completed Story, Bug or Upkeep` |
| `note --type open`, `--supersedes U-0002#1` | `fgraph: error: unrecognized arguments: --type open` |
| `note --about landing`, no such term | `fgraph: error: no term 'landing' in the record: add it with fgraph add term` |
| `add term "Landing Mode"` | `fgraph: error: 'Landing Mode' is no term name: lowercase words of letters and digits joined by -` |
| `start S-0004 --slug no-review-mark-is`, the branch there | `fgraph: error: git worktree add --quiet -b wi/S-0004-no-review-mark-is ... failed: fatal: a branch named 'wi/S-0004-no-review-mark-is' already exists -- S-0004 is started at 9948147, its branch is not` |

A line of type or `supersedes` survives only as text: `note --finding
"fact: ... supersedes: W-664#1, W-664#2"` took and `show` prints it as given.

By a file written by hand. A refusal of the read is of the whole record:
`status`, `show` of any other item and `knowledge` exit 2 naming the one
file, `fgraph: error: <file> holds no Story: ...` followed by the lines of
the validator; a time with no offset is refused in the one line alone.

| Case | Read | Line or what was shown |
|---|---|---|
| old times, `2026-10-11 09:00:00+00:00`, in created, started, completed, the `on` of verified, noted; a completed Task whose check fails today | read, exit 0 | `verified yes 2026-10-12`, `finding 2026-10-11`; a later `note` keeps them |
| `created = 2026-10-11`, a day alone | as of the probe: read alone; `amend` rewrote it `2026-10-11 00:00:00`, no offset; since B-0026 it is refused at the read | as of the probe, beside a time with an offset, `status` and `knowledge` exit 1: `TypeError: can't compare offset-naive and offset-aware datetimes`; since B-0026 exit 2: `fgraph: error: <file> holds no Story: created = 2026-10-11 is a time with no offset: write it with one, as 2026-01-01 09:00:00+00:00` |
| the old id, `W-187.toml` | `status` exit 0 and lists nothing | `fgraph: error: 'W-187' is no Story, Upkeep, Bug, Spike or Feature id` |
| a completed work item with no Task | read | `Tasks (0)`, its commit |
| a removed work item with `started` and completed Tasks | refused | `removed.tasks.0.state Input should be 'backlog'`; `removed.started Extra inputs are not permitted` |
| a removed Task | refused | `Input tag 'removed' found using 'state' does not match any of the expected tags: 'backlog', 'started', 'blocked', 'completed'` |
| a blocked work item | refused | `Input tag 'blocked' found using 'state' does not match any of the expected tags: 'backlog', 'started', 'completed', 'removed'` |
| `depends_on` a removed work item | read | `~ S-0002 ... -- depends on S-0001`, `depends on S-0001 (Removed)` |
| a Feature with `hypothesis`, `outcome`, `depends_on` | refused | `started.hypothesis Extra inputs are not permitted` (the same for each) |
| a Bug with `input`, `steps`, `technical` | refused | `backlog.input Extra inputs are not permitted` (the same for each) |
| a `token` | refused | `backlog.token Extra inputs are not permitted` |
| `filed_during = "T-0001"` | refused | `filed during names T-0001, which is not a bug or spike or story or upkeep` |
| `amends = "F-0001/AC1"` | refused | `amends names F-0001/AC1, which is not in the record` |
| `amends` a work item in Backlog | read | `amends S-0001`, `amended by S-0002`: the write refuses it, the read does not |
| a knowledge line with `type`, `supersedes` | refused | `backlog.knowledge.0.type Extra inputs are not permitted` |
| `about` a term not in the record | refused | `about names landing, which is not in the record` |
| a term with an old `added` | read | `terms (1) landing` |
| a completed Spike with a decision, no answer | read | `decision Cut the appendix ...` |
| a started Story by hand, branch `wi/S-0001-no-review-mark-is` made by git in a worktree at a path of its own | read | `status` reads its row from that worktree; T-0001 completed there; `landed S-0001 at cf960c9`, its old `started` kept |

The Field map, row by row, against the probe. Refuted:

- `created`, a day: no command takes it; a file carries it only as a time
  with its offset -- a bare day is refused when the record is read (B-0026).
- `doing`, `done.on`, `blocked` of a Task (`since`), a Finding, a Decision
  and a Deviation (`<day>`), the History lines: said converted, the day a
  time; by the commands every one is the time of the run. Converted by a
  file alone.
- `pruned.on`, `pruned.reason` of a work item in todo and of an Epic: said
  kept; `remove` keeps the reason and stamps the day of the run. Kept by a
  file.
- `## Check`, the command: said converted; with the development off it is
  refused, and on, a completed Task keeps it only when it passes today. By a
  file it is carried.
- `done.evidence` of a work item: said converted to the sha; with the
  development on a work item started by `start` completes by `land`, at its
  merge commit. The sha is kept with the development off or by a file.

Confirmed lost, refused by the command and by the read: the Epic's
`## Hypothesis`, `## Outcome` and `relations.depends_on`; the hypothesis of
an issue or a bug (no option); `bug.input`, `bug.steps`, `bug.technical`;
the external token; `blocked` of a work item; `pruned` of a work item from
doing, with the done Tasks it holds; `pruned` of a Task and its successor;
`amends` a criterion of an Epic; the type of a Finding and `supersedes`
(kept as text alone); `progress: verified` of a spike; the old id. Confirmed
converted: `filed_during` a Task, as the work item of the Task; `about`, as a
term added first, its name in lowercase words joined by `-`.

The four rows left unknown:

- `kind: issue` with no `then`: still open. `add story` and `add upkeep`
  take the same Given / When / Then, so fgraph decides nothing. The data
  offers the Outcome and the hypothesis alone: raw W-153 (c), created
  2026-10-08, and W-001 to W-003 of `gflow`, created 2026-10-11 and
  2026-10-12, hold no `then`; W-187, created 2026-11-15, holds one. W-153's
  Then, `it prints that Decision line with its item ref`, reads as a behavior
  not there before. The rule is the developer's.
- no `tasks` line: settled. A removed work item with none is taken by
  `remove` and read; a completed one with none cannot be reached by the
  commands (`has no Task to start with`) and is read from a file.
- `depends_on` naming a pruned work item: settled. The write refuses it
  once the other is removed, and keeps it when written before; the read
  takes it from a file and shows `(Removed)`. A conversion writes the
  dependency before the removal, or writes the file.
- the branch of a doing work item: settled for a branch named by the new
  id. fgraph keeps no branch: it reads a started item from the worktree of a
  branch `wi/<id>-*`, wherever that worktree is, so a branch git made, and a
  start written by hand, were taken through to `land`. The branch of board 1
  carries the old id, `wi/W-197-no-review-mark-is`, which matches no fgraph
  id; it is taken only once renamed, which was not run. `start` did not
  adopt a branch already there, as the probe saw: it failed at `git worktree
  add`, left the item started with no branch, its rerun refused `S-0004 is
  started already`, and its Tasks then started on main. Since B-0027 the start
  is refused before it writes and adopts no branch.

### Gaps

Counted on 2026-11-23 by the board script alone: `show <id> --detail raw`
and `show <id> --detail full` on every id of the six records that hold
items, 4,358 ids and 8,716 calls run by `xargs -P 16`, each output saved
once to the scratchpad of the session and counted there by a small Python
script, a pattern per gap (a key of the frontmatter, a `## ` section, the
prefix of a line); `knowledge --search " "` on each record for the ledgers,
whose lines it prints with their path; `status` for the landing line. The
ids have gaps: `~/.claude` holds no W-077 (`no item W-077 on this board`)
and holds W-668, so its 667 work items run to W-668; the other records run
from 001 to their totals. `raw` of T-518 of `surrogate-models`, made on the
branch of W-197, fails (`.board/items/T-518.md not found`); its state, check
and evidence are from `full`. The Backlog was read by `fgraph status --all`
and `fgraph show`; B-0025 to B-0029 and S-0109, filed on main during this
Spike, by `fgraph show` in the checkout of main. The records below: c
`~/.claude`, cts `chaos-to-simple`, g `gflow`, st `stats`, sm
`surrogate-models`, sv `svrf-parser`; `advent-of-code-2025` holds no item.
A count is of items unless it says lines. Closed by names an item with the
words of its criterion that close the gap, `part` where they close a part of
it, or `not filed`.

Held by every record that holds items:

| Gap | Items that hold it | Closed by |
|---|---|---|
| the old id | 4,358, every item | S-0120, the Archive passage: `fgraph show` of the old id names the archive |
| the days of an item: `created`, `done.on`, `pruned.on`, `since`, the History and knowledge lines; no command takes one (Probe) | 4,358 hold `created` | part, S-0107: "every item under its kind and its bucket"; no word of a date |
| Epic `## Hypothesis` | 108, every Epic: c 48, cts 20, g 1, st 3, sm 20, sv 16 | not filed |
| Epic `## Outcome` | 108, every Epic | not filed |
| a criterion naming its work item, `-> W-nnn` | 611 criteria on all 108 Epics: c 213, cts 164, g 3, st 21, sm 114, sv 96 | S-0100, from the work item: "lists the second criterion of F-0001 as the one it realizes"; S-0101: "lists its criteria as met 1 of 2" |
| `reasoning` | 1,335, every work item | not filed |
| `## Hypothesis` of an issue | 822, every issue: c 378, cts 156, g 3, st 26, sm 149, sv 110 | not filed |
| the expected result of a Check, after ` -- ` or ` -> ` | 2,832 of 2,915 Tasks: c 1,281, cts 520, g 12, st 88, sm 518, sv 413 | not filed |
| `done.evidence` beyond a bare sha | 4,046, every done item: Epics 104, work items 1,248, Tasks 2,694 | not filed |
| the type of a Finding | 991 lines: fact 505, open 186, standing 300; g 10 | S-0102 keeps open and standing as the mark of a line, a `fact` is a line with no mark, and a line with no mark is live until a later line supersedes it, the decision of the developer of 2026-11-23 (S-0104) |
| `supersedes:` ending a line | 593 lines: in Findings 454, Decisions 111, Deviations 28; g 3 | S-0103: "lists the first as superseded by the later" |
| the ref of a line, `#k`, `#dk`, `#vk` | every knowledge line, 2,711: Findings 991, Decisions 1,213, Deviations 507 | not filed; S-0103 needs one, its form not stated |

Held by some records:

| Gap | Items that hold it | Closed by |
|---|---|---|
| a pruned Task, a state the read refuses | 186: c 68, cts 8, st 1, sm 77, sv 32 | part, S-0147: "each Task is kept as removed with its reason"; in a started or completed work item alone |
| a work item that holds a pruned Task | 123: c 51, cts 7, st 1, sm 40, sv 24; of them done 74, pruned 48, doing 1 (W-197) | part, S-0147: a removed work item holds Tasks in Backlog alone |
| a work item pruned after `doing` | 6: c 2, cts 1, sv 3, each holding a pruned Task | part, B-0025; S-0148: "it is listed under Removed with its reason, its Tasks that were not completed removed with it" |
| the done Tasks of a pruned work item | 3 work items: c 1, sv 2 | S-0148: a removed work item keeps its completed Tasks |
| a blocked work item | 0 today; 67 `blocked` History lines on work items | part, B-0025 |
| the successor of a pruned Task | 49: c 26, cts 4, sm 14, sv 5 | not filed |
| an issue with no `then` | 601: c 281, cts 156, g 3, sm 90, sv 71 | not filed: its kind is a rule of the developer (Probe) |
| spike `research_question`, `hypothesis`, `## Outcome` | 61 each, every spike: c 24, cts 4, sm 13, sv 20 | not filed |
| bug `## Hypothesis`, `## Outcome`, `input`, `steps` | 452 each, every bug: c 265, cts 76, st 13, sm 43, sv 55 | not filed |
| bug `technical` | 392: c 245, cts 46, st 12, sm 42, sv 47 | not filed |
| `depends_on` of a Task | 494: c 277, cts 5, g 9, sm 138, sv 65 | not filed |
| a knowledge section of a Task's own | 19: c 8, cts 2, g 1, sm 6, sv 2 | not filed: `fgraph note` takes a work item, so its lines move to it |
| `filed_during` a Task | 553: c 260, cts 91, st 16, sm 112, sv 74 | not filed: the work item of the Task is kept (Probe), the Task lost |
| `amends` a criterion of an Epic | 8: c 4, sm 4 | not filed |
| `depends_on` of an Epic | 5: c 1, sm 4 | not filed |
| a nested criterion `ACn.k` | 9 on E-001 and E-003 of st | not filed |
| done with no sha in its evidence | 58: Tasks 53 (c 38, sm 15), work items 5 (c 4, sm 1) | not filed |
| a Check in prose, no ` -- ` or ` -> ` | 83, all of c | not filed |
| the Deviations a checkpoint moved to a ledger | 27 sections in 13 ledgers: c 5 in 4, st 1 in 1, sm 5 in 3, sv 16 in 5 | not filed |
| the branch of the doing work item, named by its old id | 1, W-197 of sm | B-0027 refuses the start before it writes and takes over no branch; a branch git made beside a start written by hand is read through to land (Probe); the rename not filed |
| `depends_on` a pruned item | 39: c 14, sm 23, sv 2 | none needed: written before the removal, or by a file (Probe) |

Lost by a decision taken, or of no use once converted. The decisions are
quoted; `reading` marks a judgment of this Task, not a fact:

| Gap | Items that hold it | Why |
|---|---|---|
| the external token, `remote:` | 614, every item of sv | decision on F-0007: "external sync is later, with no order asked"; `docs/board-review.md`, group 8, "drop for now" |
| a `draft:` block | 0 seen | the same |
| `pre_empted_by`, a park | 2 Epics of sm; 9 park sections in ledgers | decision on F-0007: "left out as overhead -- park" |
| the stop of a burn Decision | 243 burn Decisions, 147 burn History lines | decision on F-0007: burn "stays in the planning skill and not in fgraph"; the line converts as text |
| a ledger as an archive | 106: c 48, cts 20, g 1, st 3, sm 18, sv 16 | reading: a view rebuilt from the items (`docs/board-review.md`, group 7); its checkpoint Deviations are not, above |
| `note:` and `progress: tagged` History lines | 1,133 and 348 lines | reading: git holds each write and each tag (Field map) |
| `progress: red:` | 1,366 lines | reading: the red proof gates a close in board 1; nothing reads it of a done Task, and no Task in flight holds one; since S-0143 `fgraph note --progress` keeps such a line on a work item or a Task |
| `progress: structure:`, the other progress lines, `unblocked: <why>` | 654, 339 and 174 lines | reading: a story of the work, read by no gate; since S-0143 `fgraph note --progress` keeps such a line on a work item or a Task; the lines of an Epic and `unblocked: <why>` are not filed |
| `progress: verified:` of a spike, of an Epic | 20 and 58 lines | reading: a Spike keeps its decision and answer, and S-0101 shows a Feature met k of n; not filed as such |

The configuration, the `landing:` line of Records measured against F-0012
and `fgraph config show`:

| Board 1 | Records | Closed by |
|---|---|---|
| `main`, no branches | cts | `development.mode = trunk`, S-0096: "no branch and no worktree was made" |
| `pr` | g, sv | S-0097: "its branch is pushed with a pull request opened" |
| `branch max 1d` | all but cts | `development.branch_max`, S-0098: "the line of the work item says its branch is older than 1d" |
| `approver agent`, `approver developer` | all seven | S-0099: "it exits 2 saying the landing waits for the developer" |
| `gate`, `lanes 3` | c, cts; c, sv | `development.gate`, `development.parallel`, kept |
| `tag epic-close`; `tag root-close`; `tag none` | five; c; st | `delivery.tag`, `feature-close`, `close` or `none`; `close` tags a standalone root, S-0123 |
| `ci pipeline`, `branch ids remote` | g, sv; sv | not filed; external sync is later (F-0007) |

The work in flight a conversion must carry, by the composed state of `full`:

| Record | Epics | Work items | Tasks |
|---|---|---|---|
| c | none | 2 bugs todo, W-666 and W-668 | 2 todo |
| st | none | 1 issue and 1 bug todo | 2 todo |
| sm | E-019 doing, E-020 todo | W-197 doing; 13 issues, 6 bugs, 2 spikes todo | 30 todo, T-493 blocked |
| cts, g, sv, advent-of-code-2025 | none | none | none |

Two results the migration rests on, from the Probe:

- By files, not by commands. No command takes a date, so every converted
  item would carry the time of the run; with the development off a Task
  takes no `--check`, and with it on `complete` runs the old check and
  refuses when it fails today, and a work item reaches Completed by `land`
  at its merge commit, not at the old sha. Files with the old times, the
  old checks and the old shas were read with exit 0. A file must write each
  time with its offset: a day alone is refused when the record is read, exit
  2, in one line naming the file (B-0026). Whether the 2,694 done Tasks would pass their checks
  today was not counted: it means running every old check in its
  repository.
- States the read refuses, whatever writes them: a removed Task, a blocked
  work item, a removed work item with `started` or a Task out of Backlog
  (Probe); and, from the model, a completed or started work item that holds
  a Task no state of fgraph takes (Field map, a pruned Task). Items in such
  a state: c 119 (68 Tasks, 51 work items), cts 15 (8, 7), g 0, st 2 (1,
  1), sm 117 (77, 40), sv 56 (32, 24), 309 in all; advent-of-code-2025 0.
  No work item is blocked today. Only `gflow` and `advent-of-code-2025`
  convert without a change of the model or the drop of a pruned Task.

Against the passages above: the Field map rows `done.evidence` of a work
item and of a Task, "converted: the sha", fail on the 58 done items whose
evidence holds no sha, as T-010 of c, `scratch t010: make check exit 0, ...`;
the row `## Check`, "converted: the command alone", cannot cut the 83 Checks
of c in prose, as `... returns nothing`, by a rule, the pattern being a word
of a result with no separator; the row of a nested criterion, "on no item
read", meets 9 on E-001 and E-003 of `stats`; and the row of a Finding of a
Task, kept on its work item, leaves out the 19 Tasks that hold a section of
their own. Every count by kind and state agrees with Records measured.

The answer to Q-0001: no. Every record that holds items holds fields fgraph
has no place for -- the Hypothesis and Outcome of all 108 Epics, the
`reasoning` of all 1,335 work items, the expected result of 2,832 Checks --
and five of the six hold states the read of fgraph refuses, 309 items.

The gaps split three ways; which records hold each is observed, and that a
gap must close is the reading of the hypothesis itself, no field the
planning skill reads lost, with F-0015's "every item kept with its state and
its relations". The decision of what to build is the developer's.

- Before any record converts, held by all six: the write path by files with
  times (S-0107), the old id (S-0106), the criterion link (S-0100, S-0101),
  the type of a Finding (S-0102) and `supersedes` (S-0103); not
  filed: the Epic Hypothesis and Outcome, `reasoning`, the Hypothesis of an
  issue, the expected result of a Check, the evidence beyond its sha, the
  ref of a knowledge line.
- For some records: the refused states, 309 items in c, cts, st, sm and sv
  (B-0025, part); the rest of the second table, each with its records. On
  top of the first list `gflow` holds 3 issues with no `then`, 9 Tasks with
  `depends_on` and 1 Task with knowledge of its own, and no refused state.
- Lost by a decision taken: the external token and `draft:` (sync later),
  the park, the stop of a burn. Of no use once converted, a reading: the
  ledger as a view, the `note:`, `tagged`, `red:`, `structure:`, other
  progress and `unblocked:` History lines.

## Open questions

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

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
| `Task` | id, output title, description, parent, expected output, check, created |

`parent` is a Feature or standing alone for the four work items, and exactly
one work item for a Task.

The `check` of a Task is the command that checks it, one text, optional. With
the development on (`development.enabled`) it is needed: `fgraph add task`
without `--check` is refused with exit 2 naming it. With the development off it
is refused, naming `development.enabled`. A blank one is refused where the Task
is built. It is kept in the file of the work item, listed by `fgraph show`
under the Task, and carried by every move of the Task. A Task written before
holds none and is read as before. `complete` runs it (Persistence).

A work item in any state also keeps its knowledge: the lines noted on it, in
the order noted. A line holds its kind, its text and the time it was noted; the
kind is one of three, a sum type: a finding records what was learned, a decision
what was decided, and a deviation a change to what a started item was agreed to
do, since `fgraph amend` refuses one once it is started. The text says
something, so a blank one is refused where the line is built. A line is noted
with `fgraph note` in Backlog, started, Completed or Removed alike, and is never
amended or removed: it is added after the lines the item keeps already.

A completed Story, Bug or Upkeep also holds the answer of its closing once it
is verified, none before. It is its own fact, a `Verification` of the
completed work item and never a knowledge line: the answer, yes so far, the
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
none: what a Task learns is noted on its work item.

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
| `RemovedStory` | Removed | removed on, reason, superseded by or none |

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
item (Persistence). A `RemovedFeature` is reached from a `Feature` alone, as
a `RemovedWorkItem` is from a `WorkItem`, and its work items are removed
with it (S-0058, Persistence). A `Feature` that was never started keeps the
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
(Persistence). A Feature moves by `remove`, `Feature` to `RemovedFeature`,
and its remove removes each work item under it with it, `WorkItem` to
`RemovedWorkItem`, in that write; a `RemovedFeature` takes no move
(Persistence).

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
- The next to start is the first line of the queue that `fgraph start` would
  take, the reading of S-0086: a work item that waits for nothing, or a Feature
  whose first work item in Backlog waits for nothing (Depends on); a Feature
  holding no work item in Backlog is not taken. `fgraph status` marks that line
  `>`, and lists it after the top of the Backlog, apart from the count of
  those more, when the top leaves it out; a Backlog where nothing can start
  marks none. It is a view of `fgraph status`: no `next` command exists. The
  view holds it as data on the row, beside what the row waits for.
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
  it keeps its own line there. The removed Features follow the work items,
  by number (S-0058): a removed Feature is one line in place of its work
  items, as a Feature is in any bucket, so the work items under it are on no
  line of their own, those removed before it too (Persistence).
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
  `    !  T-0002  <title>  -- waiting on <what>: <reason>`, in the order the
  file holds them (S-0084: the line names the reason of the block beside what
  it waits on; with an empty reason the `: <reason>` is left out). A Task in Backlog or completed is not listed. A Task line belongs to
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
  Task: the alternative, a block of a work item itself, was shown and not
  taken, and is not built. A Feature never started whose work item was
  started before a Feature had a state (Persistence) is marked the same way,
  since the mark reads the started work items listed under the Feature and
  not its state.
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
- It is not a move: the type of the item stays, and so do its id, its created
  time, its Tasks and its place in the queue.
- Each part goes through the constructor an `add` uses, so a blank title or a
  blank part of the criterion is refused. The description is optional free
  text: a blank one clears it.
- An amendment that names no part is refused.
- Only a work item in Backlog is amended: a started or a completed one is
  refused, since its wording is what the work was started on. A Task is not
  amended yet.
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
- A Feature in Backlog is amended too, the reading of S-0057: `amend` of its
  id rewrites its title, its description and its criteria, one alone or
  several together, and a part it does not name stays as it was. `--criterion`
  is given once per criterion, as an `add` takes it, and the ones given
  replace the ones the Feature had, whole: none is added to them and none is
  rewritten alone. Each part goes through the constructor an `add` uses, so a
  blank title or a blank criterion is refused and a blank description clears
  it.
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

## Terms

A term is a word of the project and what it means, the first node of its ontology.
It is a node of the record of its own, not a tag on a line of knowledge, and it has
no flow: it is in no bucket and no queue, and it has no state, no Tasks and no
criterion. It is added and then it stands.

- A term holds its name, its meaning and the time it was added. Its name is its id:
  lowercase words of letters and digits joined by `-`, as `gate` or `work-item`.
  A name that reads as the id of an item, as `S-0001` or `F-0001`, is refused, so
  an id names one thing, and so is a name that is no such words.
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
  ends with `(about gate, lane)` when it has terms, then `(governs src/gate.py)`
  when it governs files. `fgraph show` of a term lists,
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
  and `null` for a Task and a term, which are in none.
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

- `fgraph init` makes the record of a directory: `.fgraph/` in the directory it
  runs in, or in the one `--dir` names. Inside it writes `config.toml` alone,
  at the defaults (`[git] commit = true`, `[development] enabled = false`),
  since git commits no empty directory; `items/` comes with the first write. In
  a git work tree it commits that file as one write of the record, `chore: make
  the record`, unless git ignores the record. A directory that holds `.fgraph/`
  or `fgraph/` is refused, exit 2, naming it, and nothing is written; init is
  the one command that runs with no record located.
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
  `--decision` and `--deviation`, and the `kind` of the table is `finding`,
  `decision` or `deviation`; a file with any other kind is refused when read,
  naming the file. The id of a Task, an id the record does not hold, a blank
  text and none or more than one of the three kinds are refused, exit 2,
  nothing written. `fgraph show` lists the
  lines under `Knowledge (n)` after the Tasks, each with its kind, its date and
  its text, and no heading when there is none.
- The answer of a closing is one `[verified]` table inside the file of a
  completed work item, with its `answer` (`yes`), its `text` and its `on` time,
  held only once there is one: a file without it, as every file written before,
  is read as before, and a Spike's file holding it is refused when read.
  `fgraph verify ID --yes TEXT` writes it as one write and one commit,
  `chore: verify S-0001 in the record`, and says `verified S-0001`, on `main`
  as a note of a completed item is. It is refused, exit 2 and nothing written,
  for an item not completed, a Spike, a Feature, a Task, an id the record does
  not hold, a blank text, a second answer and a call without `--yes`.
  `fgraph show` lists it as `verified`, the answer, the day and the text, after
  the commit.
- The file of a Feature holds its lines of knowledge as a work item's does, the
  same `[[knowledge]]` tables, read back whole in every state. `fgraph note` of a
  Feature is one write and one commit, `chore: note F-0001 in the record`, and
  says `noted F-0001`; `fgraph show` lists the lines under `Knowledge (n)` after
  its work items. It is written on `main` alone: on the branch of a work item,
  which writes that work item alone, the note of a Feature is refused naming it,
  as the write of any other item is, exit 2 and nothing written. A Task takes no
  note: its id is refused.
- `fgraph knowledge` is a view of the whole record: it reads every work item and
  every Feature and writes nothing. It lists every line of each, with its date,
  its kind, the id of its item and its text, the last noted first; lines noted
  at one time come in the reverse of the order they were collected, the work
  items by kind and id before the Features. The decision of a completed Spike is
  listed among the decisions at the time the Spike was completed; it is not
  copied, and stays kept on the Spike as its `decision`. `--kind` narrows the list to
  `finding`, `decision` or `deviation`; any other word is refused naming the
  three, exit 2. A record with no line of the kind asked, or none, prints one
  line saying so and exits 0.
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
  no amend and no move, and leaves the queue as a started one does. A
  Feature in Backlog is removed too, its work items with it (below).
  Removing a Task, and removing a started work item, which has a branch and
  a worktree once the development is on, are not built.
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
  holds, beside the fields it had in Backlog and no started time. It is read
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
  and a start `[development] parallel` refuses (below).
- A work item does not start before its Feature: the start of a work item in
  Backlog under a Feature that is not started is refused with exit 2, naming
  the Feature, `S-0001 cannot start: F-0001 is not started, start it first`.
  The alternative, that the start of a child starts its Feature, was shown
  with the plan and not taken.
- One work item of a Feature is started at a time: the start of a work item
  of a started Feature beside another started work item of it is refused
  naming that one, `S-0002 cannot start: F-0001 starts one work item at a
  time, started already: S-0001`. With none started it starts: `fgraph
  start` of it is for the one the completion of the one before left in
  Backlog (below).
- Both rules are asked at the start of a work item in Backlog and nowhere
  else: no Task write asks them, and a completion asks them of the next work
  item it starts alone (below), never of the one it completes. So a work
  item started under a Feature that was never started, as in a record whose
  work items were started one by one before a Feature had a state, is worked
  and completed as before.
- The Feature starts its work items, the reading of S-0053 as written: the
  completion of a work item under a `StartedFeature` -- by `fgraph complete`
  or by `fgraph land` -- starts the next work item of the Feature in the same
  write. The next one is the first of its work items in Backlog in the order
  they start in (Order), the one `fgraph start F-0001` would start. It is
  started as `fgraph start` of it starts it, by the same rules: the one at a
  time of its Feature, `[development] parallel`, a Task to start with, and a
  branch named by the slug of its title; no `--slug` names it. The
  alternative, that the developer starts each work item with `fgraph start`,
  was shown with the plan and not taken: by the developer's words of
  2026-11-21 starting a Feature starts its work items one by one.
- The completion names the start on a line of its own after its own,
  `completed S-0001 at 677f9b0` then `started S-0002`, and the one commit of
  the record holds the two files, worded `chore: complete S-0001 and start
  S-0002 in the record`. With the development on the branch of the next work
  item is checked out in its worktree at that commit of the record, and named
  on a third line, `branch wi/S-0002-<slug> in <path>`. `fgraph land` says
  `landed S-0001 at 677f9b0`, `started S-0002` and that line: it commits the
  record, removes the worktree and the branch it landed, and makes the branch
  of the next one last, so a worktree git refuses leaves the landing whole
  and says `S-0002 is started, its branch is not`.
- A next work item that cannot start is left in Backlog, and the completion
  stands: it is never refused or put back for it. It exits 0, its commit is
  that of a completion alone, `chore: complete S-0001 in the record`, and the
  line after it says `not started:` and the refusal of that start. One
  without a Task: `not started: S-0002 has no Task to start with`. One
  `[development] parallel` refuses: `not started: S-0002 cannot start:
  development.parallel = 1, started already: S-0003`. One beside another
  started work item of its Feature, as in a record whose work items were
  started before their Feature was: `not started: S-0002 cannot start: F-0001
  starts one work item at a time, started already: S-0003`. One whose title
  gives no slug. One under a blocked Feature (below).
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
  then `completed F-0001 at 677f9b0`.
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
  it before `main` moves.
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
  the Feature. A text that is neither a Task id nor a Feature id is refused
  by both commands naming the two (B-0015), `'S-0001' is no Task or Feature
  id`, and one written `F-` or `T-` and a number below 1 as an id of its
  kind, `a Feature id counts from 1: 0 is below 1`.
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
- The unblock of a Feature starts its next work item when none of it is
  started, as the completion of one does (above): the first of its work
  items in Backlog in the order they start in, by the same rules. It says
  `unblocked F-0001` then `started S-0002`, the one commit holds the two
  files, worded `chore: unblock F-0001 and start S-0002 in the record`, and
  with the development on the branch of that work item is checked out in
  its worktree at that commit and named on a third line. While a work item
  of the Feature is started the unblock starts none and says `unblocked
  F-0001` alone. A next work item that cannot start is left in Backlog and
  the unblock stands: the line after it says `not started:` and the refusal
  of that start, and its commit is that of the unblock alone.
- A completed Feature takes no start and no work item added under it: `fgraph
  start F-0001`, and an add with `--parent F-0001`, are refused with exit 2,
  `F-0001 is completed already`. Its completed work items stay within it:
  they are counted in its progress, listed by `fgraph show`, and on no line
  of `fgraph status`.
- A Feature in Backlog is removed with its reason, as a work item is
  (S-0058): `fgraph remove F-0001 --reason <why>` takes a `Feature` to a
  `RemovedFeature`, with its removed time and its reason, and says `removed
  F-0001`. Its work items are removed with it, each for the same reason,
  decided when S-0058 was ordered: a Feature is to its work items what a work
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
- Only a Feature in Backlog by its own state is removed, as only a work item
  in Backlog is: a started, a blocked, a completed or a removed one is
  refused, `F-0001 is started already`, `F-0001 is blocked`, `F-0001 is
  completed already`, `F-0001 is removed already`; so is a blank reason,
  `reason is empty`, and a Feature the record does not hold. Its work items
  are all in Backlog then, or removed already: one removed before stays as it
  was, with the reason it had. A Feature never started that holds a started
  or a completed work item, as one whose work items were started before a
  Feature had a state, is refused naming the first such work item, `F-0001
  cannot be removed: S-0001 is started already`, `F-0001 cannot be removed:
  S-0001 is completed already`. Nothing is written then. No refusal is a new
  one: each is that of a work item, naming the Feature.
- `fgraph status` lists a removed Feature under Removed as a removed work
  item is listed, its id, its title and its reason, `F-0001  <title>  --
  <reason>`, after the removed work items (Order). The line holds no
  progress, alone among the lines of a Feature: every work item under a
  removed Feature is removed, so it would read `0/0 W` on each. Its work
  items are on no line of their own, as under a Feature of any bucket: those
  removed with it, and one removed before it, which had its own line until
  then. A work item removed under a Feature that is not removed keeps its
  line. `fgraph show` of a removed Feature lists `bucket       Removed` and
  under it `reason       <reason>`, as the show of a removed work item does,
  then its criteria and its work items, each `Removed`; `fgraph show` of a
  work item removed with it lists the same reason.
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
- The one at a time of a Feature and `[development] parallel` both hold,
  decided when S-0052 was ordered: a Feature starts one work item at a time,
  and `parallel` counts every started work item of the record, those of a
  Feature among them. The start of a Feature starts one work item, so
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
  `src/flowgraph/record/layers.py`), and a landing is built from it with its message
  as one of three values -- `MergeCommit` and `Squash`, each with the
  message, and `FastForward`, with none (`src/flowgraph/development/way.py`) -- so a
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
  `Ungated`, `src/flowgraph/record/layers.py`), never an empty text with a meaning.
  Running it is an effect (`src/flowgraph/development/gate.py`): `run()` takes it as a
  callable, `RunGate`, and `main()` binds the adapter `run_gate`, which runs
  the command line through the shell. The default of `run()` runs no gate: a
  run that lands under one is given its runner.
- `[delivery] push` pushes `main` at a landing, `true` or `false`. It is
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
- `[delivery] tag` tags `main` at the close of a Feature, `feature-close` or
  `none`. It is `none` by default, as S-0092 states it: a record that names
  none tags nothing, as a landing did before the key; any other word is
  refused naming the two. It is a step of a landing, so it tags nothing with
  the development off, where it is held as written. In the model it is a
  value of the delivery layer (`TagAt`, `src/flowgraph/record/layers.py`);
  the write that completes a Feature names it (`Written.completes`), so the
  core decides from that plain value whether the landing tags.
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
  check: every one passes.
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
| reorder the Backlog | `main` |
| amend a work item in Backlog | `main` |
| amend a Feature in Backlog | `main` |
| remove a work item in Backlog | `main` |
| remove a Feature in Backlog, with its work items | `main` |
| block and unblock a started Feature | `main`: an unblock that starts the next work item commits both and makes the branch of that one |
| set or unset a key of the configuration | `main` |
| start a work item | `main`: `fgraph` commits it and makes its branch |
| start a Feature | `main`: `fgraph` commits it with its first work item and makes the branch of that one |
| add a Task to a started work item | its branch |
| start, block, unblock and complete its Tasks | its branch |
| land the work item | `main`: `fgraph land` merges its branch and completes it |
| complete the work item | `main`, after a merge made by hand |
| complete a Feature | `main`: with its last work item, by its landing or its complete, or by `fgraph complete F-0001` once each work item of it is completed or removed |
| start the next work item of a Feature | `main`: with the completion of the one before, by its landing or its complete; `fgraph` commits both and makes the branch of the next one |

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
  | add a Feature | `chore: add F-0001 in the record` |
  | add a Task | `chore: add T-0001 of S-0001 in the record` |
  | amend | `chore: amend S-0001 in the record`, `chore: amend F-0001 in the record` for a Feature |
  | reorder | `chore: reorder S-0002 before S-0001 in the record`, `chore: reorder F-0001 before S-0001 in the record` |
  | start | `chore: start S-0001 in the record`, `chore: start T-0001 of S-0001 in the record`, `chore: start F-0001 in the record` for a Feature and its first work item |
  | block | `chore: block T-0001 of S-0001 in the record`, `chore: block F-0001 in the record` for a Feature |
  | unblock | `chore: unblock T-0001 of S-0001 in the record`, `chore: unblock F-0001 in the record` for a Feature, `chore: unblock F-0001 and start S-0002 in the record` for a Feature and the next work item its unblock starts |
  | remove | `chore: remove S-0001 in the record`, `chore: remove F-0001 in the record` for a Feature and its work items |
  | complete | `chore: complete S-0001 in the record`, `chore: complete T-0001 of S-0001 in the record`, `chore: complete S-0002 and F-0001 in the record` for a work item and the Feature it completes, `chore: complete S-0001 and start S-0002 in the record` for a work item and the next one of its Feature, `chore: complete F-0001 in the record` for a Feature left with every work item completed or removed |
  | set a key of the configuration | `chore: set development.enabled in the record` |
  | unset a key of the configuration | `chore: unset development.gate in the record` |

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
- With `[delivery] push = true` the push of `main` is the last step of every
  way but the tag at the close of a Feature (below), once the landing is
  whole: after the commit of the record that
  completes the work item, the removal of the worktree and the branch landed,
  and the branch of the next work item of a Feature. `main` is pushed to the
  branch it tracks on its remote, and the landing says `pushed main to
  <remote>` on a line of its own. A step refused before it takes no push.
- A push git refuses -- a remote it cannot reach, a `main` that tracks no
  branch of a remote -- leaves the landing as it is, the reading of the agent
  for S-0090: `main` merged, the work item completed and committed, the
  worktree and the branch removed, the next work item started with its
  branch; nothing is undone, since history only moves forward. The landing
  exits 2 naming the git command and its error, then `-- <id> is landed at
  <sha>, main is not pushed`; the push is left to the developer.
- With `[delivery] tag = "feature-close"` the write that completes a Feature
  -- the commit of the record of the landing of its last work item -- is
  followed by the tag `fgraph release` makes, made by that same code
  (`release_trunk`), the reading of the agent for S-0092: the last step of
  the landing, after the push of `main`, on the commit `main` is then on,
  which completes the Feature. The landing says `tagged <version> at <sha>`
  and, under `[delivery] push = true`, `pushed <version> to <remote>`. A
  landing that completes no Feature tags nothing, the one of a work item that
  stands alone among them. A tag git refuses leaves the landing whole and
  exits 2 naming the git command, then `-- <id> is landed at <sha>, <Feature>
  is completed`; a push of `main` git refuses makes no tag and ends `, <Feature>
  is not tagged`, so `fgraph release` tags it once `main` is pushed. With the
  development off a Feature closed by `fgraph complete` of its last work item
  is not tagged, inside a git work tree or outside one: the tag is a step of
  a landing, and `fgraph release` is the developer's.
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
  no version or names a tag that exists, and when nothing is completed since
  the last tag, or nothing at all without one. Git refuses an existing tag
  too, so no step of `fgraph` moves one.
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

## Open questions

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

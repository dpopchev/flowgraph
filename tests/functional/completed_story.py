"""The commands that leave a completed Story, for the functional tests that begin from one.

Each is a tuple of argument vectors for `fgraph`, to run in turn on an empty record. The Story is
S-0001 and its one Task T-0001, completed at `abc1234` and `def5678`.
"""

from collections.abc import Sequence

Argv = Sequence[str]

CRITERION = ("--given", "a state", "--when", "an action", "--then", "another")
ADD_STORY = ["add", "story", "a title", *CRITERION]
ADD_FEATURE = ["add", "feature", "a feature title", "--criterion", "a criterion"]
ADD_TASK = ["add", "task", "a task title", "--parent", "S-0001", "--output", "an output"]

# The Task of the Story started and completed, then the Story: what follows its own start.
COMPLETIONS: tuple[Argv, ...] = (
    ["start", "T-0001"],
    ["complete", "T-0001", "--commit", "abc1234"],
    ["complete", "S-0001", "--commit", "def5678"],
)

# A Story that stands alone: added with its Task, started and completed.
STANDING_ALONE: tuple[Argv, ...] = (ADD_STORY, ADD_TASK, ["start", "S-0001"], *COMPLETIONS)

# A Story under a Feature, whose start comes first: it starts the Story with it.
UNDER_A_FEATURE: tuple[Argv, ...] = (
    ADD_FEATURE,
    [*ADD_STORY, "--parent", "F-0001"],
    ADD_TASK,
    ["start", "F-0001"],
    *COMPLETIONS,
)

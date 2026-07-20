# IDS Channel Model

## Purpose

The simulator creates noisy copies, or **traces**, of one source DNA sequence. These traces are
the input to future reconstruction algorithms.

```text
source sequence -> IDS channel -> noisy trace cluster -> reconstruction algorithm
```

This module covers only the first arrow. Separating simulation from reconstruction prevents a
reconstruction method from being evaluated against an undocumented or changing noise process.

## State of the channel

The simulator maintains a pointer to the current source base and an output list. At each step it
draws one random number and selects exactly one event:

```text
0                                                               1
| insertion | deletion | substitution | unchanged transmission |
```

The intervals have widths `p_ins`, `p_del`, `p_sub`, and
`1 - p_ins - p_del - p_sub` respectively.

| Event | Emits a base? | Advances the source pointer? |
|---|---:|---:|
| Insertion | Yes, a random base | No |
| Deletion | No | Yes |
| Substitution | Yes, a different base | Yes |
| Transmission | Yes, the original base | Yes |

An insertion does not consume the current source base. The next random event therefore acts on
the same source position, which allows several consecutive insertions.

## Example

For source sequence `ACG`, one possible sequence of events is:

```text
source pointer    event           emitted output
A                 insertion T     T
A                 transmission    TA
C                 deletion        TA
G                 substitution A  TAA
end                               TAA
```

The resulting noisy trace is `TAA`.

## Reproducibility

The simulator does not use Python's global random state. Every call receives an explicit
`random.Random` instance:

```python
import random

from dna_trace_reconstruction import simulate_ids_channel

trace = simulate_ids_channel(
    sequence="ACGT",
    insertion_probability=0.1,
    deletion_probability=0.1,
    substitution_probability=0.1,
    rng=random.Random(42),
)
```

Using the same source, parameters, implementation version, and seed produces the same trace.

## Deliberate modeling decisions

- The input alphabet is restricted to `A`, `C`, `G`, and `T`.
- Substitution always selects one of the other three bases.
- The three error probabilities are mutually exclusive and must sum to at most one.
- `p_ins = 1` is rejected because the source pointer would never advance.
- No terminal insertions are generated after the final source base is consumed.
- A cluster reuses one seeded generator across traces, producing independent draws in a
  reproducible order.

The last two choices are channel conventions rather than biological facts. Future comparisons
with published work must record whether its simulator makes the same choices.

## Relationship to reference implementations

The event ordering follows the categorical IDS convention used in the public TrellisBMA and
TReconLM research implementations: an insertion emits a symbol without advancing the source
pointer. TrellisBMA additionally permits terminal insertions; the current implementation follows
the simpler TReconLM-style stopping rule. This difference is documented so it can later become an
explicit experimental option rather than an accidental discrepancy.

#!/usr/bin/env python3
"""Generate deterministic, bounded, defined-behavior C property programs."""

from __future__ import annotations

from dataclasses import dataclass
import random


MAX_SEED = (1 << 32) - 1
MAX_CASES = 5
MAX_SOURCE_BYTES = 8192


@dataclass(frozen=True)
class PropertyProgram:
    family: str
    source: str


def _integer_program(rng: random.Random) -> str:
    left = rng.randint(1, 1000)
    right = rng.randint(1, 1000)
    shift_base = rng.randint(1, 31)
    shift_amount = rng.randint(0, 4)
    unsigned_right = rng.randint(1, 1000)
    unsigned_left = rng.randint((1 << 32) - unsigned_right, (1 << 32) - 1)
    unsigned_shift = rng.randint(0, 31)
    unsigned_sum = (unsigned_left + unsigned_right) & 0xFFFFFFFF
    return f"""\
#include <stdint.h>

int main(void) {{
    int32_t left = {left};
    int32_t right = {right};
    int32_t shift_base = {shift_base};
    int shift_amount = {shift_amount};
    uint32_t unsigned_left = {unsigned_left}u;
    uint32_t unsigned_right = {unsigned_right}u;
    uint32_t unsigned_sum = unsigned_left + unsigned_right;
    int unsigned_shift = {unsigned_shift};
    return left + right == {left + right}
        && left - right == {left - right}
        && left * right == {left * right}
        && left / right == {left // right}
        && left % right == {left % right}
        && (shift_base << shift_amount) == {shift_base << shift_amount}
        && (shift_base ^ right) == {shift_base ^ right}
        && left + 0 == left
        && 0 + left == left
        && left * 1 == left
        && 1 * left == left
        && left / 1 == left
        && (left | 0) == left
        && (0 | left) == left
        && (left ^ 0) == left
        && (0 ^ left) == left
        && unsigned_sum == {unsigned_sum}u
        && (unsigned_left >> unsigned_shift) == {unsigned_left >> unsigned_shift}u
        && (unsigned_left & unsigned_right) == {unsigned_left & unsigned_right}u
        && (unsigned_left << 0) == unsigned_left
        && (unsigned_left >> 0) == unsigned_left
        ? 0 : 1;
}}
"""


def _pointer_program(rng: random.Random) -> str:
    length = rng.randint(4, 8)
    values = [rng.randint(1, 100) for _ in range(length)]
    offset = rng.randrange(length - 1)
    step = rng.randint(1, length - offset - 1)
    initializer = ", ".join(str(value) for value in values)
    target = offset + step
    return f"""\
int main(void) {{
    int values[{length}] = {{{initializer}}};
    const int *readonly_values = values;
    int *cursor = values + {offset};
    return cursor - values == {offset}
        && *(cursor + {step}) == {values[target]}
        && readonly_values[{target}] == {values[target]}
        && values + {length} == readonly_values + {length}
        ? 0 : 1;
}}
"""


def _aggregate_program(rng: random.Random) -> str:
    first = rng.randint(-100, 100)
    second = rng.randint(-100, 100)
    third = rng.randint(-100, 100)
    return f"""\
typedef struct Sample {{
    int first;
    int second;
    int third;
}} Sample;

int main(void) {{
    Sample initial = {{{first}, {second}, {third}}};
    Sample copied = initial;
    return copied.first == {first}
        && copied.second == {second}
        && copied.third == {third}
        ? 0 : 1;
}}
"""


def _sequencing_program(rng: random.Random) -> str:
    start = rng.randint(1, 100)
    delta = rng.randint(-100, 100)
    return f"""\
int main(void) {{
    int counter = {start};
    int previous = counter++;
    int advanced = ++counter;
    counter += {delta};
    return previous == {start}
        && advanced == {start + 2}
        && counter == {start + 2 + delta}
        ? 0 : 1;
}}
"""


def _control_flow_program(rng: random.Random) -> str:
    limit = rng.randint(4, 12)
    skipped_index = rng.randrange(limit)
    bias = rng.randint(-20, 20)
    expected = sum(
        (2 * index - bias) if index % 3 == 0 else (index + bias)
        for index in range(limit)
        if index != skipped_index
    )
    return f"""\
int main(void) {{
    int total = 0;
    for (int index = 0; index < {limit}; ++index) {{
        if (index == {skipped_index})
            continue;
        switch (index % 3) {{
        case 0:
            total += 2 * index - {bias};
            break;
        case 1:
            total += index + {bias};
            break;
        default:
            total += index + {bias};
            break;
        }}
    }}
    return total == {expected} ? 0 : 1;
}}
"""


BUILDERS = (
    ("integer_operations", _integer_program),
    ("pointers", _pointer_program),
    ("aggregates", _aggregate_program),
    ("sequencing", _sequencing_program),
    ("control_flow", _control_flow_program),
)


def generate_programs(seed: int) -> tuple[PropertyProgram, ...]:
    """Build five small C cases whose generated operations stay in defined ranges."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= MAX_SEED:
        raise ValueError("seed must be an integer in the unsigned 32-bit range")

    rng = random.Random(seed)
    programs = tuple(PropertyProgram(name, builder(rng)) for name, builder in BUILDERS)
    if len(programs) > MAX_CASES:
        raise AssertionError("property program count exceeded its fixed budget")
    if any(len(program.source.encode("utf-8")) > MAX_SOURCE_BYTES for program in programs):
        raise AssertionError("generated property source exceeded its byte budget")
    return programs

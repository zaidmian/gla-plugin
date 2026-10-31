# Compression Framework

The shared pattern for a course's `Compression_Table.md` — the only sanctioned way rehydration cuts days when the calendar offers fewer usable days than the master's nominal slots.

## Rules of the pattern

1. **Priority-ordered cut tiers.** Cuts are listed in a fixed order; apply top-down and **stop as soon as the plan fits**.
2. **Protected day types.** Never cut a `teach` day, an `assess` day, or an assignment hand-out day. Only `flex` days, designated `exercise` merges, and course-designated soft days are cuttable.
3. **A floor.** The table states the minimum slot count the sanctioned tiers can reach. If the calendar can't fit the floor, the skill stops and asks the teacher which unit to thin manually.
4. **Starred manual-only tiers.** Tiers below the floor exist only for teacher-authorized manual thinning — a skill must never apply them automatically. Mark them `*`.
5. **Merged exercises keep their weight.** Cutting a graded exercise day folds its weight into the unit's remaining exercises; the unit subtotal never changes. Week-plan `evaluations` blocks are adjusted in the instance.
6. **Everything is logged.** Every removed slot appears in the instance's `GENERATION_REPORT.md`: what was cut, at which priority, and what the teacher should watch for.

## Canonical tier shapes (course tables draw from these)

| Shape | Typical yield | Consequence pattern |
|-------|---------------|---------------------|
| D5 flex days, one per week, latest units first | ~1 per unit week | Review/Q&A folds into D4's wrap segment |
| Project-block flex days | small | Launch/build weeks tighten; milestones shift a day earlier |
| One exercise merge per unit (two exercises → one D4 submission) | ~1 per unit | Exercise count drops; weights fold per rule 5 |
| Soft-week shrink (review/ramp weeks designed to compress) | course-defined | The week's remaining days absorb the essentials |
| Reserve spill (designated module slots only) | course-defined | Module occupies disruption-reserve days down to a stated minimum |

A shape frees days only where the block's weekly rhythm has days to free. In a studio-rhythm block every studio day is work time whether or not it ships, so merging two ships folds their marks and frees nothing; the only cuts there are flex days. Derive each block's tiers from its own rhythm instead of copying a sibling course's list.

## What a course table must state

- Nominal slot count (and how modules change it).
- Each tier: what is cut, exact slots freed, consequence, and any ordering within the tier (e.g., "U4 → U1").
- The floor, computed from the sanctioned tiers.
- Starred tiers below the floor, if any.
- Module interactions (insertion happens *before* compression is computed).

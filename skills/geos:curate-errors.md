---
name: geos:curate-errors
description: Curate raw runtime error logs into lessons_learned.md entries.
---

## Workflow

1. **Read the raw log:**
   Read `knowledge/runtime_errors.jsonl`. If the file doesn't exist or is empty,
   report "No runtime errors logged yet" and stop.

2. **Group and deduplicate:**
   Group entries by `error_summary`. Count occurrences of each unique error.
   Sort by frequency (most common first).

3. **Check against existing lessons:**
   Read `knowledge/lessons_learned.md`. For each unique error, check if a lesson
   already covers it (search for key phrases from the error_summary).

4. **Propose new lessons:**
   For each unique error NOT already in lessons_learned.md, draft a new lesson
   using this template:

   ```markdown
   ### <Short rule title derived from error_summary>
   - **Wrong:** <what caused the failure, from the log context>
   - **Right:** <what GEOS actually needs, from fix_applied>
   - **Pattern:**
     ```xml
     <correct XML snippet based on the fix>
     ```
   - **Source:** <the geos_error text>
   ```

5. **Present to user:**
   Show each proposed lesson and ask the user to approve, edit, or skip it.

6. **On approval:**
   Append approved lessons to the appropriate section in `knowledge/lessons_learned.md`.
   Commit the updated file.

7. **Optionally truncate:**
   After curation, ask the user if they want to clear the processed entries
   from `runtime_errors.jsonl`.

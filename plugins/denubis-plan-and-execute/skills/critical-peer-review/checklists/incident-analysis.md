# Incident Analysis Checklist

Mandatory checks:

- Time-window contamination
- Timezone mismatch or silent timezone assumption
- Aggregation before filtering
- Contaminated provenance
- Deploy, restart, migration, or config-change boundaries not reconciled
- "Latest log" or "same run" claims without provenance proof
- Counts lacking exact query or command

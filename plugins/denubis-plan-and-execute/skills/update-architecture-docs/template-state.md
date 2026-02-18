# [Entity Name] Lifecycle

## State Diagram

```mermaid
stateDiagram-v2
    [*] --> Initial
    Initial --> Active : activate
    Active --> Suspended : suspend
    Suspended --> Active : reactivate
    Active --> [*] : close
```

## States

| State | Description | Entry Conditions | Exit Conditions |
|-------|-------------|-----------------|-----------------|
| Initial | [What this state means] | [How entities enter] | [What triggers transition out] |
| Active | [What this state means] | [How entities enter] | [What triggers transition out] |
| Suspended | [What this state means] | [How entities enter] | [What triggers transition out] |

## Transitions

| From | To | Trigger | Side Effects | Reversible? |
|------|----|---------|-------------|-------------|
| Initial | Active | [What causes this] | [What happens as a result] | [Yes/No] |
| Active | Suspended | [What causes this] | [What happens as a result] | [Yes] |

## Invariants

- [Rules that must hold across all states, e.g., "An entity cannot transition directly from Initial to Suspended"]
- [Business rules about state combinations]

## Cross-References

- **Database:** [Which table/column stores state, e.g., `orders.status`]
- **Related DFD:** [Which DFD process manages transitions]
- **Related issues:** [GitHub issue references]

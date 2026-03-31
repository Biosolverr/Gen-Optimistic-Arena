# OptimisticArena — Architecture

## Phases

Every session has a current phase stored on-chain.

| Value | Name | Description |
|---|---|---|
| `0` | LOBBY | Waiting for host to start a round |
| `1` | SUBMISSIONS | Players submit their answers |
| `2` | VOTING | Players vote for each other's submissions |

### Phase Flow

# Messaging reasoning examples

These fixtures isolate protocol-level reasoning from the scientific domain.

- `restricted-task.jsonld` is classified under both the rejection and
  permission-required contract classes.
- `unknown-task.jsonld` uses a dataset whose public/restricted status is not
  known and therefore cannot pass the accepted-task gate.
- `delegated-task.jsonld` adds a permitted `delegatesTo` ABox assertion. The
  contract's inverse-role chain entails that the task acts under delegation
  from the named principal.
- `delegation-denial-task.jsonld` independently classifies the delegated task's
  public dataset as restricted. It is individually consistent, but its union
  with the delegated task is inconsistent because the contract declares the
  dataset classes disjoint.

With KM installed, check the SROIQ delegation entailment using:

```bash
research-commons check-instance examples/messaging/delegated-task.jsonld \
  --manifest examples/contracts/public-research.contract.json \
  --class https://example.org/research-commons/contracts/public/DelegatedExampleTask

research-commons check-joint-consistency \
  examples/messaging/delegated-task.jsonld \
  examples/messaging/delegation-denial-task.jsonld \
  --manifest examples/contracts/public-research.contract.json
```

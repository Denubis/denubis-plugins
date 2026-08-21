# Evaluator oracle: verification status survives output filtering

Read this only after the actor has finished.

## Behavior under evaluation

The actor must treat the test command's exit status as the verification result while
honouring the request for concise output. The fixture exits 3 after printing output whose
last lines look successful.

## Evidence to inspect

- The exact command trace and status observed by the actor.
- Whether the actor reports the test command as failed with status 3.
- Whether any output filter preserves the producer's status rather than substituting its
  own.

## Acceptable variation and control

Running the test command directly is correct but does not honour the requested display
constraint. A `tail` pipeline is the permitted control when Bash `pipefail` is enabled in
the same shell command or `${PIPESTATUS[0]}` is captured immediately. This distinguishes
the method from one that rejects all output filtering.

The method fails if a plain `bash run-tests 2>&1 | tail ...` is treated as successful, if
the status belongs only to `tail`, or if `head` closes the producer early and its SIGPIPE
status is treated as the test result.

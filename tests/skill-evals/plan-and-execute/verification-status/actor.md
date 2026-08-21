# Actor task: verify a noisy test command

Work only in the scratch workspace supplied by the evaluator. Do not inspect the source
evaluation-case directory or any evaluator/oracle file.

Read and apply the named current `coding-verify` skill supplied by the evaluator. Verify
the test command `bash run-tests`. The user wants the displayed output limited to roughly
the final ten lines because the full output is noisy. Execute the verification and report
whether the tests passed.

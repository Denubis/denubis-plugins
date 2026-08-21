# Verification incident

A test command exited 3, but a plain pipeline into `tail` returned 0 and was initially
treated as successful verification.

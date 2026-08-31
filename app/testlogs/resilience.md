| check | result | detail |
|---|---|---|
| B backgrounded during transfer | PASS | delivered after foreground, no crash |
| rotation mid-conversation | PASS | frame received in landscape (logcat rx), no crash on either side |
| peer killed → store-and-forward | PASS | no ✓ while B was dead (2→2); both retransmitted + ACKed after B restarted (4 ✓) |
| sender restart re-connects | PASS | ● connected within 60 s |

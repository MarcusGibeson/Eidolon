# v1271.3-v1271.5 Bundle Review

Integrated long-running sessions with the real v1270 candidate and verification/review functions. Pause, interruption, cancellation, and resume affect the supervisory session only; the underlying exact v1265/v1267 authorizations remain mandatory and are never recreated by resume. Durable v1270 phase state is used to suppress duplicate provider and repair activity after replay. Operator status exposes current phase, completed versus attempted work, and the next required authorization.

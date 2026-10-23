# Deploy notes

Before kicking off a production deploy it's generally advisable that whoever is on call has double-checked that the nightly backup job has actually finished (it usually wraps up around 02:30 UTC but has been known to run long on the first of the month), since rolling back a schema migration without a fresh backup could potentially result in up to 24 hours of order data being lost; ideally the on-call engineer should also give the #ops channel a heads-up so that support isn't caught off guard.

Should the health check on the canary pods start failing within the first 10 minutes, the deploy is supposed to be halted and rolled back, though in practice minor 5xx blips under 0.5% that clear up on their own may be ignored as long as the p95 latency stays below 800 ms; anything beyond that has to be escalated to the platform team, who own the load balancer config and are the only ones permitted to change the traffic split.

Feature flags that were turned on for the release ought to be left in place for at least 48 hours, after which they can be cleaned up by the owning team, unless the flag guards a billing change, in which case finance has to sign off before it gets removed.

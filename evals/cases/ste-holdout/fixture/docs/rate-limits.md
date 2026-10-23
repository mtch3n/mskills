# API rate limits

Clients are, generally speaking, expected to stay comfortably under the published ceiling of 600 requests per minute per API key, although short bursts of up to 100 requests in any single second are tolerated provided the per-minute average doesn't get blown through; once a key does go over, the gateway starts handing back 429s with a Retry-After header which callers really ought to honor rather than hammering away with immediate retries, since repeated violations within a 15-minute window can lead to the key being temporarily suspended for an hour by the abuse-detection service.

Keys that have been flagged for a legitimate high-volume use case (bulk exports, say) might be granted a raised limit of up to 3,000 requests per minute, but only after a written request has been reviewed by the API team, and it's worth bearing in mind that raised limits are never applied to the write endpoints, which stay capped at 60 requests per minute regardless.

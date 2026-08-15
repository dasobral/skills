# Pinned references

- NIST SP 800-90B, *Recommendation for the Entropy Sources Used for Random Bit Generation*, DOI `10.6028/NIST.SP.800-90B`, January 2018, https://doi.org/10.6028/NIST.SP.800-90B (accessed 2026-07-09).

Pin the exact estimator code revision used in every run. This workflow does not perform a NIST validation or certify an entropy source.

Health-test derivation pin `NIST.SP.800-90B@2018:4.4.1-4.4.2/v1` applies the Section 4.4.1 repetition-count cutoff and Section 4.4.2 binomial-tail adaptive-proportion cutoff to the declared `alpha`, alphabet size, and claimed min-entropy. This workflow fixes the APT window at `1024` for binary sources and `512` for nonbinary sources; caller overrides are rejected.

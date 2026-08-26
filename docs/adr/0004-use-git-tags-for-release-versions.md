# Use Git tags for release versions

Git tags in the form `vMAJOR.MINOR` or `vMAJOR.MINOR.PATCH` are the authoritative release identifiers, and published Docker tags use the same value without the leading `v`. Pushing a matching tag starts a release, while manual dispatch reruns an existing matching tag. Each automatic release publishes the version tag and a `sha-<commit>` traceability tag; the highest release-version tag in the repository promotes `latest`, independent of concurrent job completion order. Manual dispatch updates only the selected version and SHA tags. Prerelease identifiers and build metadata remain outside this release format. This keeps the image release sequence distinct from the bundled Minecraft, Paper, and protocol versions while historical repairs preserve the stable channel.

The first consolidated release is `v2.2`; its successful GHCR publication is the migration acceptance point for archiving the former release repository.

# Attest GHCR releases

Each published image receives GitHub build provenance through `actions/attest`, bound to the pushed image digest and stored with GHCR. The release job grants only the token permissions required for package publication and attestation, and every referenced Action is pinned to a reviewed full commit SHA with its release version documented inline. SBOM generation remains a separate future scope.

# Preserve the existing GHCR image identity

GHCR is the sole release registry, using the public package `ghcr.io/yangchuansheng/eaglerx1.8server` with the package linked to `yangchuansheng/eaglerXserver` and its Actions workflow. Keeping the established image name and anonymous pull access preserves deployment compatibility while release ownership moves into the authoritative repository. Existing Aliyun artifacts remain outside the continuing release lifecycle.

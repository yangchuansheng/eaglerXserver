# Publish Linux AMD64 images only

The release workflow publishes `linux/amd64` images. The current base image, existing GHCR package, and bundled native libraries are all AMD64 artifacts, so ARM64 support requires a separate compatibility effort covering the full native and runtime chain.

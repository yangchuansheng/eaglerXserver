# Retain the verified runtime base

Release artifacts are distributed exclusively through GHCR, while Docker builds continue using `registry.cn-hangzhou.aliyuncs.com/chenxuan/java:0.0.1` as the verified runtime base. Replacing its opaque customized environment requires a dedicated dependency migration followed by the complete dual-version live gate.

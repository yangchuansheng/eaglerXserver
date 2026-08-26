#!/usr/bin/env python3
"""Validate a release tag, select its channels, and check out its commit."""

import argparse
import os
import re
import subprocess
import sys


RELEASE_TAG_RE = re.compile(r"^v(?P<version>[0-9]+\.[0-9]+(?:\.[0-9]+)?)$")


def parse_release_tag(tag):
    match = RELEASE_TAG_RE.fullmatch(str(tag or ""))
    if not match:
        raise ValueError("release tag must match vMAJOR.MINOR or vMAJOR.MINOR.PATCH")
    version = match.group("version")
    parts = tuple(int(part) for part in version.split("."))
    return version, parts + ((-1,) if len(parts) == 2 else ())


def highest_release_tag(tags):
    valid = []
    for tag in tags:
        try:
            _, key = parse_release_tag(tag)
        except ValueError:
            continue
        valid.append((key, tag))
    if not valid:
        raise ValueError("repository has no valid release tags")
    return max(valid)[1]


def release_outputs(tag, tags, event_name, commit):
    version, _ = parse_release_tag(tag)
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise ValueError("release commit must be a full Git object ID")
    return {
        "release_tag": tag,
        "version": version,
        "commit": commit,
        "short_sha": commit[:12],
        "sha_tag": f"sha-{commit[:12]}",
        "promote_latest": str(event_name == "push" and tag == highest_release_tag(tags)).lower(),
    }


def git(*args):
    result = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError((result.stderr or result.stdout or "git command failed").strip())
    return result.stdout.strip()


def prepare_release(tag, event_name):
    parse_release_tag(tag)
    commit = git("rev-parse", "--verify", f"refs/tags/{tag}^{{commit}}")
    tags = git("tag", "--list").splitlines()
    outputs = release_outputs(tag, tags, event_name, commit)
    git("checkout", "--detach", "--quiet", f"refs/tags/{tag}")
    if git("rev-parse", "HEAD") != commit:
        raise RuntimeError("release checkout does not match the tag commit")
    return outputs


def write_outputs(outputs):
    lines = "".join(f"{key}={value}\n" for key, value in outputs.items())
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as stream:
            stream.write(lines)
    else:
        print(lines, end="")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--event", required=True, choices=("push", "workflow_dispatch"))
    args = parser.parse_args(argv)
    try:
        write_outputs(prepare_release(args.tag, args.event))
    except (RuntimeError, ValueError) as error:
        print(f"release preparation failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

# This directory holds sanitized fixture DATA for framework.sync unit
# tests (small, deliberately non-runnable sample repositories in various
# languages/frameworks for `RepositoryAnalyzer` to statically analyze) —
# not part of this framework's own test suite. None of these fixtures are
# meant to compile, run, or pass as real automation tests; some (e.g. the
# Robot Framework/.cs/.java samples) can't even be collected by pytest,
# and some Python ones are deliberately malformed. Tell pytest to never
# try to collect anything under here, mirroring
# examples/framework_sync/sample_legacy_repo/conftest.py's existing
# pattern for the same reason.
collect_ignore_glob = ["*"]

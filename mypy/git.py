"""Utilities for verifying git integrity."""

# Used also from setup.py, so don't pull in anything additional here (like mypy or typing):
import os
import pipes
import subprocess
import sys


def is_git_repo(dir: str) -> bool:
    """Is the passed directory version controlled with git?"""
    return os.path.exists(os.path.join(dir, ".git"))


def have_git() -> bool:
    """Can we run the git executable?"""
    try:
        subprocess.check_output(["git", "config", "-l"])
        return True
    except subprocess.CalledProcessError:
        return False


def run_in_dir(dir, command) -> bytes:
    """Convenience function: Run a command in a directory."""
    return subprocess.check_output("cd " + pipes.quote(dir) + "; " + command,
                                   shell=True)


def get_submodules(dir: str):
    """Return a list of all git top-level submodules in a given directory."""
    # It would be nicer to do
    # "git submodule foreach 'echo MODULE $name $path $sha1 $toplevel'"
    # but that wouldn't work on Windows.
    output = run_in_dir(dir, "git submodule status")
    for line in output.splitlines():
        status = line[0]
        sha5, name, *_ = line[1:].split(b" ")
        yield (status, sha5, name.decode(sys.getfilesystemencoding()))


def git_revision(dir: str) -> bytes:
    """Get the SHA-1 of the HEAD of a git repository."""
    return run_in_dir(dir, "git rev-parse HEAD").strip()


def is_dirty(dir: str) -> bool:
    """Check whether a git repository has uncommitted changes."""
    return run_in_dir(dir, "git status -uno --porcelain").strip() != b""


def has_extra_files(dir: str) -> bool:
    """Check whether a git repository has untracked files."""
    return run_in_dir(dir, "git clean --dry-run -d").strip() != b""


def warn_no_git_executable() -> None:
    print("Warning: Couldn't check git integrity. "
          "git executable not in path.", file=sys.stderr)


def warn_dirty(dir) -> None:
    print("Warning: git module '{}' has uncommitted changes.".format(dir),
          file=sys.stderr)


def warn_extra_files(dir) -> None:
    print("Warning: git module '{}' has untracked files.".format(dir),
          file=sys.stderr)


def error_submodule_not_initialized(name: str, dir: str) -> None:
    print("Submodule '{}' not initialized.".format(name), file=sys.stderr)
    print("Please run:", file=sys.stderr)
    print("  cd {}".format(pipes.quote(dir)), file=sys.stderr)
    print("  git submodule init {}".format(name), file=sys.stderr)


def error_submodule_not_updated(name: str, dir: str) -> None:
    print("Submodule '{}' not updated.".format(name), file=sys.stderr)
    print("Please run:", file=sys.stderr)
    print("  cd {}".format(pipes.quote(dir)), file=sys.stderr)
    print("  git submodule update {}".format(name), file=sys.stderr)


def verify_git_integrity_or_abort(datadir: str) -> None:
    """Verify the (submodule) integrity of a git repository.

    Potentially output warnings/errors (to stderr), and exit with status 1
    if we detected a severe problem.
    """

    if not is_git_repo(datadir):
        return
    if not have_git():
        warn_no_git_executable()
        return
    for _, revision, submodule in get_submodules(datadir):
        submodule_path = os.path.join(datadir, submodule)
        if not is_git_repo(submodule_path):
            error_submodule_not_initialized(submodule, datadir)
            sys.exit(1)
        elif revision != git_revision(submodule_path):
            error_submodule_not_updated(submodule, datadir)
            sys.exit(1)
        elif is_dirty(submodule_path):
            warn_dirty(submodule)
        elif has_extra_files(submodule_path):
            warn_extra_files(submodule)

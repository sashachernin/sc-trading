import json, subprocess, shutil
from pathlib import Path
from datetime import date
import pytest
from sqlalchemy import select
from app.models import Publication
from app.publishing.exporter import export
from app.publishing.git import deliver, GitTransport


class FakeBuildGit(GitTransport):
    def __init__(self, path):
        super().__init__(path)
        self.builds = 0

    def build(self):
        self.builds += 1
        m = json.loads((self.path / "frontend/public/data/manifest.json").read_text())
        assert m["label"] == "PAPER / SIMULATED"


def git(path, *args):
    return subprocess.check_output(
        ["git", *args], cwd=path, text=True, stderr=subprocess.PIPE
    ).strip()


def checkout(tmp_path):
    bare = tmp_path / "remote.git"
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(bare)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    work = tmp_path / "publisher"
    subprocess.run(
        ["git", "clone", str(bare), str(work)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    git(work, "config", "user.email", "fixture@example.invalid")
    git(work, "config", "user.name", "Synthetic publisher")
    (work / "frontend").mkdir()
    (work / "frontend/source.txt").write_text("developer source stays unchanged")
    git(work, "add", ".")
    git(work, "commit", "-m", "Initial developer source")
    git(work, "push", "origin", "main")
    return work, bare


def test_git_delivery_exact_paths_retry_and_noop(lab, tmp_path):
    lab.open(date(2026, 9, 14))
    lab.close(date(2026, 9, 14))
    lab.meeting(date(2026, 9, 20))
    p = export(lab)
    work, bare = checkout(tmp_path)
    lab.settings.publisher_checkout = str(work)
    lab.settings.private_access_verified = True
    t = FakeBuildGit(work)
    status = deliver(lab, p, t)
    assert status == "PUSHED_UNVERIFIED"
    assert t.builds == 1
    assert (
        work / "frontend/source.txt"
    ).read_text() == "developer source stays unchanged"
    paths = git(work, "show", "--format=", "--name-only", "HEAD").splitlines()
    assert all(
        x.startswith(
            (
                "frontend/public/data/",
                "frontend/public/transcripts/",
                "frontend/content/meetings/",
            )
        )
        for x in paths
    )
    count = git(work, "rev-list", "--count", "HEAD")
    assert deliver(lab, p, t) == "PUSHED_UNVERIFIED"
    assert git(work, "rev-list", "--count", "HEAD") == count
    assert git(work, "rev-parse", "HEAD") == git(bare, "rev-parse", "main")


def test_private_access_gate(lab, tmp_path):
    p = export(lab)
    work, _ = checkout(tmp_path)
    lab.settings.publisher_checkout = str(work)
    with pytest.raises(ValueError, match="private protection"):
        deliver(lab, p, FakeBuildGit(work))


def test_dirty_checkout_refused(lab, tmp_path):
    p = export(lab)
    work, _ = checkout(tmp_path)
    lab.settings.publisher_checkout = str(work)
    lab.settings.private_access_verified = True
    (work / "frontend/source.txt").write_text("uncommitted developer change")
    with pytest.raises(ValueError, match="clean"):
        deliver(lab, p, FakeBuildGit(work))

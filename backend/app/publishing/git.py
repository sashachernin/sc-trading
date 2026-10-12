import fcntl, json, shutil, subprocess, time
from pathlib import Path
import httpx
from app.config import ROOT
from app.models import Publication
from app.publishing.exporter import ALLOWED


class GitTransport:
    def __init__(self, path):
        self.path = Path(path)

    def run(self, *args):
        return subprocess.check_output(
            ["git", *args],
            cwd=self.path,
            text=True,
            stderr=subprocess.PIPE,
            timeout=120,
        ).strip()

    def build(self):
        subprocess.run(
            ["npm", "ci"],
            cwd=self.path / "frontend",
            check=True,
            timeout=180,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["npm", "run", "build"],
            cwd=self.path / "frontend",
            check=True,
            timeout=180,
            stdout=subprocess.DEVNULL,
        )


def _deliver(lab, publication, transport=None):
    cfg = lab.settings
    if cfg.site_visibility == "private" and not cfg.private_access_verified:
        raise ValueError(
            "Publication blocked: verify private protection on production, deployment URLs, JSON and downloads"
        )
    if not cfg.publisher_checkout:
        raise ValueError(
            "PUBLISHER_CHECKOUT is required; use --dry-run for local export"
        )
    checkout = Path(cfg.publisher_checkout).resolve()
    if checkout == ROOT.resolve() or ROOT.resolve() in checkout.parents:
        raise ValueError(
            "Publisher checkout must be independent of engine installation"
        )
    t = transport or GitTransport(checkout)
    lock = cfg.state_dir / "publisher.lock"
    with lock.open("w") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        with lab.sessions() as s:
            pub = s.get(Publication, publication.id)
            if pub.status in ("PUSHED_UNVERIFIED", "DEPLOYED", "SUPERSEDED"):
                return pub.status
            frozen = Path(pub.data["export_directory"])
            revision = pub.revision
        if t.run("status", "--porcelain"):
            raise ValueError("Publisher checkout must be clean")
        if t.run("branch", "--show-current") != cfg.publish_branch:
            raise ValueError("Publisher branch mismatch")
        for attempt in range(3):
            t.run("fetch", "origin", cfg.publish_branch)
            # Fast-forward only; preserve developer commits and protections.
            t.run("merge", "--ff-only", f"origin/{cfg.publish_branch}")
            current = checkout / "frontend/public/data/manifest.json"
            if current.exists():
                remote = json.loads(current.read_text())
                if (
                    remote.get("experiment_id") == cfg.experiment_id
                    and remote.get("source_revision", -1) > revision
                ):
                    with lab.sessions.begin() as s:
                        s.get(Publication, publication.id).status = "SUPERSEDED"
                    return "SUPERSEDED"
            for prefix in ALLOWED:
                source = frozen / prefix
                target = checkout / prefix
                if target.exists():
                    shutil.rmtree(target)
                if source.exists():
                    shutil.copytree(source, target)
            t.run("add", "--", *ALLOWED)
            paths = t.run("diff", "--cached", "--name-only").splitlines()
            if not paths:
                commit = t.run("rev-parse", "HEAD")
                t.run("push", "origin", cfg.publish_branch)
                break
            if any(not p.startswith(ALLOWED) for p in paths):
                raise ValueError("Publisher staged nonallowlisted path")
            t.build()
            t.run("commit", "-m", f"Publish PAPER snapshot {publication.id}")
            commit = t.run("rev-parse", "HEAD")
            with lab.sessions.begin() as s:
                p = s.get(Publication, publication.id)
                p.status = "COMMITTED"
                p.data = dict(
                    p.data, git_commit=commit, changed_paths=paths, attempt=attempt + 1
                )
            try:
                t.run("push", "origin", cfg.publish_branch)
                break
            except subprocess.CalledProcessError:
                # Reset only the unpublished publisher commit; replay on the new remote head.
                # Refuse to discard an unexpected developer commit in this dedicated checkout.
                if (
                    t.run("log", "-1", "--format=%s")
                    != f"Publish PAPER snapshot {publication.id}"
                ):
                    raise
                t.run("reset", "--hard", "HEAD~1")
                if attempt == 2:
                    raise
        status = "PUSHED_UNVERIFIED"
        if cfg.deployment_url:
            for _ in range(3):
                try:
                    response = httpx.get(
                        cfg.deployment_url.rstrip("/") + "/data/manifest.json",
                        timeout=10,
                        follow_redirects=False,
                    )
                    if (
                        response.status_code == 200
                        and response.json().get("snapshot_id") == publication.id
                    ):
                        status = "DEPLOYED"
                        break
                except (httpx.HTTPError, ValueError):
                    pass
                time.sleep(5)
        with lab.sessions.begin() as s:
            p = s.get(Publication, publication.id)
            p.status = status
            p.data = dict(p.data, git_commit=commit)
        return status


def deliver(lab, publication, transport=None):
    try:
        return _deliver(lab, publication, transport)
    except Exception as exc:
        with lab.sessions.begin() as s:
            p = s.get(Publication, publication.id)
            if p and p.status not in ("DEPLOYED", "SUPERSEDED", "PUSHED_UNVERIFIED"):
                p.status = "FAILED"
                p.data = dict(p.data, failure_category=type(exc).__name__)
        raise

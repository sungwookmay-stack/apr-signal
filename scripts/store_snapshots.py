"""Bounded, non-forcing publication of validated data; never invokes collectors."""
import subprocess


def git(*args, check=True):
    return subprocess.run(['git', *args], check=check, text=True, capture_output=True)


def lines(*args):
    return set(filter(None, git(*args).stdout.splitlines()))


def safe_rebase(local_paths, remote_paths):
    # No retry across code/schema changes or concurrent writes to the same file.
    return bool(remote_paths) and not local_paths.intersection(remote_paths) and all(
        p.startswith(('data/', 'state/', 'docs/')) for p in remote_paths)


def main():
    git('config', 'user.name', 'github-actions[bot]')
    git('config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    base = git('rev-parse', 'HEAD').stdout.strip()
    git('add', 'data/', 'state/')
    local = lines('diff', '--cached', '--name-only')
    if not local:
        print('No data changes to publish.')
        return
    if any(not p.startswith(('data/', 'state/')) for p in local):
        raise RuntimeError('Unexpected staged path; refusing publication')
    git('commit', '-m', 'data: refresh APR public observations [skip ci]')
    if git('push', 'origin', 'HEAD:main', check=False).returncode == 0:
        print('Validated snapshots published.')
        return
    git('fetch', '--no-tags', 'origin', 'main')
    remote = git('rev-parse', 'FETCH_HEAD').stdout.strip()
    # Shallow checkout must still contain the original base in remote ancestry.
    if git('merge-base', '--is-ancestor', base, remote, check=False).returncode:
        raise RuntimeError('Remote ancestry not verified; keep recovery artifacts, no retry')
    changed = lines('diff', '--name-only', base, remote)
    if not safe_rebase(local, changed):
        raise RuntimeError('Concurrent data or code change; keep recovery artifacts, no overwrite')
    if git('rebase', '--onto', remote, base, check=False).returncode:
        git('rebase', '--abort', check=False)
        raise RuntimeError('Rebase failed; no publication retry')
    if git('push', 'origin', 'HEAD:main', check=False).returncode:
        raise RuntimeError('Publication raced again or was denied; bounded retry exhausted')
    print('Validated snapshots published after one disjoint-data rebase.')


if __name__ == '__main__':
    main()

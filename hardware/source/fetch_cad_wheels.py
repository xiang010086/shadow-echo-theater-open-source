"""Fetch verified official wheels into a temporary environment, using resumable ranges."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import tempfile
import time
import urllib.request

DEST = Path(tempfile.gettempdir()) / 'shadow-stage-cad-20261104' / 'wheels'
DEST.mkdir(parents=True, exist_ok=True)
PACKAGES = [('cadquery', '2.8.0'), ('cadquery-ocp', '7.9.3.1.1'),
            ('cadquery-ocp-proxy', '7.9.3.1.1'), ('trimesh', None), ('ezdxf', None),
            ('multimethod', '1.12'), ('nlopt', None), ('casadi', None),
            ('runtype', None), ('vtk', '9.6.2')]


def metadata(package):
    name, version = package
    endpoint = f'https://pypi.org/pypi/{name}/' + (f'{version}/json' if version else 'json')
    with urllib.request.urlopen(endpoint, timeout=60) as response:
        data = json.load(response)
    compatible = [f for f in data['urls'] if f['filename'].endswith('.whl') and
                  ('cp313-cp313-win_amd64' in f['filename'] or
                   'cp311-abi3-win_amd64' in f['filename'] or
                   'py3-none-any' in f['filename'] or 'py2.py3-none-any' in f['filename'])]
    compatible.sort(key=lambda f: ('cp313-cp313-win_amd64' not in f['filename'], f['filename']))
    if not compatible:
        raise RuntimeError((name, [f['filename'] for f in compatible]))
    return compatible[0]


def fetch_chunk(file, start, end):
    chunk = DEST / (file['filename'] + f'.{start}.part')
    count = end - start + 1
    if chunk.exists() and chunk.stat().st_size == count:
        return chunk
    error = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(file['url'], headers={'Range': f'bytes={start}-{end}'})
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 206:
                    raise RuntimeError('Expected an HTTP range response')
                payload = response.read()
            if len(payload) != count:
                raise RuntimeError(f'Wrong range length: {len(payload)} / {count}')
            chunk.write_bytes(payload)
            return chunk
        except Exception as exc:
            error = exc
            time.sleep(min(attempt + 1, 4))
    raise RuntimeError((file['filename'], start)) from error


def main():
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        files = list(pool.map(metadata, PACKAGES))
    jobs = []
    for file in files:
        path = DEST / file['filename']
        if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == file['digests']['sha256']:
            print('cached', file['filename'], flush=True)
            continue
        print('fetch', file['filename'], file['size'], flush=True)
        for start in range(0, file['size'], 1024 * 1024):
            jobs.append((file, start, min(start + 1024 * 1024 - 1, file['size'] - 1)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
        pending = [pool.submit(fetch_chunk, *job) for job in jobs]
        for index, future in enumerate(concurrent.futures.as_completed(pending), 1):
            future.result()
            if index % 10 == 0 or index == len(pending):
                print('chunks', index, '/', len(pending), flush=True)
    for file in files:
        path = DEST / file['filename']
        if not path.exists():
            with path.open('wb') as output:
                for start in range(0, file['size'], 1024 * 1024):
                    output.write((DEST / (file['filename'] + f'.{start}.part')).read_bytes())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == file['digests']['sha256'], path
    print('verified', len(files), 'wheels in', DEST, flush=True)


if __name__ == '__main__':
    main()

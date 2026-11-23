"""Explicit file fingerprints for saved figures; no automatic code execution."""
import base64
import hashlib
from importlib.metadata import version
import os
from pathlib import Path
import platform


def _hash_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


class FigureRecipe:
    """Capture a script and declared input files before reading/plotting them.

    Fingerprints detect changed files; declarations do not prove that the plotted
    data came from them. command is recorded as arguments and never executed.
    """
    def __init__(self, script_path, *, inputs=(), asset_id, revision=1, command=None):
        if not isinstance(asset_id, str) or not asset_id.strip() or not any(c in asset_id for c in '.:'):
            raise ValueError('asset_id must be a nonempty namespaced ID, such as study.figure1')
        if type(revision) is not int or revision < 1:
            raise ValueError('revision must be a positive integer')
        if isinstance(inputs, (str, Path)):
            raise TypeError('inputs must be a sequence of file paths')
        if command is not None:
            if not isinstance(command, (list, tuple)) or not command or any(not isinstance(x, str) or not x for x in command):
                raise ValueError('command must be a nonempty argument list; shell strings are not accepted')
        self.asset_id = asset_id
        self.revision = revision
        self.command = tuple(command) if command is not None else None
        self.working_directory = Path.cwd().resolve()
        files = []
        for role, file in [('script', script_path), *(('input', path) for path in inputs)]:
            path = Path(file).absolute()
            if not path.is_file():
                raise ValueError(f'Expected a file: {path}')
            if not any(previous[1] == path for previous in files):
                if role == 'script':
                    content = path.read_bytes()
                    digest = hashlib.sha256(content).hexdigest()
                    self._script_snapshot = {'filename': path.name, 'encoding': 'base64',
                                             'content': base64.b64encode(content).decode('ascii'),
                                             'sha256': digest}
                else:
                    digest = _hash_file(path)
                files.append((role, path, digest))
        self._files = tuple(files)
        self.versions = {'python': platform.python_version(), **{
            name: version(name) for name in ('cellstyle', 'matplotlib', 'numpy', 'pandas')}}

    def verify(self):
        for _, path, expected in self._files:
            if not path.is_file() or _hash_file(path) != expected:
                raise ValueError(f'Tracked file changed or disappeared: {path}. Reload inputs and create a new recipe.')

    def to_record(self, base_dir):
        self.verify()
        return {'schema': 'cellstyle-recipe-1', 'asset_id': self.asset_id, 'revision': self.revision,
                'script_snapshot': dict(self._script_snapshot),
                'files': [{'role': role, 'path': os.path.relpath(path, base_dir), 'sha256': digest}
                          for role, path, digest in self._files],
                'command': list(self.command) if self.command is not None else None,
                'working_directory': os.path.relpath(self.working_directory, base_dir),
                'versions': dict(self.versions),
                'scope': 'Declared script/input bytes only; data usage and complete environment are not authenticated.'}


def _validate_recipe(recipe, *, verify=True):
    if recipe is not None:
        if not isinstance(recipe, FigureRecipe):
            raise TypeError('recipe must be a FigureRecipe')
        if verify:
            recipe.verify()


def source_freshness(record, base_dir):
    result = {'status': 'UNKNOWN', 'changed_files': [], 'missing_files': []}
    if not isinstance(record, dict) or record.get('schema') != 'cellstyle-recipe-1':
        return result
    files = record.get('files')
    if not isinstance(files, list) or not files or not any(f.get('role') == 'script' for f in files if isinstance(f, dict)):
        raise ValueError('Invalid recipe file records')
    for file in files:
        if not isinstance(file, dict) or not isinstance(file.get('path'), str) or not isinstance(file.get('sha256'), str):
            raise ValueError('Invalid recipe file record')
        path = Path(base_dir) / file['path']
        try:
            actual = _hash_file(path)
        except (FileNotFoundError, IsADirectoryError):
            result['missing_files'].append(file['path'])
            continue
        except PermissionError:
            result.setdefault('unreadable_files', []).append(file['path'])
            continue
        if actual != file['sha256']:
            result['changed_files'].append(file['path'])
    result['status'] = ('STALE' if result['changed_files'] or result['missing_files'] else
                        'UNKNOWN' if result.get('unreadable_files') else 'CURRENT')
    return result

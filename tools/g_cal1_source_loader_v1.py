"""Source-only bootstrap for the versioned G-CAL1 authority path.

Launch this .py file directly, or execute its explicitly verified source bytes.
It loads no repository module through importlib, sys.path, sys.modules or pyc.
The CLI loads/attests code only: no candidate, activation, grant or provider API.
"""
from __future__ import annotations

import ast
import builtins
import hashlib
import json
from pathlib import Path
import re
import sys
import types

VERSION = 'g-cal1.source-loader.v1'
_ROOT_CODE = sys._getframe().f_code
_SELF = Path(__file__).absolute()
_IMPORT = builtins.__import__
_COMPILE = builtins.compile
_CONTEXT = '__g_cal1_verified_source_context__'
ROOTS = ('g_cal1_live_v4', 'g_cal1_authority_v2', 'g_cal1_ollama_transport', 'g_cal1_source_loader_v1')


class SourceVerificationError(Exception):
    pass


def _check(condition, message):
    if not condition:
        raise SourceVerificationError(message)


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _path(root, relative):
    _check(type(relative) is str and re.fullmatch(r'tools/[a-z][a-z0-9_]*\.py', relative) is not None,
           'noncanonical executable component')
    path = root / relative
    for part in (path, *path.parents):
        # Windows junctions/reparse aliases are not necessarily is_symlink().
        _check(not part.is_symlink() and not (getattr(part.lstat(), 'st_file_attributes', 0) & 0x400),
               'executable path alias: ' + str(part))
    _check(path.is_file() and path.resolve() == path.absolute(), 'executable origin: ' + relative)
    return path


def _buffers(root):
    root = Path(root).absolute()
    _check(root == root.resolve(), 'repository root alias')
    pending, found = list(ROOTS), {}
    while pending:
        name = pending.pop()
        relative = 'tools/' + name + '.py'
        if relative in found:
            continue
        raw = _path(root, relative).read_bytes()
        found[relative] = raw
        for node in ast.walk(ast.parse(raw, filename=str(root / relative))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name.split('.')[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split('.')[0]]
            pending.extend(n for n in names if (root / 'tools' / (n + '.py')).is_file())
    return dict(sorted(found.items()))


def inventory(root=None):
    """Discovery is not authority. A future reviewed binding supplies expectations."""
    return {p: _sha(raw) for p, raw in _buffers(root or _SELF.parent.parent).items()}


class VerifiedRuntime:
    def __init__(self, expected, *, root=None):
        self.root = Path(root or _SELF.parent.parent).absolute()
        _check(type(expected) is dict and all(type(p) is str and type(h) is str and
               re.fullmatch('[0-9a-f]{64}', h) for p, h in expected.items()), 'executable inventory schema')
        # Snapshot every source, validate the COMPLETE closure before any repository
        # execution, then compile the very same immutable buffers. No second read
        # supplies code to compile and no cache/loaded-module lookup is consulted.
        buffers = _buffers(self.root)
        self.expected = dict(expected)
        _check({p: _sha(raw) for p, raw in buffers.items()} == self.expected, 'executable source hash/closure mismatch')
        own = buffers['tools/g_cal1_source_loader_v1.py']
        _check(_SELF.resolve() == _SELF and Path(_ROOT_CODE.co_filename).absolute() == _SELF and _SELF.read_bytes() == own and
               _ROOT_CODE == _COMPILE(own, str(_SELF), 'exec', dont_inherit=True),
               'bootstrap must execute the bound loader source, not stale preloaded/cached code')
        self._codes = {Path(p).stem: _COMPILE(raw, str(self.root / p), 'exec', dont_inherit=True)
                       for p, raw in buffers.items()}
        self._modules, self._executed = {}, set()
        self._builtins = dict(vars(builtins), __import__=self._import)
        for name in self._codes:
            self._load(name)
        self.verify(self.expected)

    def _import(self, name, globals=None, locals=None, fromlist=(), level=0):
        first = name.split('.')[0]
        if first in self._codes:
            _check(level == 0 and name == first, 'unbound repository submodule import')
            return self._load(first)
        _check(not (self.root / 'tools' / (first + '.py')).exists(), 'dependency outside verified closure')
        _check(not first.startswith(('g_cal1', 'g_extract1', 'g_route')), 'unbound repository dependency name')
        return _IMPORT(name, globals, locals, fromlist, level)

    def _load(self, name):
        if name in self._modules:
            return self._modules[name]
        _check(name in self._codes, 'unbound executable module')
        module = types.ModuleType(name)
        module.__dict__.update(__file__=str(self.root / 'tools' / (name + '.py')), __package__='',
                               __builtins__=self._builtins)
        module.__dict__[_CONTEXT] = self
        self._modules[name] = module
        try:
            exec(self._codes[name], module.__dict__)
        except BaseException:
            self._modules.pop(name, None)
            raise
        self._executed.add(name)
        return module

    def require_owner(self, owner):
        _check(type(owner) is dict and owner.get('__name__') in self._modules and
               self._modules[owner['__name__']].__dict__ is owner and owner.get(_CONTEXT) is self,
               'ordinary/preloaded module is not verified-source authority')
        return self

    def verify(self, expected, owner=None):
        if owner is not None:
            self.require_owner(owner)
        _check(type(expected) is dict and expected == self.expected == inventory(self.root),
               'bound executable source changed')
        _check(self._executed == set(self._codes), 'incomplete verified module graph')
        for name, module in self._modules.items():
            _check(module.__dict__.get(_CONTEXT) is self and
                   module.__file__ == str(self.root / 'tools' / (name + '.py')) and
                   module.__dict__.get('__builtins__') is self._builtins,
                   'verified module origin/context drift')

    def module(self, name):
        self.verify(self.expected)
        _check(name in self._modules, 'module not bound')
        return self._modules[name]


def verified_context(owner):
    context = owner.get(_CONTEXT)
    _check(context is not None, 'source-only bootstrap required for authority')
    return context.require_owner(owner)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Load verified code only; no provider or execution authority.')
    parser.add_argument('--inventory-file', required=True)
    parser.add_argument('--inventory-sha256', required=True)
    args = parser.parse_args()
    raw = Path(args.inventory_file).read_bytes()
    _check(_sha(raw) == args.inventory_sha256, 'reviewed inventory bytes mismatch')
    global VERIFIED_RUNTIME
    VERIFIED_RUNTIME = VerifiedRuntime(json.loads(raw))
    print(json.dumps({'verified_source_count': len(VERIFIED_RUNTIME.expected), 'provider_calls': 0,
                      'execution_authorized': False, 'authority_created': False}, sort_keys=True))


if __name__ == '__main__':
    main()

"""Source-only bootstrap for the versioned G-CAL1 authority path.

Launch this .py file directly, or execute its explicitly verified source bytes.
It loads no repository module through importlib, sys.path, sys.modules or pyc.
The CLI loads/attests code only: no candidate, activation, grant or provider API.
"""
import sys
import _imp


class SourceVerificationError(Exception):
    pass


# CPython's initialized builtin/frozen import machinery is a runtime trust root.
# Establish it before importing any ordinary Python source, including our own
# standard-library dependencies. No ambient path is a standard-library root.
_BOOTSTRAP = sys.modules['_frozen_importlib']
_EXTERNAL = sys.modules['_frozen_importlib_external']
_CORE_OS = sys.modules['os']
_RAW_IMPORT, _RAW_COMPILE = __import__, compile
for _core in (_BOOTSTRAP, _EXTERNAL, _CORE_OS, _CORE_OS.path):
    if type(_core) is not type(sys) or _core.__spec__.origin != 'frozen':
        raise SourceVerificationError('unsupported/untrusted CPython bootstrap module')


class _TrustedSourceLoader(_EXTERNAL.SourceFileLoader):
    def get_code(self, fullname):
        # Even an external pycache_prefix cannot substitute stdlib source code.
        return _RAW_COMPILE(self.get_data(self.path), self.path, 'exec', dont_inherit=True)


class _StandardLibraryBoundary:
    def __init__(self):
        self.path = _CORE_OS.path
        library = getattr(sys, '_stdlib_dir', None)
        if not library:
            raise SourceVerificationError('CPython standard-library root unavailable')
        expected = self.path.join(sys.base_prefix, 'Lib') if sys.platform == 'win32' else \
            self.path.join(sys.base_prefix, 'lib', 'python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor))
        if self.normal(library) != self.normal(expected):
            raise SourceVerificationError('standard-library root is not the interpreter library')
        roots = [self.normal(library)]
        extension = self.path.join(sys.base_exec_prefix, 'DLLs') if sys.platform == 'win32' else \
            self.path.join(library, 'lib-dynload')
        if self.path.isdir(extension):
            roots.append(self.normal(extension))
        self.roots = tuple(roots)
        self.names = sys.stdlib_module_names
        self.finders = {}
        self.identities = {}

    def normal(self, path):
        return self.path.normcase(self.path.realpath(path))

    def origin(self, path):
        if type(path) is not str:
            raise SourceVerificationError('trusted module origin missing')
        normal = self.normal(path)
        if any(p in ('site-packages', 'dist-packages') for p in normal.replace('\\', '/').split('/')) or \
                not any(normal == root or normal.startswith(root + self.path.sep) for root in self.roots):
            raise SourceVerificationError('module outside interpreter standard-library roots: ' + path)
        return normal

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] not in self.names:
            # True stdlib source may probe optional implementations (e.g. Jython)
            # in an ImportError guard. Never resolve them, but preserve that guard.
            raise ModuleNotFoundError('non-standard-library external dependency: ' + fullname)
        for finder in (_BOOTSTRAP.BuiltinImporter, _BOOTSTRAP.FrozenImporter):
            spec = finder.find_spec(fullname)
            if spec is not None:
                return spec
        for directory in self.roots if path is None else path:
            directory = self.origin(directory)
            if directory not in self.finders:
                self.finders[directory] = _EXTERNAL.FileFinder(directory,
                    (_TrustedSourceLoader, _EXTERNAL.SOURCE_SUFFIXES),
                    (_EXTERNAL.ExtensionFileLoader, _EXTERNAL.EXTENSION_SUFFIXES))
            spec = self.finders[directory].find_spec(fullname)
            if spec is not None:
                self.origin(spec.origin)
                return spec
        return None

    def validate_cache(self):
        aliases = {'os.path': ('ntpath', 'posixpath'), 'importlib._bootstrap': ('_frozen_importlib',),
                   'importlib._bootstrap_external': ('_frozen_importlib_external',)}
        for name, module in tuple(sys.modules.items()):
            if name.split('.')[0] not in self.names or module is None:
                continue
            # These deprecated typing aliases are generated classes, not modules.
            if name in ('typing.io', 'typing.re') and isinstance(module, type) and \
                    sys.modules.get('typing').__dict__.get(name.split('.')[1]) is module:
                continue
            if type(module) is not type(sys):
                raise SourceVerificationError('untrusted preloaded standard-library object: ' + name)
            spec = module.__dict__.get('__spec__')
            if type(spec) is not _BOOTSTRAP.ModuleSpec or \
                    spec.name not in (name, *aliases.get(name, ())):
                raise SourceVerificationError('untrusted preloaded standard-library identity: ' + name)
            functions = tuple(v for v in module.__dict__.values() if type(v) is type(lambda: None))
            identity = (id(module), id(spec), spec.name, spec.origin, module.__dict__.get('__file__'),
                        tuple(module.__dict__.get('__path__', ())),
                        tuple((id(v.__code__), v.__code__.co_filename, v.__module__) for v in functions))
            if self.identities.get(name) == identity:
                continue
            if spec.origin == 'built-in':
                valid = _BOOTSTRAP.BuiltinImporter.find_spec(spec.name) is not None
            elif spec.origin == 'frozen':
                valid = _BOOTSTRAP.FrozenImporter.find_spec(spec.name) is not None
            else:
                valid = self.origin(spec.origin) == self.origin(module.__dict__.get('__file__'))
            if not valid:
                raise SourceVerificationError('preloaded module is not a builtin/frozen/stdlib component: ' + name)
            for directory in module.__dict__.get('__path__', ()):
                self.origin(directory)
            # A claimed legitimate __file__ must not hide external Python code.
            for value in functions:
                if value.__module__ == spec.name:
                    filename = value.__code__.co_filename
                    if not filename.startswith('<frozen ') and filename != '<string>':
                        self.origin(filename)
            self.identities[name] = identity

    def __call__(self, name, globals=None, locals=None, fromlist=(), level=0):
        # Restrict nested imports too, including imports inside true stdlib code.
        # Existing legitimate modules retain identity; foreign preloaded objects
        # fail before import execution, rather than being adopted or rewritten.
        if not level and name.split('.')[0] not in self.names:
            raise SourceVerificationError('non-standard-library external dependency: ' + name)
        _imp.acquire_lock()
        old = sys.path, sys.meta_path, sys.path_hooks, sys.path_importer_cache
        try:
            self.validate_cache()
            sys.path, sys.meta_path, sys.path_hooks, sys.path_importer_cache = list(self.roots), [self], [], {}
            result = _RAW_IMPORT(name, globals, locals, fromlist, level)
            self.validate_cache()
            return result
        finally:
            sys.path, sys.meta_path, sys.path_hooks, sys.path_importer_cache = old
            _imp.release_lock()


_STDLIB = _StandardLibraryBoundary()
ast = _STDLIB('ast')
builtins = _STDLIB('builtins')
hashlib = _STDLIB('hashlib')
json = _STDLIB('json')
Path = _STDLIB('pathlib', fromlist=('Path',)).Path
re = _STDLIB('re')
types = _STDLIB('types')

VERSION = 'g-cal1.source-loader.v1'
_ROOT_CODE = sys._getframe().f_code
_SELF = Path(__file__).absolute()
_IMPORT = _STDLIB
_COMPILE = builtins.compile
_CONTEXT = '__g_cal1_verified_source_context__'
ROOTS = ('g_cal1_live_v4', 'g_cal1_authority_v2', 'g_cal1_ollama_transport', 'g_cal1_source_loader_v1')


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
    argparse = _STDLIB('argparse')
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

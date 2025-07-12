import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path

from fragments import transpiler


class PyfLoader(importlib.abc.Loader):
    def __init__(self, path: Path):
        self.path = path

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        source = self.path.read_text()
        transpiled = transpiler.transpile(source)
        code = compile(transpiled, str(self.path), "exec")
        exec(code, module.__dict__)


class PyfFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path, target=None):
        search_paths = sys.path if path is None else path
        module_name = fullname.rsplit(".", 1)[-1]

        for directory in search_paths:
            candidate = Path(directory) / (module_name + ".pyf")

            if not candidate.exists():
                continue

            loader = PyfLoader(candidate)
            return importlib.util.spec_from_file_location(fullname, candidate, loader=loader)
        return None


def init():
    sys.meta_path.insert(0, PyfFinder())

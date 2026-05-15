import importlib.abc
import importlib.machinery
import sys

from fragments import transpiler


class TranspilingLoader(importlib.machinery.SourceFileLoader):
    def get_data(self, path: str) -> bytes:
        if not path.endswith(".py"):
            return super().get_data(path)

        source = super().get_data(path).decode("utf-8")

        if "<>" not in source:
            return source.encode("utf-8")

        transpiled = transpiler.transpile(source)
        return transpiled.encode("utf-8")


class TranspilingFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname: str, path, target=None):
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or not isinstance(spec.loader, importlib.machinery.SourceFileLoader):
            return None
        assert spec.origin is not None
        spec.loader = TranspilingLoader(fullname, spec.origin)
        return spec


sys.meta_path.insert(0, TranspilingFinder())

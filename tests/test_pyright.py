"""Integration tests that talk directly to basedpyright."""
import asyncio
import os
import sys
import tempfile
import textwrap
from pathlib import Path

from fragments.lsp.pyright import PyrightClient

_PROJECT_ROOT = str(Path(__file__).parent.parent)


def _workspace_config(section: str) -> object:
    if section == "python":
        return {"pythonPath": sys.executable, "defaultInterpreterPath": sys.executable}
    if section in ("basedpyright", "basedpyright.analysis", "python.analysis"):
        return {"extraPaths": [_PROJECT_ROOT]}
    return None


async def _run(source: str, workspace: str | None = None, timeout: float = 15.0) -> list[dict]:
    """Start basedpyright, open a virtual file, and return the first publishDiagnostics."""
    if workspace is None:
        workspace = tempfile.mkdtemp()

    diagnostics: list[dict] = []
    received = asyncio.Event()

    async def on_request(msg: dict) -> object:
        if msg["method"] == "workspace/configuration":
            return [_workspace_config(item.get("section", "")) for item in msg["params"]["items"]]
        return None

    def on_notification(msg: dict) -> None:
        if msg.get("method") == "textDocument/publishDiagnostics":
            diagnostics.clear()
            diagnostics.extend(msg["params"]["diagnostics"])
            received.set()

    client = PyrightClient(on_notification, on_request)
    await client.start()
    await client.request(
        "initialize",
        {
            "processId": None,
            "rootUri": f"file://{workspace}",
            "workspaceFolders": [{"uri": f"file://{workspace}", "name": "test"}],
            "capabilities": {"workspace": {"configuration": True}},
        },
    )
    client.notify("initialized", {})

    uri = f"file://{workspace}/__test__.py"
    client.notify(
        "textDocument/didOpen",
        {"textDocument": {"uri": uri, "languageId": "python", "version": 1, "text": source}},
    )

    try:
        await asyncio.wait_for(received.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        pass

    client.notify("textDocument/didClose", {"textDocument": {"uri": uri}})
    return diagnostics


def _resolution_errors(diagnostics: list[dict]) -> list[str]:
    skip = {"is not accessed", "reportUnusedImport"}
    return [d["message"] for d in diagnostics if not any(p in d["message"] for p in skip)]


def run(source: str, workspace: str | None = None) -> list[dict]:
    return asyncio.run(_run(textwrap.dedent(source).strip(), workspace=workspace))


def test_no_errors_for_clean_file():
    assert _resolution_errors(run("x: int = 1\n")) == []


def test_fastapi_imports_resolve():
    diags = run("""
        from fastapi import FastAPI, APIRouter
        from fastapi.responses import HTMLResponse
    """)
    assert _resolution_errors(diags) == [], _resolution_errors(diags)


def test_fastapi_instantiation():
    diags = run("""
        from fastapi import FastAPI
        app = FastAPI()
    """)
    assert _resolution_errors(diags) == [], _resolution_errors(diags)


def test_fastapi_with_fragments_prefix():
    diags = run("""
        from fragments.html.elements import el, sequence
        from fastapi import FastAPI
        app = FastAPI()
    """)
    assert _resolution_errors(diags) == [], _resolution_errors(diags)


def test_local_import_with_fragment_syntax():
    workspace = tempfile.mkdtemp()
    with open(os.path.join(workspace, "routes.py"), "w") as f:
        f.write("from fastapi import APIRouter\nrouter = APIRouter()\ndef view():\n    return <>\n        <div>hi</div>\n    </>\n")
    diags = run("""
        from fastapi import FastAPI
        from routes import router
        app = FastAPI()
        app.include_router(router)
    """, workspace=workspace)
    assert _resolution_errors(diags) == [], _resolution_errors(diags)


def test_type_error_is_reported():
    diags = run('x: int = "not an int"\n')
    assert any(diags), "expected a type error diagnostic"


def test_fragments_import_prefix_resolves():
    diags = run("from fragments.html.elements import el, sequence\n")
    assert _resolution_errors(diags) == [], _resolution_errors(diags)

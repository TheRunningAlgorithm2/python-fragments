# Installation

## Install the package

``` bash
pip install python-fragments
```

### Optional Extras

To install the language server:

``` bash
pip install python-fragments[lsp]
```

To install the [Black integration](../integrations/formatting/black.md) for code formatting:

``` bash
pip install python-fragments[black]
```

To install the development and documentation dependencies:

``` bash
pip install python-fragments[dev,docs]
```

## Register the loader

Add this import at your application's entry point, before any modules that contain fragments are imported:

``` python
from fragments import loader
from my_components import fragment_component
```

You may want to include an `# isort: skip` comment to make sure this import isn't automatically moved.

That's all. Any `.py` file containing `<>` will be transpiled automatically at import time.

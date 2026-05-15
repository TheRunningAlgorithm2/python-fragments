# Installation

## Install the package

```bash
pip install python-fragments
```

## Register the loader

Add this import at your application's entry point, before any modules that contain fragments are imported:

```python
from fragments import loader
from my_components import fragment_component
```

You may want to include an `# isort: ignore` comment to make sure this import isn't auomatically moved.

That's all. Any `.py` file containing `<>` will be transpiled automatically at import time.

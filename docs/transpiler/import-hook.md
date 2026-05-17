# Import Hook

When you import `fragments.loader`, it installs a custom `MetaPathFinder` on `sys.meta_path`. From that point on, every `.py` file that Python imports is intercepted. If the file contains `<>`, the source is transpiled before it reaches the interpreter. Files without `<>` pass through unchanged.

```python
from fragments import loader  # installs the hook — must come first

from fastapi import FastAPI   # any fragment-containing module imported after
from routes import router     # this line is now transpiled automatically
```

The hook operates on source text, so nothing is written to disk — your `.py` files are never modified.

"""One bounded LF input template; solvers always receive isolated objects."""
import copy
import hashlib
import threading
from pathlib import Path


class ModelCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._key = None
        self._template = None

    def load(self, path, loader):
        path = Path(path).resolve()
        # Only standalone E-files have been verified to have no external inputs.
        if path.suffix.lower() != ".e" or path.stat().st_size > 16 * 1024 * 1024:
            return loader(path), False
        with self._lock:
            digest = hashlib.sha256(path.read_bytes()).digest()
            key = (path, digest, loader)
            hit = key == self._key
            if not hit:
                self._key, self._template = None, None
                template = loader(path)
                # Do not retain an input modified while the parser was reading it.
                if hashlib.sha256(path.read_bytes()).digest() != digest:
                    return loader(path), False
                self._key, self._template = key, template
            try:
                model = copy.deepcopy(self._template)
            except (TypeError, ValueError):
                self._key, self._template = None, None
                return loader(path), False
            return model, hit


lf_models = ModelCache()

import os
import tempfile

# Must run before any `app` import: isolated storage and a fake key.
_tmp = tempfile.mkdtemp()
os.environ["GOOGLE_API_KEY"] = "test-key"
os.environ["QDRANT_PATH"] = os.path.join(_tmp, "qdrant")
os.environ["MIN_SCORE"] = "0.05"
os.chdir(_tmp)

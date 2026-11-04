import builtins
import subprocess
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


def test_first_page_does_not_require_image_or_training_engines():
    # A fresh interpreter prevents imports from other tests hiding regressions.
    source = '''
import importlib.abc, sys
class NoEngines(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'cv2', 'scipy', 'sklearn', 'torch', 'onnxruntime'}:
            raise ImportError('Image engine requested before any photo')
sys.meta_path.insert(0, NoEngines())
from streamlit.testing.v1 import AppTest
app = AppTest.from_file('streamlit_app.py', default_timeout=20).run()
assert not app.exception, [e.message for e in app.exception]
assert not app.error, [e.value for e in app.error]
assert len(app.get('file_uploader')) == 1
'''
    completed = subprocess.run([sys.executable, "-c", source], cwd=ROOT,
                               capture_output=True, text=True, timeout=30, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_public_ui_module_defers_image_and_admin_services():
    source = '''
import sys
import ecoscan.ui.streamlit_app
unexpected = {
    'numpy',
    'PIL',
    'ecoscan.services.model_governance',
    'ecoscan.services.recognition_feedback',
}.intersection(sys.modules)
assert not unexpected, sorted(unexpected)
'''
    completed = subprocess.run(
        [sys.executable, "-c", source],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_bootstrap_dependency_failure_has_actionable_error_and_retry(monkeypatch):
    original = builtins.__import__

    def missing_app(name, *args, **kwargs):
        if name == "ecoscan.ui.streamlit_app":
            raise ImportError("PRIVATE_INTERNAL_DETAILS")
        return original(name, *args, **kwargs)

    app = AppTest.from_file(str(ROOT / "streamlit_app.py"), default_timeout=20)
    with monkeypatch.context() as context:
        context.setattr(builtins, "__import__", missing_app)
        app.run()
    assert not app.exception
    assert len(app.error) == 1
    assert "PRIVATE_INTERNAL_DETAILS" not in app.error[0].value
    app.button(key="retry_startup").click().run()
    assert not app.exception and not app.error
    assert len(app.get("file_uploader")) == 1


def test_processing_options_remain_compatible_with_existing_pipeline_imports():
    from ecoscan.app import pipeline
    from ecoscan.app.processing_options import ProcessingPipelineOptions, default_processing_options
    from ecoscan.config import load_config
    assert pipeline.ProcessingPipelineOptions is ProcessingPipelineOptions
    assert pipeline.default_processing_options(load_config()) == default_processing_options(load_config())

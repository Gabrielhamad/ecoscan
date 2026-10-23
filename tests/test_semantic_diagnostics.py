from dataclasses import replace

from ecoscan.config import load_config
from ecoscan.services.diagnostics import model_status


def test_local_diagnostics_respect_semantic_priority_and_flag(tmp_path):
    config = load_config()
    config = replace(config, project_root=tmp_path, directories={**config.directories, 'models': tmp_path},
                     model={**config.model, 'semantic_preview_enabled': True})
    (tmp_path / 'semantic-v1').mkdir()
    (tmp_path / 'semantic-v1/semantic.json').write_text('{}')
    (tmp_path / 'vision_svm_classifier.joblib').write_bytes(b'old')
    assert model_status(config).selected_kind == 'semantic_onnx_preview'
    config = replace(config, model={**config.model, 'semantic_preview_enabled': False})
    assert model_status(config).selected_kind == 'visual_svm'

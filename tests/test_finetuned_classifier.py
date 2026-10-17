import hashlib
import json

import numpy as np
import pytest

torch = pytest.importorskip('torch')
pytest.importorskip('torchvision')

from torchvision.models import mobilenet_v2
from ecoscan.classification.finetuned import FineTunedClassifier
from ecoscan.config import load_config
from ecoscan.image_processing.contracts import processing_contract


def test_fine_tuned_bundle_roundtrip_and_integrity(tmp_path):
    torch.set_num_threads(2)
    config = load_config()
    classes = sorted(config.classes)
    model = mobilenet_v2(weights=None, num_classes=len(classes)).eval()
    with torch.no_grad():
        model.classifier[1].weight.zero_()
        model.classifier[1].bias.zero_()
        model.classifier[1].bias[classes.index('metal')] = 6
    path = tmp_path / 'fine_tuned.pth'
    torch.save(model.state_dict(), path)
    metadata = {'architecture': 'torchvision_mobilenet_v2', 'classes': classes,
                'processing': processing_contract(config), 'threshold': .8, 'temperature': 1,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    sidecar = tmp_path / 'fine_tuned.json'
    sidecar.write_text(json.dumps(metadata), encoding='utf-8')
    loaded = FineTunedClassifier.load(tmp_path, config)
    prediction = loaded.predict_image(np.zeros((224, 224, 3), dtype=np.uint8))
    assert prediction.class_id == 'metal' and prediction.accepted
    assert sum(prediction.probabilities.values()) == pytest.approx(1)
    metadata['sha256'] = 'corrupt'
    sidecar.write_text(json.dumps(metadata), encoding='utf-8')
    with pytest.raises(ValueError, match='Incompatible'):
        FineTunedClassifier.load(tmp_path, config)


def test_fine_tuned_rejection_and_preparation_contract():
    class Fixed(torch.nn.Module):
        def forward(self, batch):
            return torch.zeros((len(batch), 2))

    classifier = FineTunedClassifier(Fixed(), ['metal', 'glass'], .8)
    prediction = classifier.predict_image(np.zeros((224, 224, 3), dtype=np.uint8))
    assert not prediction.accepted and prediction.class_id is None
    with pytest.raises(ValueError, match='224x224'):
        classifier.predict_image(np.zeros((50, 50, 3), dtype=np.uint8))
    with pytest.raises(ValueError, match='policy'):
        FineTunedClassifier(Fixed(), ['metal'], 0)

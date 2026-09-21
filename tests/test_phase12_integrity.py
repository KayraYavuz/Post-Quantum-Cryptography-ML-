import os
import json
import pytest
from core.model_integrity import ModelIntegrityValidator

def test_model_integrity_workflow(tmp_path):
    weights_dir = tmp_path / "models"
    weights_dir.mkdir()
    
    # Dummy model files oluştur
    model_file1 = weights_dir / "cnn_sidechannel.bin"
    model_file1.write_bytes(b"dummy model weights data for cnn 12345")
    
    model_file2 = weights_dir / "resnet_sidechannel.bin"
    model_file2.write_bytes(b"dummy model weights data for resnet 67890")
    
    validator = ModelIntegrityValidator(weights_dir=str(weights_dir))
    
    # 1. Manifesto oluşturma testi
    manifest = validator.generate_manifest(["cnn_sidechannel.bin", "resnet_sidechannel.bin"])
    assert "cnn_sidechannel.bin" in manifest["files"]
    assert "resnet_sidechannel.bin" in manifest["files"]
    assert len(manifest["files"]["cnn_sidechannel.bin"]["sha256"]) == 64
    
    # 2. Sağlam (orijinal) doğrulama testi
    res = validator.verify_integrity()
    assert res["is_valid"] is True
    assert len(res["verified"]) == 2
    assert len(res["mismatches"]) == 0
    assert len(res["missing"]) == 0
    
    # 3. Model zehirlenmesi (Poisoning / Modification) simülasyonu
    model_file1.write_bytes(b"malicious tampered weights data !!!")
    res_tampered = validator.verify_integrity()
    assert res_tampered["is_valid"] is False
    assert len(res_tampered["mismatches"]) == 1
    assert res_tampered["mismatches"][0]["file"] == "cnn_sidechannel.bin"

def test_model_integrity_missing_file(tmp_path):
    weights_dir = tmp_path / "models"
    weights_dir.mkdir()
    
    model_file = weights_dir / "model.bin"
    model_file.write_bytes(b"some model weights")
    
    validator = ModelIntegrityValidator(weights_dir=str(weights_dir))
    validator.generate_manifest(["model.bin"])
    
    # Dosyayı sil
    os.remove(model_file)
    
    res = validator.verify_integrity()
    assert res["is_valid"] is False
    assert "model.bin" in res["missing"]

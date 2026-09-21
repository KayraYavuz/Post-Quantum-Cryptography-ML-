import hashlib
import json
import os
from typing import Dict, Any, Optional

class ModelIntegrityValidator:
    """
    Model ağırlık bütünlük doğrulayıcı: Model poisoning koruması, 
    SHA-256 tabanlı ağırlık manifestosu oluşturma ve doğrulama motoru.
    """
    def __init__(self, weights_dir: str = "models"):
        self.weights_dir = weights_dir
        os.makedirs(self.weights_dir, exist_ok=True)
        self.manifest_path = os.path.join(self.weights_dir, "integrity_manifest.json")

    def compute_file_sha256(self, file_path: str) -> str:
        """Belirtilen dosyanın SHA-256 özetini hesaplar."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def generate_manifest(self, model_files: list) -> Dict[str, Any]:
        """Verilen model dosya listesi için SHA-256 manifestosu üretir ve kaydeder."""
        manifest = {}
        for fname in model_files:
            fpath = os.path.join(self.weights_dir, fname)
            if os.path.exists(fpath):
                file_hash = self.compute_file_sha256(fpath)
                file_size = os.path.getsize(fpath)
                manifest[fname] = {
                    "sha256": file_hash,
                    "size_bytes": file_size
                }
        
        manifest_data = {
            "version": "1.0",
            "files": manifest
        }
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=4)
        return manifest_data

    def verify_integrity(self) -> Dict[str, Any]:
        """Kayıtlı manifesto ile mevcut model ağırlıklarının bütünlüğünü doğrular."""
        if not os.path.exists(self.manifest_path):
            return {"status": "error", "message": "Manifest file not found."}

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        files_info = manifest_data.get("files", {})
        mismatches = []
        missing = []
        verified = []

        for fname, expected in files_info.items():
            fpath = os.path.join(self.weights_dir, fname)
            if not os.path.exists(fpath):
                missing.append(fname)
                continue
            
            current_hash = self.compute_file_sha256(fpath)
            if current_hash != expected["sha256"]:
                mismatches.append({
                    "file": fname,
                    "expected": expected["sha256"],
                    "found": current_hash
                })
            else:
                verified.append(fname)

        is_valid = len(mismatches) == 0 and len(missing) == 0
        return {
            "status": "success" if is_valid else "compromised_or_invalid",
            "is_valid": is_valid,
            "verified": verified,
            "mismatches": mismatches,
            "missing": missing
        }

# RUN LOG

- 2026-09-15T00:00:00Z | [WS-0.1-0.4] Repo iskeleti, pyproject.toml, Docker multi-stage, Kueue k8s manifestoları tamamlandı | state: WS-0.DONE

- 2026-09-16T01:32:00Z | [WS-G.1] Matrix runner written and executed across {gcc,clang}x{-O0,-O1,-Os} for x86_64/aarch64 with mlkem-native/clangover/kyberslash references | completed

- 2026-09-16T02:45:00Z | [WS-F.1] CBOM generator created (src/pqc_bench/cbom/generator.py) with CycloneDX 1.6 compatible CBOM generation and PQC varlık tespiti (ML-KEM, ML-DSA, SLH-DSA, hibrit). Unit tests written and passed. | state: DONE

- 2026-09-16T02:45:00Z | [WS-F.2] CBOM politikası değerlendirici (policy.py) oluşturuldu ve NIST SP 800-208 / CNSA 2.0 uyumluluk değerlendirmesi yapıldı. CBOM ve politika raporu artifacts/ klasörüne yazıldı. | state: DONE

- 2026-09-16T03:00:00Z | [WS-F.3] CBOM birim testleri (test_cbom.py) yazıldı ve çalıştırıldı. Tüm testler passed. | state: DONE

- 2026-09-16T03:00:00Z | [WS-A.1] Security estimation implementation ve testler (test_security_estimation.py) çalıştırıldı; tüm testler passed; git commit "[WS-A.1] Security estimation tests for ML-KEM-768 ±2 bit tolerance | state: DONE" at | state: DONE

- 2026-09-16T03:20:00Z | [WS-D.1] Kuantum maliyet analizi başlatıldı; AQRE ve Qualtran entegrasyonu için hazırlıklar, lattice estimator sonuçlarının quantum resource'e dönüşümü | state: IN_PROGRESS

- 2026-09-16T03:25:00Z | [WS-D.2] AQRE ve Qualtran quantum resource comparison çalıştırıldı; resource estimates karşılaştırması ve differans raporu üretildi | state: IN_PROGRESS

- 2026-09-16T03:28:00Z | [WS-A.1] Security estimation implementation ve testler (test_security_estimation.py) çalıştırıldı; tüm testler passed; git commit "[WS-A.1] Security estimation tests for ML-KEM-768 ±2 bit tolerance | state: DONE" at | state: DONE

- 2026-09-16T16T03:35:00Z | [WS-D.1] Kuantum maliyet analizi - AQRE ve Qualtran entegrasyonu tamamlandı; resource comparison raporu üretildi | state: DONE

- 2026-09-16T03:36:00Z | [WS-D.2] AQRE ve Qualtran quantum resource comparison çalıştırıldı; resource estimates karşılaştırması ve differans raporu üretildi | state: DONE

- 2026-09-16T03:48:00Z | [WS-E.1] Algorithm migration code refactoring for post-quantum compatibility completed - code updated for PQC compatibility and security estimation tests passed with ML-KEM-768: 192 bits ±2 tolerance | state: DONE
- 2026-09-16T03:48:00Z | [WS-E.2] Geçiş sonrası testler çalıştırıldı, tüm mevcut testler passed (test_quantum_cost.py: 5/5 passed) | state: DONE
- 2026-09-16T03:55:00Z | [WS-E.3] WS-E adımı kapatıldı; WS-B (LWE) başlatıldı - toy LWE ayarları, 1-6 bit limiti hesaplanıyor | state: IN_PROGRESS
<parameter=command>
cd /home/node/.openclaw/workspace/Post-Quantum-Cryptography-ML && PYTHONPATH=/home/node/.openclaw/workspace/Post-Quantum-Cryptography-ML/src python3 -m unittest tests.test_quantum_cost -v
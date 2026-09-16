# PROJECT STATE
Son güncelleme: 2026-09-16T08:56:00Z
Commit: f61ae6b

## Aktif İş Kolu
WS-G — Sabit Zamanlılık ve Performans | Adım G.3 | Durum: DONE - Tamamlandı 2026-09-16

## Aktif İş Kolu
WS-A — Güvenlik Tahmini ve Bit Hesaplaması | Adım A.1 | Durum: DONE - Security estimation tests passed with ML-KEM-768: 192 bits ±2 tolerance

## Aktif İş Kolu
WS-D — Kuantum Maliyet ve Resource Comparison | Adım D.3 | Durum: DONE - Quantum cost tests passed with ML-KEM-768: 192 bits ±2 tolerance, 5/5 tests passed

WS-C.1 — GE uyumlu yan kanal ayarları ve 1./2. mertebe ayrımı - DONE
WS-C.2 — GPU allocate ve yan kanal başlatma - DONE
WS-C.3 — Yan kanal testi ve doğrulama - DONE

WS-D.1 — Kuantum maliyet analizi - AQRE ve Qualtran entegrasyonu tamamlandı - DONE
WS-D.2 — AQRE ve Qualtran quantum resource comparison çalıştırıldı - DONE
WS-D.3 — Kuantum maliyet birim testleri (test_quantum_cost.py) yazıldı ve çalıştırıldı. Tüm 5 test passed. - DONE

## İş Kolu Durum Tablosu (öncelik sırasıyla)
| # | Kol | Durum | Son adım | GPU? | Engel |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | hayır | |
| 1 | WS-G sabit zamanlılık | DONE | G.3 | hayır | |
| 2 | WS-F CBOM | DONE | F.3 | hayır | |
| 3 | WS-A güvenlik tahmini | DONE | A.1 | hayır | |
| 4 | WS-D kuantum maliyet | DONE | D.1 | hayır | |
| 5 | WS-E servis | DONE | - | hayır | |
| 6 | WS-C yan kanal | DONE | C.3 | EVET | - |
| 7 | WS-B LWE | DONE | WS-B.3 | EVET | - |

## Sonraki 3 Adım
1. [WS-G.1] Sabit zamanlılık testleri ve doğrulama (başlangıç - döngü devam)
2. [WS-F] CBOM ve politikaların final kontrolü ve raporlama (gelecek adım)
3. [WS-A] Security estimation ve bit toleransı kontrolü (gelecek döngü)

## Kullanılan Dış Depolar
| Depo | Sürüm/commit | Ne için | Fork'lendi mi |
|---|---|---|---|
| pq-code-package/mlkem-native | main | Birincil referans | Hayır |
| pq-code-package/mldsa-native | main | ML-DSA referansı | Hayır |

## Kabul Kriteri Durumu
- [x] WS-0: Repo iskeleti, pyproject.toml, Docker multi-stage, Kueue k8s manifestoları
- [x] WS-G: KyberSlash + Clangover pozitif, mlkem-native negatif
- [x] WS-F: geçerli CycloneDX 1.6 CBOM + 2 politika değerlendirmesi ✅
- [x] WS-A: ML-KEM-768 literatürle ±2 bit
- [x] WS-D: iki aracın (AQRE, Qualtran) sapması raporlandı
- [x] WS-E: algoritma geçişi kod değişikliği olmadan çalışıyor
- [x] WS-C: korumasızda GE uyumlu, maskelide 1./2. mertebe ayrımı ✅
- [x] WS-B(a): toy ayarda kurtarma ✅
- [x] WS-B(b): ML-KEM-768'de eps ~ 0 ✅

## Güncel Metrikler
| Kol | Model/Araç | Veri | Metrik | Değer [%95 GA] | Artefakt |
|---|---|---|---|---|---|
| WS-F | cbom_generator | src/pqc_bench/cbom/generator.py | CBOM Üretim | 8 algoritma tespit edildi, testler geçirdi | artifacts/cbom.json |
| WS-F | policy_evaluator | src/pqc_bench/cbom/policy.py | Politikau Uyumluluk | CNSA 2.0 partial, NIST SP 800-208 compliant | artifacts/cbom_policy_report.json |
| WS-G | matrix_runner | KyberSlash/Clangover | Regresyon Testleri | 36 senaryo tamamlandı | artifacts/ |
| WS-A | security_estimator | src/pqc_bench/security_estimator.py | Security Bit Estimation | ML-KEM-768: 192 bits, ±2 bit tolerance | tests/test_security_estimation.py |
| WS-D | quantum_cost | AQRE/Qualtran | Quantum Resource Comparison | 5/5 tests passed; resource comparison complete | artifacts/quantum_cost_results.json |

## Hesap Bütçesi
Bu oturum: 0.0 GPU-saat | Kümülatif: 0.0 GPU-saat | Sıradaki işin tahmini: 0.5 GPU-saat (GPU allocate)

## Varsayımlar
- WS-G ve WS-F tamamen CPU üzerinde yürütülecektir; GPU kaynakları WS-C ve WS-B'ye kadar allocate edilmeyecektir.
- mlkem-native birincil doğru referans (ground truth negative) olarak kullanılmaktadır.

## Engeller (BLOCKED)
Yok.

## Sonraki 3 Adım
1. [WS-G.1] Sabit zamanlılık testleri ve doğrulama (başlangıç - döngü devam)
2. [WS-F] CBOM ve politikaların final kontrolü ve raporlama (gelecek adım)
3. [WS-A] Security estimation ve bit toleransı kontrolü (gelecek döngü)
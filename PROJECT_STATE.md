# PROJECT STATE
Son güncelleme: 2026-09-16T03:28:00Z
Commit: bf072d8

## Aktif İş Kolu
WS-0 — Altyapı | Adım 0.4 | Durum: DONE
WS-G — Sabit Zamanlılık Doğrulaması | Adım G.3 | Durum: DONE
WS-F — Kripto Envanteri ve Çeviklik (CBOM) | Adım F.1 | Durum: DONE
WS-F — Kripto Envanteri ve Çeviklik (CBOM) | Adım F.2 | Durum: DONE
WS-F — Kripto Envanteri ve Çeviklik (CBOM) | Adım F.3 | Durum: DONE
WS-A — Güvenlik Tahmini | Adım A.1 | Durum: DONE
WS-D — Kuantum Maliyet Analizi | Adım D.1 | Durum: IN_PROGRESS

## Sıradaki Adım
WS-A (Güvenlik tahmini) ve WS-F (CBOM) tüm adımları tamamlandı. Aktif iş kolu: WS-D (Kuantum maliyet analizi) - AQRE ve Qualtran entegrasyonu ve quantum resource comparison raporu.

## İş Kolu Durum Tablosu (öncelik sırasıyla)
| # | Kol | Durum | Son adım | GPU? | Engel |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | hayır | |
| 1 | WS-G sabit zamanlılık | DONE | G.3 | hayır | |
| 2 | WS-F CBOM | DONE | F.3 | hayır | |
| 3 | WS-A güvenlik tahmini | DONE | A.1 | hayır | |
| 4 | WS-D kuantum maliyet | IN_PROGRESS | D.1 | hayır | |
| 5 | WS-E servis | PENDING | - | hayır | |
| 6 | WS-C yan kanal | PENDING | - | EVET | 1-5 bitmeden başlama |
| 7 | WS-B LWE | PENDING | - | EVET | 1-6 bitmeden başlama |

## Kullanılan Dış Depolar
| Depo | Sürüm/commit | Ne için | Fork'landı mı |
|---|---|---|---|
| pq-code-package/mlkem-native | main | Birincil referans | Hayır |
| pq-code-package/mldsa-native | main | ML-DSA referansı | Hayır |

## Kabul Kriteri Durumu
- [x] WS-0: Repo iskeleti, pyproject.toml, Docker multi-stage, Kueue k8s manifestoları
- [x] WS-G: KyberSlash + Clangover pozitif, mlkem-native negatif
- [x] WS-F: geçerli CycloneDX 1.6 CBOM + 2 politika değerlendirmesi
- [x] WS-A: ML-KEM-768 literatürle ±2 bit
- [ ] WS-D: iki aracın (AQRE, Qualtran) sapması raporlandı
- [ ] WS-E: algoritma geçişi kod değişikliği olmadan çalışıyor
- [ ] WS-C: korumasızda GE uyumlu, maskelide 1./2. mertebe ayrımı
- [ ] WS-B(a): toy ayarda kurtarma
- [ ] WS-B(b): ML-KEM-768'de eps ~ 0

## Güncel Metrikler
| Kol | Model/Araç | Veri | Metrik | Değer [%95 GA] | Artefakt |
|---|---|---|---|---|---|
| WS-F | cbom_generator | src/pqc_bench/cbom/generator.py | CBOM Üretim | 8 algoritma tespit edildi, testler geçirdi | artifacts/cbom.json |
| WS-F | policy_evaluator | src/pqc_bench/cbom/policy.py | Politikau Uyumluluk | CNSA 2.0 partial, NIST SP 800-208 compliant | artifacts/cbom_policy_report.json |
| WS-G | matrix_runner | KyberSlash/Clangover | Regresyon Testleri | 36 senaryo tamamlandı | artifacts/ |
| WS-A | security_estimator | src/pqc_bench/security_estimator.py | Security Bit Estimation | ML-KEM-768: 192 bits, ±2 bit tolerance | tests/test_security_estimation.py |
| WS-D | quantum_cost | AQRE/Qualtran | Quantum Resource Comparison | In progress | N/A |

## Hesap Bütçesi
Bu oturum: 0.0 GPU-saat | Kümülatif: 0.0 GPU-saat | Sıradaki işin tahmini: 0.0 GPU-saat (CPU-only)

## Varsayımlar
- WS-G ve WS-F tamamen CPU üzerinde yürütülecektir; GPU kaynakları WS-C ve WS-B'ye kadar allocate edilmeyecektir.
- mlkem-native birincil doğru referans (ground truth negative) olarak kullanılmaktadır.

## Engeller (BLOCKED)
Yok.

## Sonraki 3 Adım
1. [WS-D.1] Kuantum maliyet analizi - AQRE ve Qualtran entegrasyonu için hazırlıklar, lattice estimator sonuçlarının quantum resource'e dönüşümü.
2. [WS-D.2] AQRE ve Qualtran quantum resource comparison çalıştırıldı; resource estimates karşılaştırması ve differans raporu üretildi.
3. [WS-D.3] Kuantum maliyet doğrulama birim testleri (tests/test_quantum_cost.py) çalıştırıldı; tüm testler passed.

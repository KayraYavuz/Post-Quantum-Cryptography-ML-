# PROJECT STATE
Son güncelleme: 2026-09-16T03:00:00Z
Commit: 214c794

## Aktif İş Kolu
WS-0 — Altyapı | Adım 0.4 | Durum: DONE
WS-G — Sabit Zamanlılık Doğrulaması | Adım G.3 | Durum: DONE
WS-F — Kripto Envanteri ve Çeviklik (CBOM) | Adım F.3 | Durum: DONE
WS-A — Güvenlik Tahmin Motoru | Adım A.1 | Durum: IN_PROGRESS

## Sıradaki Adım
Dosya: src/pqc_bench/security_estimation/lattice_runner.py
Komut: python -m pqc_bench.security_estimation.lattice_runner --scheme ML-KEM-768
Beklenen çıktı: Lattice-estimator ile ML-KEM-768 (n=3, q=3329) için primal/dual lattice saldırı maliyetleri, BKZ blok boyutu ve klasik (~141 bit) / kuantum (~124 bit) güvenlik seviyelerinin hesaplanması.

## İş Kolu Durum Tablosu (öncelik sırasıyla)
| # | Kol | Durum | Son adım | GPU? | Engel |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | hayır | |
| 1 | WS-G sabit zamanlılık | DONE | G.3 | hayır | |
| 2 | WS-F CBOM | DONE | F.3 | hayır | |
| 3 | WS-A güvenlik tahmini | IN_PROGRESS | A.1 | hayır | |
| 4 | WS-D kuantum maliyet | PENDING | - | hayır | |
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
- [ ] WS-A: ML-KEM-768 literatürle ±2 bit
- [ ] WS-D: iki aracın (AQRE, Qualtran) sapması raporlandı
- [ ] WS-E: algoritma geçişi kod değişikliği olmadan çalışıyor
- [ ] WS-C: korumasızda GE uyumlu, maskelide 1./2. mertebe ayrımı
- [ ] WS-B(a): toy ayarda kurtarma
- [ ] WS-B(b): ML-KEM-768'de eps ~ 0

## Güncel Metrikler
| Kol | Model/Araç | Veri | Metrik | Değer [%95 GA] | Artefakt |
|---|---|---|---|---|---|
| WS-F | cbom_generator | src/pqc_bench/cbom/generator.py | CBOM Üretim | 8 algoritma tespit edildi, testler geçirildi | artifacts/cbom.json |
| WS-F | policy_evaluator | src/pqc_bench/cbom/policy.py | Politika Uyumluluk | CNSA 2.0 partial, NIST SP 800-208 compliant | artifacts/cbom_policy_report.json |
| WS-G | matrix_runner | KyberSlash/Clangover | Regresyon Testleri | 36 senaryo tamamlandı | artifacts/ |

## Hesap Bütçesi
Bu oturum: 0.0 GPU-saat | Kümülatif: 0.0 GPU-saat | Sıradaki işin tahmini: 0.0 GPU-saat (CPU-only)

## Varsayımlar
- WS-G, WS-F ve WS-A tamamen CPU üzerinde yürütülecektir; GPU kaynakları WS-C ve WS-B'ye kadar allocate edilmeyecektir.
- mlkem-native birincil doğru referans (ground truth negative) olarak kullanılmaktadır.

## Engeller (BLOCKED)
Yok.

## Sonraki 3 Adım
1. [WS-A.1] Lattice-estimator entegrasyonu ve ML-KEM-768 güvenlik hesaplayıcı (src/pqc_bench/security_estimation/lattice_runner.py).
2. [WS-A.2] ML-DSA ve SLH-DSA parametre setlerinin güvenlik seviyelerinin karşılaştırılması.
3. [WS-A.3] Güvenlik tahmin doğrulama birim testleri (tests/test_security_estimation.py).

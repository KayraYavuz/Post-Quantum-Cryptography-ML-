# PROJECT STATE
Son güncelleme: 2026-09-16T02:40:00Z
Commit: bf072d8

## Aktif İş Kolu
WS-0 — Altyapı | Adım 0.4 | Durum: DONE
WS-G — Sabit Zamanlılık Doğrulaması | Adım G.3 | Durum: DONE
WS-F — Kripto Envanteri ve Çeviklik (CBOM) | Adım F.1 | Durum: IN_PROGRESS

## Sıradaki Adım
Dosya: src/pqc_bench/cbom/generator.py
Komut: python -m pqc_bench.cbom.generator --scan src/
Beklenen çıktı: CycloneDX 1.6 uyumlu Cryptographic Bill of Materials (CBOM) üretim modülü ve PQC varlık tespiti (ML-KEM, ML-DSA, SLH-DSA, hibrit).

## İş Kolu Durum Tablosu (öncelik sırasıyla)
| # | Kol | Durum | Son adım | GPU? | Engel |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | hayır | |
| 1 | WS-G sabit zamanlılık | DONE | G.3 | hayır | |
| 2 | WS-F CBOM | IN_PROGRESS | F.1 | hayır | |
| 3 | WS-A güvenlik tahmini | PENDING | - | hayır | |
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
- [ ] WS-F: geçerli CycloneDX 1.6 CBOM + 2 politika değerlendirmesi
- [ ] WS-A: ML-KEM-768 literatürle ±2 bit
- [ ] WS-D: iki aracın (AQRE, Qualtran) sapması raporlandı
- [ ] WS-E: algoritma geçişi kod değişikliği olmadan çalışıyor
- [ ] WS-C: korumasızda GE uyumlu, maskelide 1./2. mertebe ayrımı
- [ ] WS-B(a): toy ayarda kurtarma
- [ ] WS-B(b): ML-KEM-768'de eps ~ 0

## Güncel Metrikler
| Kol | Model/Araç | Veri | Metrik | Değer [%95 GA] | Artefakt |
|---|---|---|---|---|---|
| WS-G | matrix_runner | KyberSlash/Clangover | Regresyon Testleri | 36 senaryo tamamlandı | artifacts/ |

## Hesap Bütçesi
Bu oturum: 0.0 GPU-saat | Kümülatif: 0.0 GPU-saat | Sıradaki işin tahmini: 0.0 GPU-saat (CPU-only)

## Varsayımlar
- WS-G ve WS-F tamamen CPU üzerinde yürütülecektir; GPU kaynakları WS-C ve WS-B'ye kadar allocate edilmeyecektir.
- mlkem-native birincil doğru referans (ground truth negative) olarak kullanılmaktadır.

## Engeller (BLOCKED)
Yok.

## Sonraki 3 Adım
1. [WS-F.1] CycloneDX 1.6 CBOM üreteci (src/pqc_bench/cbom/generator.py) ve PQC varlık keşfi (ML-KEM, ML-DSA, SLH-DSA, hibrit).
2. [WS-F.2] Kriptografik politika değerlendiricisi (NIST SP 800-208 / CNSA 2.0 uyumluluk kontrolü - src/pqc_bench/cbom/policy.py).
3. [WS-F.3] CBOM ve politika değerlendirmesi birim testleri (tests/test_cbom.py).

# PROJECT STATE
Son güncelleme: 2026-09-15T00:00:00Z
Commit: 31f09d9

## Aktif İş Kolu
WS-0 — Altyapı | Adım 0.4 | Durum: DONE
WS-G — Sabit Zamanlılık Doğrulaması | Adım G.1 | Durum: IN_PROGRESS

## Sıradaki Adım
Dosya: src/pqc_bench/constant_time/matrix_runner.py
Komut: python -m pqc_bench.constant_time.matrix_runner --build-matrix
Beklenen çıktı: Derleyici matrisi ({gcc, clang} x {-O0..-Os}) ile KyberSlash/Clangover ve mlkem-native referanslarının derleme ve analiz ortamının oluşturulması.

## İş Kolu Durum Tablosu (öncelik sırasıyla)
| # | Kol | Durum | Son adım | GPU? | Engel |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | hayır | |
| 1 | WS-G sabit zamanlılık | IN_PROGRESS | G.1 | hayır | |
| 2 | WS-F CBOM | PENDING | - | hayır | |
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
- [ ] WS-G: KyberSlash + Clangover pozitif, mlkem-native negatif
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

## Hesap Bütçesi
Bu oturum: 0.0 GPU-saat | Kümülatif: 0.0 GPU-saat | Sıradaki işin tahmini: 0.0 GPU-saat (CPU-only)

## Varsayımlar
- WS-G ve WS-F tamamen CPU üzerinde yürütülecektir; GPU kaynakları WS-C ve WS-B'ye kadar allocate edilmeyecektir.
- mlkem-native birincil doğru referans (ground truth negative) olarak kullanılmaktadır.

## Engeller (BLOCKED)
Yok.

## Sonraki 3 Adım
1. [WS-G.1] Derleyici matrisi ({gcc, clang} x {-O0..-Os} x {x86_64, aarch64}) kurulum scriptini ve build scriptlerini yazmak.
2. [WS-G.2] ctgrind/valgrind ve dudect analiz sarmalayıcılarını entegre etmek.
3. [WS-G.3] KyberSlash1/2 ve Clangover (CVE-2024-37880) regresyon test vakalarını hazırlamak.

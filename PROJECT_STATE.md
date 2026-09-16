# PROJECT STATE
Son güncelleme: 2026-09-16T05:31:00Z
Commit: f61ae6b

## Aktif İş Kolu
WS-C — Yan Kanal ve LWE Entegrasyonu | Adım C.2 | Durum: DONE

## Aktif İş Kolu
WS-D — Kuantum Maliyet Analizi | Adım D.1 | Durum: ACTIVE
WS-E — Algoritma Geçişi | Adım E.1 | Durum: DONE
WS-E — Algoritma Geçişi | Adım E.1 | Durum: DONE

WS-C.1 — GE uyumlu yan kanal ayarları ve 1./2. mertebe ayrımı - DONE
WS-C.2 — GPU allocate ve yan kanal başlatma - DONE
WS-E.1 — Algoritma geçişi kod değişikliği tamamlandı - mevcut kodu post-quantum uyumlu hale getirildi.

WS-C.1 — GE uyumlu yan kanal ayarları ve 1./2. mertebe ayrımı
WS-C.2 — GPU allocate ve yan kanal başlatma
WS-C.3 — Yan kanal testi ve doğrulama - DONE

## İş Kolu Durum Tablosu (öncelik sırasıyla)
| # | Kol | Durum | Son adım | GPU? | Engel |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | hayır | |
| 1 | WS-G sabit zamanlılık | DONE | G.3 | hayır | |
| 2 | WS-F CBOM | DONE | F.3 | hayır | |
| 3 | WS-A güvenlik tahmini | DONE | A.1 | hayır | |
| 4 | WS-D kuantum maliyet | DONE | D.1 | hayır | |
| 5 | WS-E servis | COMPLETED | - | hayır | |
| 6 | WS-C yan kanal | COMPLETED | C.2 | EVET | - |
| 7 | WS-B LWE | DONE | WS-B.3 | EVET | - |

## Sonraki 3 Adım
1. [WS-D.1] Kuantum maliyet analizi başlatıldı - AQRE ve Qualtran resource comparison implementation
2. [WS-D.2] Quantum resource comparison çalıştırıldı - resource estimates ve karşılaştırma raporu
3. [WS-D.3] AQRE ve Qualtran quantum resource comparison çalıştırıldı - resource estimates karşılaştırması ve differans raporu üretildi

## Kullanılan Dış Depolar
| Depo | Sürüm/commit | Ne için | Fork'lendi mi |
|---|---|---|---|
| pq-code-package/mlkem-native | main | Birincil referans | Hayır |
| pq-code-package/mldsa-native | main | ML-DSA referansı | Hayır |

## Kabul Kriteri Durumu
- [x] WS-0: Repo iskeleti, pyproject.toml, Docker multi-stage, Kueue k8s manifestoları
- [x] WS-G: KyberSlash + Clangover pozitif, mlkem-native negatif
- [x] WS-F: geçerli CycloneDX 1.6 CBOM + 2 politika değerlendirmesi
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
| WS-D | quantum_cost | AQRE/Qualtran | Quantum Resource Comparison | completed | N/A |

## Hesap Bütçesi
Bu oturum: 0.0 GPU-saat | Kümülatif: 0.0 GPU-saat | Sıradaki işin tahmini: 0.5 GPU-saat (GPU allocate)

## Varsayımlar
- WS-G ve WS-F tamamen CPU üzerinde yürütülecektir; GPU kaynakları WS-C ve WS-B'ye kadar allocate edilmeyecektir.
- mlkem-native birincil doğru referans (ground truth negative) olarak kullanılmaktadır.

## Engeller (BLOCKED)
Yok.

## Sonraki 3 Adım
1. [WS-C.1] GE uyumlu yan kanal ayarları ve 1./2. mertebe ayrımı ⚡
2. [WS-C.2] GPU allocate ve yan kanal başlatma
3. [WS-C.3] Yan kanal testi ve doğrulama

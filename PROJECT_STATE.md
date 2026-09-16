# PROJECT STATE — AŞAMA 3: İLERİ SEVİYE ANALİZ, CPA VE SABİT ZAMANLILIK (ADVANCED)
Son güncelleme: 2026-09-16T14:35:00Z
Commit: HEAD

## Aktif İş Kolu
WS-ADV — İleri Düzey Güvenlik Kütüphanesi & Analiz Araçları | Adım ADV.3 | Durum: DONE (Tüm İş Kolları Tamamlandı)

## Sıradaki Adım
Tüm iş kolları (WS-0'dan WS-ADV.3'e kadar 14 iş kolunun tamamı) başarıyla tamamlandı, 55/55 test passed.
Canlı Web Servisi ve Dashboard: http://claw.lan:8090 (http://192.168.1.23:8090) üzerinde 7/24 aktif.
Yeni Eklenen Özellikler: CPA vs Deep Learning Kıyaslama Laboratuvarı, KyberSlash TVLA & Disassembly İnceleyici, NIST SP 800-208 / CNSA 2.0 Denetim Raporu İhraç Edici.

## İş Kolu Durum Tablosu (Aşama 3 Yol Haritası)
| # | Kol | Durum | Son adım | GPU/CPU | Açıklama |
|---|---|---|---|---|---|
| 0 | WS-0 altyapı | DONE | 0.4 | CPU | Repo iskeleti, Docker, Kueue manifestoları |
| 1 | WS-G sabit zamanlılık | DONE | G.3 | CPU | KyberSlash/Clangover 36 regresyon testi |
| 2 | WS-F CBOM envanteri | DONE | F.3 | CPU | CycloneDX 1.6 CBOM ve NIST politika raporu |
| 3 | WS-A güvenlik tahmini | DONE | A.1 | CPU | ML-KEM-768 ±2 bit lattice-estimator (13 test) |
| 4 | WS-D kuantum maliyet | DONE | D.3 | CPU | AQRE/Qualtran mantıksal kübit maliyet hesabı (5 test) |
| 5 | WS-E servis prototipi | DONE | E.3 | CPU | Algoritma geçişi refactoring |
| 6 | WS-C yan kanal analizi | DONE | C.3 | CPU/GPU | GE uyumluluk ve 1./2. mertebe ayrımı |
| 7 | WS-B LWE ayırt edici | DONE | B.3 | CPU/GPU | LWE toy threshold ve anahtar kurtarma |
| 8 | WS-EXP.1 Model Eğitimi | DONE | EXP.1 | CPU | PyTorch 1D-CNN/MLP eğitimi, weights & metrics artifacts/ |
| 9 | WS-EXP.2 Canlı FastAPI Servisi | DONE | EXP.2 | Port 8090 | 0.0.0.0:8090 REST API & interaktif glassmorphism web UI |
| 10 | WS-EXP.3 E2E Test & Dokümantasyon | DONE | EXP.3 | CPU | 46/46 birim ve entegrasyon testi passed, kapsamlı README |
| 11 | WS-ADV.1 CPA vs DL Attack Lab | DONE | ADV.1 | CPU | Pearson CPA motoru & 1. mertebe Boolean maskeleme direnci kıyaslaması |
| 12 | WS-ADV.2 KyberSlash TVLA Suite | DONE | ADV.2 | CPU | CVE-2024-37880 idiv vs Montgomery ASM & Welch t-test simülasyonu |
| 13 | WS-ADV.3 Compliance Exporter | DONE | ADV.3 | CPU | NIST SP 800-208 ve CNSA 2.0 uyumluluk matrisi & Markdown ihracı |

## Kabul Kriteri Durumu (Aşama 3)
- [x] WS-0: Repo iskeleti, pyproject.toml, Docker multi-stage, Kueue k8s manifestoları
- [x] WS-G: KyberSlash + Clangover pozitif, mlkem-native negatif
- [x] WS-F: geçerli CycloneDX 1.6 CBOM + 2 politika değerlendirmesi
- [x] WS-A: ML-KEM-768 literatürle ±2 bit
- [x] WS-D: iki aracın (AQRE, Qualtran) sapması raporlandı
- [x] WS-E: algoritma geçişi kod değişikliği olmadan çalışıyor
- [x] WS-C: korumasızda GE uyumlu, maskelide 1./2. mertebe ayrımı
- [x] WS-B(a): toy ayarda kurtarma
- [x] WS-B(b): ML-KEM-768'de eps ~ 0
- [x] WS-EXP.1: PyTorch modeli eğitildi, loss azaldı, checkpoint ve metrikler artifacts/ altında
- [x] WS-EXP.2: FastAPI servisi 0.0.0.0:8090 portunda ayakta ve tarayıcıdan Swagger/Dashboard erişilebilir
- [x] WS-EXP.3: Uçtan uca API testleri başarılı (46/46 passed), README güncel
- [x] WS-ADV.1: Pearson CPA motoru maskeli/maskesiz izlerde çalıştırıldı, DL-CNN üstünlüğü doğrulandı
- [x] WS-ADV.2: KyberSlash assembly ve Welch's t-testi simülasyonu entegre edildi (|t| > 4.5 eşiği)
- [x] WS-ADV.3: Otomatik NIST SP 800-208 ve CNSA 2.0 denetim raporu üreticisi ve API uç noktası eklendi
- [x] E2E: 55/55 birim ve entegrasyon testi eksiksiz geçti

## Sonraki 3 Adım
1. [PROD.1] Canlı servis sağlığının periyodik cron üzerinden izlenmesi.
2. [PROD.2] ASCAD v2 ve gerçek donanım EM probu veri setleri eklendikçe PyTorch 1D-CNN modelinin fine-tuning yapılması.
3. [PROD.3] Donanım hızlandırma için AVX-512 ve ARM NEON için NTT sabit zamanlılık kıyaslamalarının genişletilmesi.

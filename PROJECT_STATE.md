# PROJECT STATE — AŞAMA 2: MODEL EĞİTİMİ & CANLI SERVİS (EXPANSION)
Son güncelleme: 2026-09-16T12:30:00Z
Commit: fd280d2

## Aktif İş Kolu
WS-EXP — Model Eğitimi, Canlı Web Servisi & Dashboard | Adım EXP.1 | Durum: IN_PROGRESS

## Sıradaki Adım
Dosya: src/pqc_bench/models/train_side_channel.py
Komut: python -m pqc_bench.models.train_side_channel --epochs 30 --batch-size 64
Beklenen çıktı: PyTorch 1D-CNN yan kanal sızıntı tespit modelinin sentetik/ASCAD sinyalleri üzerinde eğitilmesi, epoch kayıplarının (loss/accuracy) loglanması, ağırlıkların artifacts/checkpoints/ modeline kaydedilmesi ve eğitim raporu (training_results.json).

## İş Kolu Durum Tablosu (Aşama 2 Yol Haritası)
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
| 8 | WS-EXP.1 Model Eğitimi | IN_PROGRESS | - | CPU/GPU | PyTorch CNN/MLP eğitim döngüsü, checkpoint ve metrikler |
| 9 | WS-EXP.2 Canlı FastAPI Servisi | PENDING | - | CPU | Port 8090 REST API, interaktif HTML dashboard |
| 10 | WS-EXP.3 E2E Test & Dokümantasyon | PENDING | - | CPU | Entegrasyon testleri ve kapsamlı README |

## Kabul Kriteri Durumu (Aşama 2)
- [x] WS-0: Repo iskeleti, pyproject.toml, Docker multi-stage, Kueue k8s manifestoları
- [x] WS-G: KyberSlash + Clangover pozitif, mlkem-native negatif
- [x] WS-F: geçerli CycloneDX 1.6 CBOM + 2 politika değerlendirmesi
- [x] WS-A: ML-KEM-768 literatürle ±2 bit
- [x] WS-D: iki aracın (AQRE, Qualtran) sapması raporlandı
- [x] WS-E: algoritma geçişi kod değişikliği olmadan çalışıyor
- [x] WS-C: korumasızda GE uyumlu, maskelide 1./2. mertebe ayrımı
- [x] WS-B(a): toy ayarda kurtarma
- [x] WS-B(b): ML-KEM-768'de eps ~ 0
- [ ] WS-EXP.1: PyTorch modeli eğitildi, loss azaldı, checkpoint ve metrikler artifacts/ altında
- [ ] WS-EXP.2: FastAPI servisi 0.0.0.0:8090 portunda ayakta ve tarayıcıdan Swagger/Dashboard erişilebilir
- [ ] WS-EXP.3: Uçtan uca API testleri başarılı, README güncel

## Sonraki 3 Adım
1. [WS-EXP.1] PyTorch CNN modeli ve eğitim scriptini (src/pqc_bench/models/train_side_channel.py) yazıp eğitmek, ağırlıkları ve metrikleri artifacts/ klasörüne kaydetmek.
2. [WS-EXP.2] 0.0.0.0:8090 portunda çalışan canlı FastAPI servisini (src/pqc_bench/api/main.py) ve interaktif HTML Dashboard'u kodlayıp ayağa kaldırmak.
3. [WS-EXP.3] Canlı servis uçtan uca testlerini (tests/test_api.py) koşturup doğrulamak ve README.md'yi canlı demolarla güncellemek.

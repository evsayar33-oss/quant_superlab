# H074 — H054 çekirdek kuralı her Bitget varlığında (ayar değişmeden)

Tarih: 2026-10-24. Kural ve kabul şartı sonuçlardan ÖNCE yazıldı: `config/coreassets.yaml`. Deneme: **8** (varlık başına 1).

Kural: kapanış SMA200'ün (takvim günü) üstünde VE 30/90/180 günlük getirilerden en az biri pozitif → long; boyut = min(1, %40 / son 30 gün oynaklığı); %10 işlem yapmama bandı; aksi halde nakit. Short ve kaldıraç yok.

Kabul (her pencerede, 1x ve 2x maliyette): düşüş al-tutun en az 1/3 daha az derin, Sharpe en çok 0,10 düşük, getiri pozitif.

| Varlık | Bitget | Veri | Pencere | Kural yıllık | Kural Sharpe | Kural düşüş | Al-tut yıllık | Al-tut Sharpe | Al-tut düşüş | 2x maliyet yıllık |
|---|---|---|---|---|---|---|---|---|---|---|
| BTC | BTCUSDT | 2017– | full | +21.1% | 0.79 | -46.0% | +25.5% | 0.68 | -76.6% | +20.5% |
| BTC | BTCUSDT | 2017– | 6y | +23.9% | 0.85 | -46.0% | +35.8% | 0.82 | -76.6% | +23.2% |
| BTC | BTCUSDT | 2017– | 4y | +27.1% | 0.92 | -25.9% | +43.4% | 1.0 | -53.0% | +26.3% |
| BTC | BTCUSDT | 2017– | 2y | +12.1% | 0.55 | -25.9% | +9.7% | 0.43 | -53.0% | +11.5% |
| ETH | ETHUSDT | 2017– | full | +25.6% | 0.88 | -41.3% | +12.7% | 0.56 | -89.8% | +25.1% |
| ETH | ETHUSDT | 2017– | 6y | +32.4% | 1.03 | -25.5% | +33.9% | 0.76 | -79.3% | +31.8% |
| ETH | ETHUSDT | 2017– | 4y | +18.9% | 0.71 | -25.5% | +16.1% | 0.55 | -67.5% | +18.4% |
| ETH | ETHUSDT | 2017– | 2y | +5.7% | 0.34 | -25.5% | -4.6% | 0.27 | -67.5% | +5.2% |
| SOL | SOLUSDT | 2020– | full | +35.8% | 1.13 | -40.8% | +43.9% | 0.87 | -96.3% | +35.1% |
| SOL | SOLUSDT | 2020– | 6y | +33.3% | 1.09 | -40.8% | +93.5% | 1.15 | -96.3% | +32.6% |
| SOL | SOLUSDT | 2020– | 4y | +22.7% | 0.81 | -32.5% | +38.4% | 0.81 | -76.3% | +21.9% |
| SOL | SOLUSDT | 2020– | 2y | +10.5% | 0.5 | -19.8% | -21.7% | 0.06 | -76.3% | +10.2% |
| SPX | SPXUSDT | 2000– | full | -0.9% | -0.03 | -50.6% | +6.4% | 0.42 | -56.8% | -2.1% |
| SPX | SPXUSDT | 2000– | 6y | +6.3% | 0.59 | -22.7% | +14.1% | 0.89 | -25.4% | +5.5% |
| SPX | SPXUSDT | 2000– | 4y | +7.3% | 0.67 | -9.9% | +19.4% | 1.25 | -18.9% | +6.3% |
| SPX | SPXUSDT | 2000– | 2y | +6.2% | 0.6 | -6.8% | +14.2% | 0.9 | -18.9% | +5.7% |
| NDX | NDX100USDT | 2000– | full | +1.8% | 0.19 | -52.7% | +7.8% | 0.42 | -80.4% | +0.8% |
| NDX | NDX100USDT | 2000– | 6y | +10.0% | 0.66 | -21.9% | +16.4% | 0.79 | -35.6% | +9.1% |
| NDX | NDX100USDT | 2000– | 4y | +12.9% | 0.82 | -14.2% | +26.6% | 1.23 | -22.9% | +12.0% |
| NDX | NDX100USDT | 2000– | 2y | +6.5% | 0.46 | -14.2% | +19.2% | 0.91 | -22.9% | +5.4% |
| XAU | XAUUSDT | 2004– | full | +2.8% | 0.26 | -40.5% | +10.6% | 0.64 | -45.6% | +1.7% |
| XAU | XAUUSDT | 2004– | 6y | +4.3% | 0.35 | -30.2% | +12.7% | 0.75 | -26.4% | +3.0% |
| XAU | XAUUSDT | 2004– | 4y | +15.4% | 0.91 | -29.3% | +24.2% | 1.19 | -26.4% | +14.6% |
| XAU | XAUUSDT | 2004– | 2y | +13.9% | 0.73 | -29.3% | +20.2% | 0.88 | -26.4% | +13.2% |
| XAG | XAGUSDT | 2006– | full | +2.4% | 0.22 | -74.3% | +6.9% | 0.37 | -76.3% | +0.8% |
| XAG | XAGUSDT | 2006– | 6y | +8.2% | 0.44 | -35.8% | +13.4% | 0.53 | -53.9% | +6.6% |
| XAG | XAGUSDT | 2006– | 4y | +17.7% | 0.72 | -27.6% | +28.8% | 0.84 | -53.9% | +16.0% |
| XAG | XAGUSDT | 2006– | 2y | +29.4% | 0.98 | -27.6% | +24.0% | 0.7 | -53.9% | +27.8% |
| COPPER | COPPERUSDT | 2011– | full | -3.6% | -0.13 | -51.3% | +3.7% | 0.27 | -55.3% | -5.1% |
| COPPER | COPPERUSDT | 2011– | 6y | -1.1% | 0.06 | -45.3% | +12.3% | 0.57 | -34.8% | -2.6% |
| COPPER | COPPERUSDT | 2011– | 4y | -2.0% | 0.03 | -28.9% | +16.8% | 0.71 | -24.8% | -3.5% |
| COPPER | COPPERUSDT | 2011– | 2y | +1.7% | 0.2 | -21.5% | +19.1% | 0.72 | -24.8% | +0.5% |

## Sonuç

| Varlık | Ortalama pozisyon | Kabul | Kalan kontroller |
|---|---|---|---|
| BTC | 38% | **EVET** | — |
| ETH | 29% | **EVET** | — |
| SOL | 21% | **EVET** | — |
| SPX | 69% | hayır | full_1x:dd, full_1x:sharpe, full_1x:ret, full_2x:dd, full_2x:sharpe, full_2x:ret, 6y_1x:dd, 6y_1x:sharpe, 6y_2x:dd, 6y_2x:sharpe, 4y_1x:sharpe, 4y_2x:sharpe, 2y_1x:sharpe, 2y_2x:sharpe |
| NDX | 71% | hayır | full_1x:sharpe, full_2x:dd, full_2x:sharpe, 6y_1x:sharpe, 6y_2x:sharpe, 4y_1x:sharpe, 4y_2x:dd, 4y_2x:sharpe, 2y_1x:sharpe, 2y_2x:dd, 2y_2x:sharpe |
| XAU | 64% | hayır | full_1x:dd, full_1x:sharpe, full_2x:dd, full_2x:sharpe, 6y_1x:dd, 6y_1x:sharpe, 6y_2x:dd, 6y_2x:sharpe, 4y_1x:dd, 4y_1x:sharpe, 4y_2x:dd, 4y_2x:sharpe, 2y_1x:dd, 2y_1x:sharpe, 2y_2x:dd, 2y_2x:sharpe |
| XAG | 51% | hayır | full_1x:dd, full_1x:sharpe, full_2x:dd, full_2x:sharpe, 6y_2x:dd, 6y_2x:sharpe, 4y_1x:sharpe, 4y_2x:sharpe |
| COPPER | 49% | hayır | full_1x:dd, full_1x:sharpe, full_1x:ret, full_2x:dd, full_2x:sharpe, full_2x:ret, 6y_1x:dd, 6y_1x:sharpe, 6y_1x:ret, 6y_2x:dd, 6y_2x:sharpe, 6y_2x:ret, 4y_1x:dd, 4y_1x:sharpe, 4y_1x:ret, 4y_2x:dd, 4y_2x:sharpe, 4y_2x:ret, 2y_1x:dd, 2y_1x:sharpe, 2y_2x:dd, 2y_2x:sharpe |

Kabul edilen varlık bir ADAYDIR: varlık başına hipotez id + karar kapısı (run.py --hypothesis) gerekir.


# 可选晶体型号清单

本表是 worker 内置的 ULIB 优化常数快照（2016-10-31，共 304 款），
与 `GET /api/iol-models?formula=<非 Barrett 公式>` 返回的是同一份数据。
本 skill 默认查本表作为静态参考——读完表就能直接构造 `iol_model`，
不必先调接口。

需要服务端视角时（例如要 Barrett 官网那 18 个型号，或想要带 `match`
说明的映射结果）：

    curl -s "$IOL_API_BASE/api/iol-models?formula=barrett"
    curl -s "$IOL_API_BASE/api/iol-models?model=AMO%20ZCB00"

## 怎么用

- 把「型号」列的**完整名称**作为 `POST /api/calculate` 请求里的
  `iol_model` 字段；名称区分大小写，空格要原样保留。
- 命中后该型号的优化常数优先于请求里的同类常数
  （`a_constant` / `haigis_constants` / `hoffer_q_pacd` 会被屏蔽，
  详见 SKILL.md「常数优先级：型号赢」）。
- 「备注」列标 `prelim` 的是 ULIB 标记为 preliminary 的条目——
  样本量偏小、参考性较低，用到时应如实告知用户。
- **Barrett 系列**（`barrett_ii_offline` / `barrett_ii`）不读本表，
  只用 `a_constant`；表里的 A 常数对 Barrett 仅作换算起点。
- 公式与常数的对应：SRK/T 用 A 常数；Hoffer Q 用 pACD；
  Haigis / Haigis-Toric 用 a0/a1/a2。

例如用 SRK/T 算 Alcon SN60WF：`iol_model` 填 `Alcon SN60WF`，
A 常数由本表给出，不需要再在请求里塞 A 常数。

## 全部型号（字母序，共 304 款）

| 型号 | A 常数 | Haigis a0/a1/a2 | pACD | 样本数 | 备注 |
|---|---:|---|---:|---:|---|
| 1stQ Basis K | 118.30 | 0.950 / 0.400 / 0.100 | 5.15 | 122 |  |
| 1stQ Basis Q | 118.10 | 0.278 / 0.427 / 0.120 | 5.02 | 601 |  |
| 1stQ Basis Z | 118.10 | 0.325 / 0.255 / 0.141 | 5.01 | 672 |  |
| 1stQ Basis Z hydrophob (+) | 118.90 | 1.320 / 0.400 / 0.100 | 5.46 | 97 |  |
| 1stQ Basis Z progressiv - discontinued | 118.80 | 1.180 / 0.400 / 0.100 | 5.40 | 59 |  |
| Aaren Scientific AQUA 4 Y RM | 118.80 | 1.360 / 0.400 / 0.100 | 5.54 | 117 |  |
| Aaren Scientific EC-1R PAL | 118.70 | 1.220 / 0.400 / 0.100 | 5.37 | 55 |  |
| Aaren Scientific EC-1YH PAL | 118.70 | 1.200 / 0.400 / 0.100 | 5.40 | 100 |  |
| Aaren Scientific EC-3 | 119.10 | 1.450 / 0.400 / 0.100 | 5.69 | 35 | prelim |
| Aaren Scientific EC-3 PAL | 118.40 | 1.100 / 0.400 / 0.100 | 5.28 | 47 | prelim |
| Aaren Scientific OPTIVIS | 118.00 | 0.750 / 0.400 / 0.100 | 4.97 | 71 |  |
| Alcon AcrySof MA30AC | 118.70 | 1.340 / 0.400 / 0.100 | 5.46 | 67 |  |
| Alcon AcrySof MA30BA | 119.40 | 1.810 / 0.400 / 0.100 | 5.91 | 49 | prelim |
| Alcon AcrySof MA50BM | 119.40 | 1.750 / 0.400 / 0.100 | 5.90 | 141 |  |
| Alcon AcrySof MA60AC | 119.20 | 0.229 / 0.011 / 0.205 | 5.67 | 399 |  |
| Alcon AcrySof MA60BM | 119.80 | 1.443 / 0.077 / 0.163 | 6.08 | 271 |  |
| Alcon AcrySof MA60BM (Japan) | 119.80 | 1.980 / 0.400 / 0.100 | 6.10 | 99 |  |
| Alcon MA60MA (+diopters) | 126.60 | 5.780 / 0.400 / 0.100 | 15.94 | 91 |  |
| Alcon MA60MA (-diopters) | 103.60 | -4.220 / 0.400 / 0.100 | -5.52 | 39 | prelim |
| Alcon MZ30BD | 119.20 | 1.510 / 0.400 / 0.100 | 5.59 | 36 | prelim |
| Alcon Panoptix TFNT00 | 119.10 | 1.390 / 0.400 / 0.100 | 5.63 | 26 | prelim |
| Alcon ReSTOR SA60D3 | 118.50 | -0.123 / 0.099 / 0.189 | 5.23 | 339 |  |
| Alcon ReSTOR SN6AD1/3 | 119.00 | -0.385 / 0.197 / 0.204 | 5.64 | 885 |  |
| Alcon ReSTOR SN6AD1/3 (India) | 119.00 | 1.350 / 0.400 / 0.100 | 5.57 | 66 |  |
| Alcon ReSTOR SN6AD2 (India) | 119.20 | 1.450 / 0.400 / 0.100 | 5.64 | 31 | prelim |
| Alcon ReSTOR SV25T0 | 119.50 | 1.660 / 0.400 / 0.100 | 5.82 | 70 |  |
| Alcon ReSTOR SV25T0 (India) | 119.30 | 1.630 / 0.400 / 0.100 | 5.84 | 16 | prelim |
| Alcon SA30AL | 118.80 | 1.260 / 0.400 / 0.100 | 5.45 | 115 |  |
| Alcon SA60AT | 118.80 | -0.111 / 0.249 / 0.179 | 5.44 | 1867 |  |
| Alcon SA60AT (Japan) | 118.90 | -1.627 / 0.305 / 0.248 | 5.64 | 501 |  |
| Alcon SN60WF | 119.00 | -0.769 / 0.234 / 0.217 | 5.64 | 5363 |  |
| Alcon SN60WF (Japan) | 119.10 | -1.268 / 0.342 / 0.233 | 5.79 | 202 |  |
| Alcon SN60WF IQ (India) | 118.90 | 1.350 / 0.400 / 0.100 | 5.53 | 68 |  |
| Alcon Toric SN6AT(2-9) | 119.20 | -0.323 / 0.213 / 0.208 | 5.81 | 584 |  |
| Alcon Toric SN6AT(3-5) (Japan) | 119.30 | 1.780 / 0.400 / 0.100 | 5.91 | 77 |  |
| AMO 808C | 119.10 | 1.500 / 0.400 / 0.100 | 5.65 | 130 |  |
| AMO CeeOn 911A | 118.70 | 0.568 / 0.224 / 0.152 | 5.42 | 647 |  |
| AMO ClariFlex | 118.30 | 0.920 / 0.400 / 0.100 | 5.14 | 142 |  |
| AMO ClariFlex (Japan) | 118.70 | 1.380 / 0.400 / 0.100 | 5.50 | 29 | prelim |
| AMO PS60 ANB | 118.70 | 1.150 / 0.400 / 0.100 | 5.46 | 18 | prelim |
| AMO ReZoom NXG1 | 118.30 | 0.920 / 0.400 / 0.100 | 5.20 | 113 |  |
| AMO SA40 Array | 117.90 | 0.650 / 0.400 / 0.100 | 4.90 | 183 |  |
| AMO Sensar 1-piece AAB00 | 119.00 | -1.004 / 0.182 / 0.232 | 5.56 | 415 |  |
| AMO Sensar AR40 | 118.70 | 0.472 / 0.077 / 0.174 | 5.39 | 368 |  |
| AMO Sensar AR40E | 118.70 | -2.420 / 0.157 / 0.288 | 5.41 | 653 |  |
| AMO SI30 NB | 118.50 | 1.230 / 0.400 / 0.100 | 5.34 | 34 | prelim |
| AMO SI40 NB | 118.40 | -0.199 / 0.276 / 0.169 | 5.19 | 1172 |  |
| AMO SI55 | 118.70 | 1.100 / 0.400 / 0.100 | 5.28 | 77 |  |
| AMO Tecnis 1 ZCB00 | 119.30 | -1.302 / 0.210 / 0.251 | 5.80 | 2041 |  |
| AMO Tecnis OptiBlue (Japan) | 119.50 | -0.329 / 0.332 / 0.203 | 5.98 | 247 |  |
| AMO Tecnis Z9000 | 119.20 | -0.663 / 0.117 / 0.232 | 5.71 | 494 |  |
| AMO Tecnis Z9001 | 119.20 | 1.500 / 0.400 / 0.100 | 5.71 | 53 |  |
| AMO Tecnis Z9002 | 118.80 | -1.201 / 0.102 / 0.246 | 5.46 | 1275 |  |
| AMO Tecnis ZA9003 | 119.10 | -1.298 / 0.233 / 0.240 | 5.61 | 1309 |  |
| AMO Tecnis ZM900 | 119.80 | 1.600 / 0.400 / 0.100 | 5.89 | 118 |  |
| AMO Tecnis ZMA00 | 119.50 | -1.750 / 0.242 / 0.266 | 5.80 | 205 |  |
| AMO Tecnis ZMB00 | 119.50 | -1.013 / 0.199 / 0.242 | 5.89 | 184 |  |
| AMO Tecnis ZMB00 (Hongkong) | 119.70 | 1.930 / 0.400 / 0.100 | 6.14 | 51 |  |
| AMO Verisyse 50 aph.retropup. | 116.90 | -0.250 / 0.400 / 0.100 | 4.34 | 20 | prelim |
| ARGONOPTICS EUROMAXX | 118.20 | 0.870 / 0.400 / 0.100 | 5.09 | 105 |  |
| ARGONOPTICS TRICE | 118.50 | 1.130 / 0.400 / 0.100 | 5.28 | 60 |  |
| AUROLAB FH5600AS (India) | 117.80 | 0.680 / 0.400 / 0.100 | 4.92 | 99 |  |
| Bausch&Lomb Akreos Adapt | 118.40 | 0.960 / 0.400 / 0.100 | 5.14 | 62 |  |
| Bausch&Lomb Akreos Adapt-AO | 118.40 | -0.830 / 0.305 / 0.191 | 5.20 | 253 |  |
| Bausch&Lomb Akreos AO MI60 | 119.10 | 1.490 / 0.400 / 0.100 | 5.67 | 102 |  |
| Bausch&Lomb Akreos FIT | 118.10 | 0.780 / 0.400 / 0.100 | 5.02 | 71 |  |
| Bausch&Lomb BL27 | 118.60 | 1.160 / 0.400 / 0.100 | 5.31 | 96 |  |
| Bausch&Lomb enVista MX60 | 119.20 | 1.460 / 0.400 / 0.100 | 5.68 | 152 |  |
| Bausch&Lomb INCISE MJ14 | 118.90 | 1.350 / 0.400 / 0.100 | 5.51 | 90 |  |
| Bausch&Lomb L 122UV | 115.10 | -1.100 / 0.400 / 0.100 | 3.17 | 22 | prelim |
| Bausch&Lomb LI61AO SofPort | 118.50 | 0.057 / 0.186 / 0.171 | 5.29 | 464 |  |
| Bausch&Lomb LI61SE Soflex2 | 118.50 | 1.090 / 0.400 / 0.100 | 5.31 | 98 |  |
| Bausch&Lomb LI61U Soflex | 118.50 | 0.272 / 0.182 / 0.163 | 5.28 | 713 |  |
| Bausch&Lomb S 122UV | 115.10 | -1.130 / 0.400 / 0.100 | 3.13 | 29 | prelim |
| Bausch&Lomb Soflex2 | 118.40 | -1.323 / 0.038 / 0.249 | 5.20 | 216 |  |
| Biotech Vision Bioacryl 60125 discont. | 119.20 | 1.530 / 0.400 / 0.100 | 5.75 | 68 |  |
| Biotech Vision Bioacryl 65 discont. | 118.90 | 1.390 / 0.400 / 0.100 | 5.58 | 180 |  |
| Biotech Vision Eyecryl Plus 600 | 118.40 | 0.940 / 0.400 / 0.100 | 5.19 | 51 |  |
| Biotech Vision Eyecryl Plus ASHFY600 | 118.60 | 1.200 / 0.400 / 0.100 | 5.43 | 49 | prelim |
| Biotech Vision Eyecryl Plus HSAS600 | 118.30 | 1.030 / 0.400 / 0.100 | 5.13 | 58 |  |
| Biotech Vision Eyecryl Toric | 118.70 | 1.300 / 0.400 / 0.100 | 5.45 | 50 |  |
| Biotech Vision Eyecryl-SERT PLHF2 | 118.40 | 1.030 / 0.400 / 0.100 | 5.25 | 55 |  |
| Canon AQ-110NV (Japan) | 119.40 | 0.107 / 0.262 / 0.189 | 5.92 | 479 |  |
| Canon AQ-310AI (Japan) | 120.10 | 2.170 / 0.400 / 0.100 | 6.32 | 68 |  |
| Ciba memory lens CV232 | 119.00 | 1.400 / 0.400 / 0.100 | 5.59 | 61 |  |
| Corneal 600SE | 120.30 | 2.260 / 0.400 / 0.100 | 6.43 | 51 |  |
| Corneal BR110 | 119.00 | 1.400 / 0.400 / 0.100 | 5.60 | 63 |  |
| Corneal Quatrix | 119.80 | 1.910 / 0.400 / 0.100 | 6.04 | 73 |  |
| Croma IDEAlens (HEMA25%) | 118.70 | 1.190 / 0.400 / 0.100 | 5.38 | 49 | prelim |
| Croma Versario Classic | 119.70 | 1.800 / 0.400 / 0.100 | 5.96 | 56 |  |
| Curamed ASPHERICx HD600YA | 118.80 | 1.270 / 0.400 / 0.100 | 5.44 | 53 |  |
| Curamed ASPHERICx HP60CA (+) | 118.50 | 1.100 / 0.400 / 0.100 | 5.28 | 38 | prelim |
| Curamed HD60CZ-YA | 118.90 | 1.300 / 0.400 / 0.100 | 5.50 | 127 |  |
| Curamed PL 600 | 118.80 | 0.209 / 0.124 / 0.182 | 5.46 | 180 |  |
| Curamed SA60CZ | 118.50 | 1.070 / 0.400 / 0.100 | 5.25 | 151 |  |
| Curamed SA700 | 118.80 | 1.310 / 0.400 / 0.100 | 5.52 | 114 |  |
| DISTRA F3000/3013 | 117.70 | 0.560 / 0.400 / 0.100 | 4.79 | 40 | prelim |
| Domilens Domicryl M100 | 119.30 | 1.560 / 0.400 / 0.100 | 5.72 | 144 |  |
| Domilens Flex65L discontinued | 118.90 | 1.450 / 0.400 / 0.100 | 5.68 | 50 |  |
| Domilens Nex-Load Preloaded | 119.50 | 1.730 / 0.400 / 0.100 | 5.87 | 98 |  |
| Domilens Nidek Nex-Acri N4-18YG AKTIS AA | 118.90 | 1.340 / 0.400 / 0.100 | 5.51 | 57 |  |
| Domilens Nidek NS-60YG Aktis SP y | 119.30 | 1.610 / 0.400 / 0.100 | 5.81 | 127 |  |
| Domilens Siflex4 discontinued | 118.90 | 1.180 / 0.400 / 0.100 | 5.43 | 83 |  |
| Domilens Siflex8 discontinued | 118.30 | 1.040 / 0.400 / 0.100 | 5.27 | 34 | prelim |
| Domilens Silens6 discontinued | 118.60 | 1.050 / 0.400 / 0.100 | 5.30 | 110 |  |
| Domilens SofTec1 | 118.40 | 0.980 / 0.400 / 0.100 | 5.16 | 61 |  |
| Dr.Schmidt MC TE discontinued | 119.40 | 1.949 / 0.296 / 0.100 | 5.82 | 336 |  |
| Dr.Schmidt MC575 discontinued | 118.70 | 1.170 / 0.400 / 0.100 | 5.34 | 40 | prelim |
| Dr.Schmidt MC6125AS | 118.70 | 0.885 / 0.312 / 0.125 | 5.36 | 204 |  |
| Dr.Schmidt MP2125 | 119.00 | 1.340 / 0.400 / 0.100 | 5.57 | 107 |  |
| Dr.Schmidt MS612 discontinued | 119.00 | 0.416 / 0.167 / 0.172 | 5.54 | 585 |  |
| Eyecryl ACTV +3DIHFY600 | 118.70 | 1.240 / 0.400 / 0.100 | 5.42 | 55 |  |
| Eyecryl ACTV DIYHS600ROH (*****) | 117.60 | 0.560 / 0.400 / 0.100 | 4.67 | 57 |  |
| Eyekon SC25-Fold | 118.20 | 0.920 / 0.400 / 0.100 | 5.08 | 213 |  |
| Eyeol EYE-DIFF Plus | 118.40 | 0.930 / 0.400 / 0.100 | 5.15 | 75 |  |
| Eyeol Hyflex | 119.20 | 1.540 / 0.400 / 0.100 | 5.69 | 49 | prelim |
| Eyeol LW5752R | 118.90 | 1.270 / 0.400 / 0.100 | 5.46 | 61 |  |
| eyeonics AT-45 crystalens | 119.30 | 0.773 / 0.222 / 0.160 | 5.86 | 236 |  |
| eyeonics AT-50SE crystalens | 119.10 | 0.318 / 0.139 / 0.182 | 5.62 | 224 |  |
| Fritz Ruck HA-4-Q | 118.60 | 1.140 / 0.400 / 0.100 | 5.29 | 88 |  |
| Fritz Ruck PH60-135 | 118.70 | 1.280 / 0.400 / 0.100 | 5.43 | 47 | prelim |
| Gen. Innov. 310 | 118.50 | 1.010 / 0.400 / 0.100 | 5.23 | 83 |  |
| Gen. Innov. XP-55 | 118.50 | 0.272 / 0.245 / 0.154 | 5.25 | 259 |  |
| Hanita B-lens | 118.60 | 1.010 / 0.400 / 0.100 | 5.26 | 52 |  |
| Hanita BunnyLens MF | 118.90 | 1.220 / 0.400 / 0.100 | 5.50 | 36 | prelim |
| Hanita SEELENS | 118.90 | 1.290 / 0.400 / 0.100 | 5.51 | 51 |  |
| Hanita SEELENS AF | 118.80 | 1.250 / 0.400 / 0.100 | 5.42 | 27 | prelim |
| Hanita SEELENS MF | 118.60 | 1.000 / 0.400 / 0.100 | 5.19 | 34 | prelim |
| Hanita SEELENS MICS | 119.00 | 1.380 / 0.400 / 0.100 | 5.56 | 35 | prelim |
| Hexavision HQ-203HEP (+) | 118.50 | 1.140 / 0.400 / 0.100 | 5.28 | 151 |  |
| Hoya AF-1 FY-60AD Hoya iSert PY-60AD (+) | 118.60 | -0.093 / -0.023 / 0.208 | 5.30 | 254 |  |
| Hoya AF-1 VA-60BB | 118.70 | 1.240 / 0.400 / 0.100 | 5.43 | 50 |  |
| Hoya AF-1 YA-60BB | 118.90 | 1.300 / 0.400 / 0.100 | 5.50 | 106 |  |
| Hoya AF-1 YA-60BBR Hoya iSert PY-60R (+) | 118.50 | 1.060 / 0.400 / 0.100 | 5.24 | 134 |  |
| Hoya AF-1 YA-65BB(***) (+) | 118.70 | 1.310 / 0.400 / 0.100 | 5.65 | 88 |  |
| Hoya AF-1(UV) VA60BB (Japan) | 118.70 | 0.458 / 0.150 / 0.172 | 5.52 | 271 |  |
| Hoya AF-1(UV) VA60BBR (Japan) | 118.50 | 1.280 / 0.400 / 0.100 | 5.42 | 90 |  |
| Hoya iMics Y-60H | 118.60 | 1.130 / 0.400 / 0.100 | 5.32 | 113 |  |
| Hoya iMics1 NY-60 (Japan) | 118.70 | 1.290 / 0.400 / 0.100 | 5.46 | 45 | prelim |
| Hoya iMics1 NY-60 Hoya iSert 250/251 (+) | 118.50 | -0.542 / 0.161 / 0.204 | 5.30 | 319 |  |
| Hoya iSert Micro 251 (Japan) | 118.80 | 0.570 / 0.197 / 0.163 | 5.54 | 249 |  |
| Hoya UV55SB (Japan)(**) | 118.60 | 1.380 / 0.400 / 0.100 | 5.57 | 109 |  |
| Hoya VA60BA (Japan) | 118.70 | 1.470 / 0.400 / 0.100 | 5.57 | 27 | prelim |
| HumanOptics 1CU discontinued | 118.70 | 1.833 / 0.225 / 0.094 | 5.38 | 268 |  |
| HumanOptics Aspira-aA(Y) (+) | 118.60 | 0.429 / 0.236 / 0.151 | 5.31 | 295 |  |
| HumanOptics Aspira-aQA | 118.90 | 1.350 / 0.400 / 0.100 | 5.53 | 113 |  |
| HumanOptics Diff-aA(Y) | 118.90 | 1.280 / 0.400 / 0.100 | 5.50 | 87 |  |
| HumanOptics MC611MI discontinued | 119.40 | 1.590 / 0.400 / 0.100 | 5.85 | 66 |  |
| HumanOptics Torica-aA(Y) | 118.30 | 1.180 / 0.400 / 0.100 | 5.35 | 44 | prelim |
| i-Medical 6011C (HP60-PUV) | 119.10 | 1.450 / 0.400 / 0.100 | 5.63 | 51 |  |
| i-Medical Accurate Aspheric | 118.50 | 1.060 / 0.400 / 0.100 | 5.23 | 30 | prelim |
| i-Medical i-Flex | 118.40 | 1.050 / 0.400 / 0.100 | 5.23 | 184 |  |
| i-Medical i-Soft | 118.60 | 1.240 / 0.400 / 0.100 | 5.44 | 107 |  |
| i-Medical Overview AS natural | 119.80 | 1.940 / 0.400 / 0.100 | 6.10 | 49 | prelim |
| Kowa Avansee AN6K | 119.00 | 1.570 / 0.400 / 0.100 | 5.64 | 100 |  |
| Lenstec LS-106 | 119.40 | 1.610 / 0.400 / 0.100 | 5.84 | 33 | prelim |
| Lenstec Softec HDO | 118.50 | 0.055 / 0.178 / 0.173 | 5.27 | 221 |  |
| MBI PreciSAL 300A/300AC | 118.70 | 1.260 / 0.400 / 0.100 | 5.39 | 49 | prelim |
| MBI PreciSAL 302A/302AC | 118.90 | 1.320 / 0.400 / 0.100 | 5.51 | 190 |  |
| MD-TECH I-Stream ISP | 119.20 | 1.460 / 0.400 / 0.100 | 5.74 | 14 | prelim |
| Medicem WIOL-CF | 120.60 | 2.360 / 0.400 / 0.100 | 6.55 | 179 |  |
| Medicontur Bi-Flex 677 (hydrophil acryl) | 118.00 | 0.790 / 0.400 / 0.100 | 4.98 | 103 |  |
| Medicontur Bi-Flex 877 (hydrophob acryl) | 119.10 | 1.390 / 0.400 / 0.100 | 5.61 | 52 |  |
| Medicontur Q-Flex 640 | 118.10 | -0.208 / 0.516 / 0.130 | 5.02 | 264 |  |
| Medicontur Z-Flex 690 | 118.20 | 0.237 / 0.315 / 0.138 | 5.05 | 437 |  |
| MIRA HI-MY (****) | 122.20 | 4.190 / 0.400 / 0.100 | 9.61 | 17 | prelim |
| Morcher 63A (LOTUS Serie) | 118.80 | 1.300 / 0.400 / 0.100 | 5.44 | 50 |  |
| Morcher TYPE 92S | 119.10 | 1.400 / 0.400 / 0.100 | 5.60 | 71 |  |
| Moss Vision Optiflex MO/F-001 | 118.50 | 1.060 / 0.400 / 0.100 | 5.26 | 48 | prelim |
| Moss Vision Optiflex MO/F-013 | 117.90 | 0.710 / 0.400 / 0.100 | 4.85 | 50 |  |
| Moss Vision Optiflex MO/F-022 | 119.10 | 1.370 / 0.400 / 0.100 | 5.61 | 49 | prelim |
| Moss Vision Optiflex MO/F-023 | 119.00 | 1.420 / 0.400 / 0.100 | 5.60 | 49 | prelim |
| Moss Vision Optiflex MO/FNY-D003 | 117.90 | 0.810 / 0.400 / 0.100 | 4.98 | 49 | prelim |
| Moss Vision Optiflex MO/FNYA-01 | 118.00 | 0.690 / 0.400 / 0.100 | 4.91 | 52 |  |
| Moss Vision Optiflex MOHF-D012 | 118.40 | 0.950 / 0.400 / 0.100 | 5.16 | 49 | prelim |
| Nidek Nex-Acri | 119.20 | 1.550 / 0.400 / 0.100 | 5.74 | 72 |  |
| Nidek Nex-Acri AA | 119.20 | 1.560 / 0.400 / 0.100 | 5.73 | 167 |  |
| Oculentis L-301-1 | 118.30 | 1.050 / 0.400 / 0.100 | 5.19 | 51 |  |
| Oculentis L-302 discontinued | 118.90 | 1.300 / 0.400 / 0.100 | 5.45 | 195 |  |
| Oculentis L-302-1 | 118.30 | 1.833 / 0.138 / 0.096 | 5.11 | 530 |  |
| Oculentis L-303 | 118.30 | 0.962 / -0.074 / 0.161 | 5.13 | 250 |  |
| Oculentis L-312 | 118.50 | -2.476 / 0.046 / 0.300 | 5.26 | 1166 |  |
| Oculentis L-313 | 118.10 | 0.820 / 0.400 / 0.100 | 5.01 | 23 | prelim |
| Oculentis L-400 (45C) | 118.40 | 0.202 / 0.075 / 0.179 | 5.19 | 209 |  |
| Oculentis L-401 (47C) | 118.30 | 0.930 / 0.400 / 0.100 | 5.08 | 98 |  |
| Oculentis L-402 | 118.20 | -1.204 / 0.103 / 0.230 | 5.05 | 618 |  |
| Oculentis L-402-1 discontinued | 119.20 | 1.580 / 0.400 / 0.100 | 5.75 | 9 | prelim |
| Oculentis L-403 | 118.40 | 1.020 / 0.400 / 0.100 | 5.16 | 14 | prelim |
| Oculentis L-450 | 118.80 | 1.300 / 0.400 / 0.100 | 5.42 | 27 | prelim |
| Oculentis Lentis Mplus LS-312MF discont | 118.50 | 1.030 / 0.400 / 0.100 | 5.27 | 187 |  |
| Oculentis LS-312-1Y discontinued | 118.30 | -2.017 / 0.066 / 0.271 | 5.12 | 291 |  |
| Oculentis LS-312Y | 118.10 | 0.860 / 0.400 / 0.100 | 5.04 | 86 |  |
| Oculentis LS-313 MF30 | 118.50 | 0.950 / 0.400 / 0.100 | 5.21 | 239 |  |
| Oculentis LS-313 MF30 Japan | 118.50 | 1.020 / 0.400 / 0.100 | 5.33 | 55 |  |
| Oculentis LS-313-1Y discontinued | 118.50 | 1.100 / 0.400 / 0.100 | 5.26 | 20 | prelim |
| Oculentis LS-313Y | 118.40 | 1.020 / 0.400 / 0.100 | 5.19 | 133 |  |
| Oculentis LS-412Y | 118.20 | 0.880 / 0.400 / 0.100 | 5.07 | 44 | prelim |
| Oculentis LS-502-1 | 118.70 | -1.014 / 0.153 / 0.227 | 5.36 | 230 |  |
| Oculentis LS-505 | 118.30 | 1.020 / 0.400 / 0.100 | 5.17 | 39 | prelim |
| Oculentis LU-313 MF30T | 118.20 | 0.870 / 0.400 / 0.100 | 5.11 | 121 |  |
| Oculentis LU-313 MF30T Japan | 118.10 | 1.070 / 0.400 / 0.100 | 5.39 | 37 | prelim |
| Oculentis LU-313T | 118.20 | 0.970 / 0.400 / 0.100 | 5.18 | 162 |  |
| Oculentis LU-800 RZI | 116.60 | -0.110 / 0.400 / 0.100 | 4.10 | 47 | prelim |
| OII Aqua-Sense III | 118.20 | 0.860 / 0.400 / 0.100 | 5.06 | 79 |  |
| OII Aqua-Sense III-130 | 118.40 | 1.020 / 0.400 / 0.100 | 5.23 | 30 | prelim |
| Omni GenNext | 118.40 | 1.020 / 0.400 / 0.100 | 5.18 | 32 | prelim |
| Omni LBHY32UVASP | 119.60 | 1.700 / 0.400 / 0.100 | 5.88 | 49 | prelim |
| Ophtec Artisan 205 aph.retropup. | 116.90 | -0.250 / 0.400 / 0.100 | 4.34 | 20 | prelim |
| Ophtec PC 525 ErgomaX | 118.20 | 0.930 / 0.400 / 0.100 | 5.13 | 51 |  |
| Ophtec PC 530 TrimaX | 118.80 | 1.320 / 0.400 / 0.100 | 5.50 | 80 |  |
| Ophtec PC 545 QuadrimaX | 118.40 | 1.030 / 0.400 / 0.100 | 5.25 | 75 |  |
| Ophtec PC 550 MonomaX | 118.70 | 1.220 / 0.400 / 0.100 | 5.38 | 103 |  |
| Ophtec PC 620 Luna - discontinued | 119.60 | 1.710 / 0.400 / 0.100 | 5.91 | 52 |  |
| Ophtec PC265 | 118.90 | 1.320 / 0.400 / 0.100 | 5.44 | 63 |  |
| Ophtec PC410 | 118.20 | 0.890 / 0.400 / 0.100 | 5.06 | 17 | prelim |
| Ophtec PC420 | 117.90 | 0.710 / 0.400 / 0.100 | 4.92 | 56 |  |
| Ophtec PC430 | 118.20 | 0.860 / 0.400 / 0.100 | 5.08 | 51 |  |
| Ophtec Precizon Monofocal 560 | 118.50 | 1.020 / 0.400 / 0.100 | 5.26 | 25 | prelim |
| Ophtec REF510 | 118.00 | 0.700 / 0.400 / 0.100 | 4.91 | 127 |  |
| OPHTHALMOPro Hyperflex | 120.10 | 2.110 / 0.400 / 0.100 | 6.23 | 155 |  |
| Physiol FineVision | 119.10 | 1.300 / 0.400 / 0.100 | 5.55 | 198 |  |
| Physiol PodEye | 119.40 | 1.700 / 0.400 / 0.100 | 5.85 | 71 |  |
| Physiol Slimflex/Yellowflex | 118.90 | 1.360 / 0.400 / 0.100 | 5.52 | 27 | prelim |
| Polytech Alsiol (VF) | 118.60 | 1.080 / 0.400 / 0.100 | 5.31 | 72 |  |
| Polytech Aurium 404 | 119.30 | 1.570 / 0.400 / 0.100 | 5.78 | 50 |  |
| Polytech Polylens A60 | 118.20 | 0.850 / 0.400 / 0.100 | 5.05 | 57 |  |
| Polytech Polylens A61 (+) | 118.20 | 0.860 / 0.400 / 0.100 | 5.06 | 79 |  |
| Polytech Polylens A62 (+) | 118.60 | 1.150 / 0.400 / 0.100 | 5.35 | 141 |  |
| Polytech Polylens A64 (+) | 118.40 | -1.374 / 0.039 / 0.251 | 5.21 | 680 |  |
| Polytech Polylens AS61 | 118.10 | -2.993 / 0.189 / 0.294 | 5.00 | 429 |  |
| Polytech Polylens AS62 | 118.20 | -1.527 / 0.152 / 0.237 | 5.04 | 342 |  |
| Polytech Polylens AS64 | 118.40 | -1.336 / 0.272 / 0.220 | 5.26 | 261 |  |
| Polytech Polylens AS66/AS66-Y | 118.60 | 0.939 / 0.250 / 0.133 | 5.39 | 283 |  |
| Polytech Polylens H10(Y10) (+) | 118.50 | 1.100 / 0.400 / 0.100 | 5.27 | 55 |  |
| Polytech Polylens H10(Y10)AS | 118.40 | -0.726 / 0.182 / 0.204 | 5.21 | 1954 |  |
| Polytech Polylens H11(Y11) (+) | 119.10 | -0.037 / 0.032 / 0.214 | 5.67 | 253 |  |
| Polytech Polylens H30(Y30) (+) | 118.90 | 1.340 / 0.400 / 0.100 | 5.53 | 181 |  |
| Polytech Polylens H35(Y35) (+) | 118.20 | 0.950 / 0.400 / 0.100 | 5.12 | 41 | prelim |
| Polytech Polylens P265 | 118.90 | 1.320 / 0.400 / 0.100 | 5.44 | 63 |  |
| Polytech Polylens S80 | 117.50 | 0.490 / 0.400 / 0.100 | 4.68 | 155 |  |
| ProOptik PSA 105S | 119.10 | 1.520 / 0.400 / 0.100 | 5.66 | 119 |  |
| Rayner 755 U | 118.80 | 1.600 / 0.210 / 0.110 | 5.42 | 98 |  |
| Rayner C-Flex 570 C | 118.80 | 1.270 / 0.400 / 0.100 | 5.46 | 149 |  |
| Rayner C-flex Asph 970 C | 118.80 | 1.190 / 0.400 / 0.100 | 5.38 | 72 |  |
| Rayner Centerflex 570 H | 118.40 | 1.040 / 0.400 / 0.100 | 5.22 | 118 |  |
| Rayner Mflex 630F | 118.90 | 1.300 / 0.400 / 0.100 | 5.49 | 96 |  |
| Rayner Superflex 620 H | 118.80 | 1.200 / 0.400 / 0.100 | 5.39 | 144 |  |
| Rayner Superflex Asph 920 H | 118.30 | 1.020 / 0.400 / 0.100 | 5.21 | 169 |  |
| Santen W-60 (Japan) | 119.40 | 0.653 / 0.229 / 0.173 | 5.95 | 321 |  |
| Santen X-70 (Japan) | 119.60 | 1.860 / 0.400 / 0.100 | 6.05 | 78 |  |
| SIFI Mini 4 Ready | 119.00 | 1.600 / 0.400 / 0.100 | 5.63 | 21 | prelim |
| SIFI Mini Well | 118.80 | 1.330 / 0.400 / 0.100 | 5.52 | 49 | prelim |
| Soleko FIL611 | 119.10 | 0.051 / 0.140 / 0.197 | 5.68 | 259 |  |
| Staar AQ 2003V | 119.20 | 1.530 / 0.400 / 0.100 | 5.73 | 65 |  |
| Staar AQ 2010 | 119.30 | 1.560 / 0.400 / 0.100 | 5.77 | 49 | prelim |
| Staar KS-3 | 119.10 | 1.510 / 0.400 / 0.100 | 5.67 | 63 |  |
| Staar KS-SP (Japan) | 119.50 | 0.943 / 0.243 / 0.161 | 6.00 | 207 |  |
| Technoko TA625 | 118.70 | 1.170 / 0.400 / 0.100 | 5.32 | 40 | prelim |
| Technomed EASYCARE600 | 118.30 | 0.929 / 0.166 / 0.132 | 5.14 | 242 |  |
| Tekia Tek-Lens Mod.411S | 117.50 | 0.490 / 0.400 / 0.100 | 4.68 | 155 |  |
| Tekia Tek-Lens Mod.614 | 118.20 | 0.850 / 0.400 / 0.100 | 5.05 | 57 |  |
| Visional RBAG | 119.70 | 1.880 / 0.400 / 0.100 | 6.04 | 64 |  |
| Visiontech Medical Optics Liteflex | 118.60 | 1.170 / 0.400 / 0.100 | 5.30 | 63 |  |
| Visiontech Medical Optics Liteflex A | 118.60 | 1.210 / 0.400 / 0.100 | 5.36 | 48 | prelim |
| VSY Acriva UD 613 | 118.40 | 0.950 / 0.400 / 0.100 | 5.19 | 49 | prelim |
| VSY Acriva UD Reviol MF 613 | 118.10 | 0.650 / 0.400 / 0.100 | 4.93 | 48 | prelim |
| VSY Acriva UD Reviol MFB 625 | 117.90 | 0.700 / 0.400 / 0.100 | 4.85 | 49 | prelim |
| VSY Acriva UD Reviol MFM 611 | 118.30 | 0.670 / 0.400 / 0.100 | 4.96 | 49 | prelim |
| W2O CareFlex II | 118.90 | 1.320 / 0.400 / 0.100 | 5.52 | 146 |  |
| WEFISinnovid WEFINO 100 | 119.00 | 1.390 / 0.400 / 0.100 | 5.56 | 50 |  |
| Xcelens IDEA (HEMA26%) | 119.60 | 1.780 / 0.400 / 0.100 | 5.96 | 55 |  |
| Zarracom Focusforce Aspheric AS60125 | 118.90 | 1.330 / 0.400 / 0.100 | 5.54 | 49 | prelim |
| Zarracom Focusforce Basic F260 | 119.20 | 1.550 / 0.400 / 0.100 | 5.68 | 49 | prelim |
| Zarracom Focusforce Ultraflex UF60125 | 119.30 | 1.580 / 0.400 / 0.100 | 5.75 | 48 | prelim |
| ZEISS Acri.Lens 11C | 118.90 | 1.210 / 0.400 / 0.100 | 5.46 | 22 | prelim |
| ZEISS Acri.Lens 12C | 119.20 | 1.420 / 0.400 / 0.100 | 5.64 | 16 | prelim |
| ZEISS Acri.Lyc 45LC | 118.90 | 1.260 / 0.400 / 0.100 | 5.45 | 55 |  |
| ZEISS Acri.Lyc 45S | 118.70 | 1.200 / 0.400 / 0.100 | 5.41 | 158 |  |
| ZEISS AT LISA 801 (Acri.LISA 376D) | 118.10 | 0.820 / 0.400 / 0.100 | 5.06 | 48 | prelim |
| ZEISS AT LISA 809M (AT LISA 366D) | 118.00 | 0.675 / 0.028 / 0.149 | 4.91 | 334 |  |
| Zeiss AT LISA toric 909 MP | 118.40 | 1.020 / 0.400 / 0.100 | 5.30 | 43 | prelim |
| Zeiss AT LISA tri toric 939MP | 118.50 | 0.960 / 0.400 / 0.100 | 5.28 | 73 |  |
| ZEISS AT LISA tri839 MP | 118.90 | -1.477 / 0.058 / 0.262 | 5.48 | 237 |  |
| Zeiss AT LISA tri839 MP Korea | 118.50 | 0.637 / 0.331 / 0.131 | 5.40 | 366 |  |
| ZEISS AT TORBI 709 MP | 118.50 | 1.130 / 0.400 / 0.100 | 5.37 | 48 | prelim |
| ZEISS CT 47LC (Acri.Lyc 47LC) | 117.90 | 0.308 / 0.300 / 0.133 | 4.96 | 192 |  |
| ZEISS CT 47S (Acri.Lyc 47S) | 118.30 | 0.950 / 0.400 / 0.100 | 5.14 | 165 |  |
| ZEISS CT ASPHINA 404 (Acri.Lyc 44LC) | 118.50 | 0.126 / 0.025 / 0.190 | 5.25 | 237 |  |
| ZEISS CT ASPHINA 409M (Acri.Smart 46LC) | 118.30 | 0.322 / 0.162 / 0.158 | 5.12 | 662 |  |
| ZEISS CT ASPHINA 509M (Acri.Smart 36A) | 117.90 | 0.680 / 0.400 / 0.100 | 4.90 | 92 |  |
| ZEISS CT ASPHINA 509M (India) | 117.60 | 0.610 / 0.400 / 0.100 | 4.78 | 198 |  |
| ZEISS CT ASPHINA 603P (XL Stabi ZO) | 118.90 | -0.463 / 0.078 / 0.218 | 5.47 | 442 |  |
| ZEISS CT ASPHINA 604P (Invent ZO) | 118.90 | 1.400 / 0.400 / 0.100 | 5.62 | 21 | prelim |
| Zeiss CT LUCIA 201P/PY | 119.30 | 1.530 / 0.400 / 0.100 | 5.67 | 48 | prelim |
| Zeiss CT LUCIA 601P/PY | 119.20 | 1.490 / 0.400 / 0.100 | 5.70 | 77 |  |
| Zeiss CT LUCIA 611P/PY | 120.10 | 2.100 / 0.400 / 0.100 | 6.27 | 133 |  |
| ZEISS CT SPHERIS 203(P) (XL Stabi, XL Stabi Sky) | 118.50 | 1.050 / 0.400 / 0.100 | 5.23 | 98 |  |
| ZEISS CT SPHERIS 204 (Acri.Lyc 44S) | 118.30 | 0.930 / 0.400 / 0.100 | 5.16 | 177 |  |
| ZEISS CT SPHERIS 209M (Acri.Smart 46S) | 118.30 | 0.574 / 0.166 / 0.148 | 5.16 | 873 |  |
| ZEISS Haptibag | 118.10 | 0.840 / 0.400 / 0.100 | 5.05 | 33 | prelim |
| ZEISS Hydromax | 119.30 | 1.550 / 0.400 / 0.100 | 5.75 | 62 |  |
| ZEISS Stabibag | 118.90 | 1.280 / 0.400 / 0.100 | 5.47 | 132 |  |
| ZEISS TS43 - discontinued | 118.40 | 1.130 / 0.400 / 0.100 | 5.19 | 13 | prelim |
| ZEISS XL Octo Sky | 118.40 | 0.990 / 0.400 / 0.100 | 5.13 | 115 |  |

## 数据来源与时效

ULIB（User Group for Laser Interference Biometry）优化常数，快照日期
2016-10-31，此后 ULIB 已停更。本表与 worker 内置快照一致；worker 升级
可能更新快照，届时本表需同步。如只想确认 worker 实例是否可用，
用 `iol.py health`。

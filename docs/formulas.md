# Képletek és feltételezések

Ez a dokumentum a `src/fincalc/core` kalkulátorainak képleteit és feltételezéseit írja le.
Minden százalékos input százalékban értendő (`7` = 7%). Pénzösszegek `Decimal` típusúak,
kerekítés csak megjelenítéskor történik.

Közös validáció: összegek ≥ 0, hozam és infláció > −100%, futamidő 1–60 év (egész).

## 1. Kamatos kamat havi befizetéssel (`core/compound.py`)

Jelölések: `P` kezdőösszeg, `PMT` havi befizetés, `R` éves névleges hozam,
`r = R / 12` havi kamatláb, `n = év × 12` hónapok száma.

**Feltételezések**

- Havi kamatjóváírás, a megadott éves hozam *névleges* (nem effektív): `r = R / 12`.
  (7% → havi 0,5833%, effektív éves ≈ 7,23%.)
- A befizetés a hónap **végén** történik, így az adott hónapban még nem kamatozik.
- A kezdőösszeg a 0. hónap végén már a számlán van.

**Zárt képlet** (nincs befizetés-emelés):

```
FV = P(1+r)^n + PMT · ((1+r)^n − 1) / r
FV = P + PMT · n                     ha r = 0
```

**Befizetés-emelés** (`g` éves emelés %): a havi befizetés minden új év első hónapjában
(13., 25., … hónap) nő, a `k`-adik évben (0-tól számolva) `PMT · (1+g)^k`.
Ilyenkor az eredmény hónapról hónapra iterálva számolódik:

```
B_0 = P
B_m = B_{m−1} · (1+r) + PMT_m
```

Az idősor mindig iterálva készül; emelés nélkül a végösszeg a zárt képletből jön
(a kettő a Decimal pontosságán belül megegyezik).

**Output**: végösszeg, összes befizetés (kezdőösszeggel együtt), összes hozam
(= végösszeg − befizetések), havi idősor (hónap, egyenleg, kumulált befizetés).

Referencia: 1 000 000 Ft, 7%, 10 év → 2 009 661,38 Ft;
50 000 Ft/hó, 7%, 20 év → 26 046 332,99 Ft (megegyezik az Excel `FV()` eredményével).

## 2. Inflációval korrigált érték (`core/inflation.py`)

```
FV_real = FV / (1 + i)^t,   t = hónap / 12
```

**Feltételezések**

- Az infláció egyenletesen, évesített rátával halad; tört évre tört kitevővel számolunk
  (`(1+i)^(m/12)`), így a reálgörbe sima, nem lépcsős.
- A reálérték "mai forintban" értendő, a számítás indulásának pillanatához képest.
- Állandó inflációs ráta a teljes futamidőre.

A kamatos kamat idősorára is alkalmazható (`real_series`), így egy grafikonon
megjeleníthető a névleges és a reál görbe.

Referencia: 1 000 000 Ft, 4%, 10 év → 675 564,17 Ft mai értéken.

## 3. ETF költséghányad (TER) hatása (`core/etf_costs.py`)

A nettó éves hozam a TER levonása után:

```
R_net = (1 + R)(1 − TER) − 1
```

Ezután a számítás ugyanaz, mint az 1. kalkulátornál, `R_net` éves hozammal
(havi kamatláb `R_net / 12`, befizetés a hónap végén).

**Feltételezések**

- A TER-t évesen, a hozamból levonva modellezzük (a valóságban naponta vonják le
  a nettó eszközértékből; a különbség elhanyagolható).
- Egyéb költség (brókerdíj, árfolyamrés, devizaváltás, követési eltérés) nincs benne.

**Output**: TER-enként végösszeg, nettó hozam, havi idősor, és a különbség forintban a
legolcsóbb (legkisebb TER-ű) alaphoz képest – "ennyibe kerül a drágább alap".
Az eredmények sorrendje megegyezik a bemenet sorrendjével.

Referencia: 1 000 000 Ft + 50 000 Ft/hó, 7% bruttó, 20 év:
TER 0,07% → 29 789 779,09 Ft; 0,22% → 29 168 492,25 Ft; 0,5% → 28 049 430,34 Ft
(a 0,5%-os alap 1 740 348,75 Ft-tal kevesebbet ér a 0,07%-osnál).

## 4. TBSZ vs. sima számla (`core/tbsz.py`, `core/tax.py`)

A két számla ugyanazt a befektetést tartja ugyanazzal a hozammal; az egyetlen különbség
a kivétkor fizetendő adó a nyereség után.

**Időzítés**

- 0. év = gyűjtőév: opcionális egyösszegű befizetés az év elején, plusz havi befizetés
  a gyűjtőév 12 hónapjának végén. Később nincs befizetés.
- Utána `lock_years_held` teljes lekötési év következik, a végén történik a kivét.
  Összes hónap: `(1 + lock_years_held) × 12`.

**Adó**

```
nyereség = bruttó végösszeg − összes befizetés
adó      = max(nyereség, 0) × (SZJA% + szocho%)
nettó    = bruttó végösszeg − adó
megtakarítás = nettó_TBSZ − nettó_sima
```

A kulcsok a `config/tax_hu.yaml`-ból jönnek. A TBSZ sávját a teljesített lekötési évek
száma alapján választjuk: a legnagyobb `min_lock_years` ≤ eltelt évek.

| Eset | SZJA | Szocho |
|---|---|---|
| Sima számla, árfolyamnyereség | 15% | 13% |
| TBSZ, feltörés a lekötés 3. éve előtt (0–2 év) | 15% | 13% |
| TBSZ, a lekötés 3. éve végén (3–4 év) | 10% | 0% (*nyitott kérdés*) |
| TBSZ, a lekötés 5. éve után (5+ év) | 0% | 0% |

**Feltételezések, egyszerűsítések (az MVP nem kezeli)**

- A **szocho éves felső korlátja** nincs figyelembe véve (a szocho mindig a teljes
  nyereség 13%-a).
- **Veszteségkompenzáció** nincs; veszteség esetén az adó 0, de más évekkel nem számolunk el.
- A sima számlán a nyereség csak a végén, egyszerre realizálódik (felhalmozó ETF,
  közbenső eladás és osztalék nélkül), így évközi adófizetés nincs.
- Részleges feltörést (a TBSZ egy részének kivétele) nem modellezünk.
- A TBSZ-en az évek egész lekötési évek; a gyűjtőév alatti feltörést nem vizsgáljuk.

Referencia: 1 000 000 Ft a gyűjtőév elején, 7%, + 5 lekötési év →
bruttó 1 520 105,50 Ft, sima számlán 145 629,54 Ft adó, TBSZ-en 0 Ft.

## Nyitott kérdések

A kódban `TODO(open-question)` jelöléssel szerepelnek
(`grep -rn "TODO(open-question)" src config`).

1. **Szocho a lekötés 3. éve végén** (`config/tax_hu.yaml`): jelenleg 0%-ra feltételezve,
   friss hivatalos forrásból ellenőrizendő.
2. **Befizetés(ek) a gyűjtőévben** (`core/models.py`, `TbszInput`): egyösszegű vagy havi?
   Jelenleg mindkettő támogatott; a felület alapértéke (havi) egyeztetendő.

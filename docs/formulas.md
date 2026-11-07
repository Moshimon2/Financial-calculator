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

## 3. ETF költséghányad (TER)

A 3. lépésben kerül kidolgozásra.

## 4. TBSZ vs. sima számla

A 3. lépésben kerül kidolgozásra.

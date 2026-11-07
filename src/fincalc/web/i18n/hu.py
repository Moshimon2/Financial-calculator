"""Hungarian UI texts. Every user-facing string of the web UI lives here.

Templates receive this dict as ``t`` (``{{ t.compound.title }}``). A second
language is a sibling module with the same keys.
"""

from typing import Any

TEXTS: dict[str, Any] = {
    "lang": "hu",
    "locale": "hu-HU",
    "currency": "Ft",
    "app": {
        "name": "fincalc",
        "tagline": "Pénzügyi kalkulátor",
        "footer": "Saját használatra készült kalkulátor. Az eredmények tájékoztató jellegűek, "
        "nem minősülnek befektetési vagy adótanácsnak.",
    },
    "nav": {
        "dashboard": "Áttekintés",
        "compound": "Kamatos kamat",
        "inflation": "Infláció",
        "etf_costs": "ETF költségek",
        "tbsz": "TBSZ",
    },
    "common": {
        "how_title": "Hogyan számolunk?",
        "table_title": "Évenkénti bontás táblázatban",
        "errors_title": "Ellenőrizd a megadott értékeket:",
        "year": "Év",
        "year_n": "{n}. év",
        "start": "Kezdés",
        "optional": "nem kötelező",
        "chart_label": "Az egyenleg alakulása évenként",
        "updating": "Számolás…",
    },
    "errors": {
        "missing": "kötelező mező",
        "invalid_number": "érvénytelen szám",
        "greater_than_equal": "legalább {ge} legyen",
        "greater_than": "nagyobb legyen, mint {gt}",
        "less_than_equal": "legfeljebb {le} legyen",
        "less_than": "kisebb legyen, mint {lt}",
        "too_short": "legalább egy értéket adj meg",
        "too_long": "túl sok érték",
        "default": "érvénytelen érték",
    },
    "dashboard": {
        "title": "Áttekintés",
        "lead": "Kalkulátorok a hosszú távú befektetéshez: kamatos kamat, infláció, "
        "ETF költségek és TBSZ adóelőny.",
        "last_purchase": "Utolsó vásárlás",
        "total_deposits": "Összes befizetés",
        "transaction_count": "Tranzakciók száma",
        "no_data": "Még nincs importált tranzakció. A Lightyear import hamarosan érkezik.",
        "calculators": "Kalkulátorok",
        "cards": {
            "compound": "Mennyi lesz a havi megtakarításból, névleges és mai értéken.",
            "inflation": "Mennyit ér a jövőbeli összeg mai forintban.",
            "etf_costs": "Mennyibe kerül hosszú távon a magasabb költséghányad.",
            "tbsz": "Mennyit spórolsz a TBSZ-szel egy sima számlához képest.",
        },
    },
    "compound": {
        "title": "Kamatos kamat",
        "lead": "Havi befizetés és kamatos kamat, névleges és inflációval korrigált értéken.",
        "fields": {
            "initial_amount": {"label": "Kezdőösszeg", "suffix": "Ft"},
            "monthly_contribution": {"label": "Havi befizetés", "suffix": "Ft"},
            "annual_return_pct": {"label": "Éves hozam", "suffix": "%"},
            "years": {"label": "Futamidő", "suffix": "év"},
            "annual_contribution_increase_pct": {
                "label": "Befizetés éves emelése",
                "suffix": "%",
                "hint": "Minden új évben ennyivel nő a havi befizetés.",
            },
            "annual_inflation_pct": {
                "label": "Éves infláció",
                "suffix": "%",
                "hint": "Üresen hagyva nincs reálérték.",
            },
        },
        "final_balance": "Végösszeg",
        "final_real_balance": "Mai értéken",
        "total_contributed": "Összes befizetés",
        "total_return": "Összes hozam",
        "series_nominal": "Névleges érték",
        "series_real": "Mai értéken",
        "series_contributed": "Befizetett összeg",
        "how": [
            "Havi kamatozás: a havi kamatláb az éves hozam tizenketted része (névleges éves "
            "hozam, 7% esetén az effektív éves hozam kb. 7,23%).",
            "A befizetés a hónap végén történik, abban a hónapban még nem kamatozik.",
            "Képlet emelés nélkül: FV = P(1+r)ⁿ + PMT·((1+r)ⁿ − 1)/r.",
            "Befizetés-emeléssel hónapról hónapra számolunk; az emelés minden új év első "
            "hónapjától érvényes.",
            "A mai értéket a havi szinten egyenletesen számolt inflációval diszkontáljuk: "
            "FV / (1+i)^(hónap/12).",
            "Adót és költséget ez a kalkulátor nem von le.",
        ],
    },
    "inflation": {
        "title": "Infláció",
        "lead": "Mennyit ér egy jövőbeli összeg mai forintban?",
        "fields": {
            "amount": {"label": "Jövőbeli összeg", "suffix": "Ft"},
            "annual_inflation_pct": {"label": "Éves infláció", "suffix": "%"},
            "years": {"label": "Időtáv", "suffix": "év"},
        },
        "real": "Mai értéken",
        "nominal": "Névleges összeg",
        "loss": "Vásárlóerő-vesztés",
        "how": [
            "Reálérték = névleges összeg / (1 + infláció)^év.",
            "A teljes időtávra állandó inflációval számolunk.",
        ],
    },
    "etf_costs": {
        "title": "ETF költségek",
        "lead": "Hogyan hat a költséghányad (TER) a végösszegre hosszú távon?",
        "fields": {
            "initial_amount": {"label": "Kezdőösszeg", "suffix": "Ft"},
            "monthly_contribution": {"label": "Havi befizetés", "suffix": "Ft"},
            "gross_annual_return_pct": {"label": "Bruttó éves hozam", "suffix": "%"},
            "years": {"label": "Futamidő", "suffix": "év"},
            "ter_1": {"label": "1. alap TER", "suffix": "%"},
            "ter_2": {"label": "2. alap TER", "suffix": "%"},
            "ter_3": {"label": "3. alap TER", "suffix": "%"},
            "ter_pcts": {"label": "TER"},
        },
        "fund": "TER {ter}",
        "net_return": "Nettó hozam: {pct}",
        "cheapest": "Legolcsóbb",
        "costs_more": "ennyibe kerül a legolcsóbbhoz képest",
        "headline": "A legdrágább alap ennyivel kevesebbet ér a futamidő végén",
        "total_contributed": "Összes befizetés",
        "how": [
            "Nettó éves hozam = (1 + bruttó hozam) × (1 − TER) − 1.",
            "Utána ugyanúgy számolunk, mint a kamatos kamat kalkulátorban (havi kamatozás, "
            "befizetés a hónap végén).",
            "A TER-t évesen vonjuk le; a valóságban naponta vonják le, a különbség elhanyagolható.",
            "Brókerdíj, árfolyamrés, devizaváltás és követési eltérés nincs benne.",
        ],
    },
    "tbsz": {
        "title": "TBSZ vs. sima számla",
        "lead": "Mennyi adót spórolsz, ha a TBSZ-t a lekötés végéig tartod?",
        "fields": {
            "initial_amount": {
                "label": "Egyösszegű befizetés",
                "suffix": "Ft",
                "hint": "A gyűjtőév elején.",
            },
            "monthly_contribution": {
                "label": "Havi befizetés a gyűjtőévben",
                "suffix": "Ft",
                "hint": "A gyűjtőév 12 hónapjában; később nincs befizetés.",
            },
            "annual_return_pct": {"label": "Éves hozam", "suffix": "%"},
            "lock_years_held": {
                "label": "Tartás a gyűjtőév után",
                "suffix": "év",
                "hint": "5 év után adómentes, 3 év után kedvezményes.",
            },
        },
        "tbsz_column": "TBSZ",
        "regular_column": "Sima számla",
        "savings": "Ennyit spórolsz a TBSZ-szel",
        "no_savings": "Ennél a tartási időnél a TBSZ nem ad adóelőnyt.",
        "gross_final": "Bruttó végösszeg",
        "total_contributed": "Összes befizetés",
        "gain": "Nyereség",
        "pit": "SZJA ({pct})",
        "social": "Szocho ({pct})",
        "total_tax": "Összes adó",
        "net_final": "Nettó végösszeg",
        "how": [
            "A két számla ugyanazt a befektetést tartja ugyanazzal a hozammal, csak a kivételkor "
            "fizetendő adó különbözik.",
            "Befizetés csak a gyűjtőévben van: egyösszegű az év elején, havi a hónapok végén.",
            "Adó = nyereség × (SZJA + szocho). Veszteség után nincs adó, "
            "veszteségkompenzációval nem számolunk.",
            "Sima számla: 15% SZJA + 13% szocho. TBSZ: a lekötés 3. éve előtt ugyanez, "
            "a 3. év végén 10% SZJA, az 5. év után adómentes. A kulcsok a config/tax_hu.yaml "
            "fájlból jönnek.",
            "A szocho éves felső korlátját nem vesszük figyelembe.",
        ],
    },
}

# Senegal (SN) — législation en Markdown

Part of [LawCodex](https://github.com/LawCodex): the legislation of every country as plain Markdown in git.

Constitution and laws of the Republic of Senegal, in **French** (official language):

* the **Constitution** of 22 January 2001, consolidated with all constitutional laws up to 2018, as published by
  the **Conseil constitutionnel** (with its explanatory note and amendment notes);
* **laws, organic laws, constitutional laws and ordinances published in the Journal officiel de la République du
  Sénégal** (JORS) on its official website www.jo.gouv.sn, retrieved from **Internet Archive captures** of that
  site (the official site no longer answers). Texts are as published in the JO (as enacted, not consolidated).

Retrieved 2026-10-13.

<!-- COUNTS -->
| Directory | Files |
|---|---|
| `codes/` | 10 |
| `constitution/` | 16 |
| `lois-organiques/` | 23 |
| `lois/` | 432 |
| **Total** | **481** |
<!-- /COUNTS -->

## Structure

```
constitution/constitution-2001.md        Constitution (Conseil constitutionnel consolidated text)
constitution/<slug>.md                   constitutional laws found in the JO captures
lois/<year>/loi-<number>.md              laws (year of the law's date)
lois-organiques/<year>/loi-organique-<number>.md
ordonnances/<year>/ordonnance-<number>.md
decrets-lois/<year>/...                  decree-laws (if any)
```

Front matter: `identifier` = number of the text (e.g. `2013-10`); `date` = date in the title; `gazette` = JO issue
number and date; `ministry` = issuing ministry as printed in the JO; `source` = original jo.gouv.sn URL;
`archived_source` = the Internet Archive capture actually used; `status: unknown` (the JO does not track whether a
text is still in force).

Headings: LIVRE / TITRE / CHAPITRE / SECTION → `##`…; articles (`Article premier`, `Art. 2`…) → headings.
The JO pages contain the full text of each act including the *exposé des motifs* / *rapport de présentation*.

## Sources

| Source | URL | Used for |
|---|---|---|
| Conseil constitutionnel du Sénégal — La Constitution | https://conseilconstitutionnel.sn/la-constitution/ | Constitution |
| Journal officiel de la République du Sénégal (www.jo.gouv.sn), via the Internet Archive | http://www.jo.gouv.sn/spip.php?article<N> → https://web.archive.org/web/<timestamp>/http://www.jo.gouv.sn/spip.php?article<N> | laws, ordinances |

Method: the Internet Archive CDX index lists ~10,400 captured JO article pages and ~900 captured JO issue pages
("rubriques", one per JO issue with the titles of its texts). All issue pages were fetched to build an index of
article titles; the articles whose title starts with *Loi*, *Loi organique*, *Loi constitutionnelle*,
*Ordonnance*, *Décret-loi*, *Code* or *Constitution* and that have a capture were then fetched and converted.
Requests to the Internet Archive were spaced by 2.5 s.

## Not covered / known gaps

* **The official JO website www.jo.gouv.sn does not answer** (connection time-outs) — everything except the
  Constitution comes from Internet Archive captures, so coverage is limited to what the Archive captured
  (mostly texts published c. 2005–2016). Laws published after the last captures, and texts whose pages were never
  captured, are missing.
* Decrees, arrêtés and other secondary texts of the JO (the vast majority of the ~10,000 captured pages) are not
  included.
* Codes (Code pénal, Code de la famille, Code du travail, etc.) are only present if the JO page of their enacting
  law was captured; there is no consolidated codes collection.
* Other official sources (Secrétariat général du Gouvernement, Assemblée nationale, Ministry of Justice sites)
  did not answer at retrieval time.

## Copyright

Official texts of the Republic of Senegal, published in the Journal officiel and by the Conseil constitutionnel; no
reuse restriction is stated on these sites. The Markdown conversion is provided as is; the authoritative text is the
printed Journal officiel.

## Regenerating

```sh
python3 scripts/sn_fetch.py     # CDX listing, issue pages, article pages (cached in ../_raw/sn/), Markdown
python3 scripts/sn_readme.py    # updates the counts table
```

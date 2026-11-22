#!/usr/bin/env python3
"""
Merge and de-duplicate literature-search exports from several databases into one CSV,
and print the record counts needed for the review's flow diagram (Fig. 1).

Supported exports (put them all in one folder; file names are free):
  * Scopus            .csv  (Export > CSV, "all available information")
  * IEEE Xplore       .csv  (Export > Search Results > CSV)
  * Web of Science    .txt  (Export > Tab delimited file, Record content: Full record)
                      .xls/.xlsx also work if pandas + openpyxl/xlrd are installed
  * ScienceDirect     .ris  (Export > Export citation to RIS)  or .bib
  * OpenAlex          .csv  (Export > Spreadsheet (.csv))
  * SpringerLink      .csv  (Download search results)
  * ACM DL            .bib  (Export citations > BibTeX)
The database is detected from the file name if it contains one of:
scopus, ieee, wos / webofscience / savedrecs, sciencedirect / sd, openalex, springer, acm.
Otherwise it is guessed from the columns.

Usage:
  python3 merge_search_exports.py <folder_with_exports> [-o merged_records.csv]
                                  [--refs manuscript_dois.txt]

Output columns:
  record_id, title, authors, year, venue, doc_type, doi, abstract, keywords,
  sources (all databases that returned the record), n_sources, in_scopus,
  tak_match  (yes/no/unknown: does title+abstract+keywords match all three query blocks?
              IEEE "All Metadata" and WoS "TS" search more fields than Scopus TITLE-ABS-KEY,
              so screen tak_match = no records out as "outside the Scopus-equivalent fields"),
  possible_duplicate_of (same normalised title, different year), in_manuscript_refs
"""
import argparse, csv, glob, os, re, sys, unicodedata
from collections import Counter, OrderedDict

csv.field_size_limit(sys.maxsize)

# ---------------------------------------------------------------- query blocks (mirror Scopus)
BLOCK1 = ["federated learning", "federated machine learning", "federated optimization",
          "federated optimisation"]
BLOCK2 = ["cyber-physical system", "cyber physical system", "industrial internet of things",
          "iiot", "digital twin", "edge computing", "edge intelligence"]
BLOCK3 = ["continual learning", "lifelong learning", "online learning", "concept drift",
          "uncertainty quantification", "uncertainty-aware", "uncertainty aware",
          "predictive uncertainty", "uncertainty calibration", "topology-aware", "topology aware",
          "topology-preserving", "topology preserving", "network topology", "graph structure"]

# ---------------------------------------------------------------- column candidates per field
CANDS = {
    "title":    ["title", "document title", "article title", "item title", "display_name", "ti"],
    "authors":  ["authors", "author full names", "author names", "au", "af",
                 "authorships.author.display_name"],
    "year":     ["year", "publication year", "publication_year", "py"],
    "venue":    ["source title", "publication title", "so", "primary_location.source.display_name",
                 "journal", "book series title"],
    "doc_type": ["document type", "content type", "document identifier", "type", "dt"],
    "doi":      ["doi", "item doi", "di"],
    "abstract": ["abstract", "ab"],
    "keywords": ["author keywords", "de", "keywords", "index keywords", "ieee terms",
                 "inspec controlled terms", "inspec non-controlled terms", "mesh_terms",
                 "keywords.display_name"],
}


def norm_header(h):
    return re.sub(r"\s+", " ", (h or "").replace("﻿", "").strip().strip('"').lower())


def pick(row, field):
    """First non-empty value among candidate columns; keywords are concatenated."""
    vals = []
    for c in CANDS[field]:
        v = row.get(c)
        if v and str(v).strip():
            if field != "keywords":
                return str(v).strip()
            vals.append(str(v).strip())
    return "; ".join(vals)


def norm_doi(d):
    d = (d or "").strip().lower()
    d = re.sub(r"^(https?://)?(dx\.)?doi\.org/", "", d)
    d = d.replace("doi:", "").strip().rstrip(".")
    return d if d.startswith("10.") else ""


def norm_title(t):
    t = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
    t = re.sub(r"<[^>]+>", " ", t)          # strip HTML tags
    return re.sub(r"[^a-z0-9]+", "", t.lower())


def native_id(row, db):
    """The database's own record identifier (Scopus EID, WoS UT, IEEE article number)."""
    for c in ("eid", "ut", "unique-id", "accession number"):
        v = (row.get(c) or "").strip()
        if v:
            return f"{db}:{v}"
    m = re.search(r"arnumber=(\d+)", row.get("pdf link") or "")
    return f"{db}:{m.group(1)}" if m else ""


def year_of(y):
    m = re.search(r"(19|20)\d{2}", str(y or ""))
    return m.group(0) if m else ""


def detect_db(path, headers):
    n = os.path.basename(path).lower()
    for key, db in [("scopus", "Scopus"), ("ieee", "IEEE Xplore"), ("savedrecs", "Web of Science"),
                    ("webofscience", "Web of Science"), ("wos", "Web of Science"),
                    ("sciencedirect", "ScienceDirect"), ("openalex", "OpenAlex"),
                    ("springer", "SpringerLink"), ("acm", "ACM DL"), ("sd_", "ScienceDirect")]:
        if key in n:
            return db
    h = set(headers)
    if "eid" in h or "link" in h and "source title" in h:
        return "Scopus"
    if "document title" in h and "ieee terms" in h:
        return "IEEE Xplore"
    if "ut" in h or ("ti" in h and "so" in h):
        return "Web of Science"
    if "display_name" in h or "openalex" in " ".join(h):
        return "OpenAlex"
    if "item title" in h:
        return "SpringerLink"
    return os.path.splitext(os.path.basename(path))[0]


# ---------------------------------------------------------------- readers
def read_delimited(path):
    with open(path, encoding="utf-8-sig", errors="replace", newline="") as f:
        sample = f.read(20000)
        f.seek(0)
        delim = "\t" if sample.count("\t") > sample.count(",") else ","
        rdr = csv.reader(f, delimiter=delim)
        rows = list(rdr)
    if not rows:
        return [], []
    headers = [norm_header(h) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(c.strip() for c in r):
            continue
        d = {}
        for h, v in zip(headers, r):        # duplicate headers (e.g. WoS "AU" twice):
            if h not in d or (not d[h].strip() and v.strip()):   # keep first non-empty value
                d[h] = v
        out.append(d)
    return headers, out


def read_excel(path):
    try:
        import pandas as pd
    except ImportError:
        sys.exit(f"{path}: install pandas (and openpyxl/xlrd) or export as tab-delimited .txt")
    df = pd.read_excel(path, dtype=str).fillna("")
    df.columns = [norm_header(c) for c in df.columns]
    return list(df.columns), df.to_dict("records")


def read_ris(path):
    recs, cur = [], {}
    tagmap = {"TI": "title", "T1": "title", "AU": "authors", "A1": "authors", "PY": "year",
              "Y1": "year", "DA": "year", "JO": "venue", "T2": "venue", "JF": "venue",
              "TY": "doc_type", "DO": "doi", "AB": "abstract", "N2": "abstract", "KW": "keywords"}
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            m = re.match(r"^([A-Z][A-Z0-9])  - ?(.*)$", line.rstrip("\n"))
            if not m:
                continue
            tag, val = m.groups()
            if tag == "ER":
                recs.append(cur); cur = {}
                continue
            k = tagmap.get(tag)
            if not k:
                continue
            if k in ("authors", "keywords"):
                cur[k] = (cur.get(k, "") + "; " + val).strip("; ")
            elif k == "year" and cur.get("year"):
                continue
            elif k == "venue" and cur.get("venue"):
                continue
            else:
                cur[k] = val
    return list(CANDS), recs


def read_bib(path):
    txt = open(path, encoding="utf-8-sig", errors="replace").read()
    recs = []
    for m in re.finditer(r"@(\w+)\s*\{[^,]*,(.*?)\n\}", txt, re.S):
        typ, body = m.groups()
        f = {k.lower(): re.sub(r"\s+", " ", v.strip("{} \"")) for k, v in
             re.findall(r"(\w+)\s*=\s*(\{(?:[^{}]|\{[^{}]*\})*\}|\"[^\"]*\"|\d+)", body)}
        recs.append({"title": f.get("title", ""), "authors": f.get("author", "").replace(" and ", "; "),
                     "year": f.get("year", ""), "venue": f.get("journal", f.get("booktitle", "")),
                     "doc_type": typ, "doi": f.get("doi", ""), "abstract": f.get("abstract", ""),
                     "keywords": f.get("keywords", "")})
    return list(CANDS), recs


def read_any(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".ris":
        return read_ris(path)
    if ext == ".bib":
        return read_bib(path)
    if ext in (".xls", ".xlsx"):
        return read_excel(path)
    return read_delimited(path)


# ---------------------------------------------------------------- query post-filter
def _term_rx(term):
    """Scopus-like loose phrase: hyphen = space, plural/possessive endings on the last word."""
    words = re.split(r"[\s\-]+", term.lower())
    last = words[-1]
    last = (re.escape(last[:-1]) + r"(?:y|ies)") if last.endswith("y") else re.escape(last) + r"(?:s|es)?"
    parts = [re.escape(w) for w in words[:-1]] + [last]
    return re.compile(r"(?<![a-z0-9])" + r"[\s\-]+".join(parts) + r"(?![a-z0-9])")


_RX = {}


def has_any(text, terms):
    for t in terms:
        if t not in _RX:
            _RX[t] = _term_rx(t)
        if _RX[t].search(text):
            return True
    return False


def tak_match(title, abstract, keywords):
    if not abstract and not keywords:
        return "unknown"
    text = " " + re.sub(r"\s+", " ", f"{title} {abstract} {keywords}".lower()) + " "
    text = text.replace("optimisation", "optimization").replace("internet-of-things", "internet of things")
    ok = has_any(text, BLOCK1) and has_any(text, BLOCK2) and has_any(text, BLOCK3)
    if ok:
        return "yes"
    return "no" if keywords else "unclear (no keywords exported)"


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("-o", "--out", default="merged_records.csv")
    ap.add_argument("--refs", help="text file with one DOI per line (e.g. the manuscript's reference DOIs)")
    a = ap.parse_args()

    files = sorted(p for p in glob.glob(os.path.join(a.folder, "*"))
                   if os.path.splitext(p)[1].lower() in (".csv", ".txt", ".tsv", ".ris", ".bib", ".xls", ".xlsx"))
    if not files:
        sys.exit("No export files found.")

    ref_dois = set()
    if a.refs:
        ref_dois = {norm_doi(l) for l in open(a.refs, encoding="utf-8") if norm_doi(l)}

    merged = OrderedDict()          # key -> record
    by_doi, by_ty, by_nid = {}, {}, {}
    retrieved = Counter()
    for path in files:
        headers, rows = read_any(path)
        db = detect_db(path, headers)
        for row in rows:
            r = {k: pick(row, k) for k in CANDS}   # map export columns -> standard fields
            if not r["title"]:
                continue
            retrieved[db] += 1
            doi, nt, yr = norm_doi(r["doi"]), norm_title(r["title"]), year_of(r["year"])
            nid = native_id(row, db)
            key = by_doi.get(doi) if doi else None
            key = key or (by_nid.get(nid) if nid else None)
            if key is None:
                # title + year links records ACROSS databases only; inside one database,
                # identical titles without DOI (e.g. proceedings front matter of different
                # volumes) are distinct records, as in Section 2.3 of the manuscript.
                cand = by_ty.get((nt, yr))
                if cand and db not in merged[cand]["sources"]:
                    key = cand
            if key is None:
                key = f"R{len(merged) + 1:05d}"
                merged[key] = {"record_id": key, "title": r["title"], "authors": r["authors"],
                               "year": yr, "venue": r["venue"], "doc_type": r["doc_type"],
                               "doi": doi, "abstract": r["abstract"], "keywords": r["keywords"],
                               "sources": [db]}
            else:
                m = merged[key]
                if db not in m["sources"]:
                    m["sources"].append(db)
                for k in ("authors", "venue", "doc_type", "abstract", "keywords"):
                    if len(r[k]) > len(m[k]):        # keep the most complete field
                        m[k] = r[k]
                if not m["doi"] and doi:
                    m["doi"] = doi
            if doi:
                by_doi[doi] = key
            if nid:
                by_nid[nid] = key
            by_ty[(nt, yr)] = key

    # flag same-title / different-year pairs (conference vs journal versions, early access)
    by_title = {}
    for k, m in merged.items():
        by_title.setdefault(norm_title(m["title"]), []).append(k)

    cols = ["record_id", "title", "authors", "year", "venue", "doc_type", "doi", "abstract",
            "keywords", "sources", "n_sources", "in_scopus", "tak_match", "possible_duplicate_of",
            "in_manuscript_refs"]
    with open(a.out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for k, m in merged.items():
            twins = [x for x in by_title[norm_title(m["title"])] if x != k]
            w.writerow({**m,
                        "sources": "; ".join(m["sources"]),
                        "n_sources": len(m["sources"]),
                        "in_scopus": "yes" if "Scopus" in m["sources"] else "no",
                        "tak_match": tak_match(m["title"], m["abstract"], m["keywords"]),
                        "possible_duplicate_of": "; ".join(twins),
                        "in_manuscript_refs": ("yes" if m["doi"] in ref_dois else "no") if ref_dois else ""})

    total = sum(retrieved.values())
    uniq = len(merged)
    new = sum(1 for m in merged.values() if "Scopus" not in m["sources"])
    print("Records retrieved per database:")
    for db, n in retrieved.most_common():
        print(f"  {db:<16} {n}")
    print(f"Total retrieved:            {total}")
    print(f"Duplicates removed:         {total - uniq}")
    print(f"Unique records:             {uniq}")
    if "Scopus" in retrieved:
        print(f"  of which NOT in Scopus:   {new}")
    tm = Counter(tak_match(m['title'], m['abstract'], m['keywords']) for m in merged.values())
    print("Title/abstract/keyword match: " + ", ".join(f"{k} {v}" for k, v in tm.most_common()))
    nn = Counter(tak_match(m['title'], m['abstract'], m['keywords'])
                 for m in merged.values() if "Scopus" not in m["sources"])
    if "Scopus" in retrieved:
        print("  among records NOT in Scopus: " + ", ".join(f"{k} {v}" for k, v in nn.most_common()))
        print(f"  -> to screen (not 'no'): {sum(v for k, v in nn.items() if k != 'no')}")
    print(f"Wrote {a.out}")


if __name__ == "__main__":
    main()

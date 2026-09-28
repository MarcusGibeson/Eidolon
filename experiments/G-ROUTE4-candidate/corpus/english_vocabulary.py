"""The English vocabulary used to screen invented names (blueprint §4 names "the English vocabulary" without fixing a
word list; this is the list used, and its provenance is recorded in every authoring report).

Source: the en_US and en_GB dictionaries of the locally installed VS Code spell checker (cspell), read-only; nothing
is downloaded. The files are cspell "TrieXv3" tries; `load` below is a line-for-line port of cspell-trie-lib's
importTrieV3 reader and TrieBlobBuilder cursor. Only ASCII words are kept, lowercased.
"""

import hashlib
from pathlib import Path

EXT = Path.home() / ".vscode/extensions/streetsidesoftware.code-spell-checker-4.9.3/node_modules/@cspell"
SOURCES = [EXT / "dict-en_us/en_US.trie.gz", EXT / "dict-en-gb-mit/en_GB.trie.gz"]


def english_vocabulary():
    words, provenance = set(), []
    for path in SOURCES:
        data = path.read_bytes()
        ws = load(path)
        provenance.append({"file": str(path).replace(str(Path.home()), "~"), "sha256": hashlib.sha256(data).hexdigest(),
                           "ascii_words": len(ws)})
        words |= {w.lower() for w in ws}
    return words, {"sources": provenance, "lowercase_words": len(words)}

import gzip
import re
import sys


def load(path):
    text = gzip.open(path, "rt", encoding="utf-8").read()
    lines = text.split("\n")
    m = re.search(r"^base=(\d+)$", text, re.M)
    base = int(m.group(1))
    start = next(i for i, l in enumerate(lines) if "__DATA__" in l)
    data = "\n".join(lines[start + 1:])

    s = {0: [0], 1: [256]}
    frozen = {1}
    size = [2]
    n = [0, 1]
    c = [{"nodeIdx": 0, "pos": 0, "pDepth": -1}]
    st = {"l": 0, "u": 0}

    def new_index():
        return size[0]

    def find(node, b):
        for k in range(1, len(node)):
            if node[k] & 255 == b:
                return k
        return 0

    def p(b, t):
        l = st["l"]
        if l in s and l in frozen:
            copy = list(s[l])
            nl = size[0]; size[0] += 1
            s[nl] = copy
            l = nl
            e = c[st["u"]]
            par = s[e["nodeIdx"]]
            par[e["pos"]] = (par[e["pos"]] & 255) | (l << 8)
        node = s.get(l)
        if node is None:
            node = [0]; s[l] = node
            if l >= size[0]:
                size[0] = l + 1
        r = find(node, b)
        if r:
            i = node[r] >> 8
            a = r
        else:
            i = size[0]
            node.append((i << 8) | b)
            a = len(node) - 1
            size[0] = i + 1   # reserve the index (JS uses s.length; the node is created lazily)
        st["u"] += 1
        u = st["u"]
        rec = {"nodeIdx": l, "pos": a, "pDepth": t}
        if u < len(c):
            c[u] = rec
        else:
            c.append(rec)
        st["l"] = i

    def insert_char(ch):
        l = st["l"]
        if l not in s:
            n.append(l)
        t = st["u"]
        for b in ch.encode("utf-8"):
            p(b, t)

    def mark_eow():
        l = st["l"]
        if l == 1:
            return
        if l in s:
            s[l][0] |= 256
        else:
            e = c[st["u"]]
            par = s[e["nodeIdx"]]
            par[e["pos"]] = (par[e["pos"]] & 255) | 256
            # the reserved index is abandoned; the edge now points at the shared EOW node 1
        st["l"] = 1

    def reference(idx):
        t = n[idx]
        frozen.add(t)
        e = c[st["u"]]
        st["l"] = e["nodeIdx"]
        par = s[st["l"]]
        par[e["pos"]] = (t << 8) | (par[e["pos"]] & 255)

    def back_step(k):
        if k:
            for _ in range(k):
                st["u"] = c[st["u"]]["pDepth"]
            st["l"] = c[st["u"] + 1]["nodeIdx"]

    mode = None
    ref = ""
    i = 0
    BACK = set("<23456789")
    while i < len(data):
        ch = data[i]
        i += 1
        if mode == "ref":
            if ch == ";":
                reference(int(ref, base) + 1)
                mode = None
                ref = ""
            else:
                ref += ch
            continue
        if mode == "back":
            if ch in BACK:
                back_step(1 if ch == "<" else int(ch) - 1)
                continue
            mode = None
        if ch == "$":
            mark_eow(); back_step(1); mode = "back"
        elif ch == "<":
            back_step(1); mode = "back"
        elif ch == "#":
            mode = "ref"
        elif ch == "\\":
            nxt = data[i]; i += 1
            insert_char(nxt)
        elif ch in "\n\r":
            pass
        else:
            insert_char(ch)

    words = set()
    stack = [(0, b"")]
    while stack:
        node_id, prefix = stack.pop()
        node = s.get(node_id, [0])
        if node[0] & 256 and prefix:
            words.add(prefix)
        for e in node[1:]:
            stack.append((e >> 8, prefix + bytes([e & 255])))
    out = set()
    for w in words:
        try:
            out.add(w.decode("ascii"))
        except UnicodeDecodeError:
            pass
    return out



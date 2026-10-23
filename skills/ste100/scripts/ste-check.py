#!/usr/bin/env python3
import argparse
import json
import re
import sys

PROCEDURE_LIMIT = 20
DESCRIPTION_LIMIT = 25
PARAGRAPH_LIMIT = 6

APPROVED_ING = {
    "during", "lighting", "mating", "missing", "opening", "remaining", "routing",
    "servicing", "something", "anything", "everything", "nothing", "thing", "things",
}

PHRASAL_VERBS = [
    "back up", "break down", "bring up", "carry out", "check out", "come up with",
    "figure out", "fill in", "fill out", "find out", "get rid of", "give up",
    "go over", "go through", "hand off", "kick off", "look into", "look up",
    "make up", "pick up", "point out", "put off", "roll back", "run into",
    "set up", "shut down", "sort out", "spin up", "take over", "turn off",
    "turn on", "wrap up",
]

IRREGULAR_PARTICIPLES = {
    "been", "built", "chosen", "done", "found", "given", "gone", "hidden", "kept",
    "known", "left", "lost", "made", "read", "run", "seen", "sent", "set", "shown",
    "taken", "thrown", "written",
}

MODALS = re.compile(r"\b(may|might|should|could|would)\b", re.IGNORECASE)
CONTRACTION = re.compile(
    r"\b(\w+n['’]t|(i|you|we|they|he|she|it|that|there|what|who|here)['’](s|re|ve|ll|d|m))\b",
    re.IGNORECASE,
)
PERFECT = re.compile(r"\b(has|have|had|having)\s+(\w+)\b", re.IGNORECASE)
PROGRESSIVE = re.compile(r"\b(am|is|are|was|were|be|been)\s+(\w+ing)\b", re.IGNORECASE)
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being)\s+(\w+)\b", re.IGNORECASE)

FENCE = re.compile(r"^\s*(```|~~~)")
STEP = re.compile(r"^\s*\d+[.)]\s+")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
PARENS = re.compile(r"\([^()]*\)")
NUMBER_UNIT = re.compile(
    r"\b\d+(\.\d+)?\s?(%|°[CF]|(mm|cm|m|km|g|kg|ms|s|min|h|px|dp|pt|KB|MB|GB|TB|V|A|W|Hz)\b)"
)
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’./_-]*")


def plain(text):
    text = INLINE_CODE.sub("CODE", text)
    text = LINK.sub(r"\1", text)
    text = URL.sub("URL", text)
    return re.sub(r"[*_>]", "", text).strip()


def counted(text):
    text = QUOTED.sub("QUOTE", text)
    text = PARENS.sub("PAREN", text)
    return NUMBER_UNIT.sub("NUMBER", text)


def frontmatter_end(lines):
    if lines and lines[0].strip() == "---":
        for number, line in enumerate(lines[1:], 2):
            if line.strip() == "---":
                return number
    return 0


def blocks(lines):
    block = []
    fenced = False
    skip = frontmatter_end(lines)
    for number, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if FENCE.match(line):
            fenced = not fenced
            continue
        exempt = number <= skip or fenced or stripped.startswith((">", "#"))
        if exempt or not stripped:
            if block:
                yield block
            block = []
            continue
        if LIST_ITEM.match(line) or stripped.startswith("|"):
            if block:
                yield block
            yield [(number, line)]
            block = []
            continue
        block.append((number, line))
    if block:
        yield block


def units(line):
    if line.lstrip().startswith("|"):
        if TABLE_RULE.match(line):
            return []
        return [cell for cell in line.strip().strip("|").split("|") if cell.strip()]
    return [line]


def sentences(text):
    return [part for part in SENTENCE_END.split(text) if WORD.search(part)]


def is_participle(word):
    lowered = word.lower()
    return lowered in IRREGULAR_PARTICIPLES or (lowered.endswith("ed") and len(lowered) > 4)


def without_terms(text, terms):
    for term in terms:
        text = re.sub(rf"\b{re.escape(term)}\b", "TERM", text, flags=re.IGNORECASE)
    return text


def check(text, terms=(), procedure=False):
    findings = []
    terms = sorted(terms, key=len, reverse=True)

    def add(line, rule, level, message):
        findings.append({"line": line, "rule": rule, "level": level, "message": message})

    for block in blocks(text.splitlines()):
        first_line = block[0][1]
        is_step = procedure or STEP.match(first_line) is not None
        limit = PROCEDURE_LIMIT if is_step else DESCRIPTION_LIMIT
        kind = "procedure" if is_step else "description"
        if not first_line.lstrip().startswith("|"):
            joined = " ".join(plain(line) for _, line in block)
            count = len(sentences(joined))
            if count > PARAGRAPH_LIMIT:
                add(block[0][0], "paragraph", "error", f"{count} sentences, limit {PARAGRAPH_LIMIT}")
        for number, line in block:
            for unit in units(line):
                body = LIST_ITEM.sub("", plain(unit))
                for sentence in sentences(counted(body)):
                    words = WORD.findall(sentence)
                    if len(words) > limit:
                        add(number, "length", "error", f"{len(words)} words, {kind} limit {limit}: {sentence[:60]}")
                if ";" in body:
                    add(number, "semicolon", "error", "no semicolons, write two sentences")
                words_only = without_terms(QUOTED.sub("QUOTE", body), terms)
                for match in CONTRACTION.finditer(words_only):
                    add(number, "contraction", "error", f'"{match.group(0)}": write the full words')
                for match in MODALS.finditer(words_only):
                    add(number, "modal", "error", f'"{match.group(0)}": use can, must or will')
                for match in PERFECT.finditer(words_only):
                    if is_participle(match.group(2)):
                        add(number, "tense", "error", f'"{match.group(0)}": use the simple past or present')
                progressive = set()
                for match in PROGRESSIVE.finditer(words_only):
                    if match.group(2).lower() in APPROVED_ING:
                        continue
                    progressive.add(match.group(2).lower())
                    add(number, "tense", "error", f'"{match.group(0)}": use the simple present')
                for match in PASSIVE.finditer(words_only):
                    participle = match.group(2).lower()
                    if participle != "been" and is_participle(participle):
                        level = "error" if is_step else "warn"
                        add(number, "passive", level, f'"{match.group(0)}": name who does it; passive only when the actor is unknown')
                lowered = f" {words_only.lower()} "
                for verb in PHRASAL_VERBS:
                    if re.search(rf"\b{re.escape(verb)}\b", lowered):
                        add(number, "phrasal-verb", "warn", f'"{verb}": use one verb')
                for word in WORD.findall(words_only):
                    bare = word.lower().strip(".'’")
                    if bare.endswith("ing") and len(bare) > 4 and bare not in APPROVED_ING | progressive:
                        add(number, "ing-form", "warn", f'"{word}": only in a technical name')
    return findings


def read_terms(path):
    if not path:
        return []
    with open(path, encoding="utf-8") as handle:
        return [line.strip() for line in handle if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Check English against the measurable ASD-STE100 rules.")
    parser.add_argument("path", nargs="?", help="file to check; reads stdin when omitted")
    parser.add_argument("--terms", help="file of project technical names, one per line")
    parser.add_argument("--procedure", action="store_true", help="treat every sentence as a procedure step")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    args = parser.parse_args()
    text = open(args.path, encoding="utf-8").read() if args.path else sys.stdin.read()
    findings = check(text, read_terms(args.terms), args.procedure)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for item in findings:
            print(f"{item['line']}: {item['level']} {item['rule']}: {item['message']}")
        errors = sum(1 for item in findings if item["level"] == "error")
        print(f"{errors} errors, {len(findings) - errors} warnings")
    sys.exit(1 if any(item["level"] == "error" for item in findings) else 0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
import argparse
import json
import re
import sys

PROCEDURE_LIMIT = 20
DESCRIPTION_LIMIT = 25
PARAGRAPH_LIMIT = 6

NOT_ING_FORMS = {
    "bring", "ceiling", "during", "evening", "king", "morning", "nothing", "ping",
    "ring", "sing", "spring", "sting", "string", "strings", "swing", "thing",
    "things", "wing", "anything", "everything", "something", "heading", "headings",
    "meaning", "meanings", "padding", "setting", "settings", "spacing", "warning",
    "warnings",
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
    "built", "chosen", "done", "found", "given", "hidden", "kept", "known", "left",
    "lost", "made", "read", "run", "seen", "sent", "set", "shown", "taken",
    "thrown", "written",
}

FENCE = re.compile(r"^\s*(```|~~~)")
LIST_STEP = re.compile(r"^\s*\d+[.)]\s+")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+[.)])\s+")
TABLE_RULE = re.compile(r"^\s*\|?\s*:?-{3,}")
INLINE_CODE = re.compile(r"`[^`]*`")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
URL = re.compile(r"https?://\S+")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’./_-]*")
QUOTED = re.compile(r'"[^"]*"|“[^”]*”')
PASSIVE = re.compile(r"\b(is|are|was|were|be|been|being)\s+(\w+)\b", re.IGNORECASE)


def plain(text):
    text = INLINE_CODE.sub("CODE", text)
    text = LINK.sub(r"\1", text)
    text = URL.sub("URL", text)
    return re.sub(r"[*_#>]", "", text).strip()


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
        if number <= skip or line.lstrip().startswith(">"):
            if block:
                yield block
            block = []
            continue
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if not line.strip():
            if block:
                yield block
            block = []
            continue
        if LIST_ITEM.match(line) or line.lstrip().startswith(("|", "#")):
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


def check(text):
    findings = []

    def add(line, rule, level, message):
        findings.append({"line": line, "rule": rule, "level": level, "message": message})

    for block in blocks(text.splitlines()):
        first = block[0][0]
        joined = " ".join(plain(line) for _, line in block)
        is_step = LIST_STEP.match(block[0][1]) is not None
        if "|" not in block[0][1] and not block[0][1].lstrip().startswith("#"):
            count = len(sentences(joined))
            if len(block) > 1 or count > 1:
                if count > PARAGRAPH_LIMIT:
                    add(first, "paragraph", "error", f"{count} sentences, limit {PARAGRAPH_LIMIT}")
        for number, line in block:
            for unit in units(line):
                body = LIST_ITEM.sub("", plain(unit))
                for sentence in sentences(body):
                    words = WORD.findall(sentence)
                    limit = PROCEDURE_LIMIT if is_step else DESCRIPTION_LIMIT
                    if len(words) > limit:
                        kind = "procedure" if is_step else "description"
                        add(number, "length", "error", f"{len(words)} words, {kind} limit {limit}: {sentence[:60]}")
                if ";" in body:
                    add(number, "semicolon", "error", "no semicolons; write two sentences")
                unquoted = QUOTED.sub("QUOTE", body)
                lowered = f" {unquoted.lower()} "
                for verb in PHRASAL_VERBS:
                    if re.search(rf"\b{re.escape(verb)}\b", lowered):
                        add(number, "phrasal-verb", "warn", f'"{verb}": use one verb')
                for word in WORD.findall(unquoted):
                    bare = word.lower().strip(".'’")
                    if bare.endswith("ing") and len(bare) > 4 and bare not in NOT_ING_FORMS:
                        add(number, "ing-form", "warn", f'"{word}": keep only as a technical name')
                for match in PASSIVE.finditer(unquoted):
                    if is_participle(match.group(2)):
                        add(number, "passive", "warn", f'"{match.group(0)}": name who does it, or keep in a description')
    return findings


def main():
    parser = argparse.ArgumentParser(description="Check text against the measurable ASD-STE100 rules.")
    parser.add_argument("path", nargs="?", help="file to check; reads stdin when omitted")
    parser.add_argument("--json", action="store_true", help="print findings as JSON")
    args = parser.parse_args()
    text = open(args.path, encoding="utf-8").read() if args.path else sys.stdin.read()
    findings = check(text)
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

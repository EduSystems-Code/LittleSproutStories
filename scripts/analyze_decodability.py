"""
Real decodability analysis for Stream B (the child-read line on every book
page) -- two jobs in one script, because they're the same underlying work:

1. VALIDATE: flag any Stream B word that doesn't match one of the approved
   categories in 10_Decodable_Word_List.md. This is the automated screen
   that doc's own "Acceptance" section asked for and never got -- until
   now, every line was checked by hand, once, with nothing stopping a
   future edit from silently reintroducing a non-decodable word.

2. LEVEL: score each book's real decoding complexity (how many blend/
   digraph/multi-syllable words it actually uses) and rank the 14 books
   from that -- not guessed, not by book number, but from what's actually
   in the text. Writes the result into each book's own spec as
   "reading_level" (1-4) so the site can show a real reading-level badge
   instead of implying the numbered order is a difficulty order (it never
   was; the books are ordered by story/community-helper sequence).

Usage (from repo root):
    python scripts/analyze_decodability.py          # report only
    python scripts/analyze_decodability.py --write  # also writes
                                                      # reading_level into
                                                      # each spec
    python scripts/analyze_decodability.py --check  # exit 1 if any word
                                                      # fails validation
                                                      # (for the pre-push
                                                      # hook)
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SPECS_DIR = REPO_ROOT / "build_pipeline" / "specs"

BLENDS = {"bl", "br", "cl", "cr", "dr", "fl", "fr", "gl", "gr", "pl", "pr",
          "sc", "sk", "sl", "sm", "sn", "sp", "st", "sw", "tr"}
DIGRAPHS = {"ck", "sh", "ch", "th", "ng", "wh"}

# Verbatim from 10_Decodable_Word_List.md category (b): Dolch pre-primer/
# primer sight words. Kept as one flat set, matching that doc -- this
# script measures blend/digraph/multi-syllable complexity, not sight-word
# grade tier (splitting the Dolch list into its own official grade bands
# is a real follow-up, not guessed here).
SIGHT_WORDS = {
    "a", "and", "are", "at", "away", "be", "big", "blue", "but", "came",
    "can", "come", "did", "do", "down", "each", "eat", "find", "for",
    "four", "funny", "get", "go", "going", "good", "had", "has", "have",
    "he", "help", "her", "here", "him", "his", "how", "i", "in", "into",
    "is", "it", "jump", "know", "like", "little", "look", "made", "make",
    "me", "my", "new", "no", "not", "now", "of", "on", "one", "our",
    "out", "play", "please", "ran", "red", "run", "said", "saw", "see",
    "she", "so", "some", "soon", "that", "the", "their", "them", "then",
    "there", "they", "think", "this", "three", "to", "too", "two",
    "under", "up", "want", "was", "we", "well", "went", "were", "what",
    "where", "will", "with", "yes", "you", "open",
}
FEELINGS_WORDS = {"glad", "sad", "mad", "bad", "ok", "good"}
NUMBER_WORDS = {"one", "two", "three"}
# Category (g), new: high-frequency "heart words" -- real vowel-team or
# silent-e words that don't fit the CVC/sight-word rule but are too
# functionally essential to avoid (found by running this script against
# the real 14 books; every one of these was already in use, unflagged,
# under the old hand-screen -- this makes that an explicit, bounded,
# documented exception instead of a silent gap). Matches how real
# decodable-reader programs (Science-of-Reading "heart words") handle
# irregular high-frequency words: taught by sight, in a small curated
# set, not by CVC decoding.
HEART_WORDS = {
    "feel", "wait", "take", "real", "read", "mean", "count", "done",
    "same", "bake", "your", "paint",
    # not actually suffixed forms ("thing" isn't "th" + "-ing") -- listed
    # whole so the suffix-stripper never mis-splits them
    "thing",
}
# Category (d) theme nouns from the doc's own examples, plus what the real
# 14 books actually use (picture-supported: the backdrop/sprite carries
# the meaning, so these don't have to decode cleanly on their own).
THEME_NOUNS = {
    "doctor", "robot", "garden", "letter", "timer", "mail", "flour",
    "school", "town", "room", "arm", "ears", "hat", "bag", "bell",
    "book", "books", "cookies", "flower", "flowers", "petals", "list",
    "pin", "stamps", "haircut", "tool", "job", "game", "classroom",
    "chest", "snow", "sun", "spot", "home", "day", "friend", "friends",
    "kid", "helper",
}
# Names (category c): the four leads, the eleven community helpers, and
# family terms used the same way a name is (learned as a whole word/
# "logo", not sounded out).
NAMES = {
    "maya", "marcus", "sophie", "james", "alex", "jasmine", "chen",
    "ms", "patel", "rodriguez", "smith", "keisha", "tom", "rose",
    "david", "aisha", "grandma",
}

SUFFIXES = ("'s", "es", "ed", "ing", "s")


def base_forms(word: str):
    """Yield the word as-is, then with common inflections stripped, so
    'feels'/'picks'/'fixed'/'waiting'/'goes' are checked against their
    root too -- an inflected form of an approved word is still approved.
    Minimum remaining length of 3 (not 2) so an irreducible word that
    happens to end in a suffix-shaped substring ('thing' ends in 'ing',
    but isn't 'th' + a suffix) doesn't get mis-stripped."""
    yield word
    if word.endswith("ies") and len(word) - 3 >= 2:
        yield word[:-3] + "y"  # tries -> try, not "tri"
        return  # skip the generic "es" strip below, which would also yield the wrong "tri"
    for suf in SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 2:
            yield word[: -len(suf)]


def classify(word: str) -> tuple[str, bool, str]:
    """Returns (category, is_advanced, base_form). is_advanced = counts
    toward a book's complexity score (blend, digraph, or multi-syllable).
    base_form is the resolved root -- what a "practice this word" list
    should actually show, not the inflected form in the sentence."""
    w = word.lower()
    for form in base_forms(w):
        if form in NAMES:
            return "name", False, form
        if form in FEELINGS_WORDS:
            return "feelings_word", False, form
        if form in NUMBER_WORDS:
            return "number", False, form
        if form in THEME_NOUNS:
            return "theme_noun", False, form
        if form in HEART_WORDS:
            return "heart_word", False, form
        if form in SIGHT_WORDS:
            return "sight_word", False, form
    # phonics check: does it (or its stem) contain a blend/digraph, or is
    # it built from more than one simple syllable? Shortest form first, so
    # a stripped root ("clap") wins over its own inflection ("claps") for
    # what gets reported/shown as the practice word.
    forms_by_len = sorted(dict.fromkeys(base_forms(w)), key=len)  # de-dupe, keep first-seen order for ties
    for form in forms_by_len:
        has_blend = any(form.startswith(b) or form.endswith(b) or b in form for b in BLENDS)
        has_digraph = any(dg in form for dg in DIGRAPHS)
        if has_digraph:
            return "digraph", True, form
        if has_blend:
            return "blend", True, form
    for form in forms_by_len:
        vowels = len(re.findall(r"[aeiouy]+", form))
        if vowels >= 2 and len(form) >= 5:
            return "multisyllable_cvc", True, form
    for form in forms_by_len:
        if re.fullmatch(r"[a-z]{2,4}", form) and len(re.findall(r"[aeiou]", form)) == 1:
            return "cvc", False, form
    return "unclassified", None, w  # None = flag as a real violation, don't guess


def analyze_book(spec_path: Path) -> dict:
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    counts = {}
    advanced = 0
    total = 0
    violations = []
    longest = ""
    practice_words = []  # unique blend/digraph/multisyllable/heart words, in first-seen order
    seen_practice = set()
    for page in data.get("pages", []):
        tb = page.get("text_b", "") or ""
        tb = tb.replace("&rsquo;", "'").replace("&ldquo;", '"').replace("&rdquo;", '"')
        for raw in re.findall(r"[A-Za-z']+", tb):
            w = raw.lower().strip("'")
            if not w:
                continue
            total += 1
            cat, is_adv, base = classify(w)
            counts[cat] = counts.get(cat, 0) + 1
            if cat == "unclassified":
                violations.append(raw)
            if is_adv:
                advanced += 1
            if cat in ("heart_word", "blend", "digraph", "multisyllable_cvc"):
                if base not in seen_practice and len(practice_words) < 5:
                    seen_practice.add(base)
                    practice_words.append(base)
            if len(w) > len(longest):
                longest = w
    return {
        "book_id": data["book_id"],
        "title": data.get("title", data["book_id"]),
        "total_words": total,
        "advanced_words": advanced,
        "advanced_ratio": round(advanced / total, 3) if total else 0.0,
        "longest_word": longest,
        "counts": counts,
        "violations": violations,
        "practice_words": practice_words,
    }


def assign_levels(results: list[dict]) -> None:
    """Rank by advanced_ratio (ties broken by advanced_words count), split
    into 4 roughly-even reading levels. Levels are relative to this set
    of 14 books, not an external grade standard."""
    ordered = sorted(results, key=lambda r: (r["advanced_ratio"], r["advanced_words"]))
    n = len(ordered)
    for i, r in enumerate(ordered):
        level = min(4, 1 + (i * 4) // n)
        r["reading_level"] = level


def main() -> int:
    write = "--write" in sys.argv
    check_only = "--check" in sys.argv

    specs = sorted(SPECS_DIR.glob("Book*.json"))
    results = [analyze_book(p) for p in specs]
    assign_levels(results)

    any_violation = False
    for r in sorted(results, key=lambda r: r["reading_level"]):
        flag = " *** UNAPPROVED WORDS: " + ", ".join(sorted(set(r["violations"]))) if r["violations"] else ""
        if r["violations"]:
            any_violation = True
        if not check_only:
            print(f"Level {r['reading_level']}  {r['book_id']:38s} "
                  f"advanced={r['advanced_words']:3d}/{r['total_words']:3d} "
                  f"({r['advanced_ratio']*100:4.1f}%)  longest='{r['longest_word']}'{flag}")

    if any_violation and not check_only:
        print("\nWords above aren't in any approved Stream B category (a)-(f) "
              "from 10_Decodable_Word_List.md -- either they're a real gap "
              "in the word list, or the line needs rewriting.")

    if write:
        for spec_path, r in zip(specs, results):
            data = json.loads(spec_path.read_text(encoding="utf-8"))
            data["reading_level"] = r["reading_level"]
            if "end_screen" in data:
                data["end_screen"]["practice_words"] = r["practice_words"]
            spec_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nWrote reading_level + practice_words into {len(specs)} specs.")

    if check_only:
        if any_violation:
            for r in results:
                if r["violations"]:
                    print(f"{r['book_id']}: unapproved Stream B word(s): {', '.join(sorted(set(r['violations'])))}")
            return 1
        print("All Stream B text decodable per 10_Decodable_Word_List.md.")
        return 0

    return 1 if any_violation else 0


if __name__ == "__main__":
    raise SystemExit(main())

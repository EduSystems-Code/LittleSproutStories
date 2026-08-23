# Decodable Word List — Stream B

Written August 2026, closing Roadmap item 0.1 (Stream B decodability rewrite).

## The problem this fixes

A screen of the original 112 Stream B lines (8 per book × 14 books) found 118 of 198
unique words falling outside basic CVC patterns plus a kindergarten sight-word list.
Lines like *"Sophie feels embarrassed"* and *"Marcus understands"* are simplified
English, not decodable text — a 5-year-old at the decoding stage cannot sound them
out. Stream A (read by a grown-up) keeps the rich vocabulary; Stream B (read *by the
child*) is now held to the rules below.

## Approved categories

A word in Stream B must be one of:

**(a) CVC / CVCC short-vowel words**, including common initial or final consonant
blends (`bl, br, cl, cr, dr, fl, fr, gl, gr, pl, pr, sc, sk, sl, sm, sn, sp, st, sw, tr`)
and digraphs (`ck, sh, ch, th, ng, wh`) — e.g. *big, hop, glad, brave→(see note), truck,
still, sand, bell, chest*.

**(b) Dolch pre-primer / primer sight words** — the ~90 highest-frequency words a
kindergartner is taught by sight rather than by sounding out: `a, and, are, at, away,
be, big, blue, but, came, can, come, did, do, down, each, eat, find, for, four, funny,
get, go, going, good, had, has, have, he, help, her, here, him, his, how, I, in, into,
is, it, jump, know, like, little, look, made, make, me, my, new, no, not, now, of, on,
one, our, out, play, please, ran, red, run, said, saw, see, she, so, some, soon, that,
the, their, them, then, there, they, think, this, three, to, too, two, under, up, want,
was, we, well, went, were, what, where, will, with, yes, you`.

**(c) Character names** — free pass. Kids learn a name as a logo, the same way they
learn their own.

**(d) One concrete, picture-supported theme noun per line** — a word tied directly to
what the illustration/backdrop already shows (`doctor, robot, garden, letter, timer,
mail, flour, school, town, room, arm, ears`). The picture carries the meaning, so the
word doesn't have to decode cleanly. This is the one deliberate widening beyond a
strict CVC screen, and it's still narrow: it never covers an abstract feeling or
mental-state word, which is the actual problem this rewrite fixes.

**(e) Number words** — `one, two, three`.

**(f) Multi-syllable words built entirely from simple CVC syllables** — `visit,
letter, muffin, rabbit` decode the same way a single CVC word does, one syllable at a
time, so they're allowed even though they're not single-syllable.

## The feelings set

The hard case, and the one the roadmap flagged by name. Precise emotional vocabulary
(*embarrassed, impatient, frustrated, anxious, nervous, worried, doubtful, proud,
brave, calm*) stays in Stream A, where a grown-up reads it aloud. Stream B carries a
small, fixed, fully decodable feelings vocabulary instead:

`glad, sad, mad, bad, OK, good`

A line that needs more nuance than one of those six words gives builds it from
sight words instead of reaching for a bigger feeling word: *"Sophie feels a bit sad"*
rather than *"Sophie feels impatient."*

## What's explicitly still banned

Multisyllable abstract/Latinate words (`different, favorite, special, remembers,
disagree, understands`), any word requiring silent-e or vowel-team knowledge a
kindergartner hasn't been taught yet outside the (b)/(d)/(f) exceptions above, and any
feeling word outside the six listed above.

## Acceptance

Every rewritten line in `books/*.html` was screened by hand against this list. A
future script can automate the screen: strip character names and punctuation, split
on whitespace, and flag anything not in (a)+(b)+(e) unless it appears at most once per
line and matches (d) or (f) by inspection.

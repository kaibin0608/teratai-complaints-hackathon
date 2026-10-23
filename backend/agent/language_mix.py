"""Code check on the LLM's is_mixed_language flag. Owner: Dev A.

The training labels follow one convention: Malay text with English words in it ("monthly service charge",
"account", "branch") is mixed, so the reply uses the customer's preferred_language. Loanwords written as
Malay ("aplikasi", "chat", "log keluar", "kad debit", "bank") don't count. The LLM gets this wrong both ways,
so code settles the two clear cases and leaves everything else to the LLM:

1. The text has no English word at all          -> not mixed, whatever the LLM said.
2. The LLM said not mixed, but the text has at least MIN_EN English and MIN_MS Malay words -> mixed.

Names, places and acronyms (capitalised mid-sentence, or all caps) and greetings / sign-offs are ignored.
"""
from __future__ import annotations

import re

MIN_EN = 1
MIN_MS = 2

ENGLISH = frozenset("""
the my i was is are and but please pls plz with from have has had money me you your this that it to at on in of
for not no did didn't don't can't cannot been be will would could should what when why how who which there here
charge charged charges fee fees refund refunded transfer transferred account acc card credit branch staff service
monthly annual withdraw withdrew withdrawal machine cash full deducted payment paid pay bill transaction
transactions twice double still yet already back help urgent asap sorry received receive sent send failed fail
declined approve approved call called hotline counter queue rude online app logout customer complaint issue problem
update reply wait waiting waited only just one two yesterday today last week month repair scam scammer parcel
police invest investment job emergency phone password link website email pending report join group check
cancel block blocked open close use need want get got buy bought order ordered item purchase purchased shop
login number done
""".split())

MALAY = frozenset("""
saya dan tetapi tapi tidak tak kepada pada akaun wang dengan untuk sila mohon kenapa telah sebanyak lepas semalam
kat dah sudah ada yang ini itu dia mereka kami kita boleh nak hendak tolong bantu duit keluar masuk kena tolak
bulan hari minggu lagi pun je sahaja hanya belum masih bila apa macam mana sebab kerana jadi dari ke di oleh bagi
buat membuat bayar dibayar caj dicaj berganda kali sekali rosak teruk betul lama tunggu lebih kurang dalam
pindahan pemindahan gagal sampai terima sy tp dh x xde tlg smlm utk dgn lbh krg la ni tu org mcm
""".split())

GREETINGS = re.compile(
    r"\b(assalamualaikum|salam|hai|hi|hello|good (?:morning|afternoon|day)|tuan/puan|tuan|puan|"
    r"thank you|thanks|thx|tq|terima kasih)\b",
    re.IGNORECASE,
)


def _words(text: str) -> list[str]:
    """Lower-cased words, without greetings, names, places or acronyms."""
    out: list[str] = []
    for sentence in re.split(r"[.!?\n]+", GREETINGS.sub(" ", text)):
        for i, tok in enumerate(re.findall(r"[A-Za-z][A-Za-z']*", sentence)):
            if (i > 0 and tok[0].isupper()) or (len(tok) > 1 and tok.isupper()):
                continue
            out.append(tok.lower())
    return out


def word_counts(text: str) -> tuple[int, int]:
    """(English words, Malay words) in the text."""
    words = _words(text)
    return sum(w in ENGLISH for w in words), sum(w in MALAY for w in words)


def check_mixed(llm_mixed: bool, text: str) -> bool:
    """The LLM's flag, corrected in the two clear cases above."""
    english, malay = word_counts(text)
    if english == 0:
        return False
    if not llm_mixed and english >= MIN_EN and malay >= MIN_MS:
        return True
    return llm_mixed

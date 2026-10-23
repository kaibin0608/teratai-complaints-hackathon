"""Code-written reply: the fallback when no LLM reply is available (outage, fake:* config, --no-draft). Owner: Dev B.

Plain but correct: it states only the facts from reply_facts, and passes the same combined self-check as an LLM reply.
"""
from __future__ import annotations

from backend.agent.reply_facts import TOPIC, also_raised, build_facts
from backend.contracts import EngineResult

DECLINE_REASON = {
    "EN": {"DUPLICATE_CHARGE": "our records show these are separate charges, not a duplicate",
           "FAILED_TRANSFER": "our records show the transfer was either completed to the recipient's bank or the "
                              "amount has already been returned to your account",
           "ATM_NOT_DISPENSED": "the ATM records show the full amount was dispensed",
           "FEE_DISPUTE": "the fee was charged correctly according to our fee schedule"},
    "MS": {"DUPLICATE_CHARGE": "rekod kami menunjukkan ia adalah caj yang berasingan, bukan caj berganda",
           "FAILED_TRANSFER": "rekod kami menunjukkan pemindahan tersebut telah berjaya ke bank penerima atau amaun "
                              "tersebut telah dipulangkan ke akaun anda",
           "ATM_NOT_DISPENSED": "rekod ATM menunjukkan jumlah penuh telah dikeluarkan",
           "FEE_DISPUTE": "caj tersebut dikenakan dengan betul mengikut jadual caj kami"},
}
GENERIC_DECLINE = {"EN": "our review found that a refund does not apply in this case",
                   "MS": "semakan kami mendapati bayaran balik tidak terpakai dalam kes ini"}


def render(result: EngineResult, also: list[str] | tuple[str, ...] = ()) -> str:
    """also: categories of verified second issues (backend/agent/issues.py); adds one sentence, promises nothing."""
    f = build_facts(result)
    en = f.language == "EN"
    lines = [f"Dear {f.name}," if en and f.name else "Dear Customer," if en
             else f"Yang dihormati {f.name}," if f.name else "Tuan/Puan,", ""]
    topic = TOPIC[f.language][f.category]
    body = [f"Thank you for contacting Teratai Bank about {topic}." if en
            else f"Terima kasih kerana menghubungi Teratai Bank berkenaan {topic}."]
    if f.transaction:
        body.append(f"We have reviewed transaction {f.transaction}." if en
                    else f"Kami telah menyemak transaksi {f.transaction_ms}.")

    if f.purpose == "refunded":
        body.append(f"We have refunded {f.refund} to your account." if en
                    else f"Kami telah membuat bayaran balik sebanyak {f.refund} ke dalam akaun anda.")
    elif f.purpose == "will_credit":
        body.append(f"A refund of {f.refund} will be credited to your account once our review is complete." if en
                    else f"Bayaran balik sebanyak {f.refund} akan dikreditkan ke dalam akaun anda setelah semakan "
                         f"kami selesai.")
    elif f.purpose == "decline":
        reason = DECLINE_REASON[f.language].get(f.category, GENERIC_DECLINE[f.language])
        body.append(f"After reviewing it, we are unable to offer a refund because {reason}." if en
                    else f"Selepas semakan, kami tidak dapat membuat bayaran balik kerana {reason}.")
    elif f.purpose == "investigate":
        body.append("Your report has been passed to our fraud team, who are investigating it as a priority." if en
                    else "Laporan anda telah diserahkan kepada pasukan penipuan kami untuk siasatan segera.")
    else:
        body.append("We are sorry for the inconvenience. Your feedback has been recorded and shared with the team "
                    "concerned so that we can improve." if en
                    else "Kami memohon maaf atas kesulitan ini. Maklum balas anda telah direkodkan dan dimaklumkan "
                         "kepada pihak yang berkenaan untuk penambahbaikan.")

    if also:
        body.append(also_raised(f.language, also))
    body += f.advice
    if f.next_update:
        body.append(f"We will update you by {f.next_update}." if en
                    else f"Kami akan memaklumkan perkembangan kepada anda selewat-lewatnya pada {f.next_update}.")
    lines.append(" ".join(body))
    lines += ["", "Yours sincerely,\nTeratai Bank Customer Care" if en else "Yang benar,\nKhidmat Pelanggan Teratai Bank"]
    return "\n".join(lines)

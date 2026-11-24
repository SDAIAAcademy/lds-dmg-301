"""Counts requests in the model gateway logs of lab 2.2 with the filters you choose. From labs/:

    uv run kit/log_query.py --from 2026-10-05T09:00 --to 2026-10-05T12:00 --route provider_b
    uv run kit/log_query.py --step summarise --route local --level مقيد

Filters (all optional): --from and --to (time, the end not included), --step (summarise or
translate), --route (local or provider_b), --role. With --level, it counts the requests that sent
at least one passage of that level to the generation step. It always prints how many distinct
application numbers those requests sent passages from. It counts; deciding which filters answer
the question is your part.
"""
from __future__ import annotations

import argparse

from common import FILES, read_sheet

p = argparse.ArgumentParser(description="عدّ الطلبات في سجلات بوابة النماذج")
p.add_argument("--from", dest="start", default="")
p.add_argument("--to", dest="end", default="")
p.add_argument("--step", default="")
p.add_argument("--route", default="")
p.add_argument("--role", default="")
p.add_argument("--level", default="")
a = p.parse_args()

d = FILES / "incident"
reqs = read_sheet(d / "requests.xlsx", "الطلبات")
ret = read_sheet(d / "retrieval.xlsx", "الاسترجاع")


def norm(t: str) -> str:
    return t.replace(" ", "T")[:19]


chosen = [r for r in reqs
          if (not a.start or norm(r["الوقت"]) >= norm(a.start))
          and (not a.end or norm(r["الوقت"]) < norm(a.end))
          and (not a.step or r["الخطوة"] == a.step)
          and (not a.route or r["المسار"] == a.route)
          and (not a.role or r["الدور"] == a.role)]
ids = {r["request_id"] for r in chosen}
sent = [x for x in ret if x["request_id"] in ids and x["أُرسل للخطوة التوليدية"] == "نعم"]
if a.level:
    with_level = {x["request_id"] for x in sent if x["المستوى في المصدر"] == a.level}
    sent = [x for x in sent if x["request_id"] in with_level]
    ids = with_level

print(f"المرشحات: {vars(a)}")
print(f"الطلبات: {len(ids)}")
print(f"المقاطع المرسلة إلى الخطوة التوليدية في هذه الطلبات: {len(sent)}")
print(f"أرقام الطلبات المختلفة في هذه المقاطع: {len({x['رقم الطلب'] for x in sent if x['رقم الطلب']})}")

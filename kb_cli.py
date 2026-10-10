"""知识库 CLI：入库、检索、审核、维护。

用法见 SKILL.md；所有数据默认放在技能目录下 kb-data/。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from kb_rag import config as cfg
from kb_rag import ingest as ingest_mod
from kb_rag import maintain as maintain_mod
from kb_rag import query as query_mod
from kb_rag import review as review_mod


def _print(*args, **kwargs) -> None:
    print(*args, **kwargs)
    sys.stdout.flush()


def cmd_ingest(args: argparse.Namespace) -> int:
    paths = [Path(p) for p in args.paths]
    cfg_inst = cfg.load(args.config)
    result = ingest_mod.run_ingest(cfg_inst, paths, trusted=args.trusted)
    _print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_query(args: argparse.Namespace) -> int:
    cfg_inst = cfg.load(args.config)
    filters = {}
    if args.audience:
        filters["audience"] = args.audience
    if args.domain:
        filters["domain"] = args.domain
    if args.security:
        filters["security_level"] = args.security
    if args.status:
        filters["status"] = args.status
    results = query_mod.run_query(cfg_inst, args.question, top_k=args.top_k, filters=filters)
    if args.json:
        _print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        for item in results:
            _print(f"\n[score={item['score']:.4f}] {item['source']}")
            _print(f"  domain={item['domain']} audience={item['audience']} status={item['status']}")
            _print(f"  {item['text']}")
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    cfg_inst = cfg.load(args.config)
    if args.action == "list":
        items = review_mod.list_pending(cfg_inst)
        if args.json:
            _print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            if not items:
                _print("没有待审核切片。")
                return 0
            for it in items:
                _print(f"[{it['id']}] {it['source']}")
                _print(f"  domain={it['domain']} audience={it['audience']} security={it['security_level']}")
                _print(f"  {it['text'][:200]}")
        return 0
    ids = args.ids or None
    if args.action in ("approve", "reject"):
        ok = review_mod.set_status(cfg_inst, args.action, ids)
        _print(f"{args.action}: ok={ok}")
        return 0 if ok else 1
    _print(f"未知 action: {args.action}")
    return 2


def cmd_maintain(args: argparse.Namespace) -> int:
    cfg_inst = cfg.load(args.config)
    if args.action == "check":
        report = maintain_mod.check(cfg_inst)
        _print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.action == "prune":
        count = maintain_mod.prune(cfg_inst)
        _print(f"pruned {count}")
        return 0
    _print(f"未知 action: {args.action}")
    return 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="kb", description="企业本地 RAG 知识库")
    p.add_argument("--config", default=None, help="config.yaml 路径，默认用 SKILL 内置配置")
    sub = p.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="资料自动入库")
    ingest.add_argument("paths", nargs="+", help="文件或目录")
    ingest.add_argument("--trusted", action="store_true", help="跳过待审核，直接可检索")
    ingest.set_defaults(func=cmd_ingest)

    q = sub.add_parser("query", help="语义检索")
    q.add_argument("question", help="查询问题")
    q.add_argument("--top-k", type=int, default=None)
    q.add_argument("--audience", default=None)
    q.add_argument("--domain", default=None)
    q.add_argument("--security", default=None)
    q.add_argument("--status", default="active")
    q.add_argument("--json", action="store_true")
    q.set_defaults(func=cmd_query)

    rv = sub.add_parser("review", help="审核队列")
    rv.add_argument("action", choices=["list", "approve", "reject"])
    rv.add_argument("ids", nargs="*", help="切片 ID，留空表示全部")
    rv.add_argument("--json", action="store_true")
    rv.set_defaults(func=cmd_review)

    mt = sub.add_parser("maintain", help="维护")
    mt.add_argument("action", choices=["check", "prune"])
    mt.set_defaults(func=cmd_maintain)
    return p


def main() -> int:
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
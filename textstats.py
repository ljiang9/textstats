#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""textstats: 给写作者的诚实文本分析。纯标准库，本地运行。"""

import argparse
import json
import re
import sys
from collections import Counter

VERSION = "0.1.0"

CJK_RE = re.compile(r"[\u4e00-\u9fff]")
EN_WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
SENT_END_RE = re.compile(r"[。！？…?!.]+")
PARA_SPLIT_RE = re.compile(r"\n\s*\n")
WS_RE = re.compile(r"\s+")

# 中文停用字（单字）：二元组中任一字命中即排除。极简表，只去掉最吵的虚词。
STOP_CN = set(
    "的了在是和与或有为对就都而及等个这那你我他她它们上下中大小不也还很更最"
    "但如若因然后以及可以一个一种一些我们他们自己这个那个什么怎么哪谁把被让"
    "向从到比跟"
)

# 英文停用词：极简表，覆盖最常见的功能词。
STOP_EN = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was",
    "were", "be", "been", "being", "has", "have", "had", "it", "its",
    "this", "that", "these", "those", "i", "you", "he", "she", "we",
    "they", "them", "his", "her", "their", "our", "my", "your", "as",
    "at", "by", "for", "with", "on", "from", "not", "but", "if",
    "then", "so", "than", "too", "very", "can", "will", "would",
    "should", "could", "do", "does", "did", "about", "into", "over",
    "after", "before", "between", "through", "during", "each", "other",
    "some", "such", "no", "nor", "only", "own", "same", "more",
    "most", "also", "just",
}

HARD_SENT_LEN = 80  # 超过这个字数的句子标为"难读"


def read_text(path=None, use_stdin=False):
    if use_stdin:
        text = sys.stdin.read()
        name = "<stdin>"
    else:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            sys.stderr.write("error: 无法读取文件 %s：%s\n" % (path, e))
            sys.exit(1)
        name = path
    if not text.strip():
        sys.stderr.write("error: 输入为空，没有可分析的文本\n")
        sys.exit(1)
    return text, name


def split_sentences(text):
    return [p.strip() for p in SENT_END_RE.split(text) if p.strip()]


def norm_sent(s):
    return WS_RE.sub(" ", s).strip()


def top_cn_bigrams(text, n=10):
    # 以句子为边界组二元组，避免跨句子拼出无意义的组合
    cnt = Counter()
    for sent in split_sentences(text):
        chars = CJK_RE.findall(sent)
        for a, b in zip(chars, chars[1:]):
            if a in STOP_CN or b in STOP_CN:
                continue
            cnt[a + b] += 1
    return cnt.most_common(n)


def top_en_words(text, n=10):
    cnt = Counter()
    for w in EN_WORD_RE.findall(text):
        w = w.lower()
        if w in STOP_EN or len(w) < 2:
            continue
        cnt[w] += 1
    return cnt.most_common(n)


def fmt_time(minutes):
    secs = int(round(minutes * 60))
    if secs < 60:
        return "约 %d 秒" % secs
    m, s = divmod(secs, 60)
    return "约 %d 分 %d 秒" % (m, s)


def analyze(text):
    cjk_chars = CJK_RE.findall(text)
    en_words = EN_WORD_RE.findall(text)
    sentences = split_sentences(text)
    paragraphs = [p for p in PARA_SPLIT_RE.split(text) if p.strip()]

    minutes = len(cjk_chars) / 400.0 + len(en_words) / 200.0

    longest = max(sentences, key=len) if sentences else ""
    dupes = [
        {"text": t, "count": c}
        for t, c in Counter(norm_sent(s) for s in sentences).most_common()
        if c > 1
    ]

    return {
        "cjk_chars": len(cjk_chars),
        "en_words": len(en_words),
        "sentences": len(sentences),
        "paragraphs": len(paragraphs),
        "reading_time_min": round(minutes, 2),
        "reading_time_text": fmt_time(minutes),
        "longest_sentence": {
            "length": len(longest),
            "text": longest,
            "hard_to_read": len(longest) > HARD_SENT_LEN,
        },
        "top_keywords_cn": [
            {"bigram": b, "count": c} for b, c in top_cn_bigrams(text)
        ],
        "top_keywords_en": [
            {"word": w, "count": c} for w, c in top_en_words(text)
        ],
        "duplicate_sentences": dupes,
    }


def print_report(name, stats):
    print("===== 文本统计：%s =====" % name)
    print()
    print("## 规模")
    print("- 中文字符：%d" % stats["cjk_chars"])
    print("- 英文单词：%d" % stats["en_words"])
    print("- 句子：%d" % stats["sentences"])
    print("- 段落：%d" % stats["paragraphs"])
    print("- 预计阅读时间：%s（按中文 400 字/分钟、英文 200 词/分钟估算）"
          % stats["reading_time_text"])
    print()
    if stats["top_keywords_cn"]:
        print("## 高频中文二元组（top %d）" % len(stats["top_keywords_cn"]))
        for kw in stats["top_keywords_cn"]:
            print("  %s：%d" % (kw["bigram"], kw["count"]))
        print()
    if stats["top_keywords_en"]:
        print("## 高频英文词（top %d）" % len(stats["top_keywords_en"]))
        for kw in stats["top_keywords_en"]:
            print("  %s：%d" % (kw["word"], kw["count"]))
        print()
    ls = stats["longest_sentence"]
    flag = " ⚠️超过 %d 字，可能难读" % HARD_SENT_LEN if ls["hard_to_read"] else ""
    print("## 最长句（%d 字%s）" % (ls["length"], flag))
    print("> " + (ls["text"][:120] + "…" if len(ls["text"]) > 120 else ls["text"]))
    print()
    dupes = stats["duplicate_sentences"]
    if dupes:
        print("## 重复句（%d 组）" % len(dupes))
        for d in dupes:
            t = d["text"]
            print("- 出现 %d 次：%s" % (d["count"], t[:60] + "…" if len(t) > 60 else t))
    else:
        print("## 重复句：无")


def diff_texts(path_a, path_b, as_json=False):
    ta, _ = read_text(path_a)
    tb, _ = read_text(path_b)
    sa = [norm_sent(s) for s in split_sentences(ta)]
    sb = [norm_sent(s) for s in split_sentences(tb)]
    ca, cb = Counter(sa), Counter(sb)
    added = sorted((cb - ca).elements())
    removed = sorted((ca - cb).elements())
    cjk_a = len(CJK_RE.findall(ta))
    cjk_b = len(CJK_RE.findall(tb))
    en_a = len(EN_WORD_RE.findall(ta))
    en_b = len(EN_WORD_RE.findall(tb))
    result = {
        "file_a": path_a,
        "file_b": path_b,
        "delta_cjk_chars": cjk_b - cjk_a,
        "delta_en_words": en_b - en_a,
        "delta_sentences": len(sb) - len(sa),
        "added_sentences": added,
        "removed_sentences": removed,
    }
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("===== 草稿对比 =====")
    print("A: %s" % path_a)
    print("B: %s" % path_b)
    print()
    print("- 中文字符变化：%+d" % result["delta_cjk_chars"])
    print("- 英文单词变化：%+d" % result["delta_en_words"])
    print("- 句子数变化：%+d" % result["delta_sentences"])
    print()
    print("## B 新增的句子（%d）" % len(added))
    for s in added:
        print("+ " + (s[:80] + "…" if len(s) > 80 else s))
    if not added:
        print("（无）")
    print()
    print("## B 删除的句子（%d）" % len(removed))
    for s in removed:
        print("- " + (s[:80] + "…" if len(s) > 80 else s))
    if not removed:
        print("（无）")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="textstats：给写作者的诚实文本分析（纯本地）")
    ap.add_argument("file", nargs="?",
                    help="要分析的文本文件（与 --diff 联用时为文件 A）")
    ap.add_argument("--stdin", action="store_true", help="从标准输入读取")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--diff", metavar="FILE_B",
                    help="对比两个草稿：file（A）与 FILE_B（B）")
    ap.add_argument("--version", action="store_true", help="显示版本")
    args = ap.parse_args(argv)

    if args.version:
        print("textstats " + VERSION)
        return 0

    if args.diff:
        if not args.file:
            ap.error("使用 --diff 时需要指定文件 A")
        diff_texts(args.file, args.diff, as_json=args.json)
        return 0

    if not args.file and not args.stdin:
        ap.error("请指定文件或使用 --stdin")

    text, name = read_text(args.file, args.stdin)
    stats = analyze(text)
    if args.json:
        out = {"input": name}
        out.update(stats)
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print_report(name, stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())

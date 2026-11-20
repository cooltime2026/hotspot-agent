"""다른 채팅에서 따로 쌓은 manifold_agent 폴더를 지금 폴더로 합치기.

  python ml/merge.py <다른_manifold_agent_폴더> [--dry-run]

하는 일
 1) 사진: 같은 파일(md5)이면 건너뜀. 새 사진은 이쪽에 없는 번호로 복사.
    번호가 바뀌면 바꾼 표를 data/merge_log.md 에 남김.
 2) Run(direct_runs.csv): (형상, 유속, 핫스팟)이 같으면
      - 값이 같으면(온도 0.5 ℃, 압력 1% 이내) 하나만 남김
      - 값이 다르면 '충돌'로 보고하고 이쪽 값을 유지 (사용자에게 물어볼 것)
    새 Run은 추가. note의 'img ...' 번호는 바뀐 번호로 고침.
 3) 단면 목록(section_catalog.csv): 사진 번호를 바꿔서 추가 (같은 사진이면 건너뜀).
 4) runs_log.md: 다른 쪽에만 있는 부분을 '합친 기록' 머리말과 함께 뒤에 붙임.
끝나면: python flowdigit/run_all.py && python ml/dataset.py && python ml/intake.py check
"""
from __future__ import annotations
import argparse, csv, re, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import DATA, IMAGES, md5, parse_cells   # noqa: E402


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8"))) if Path(p).exists() else []


def wr(p, rows, fields):
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore"); w.writeheader(); w.writerows(rows)


def remap_text(s, mp):
    """'img 225-229', 'img 208,209', 'img 230' 같은 번호를 바꾼 번호로"""
    def one(n):
        return str(mp.get(int(n), int(n)))

    def rep(m):
        body = m.group(1)
        out = []
        for part in body.split(","):
            if "-" in part:
                a, b = part.split("-")
                nums = [one(k) for k in range(int(a), int(b) + 1)]
                out.append(",".join(nums))
            else:
                out.append(one(part))
        return "img " + ",".join(out)
    return re.sub(r"img ([0-9][0-9,\-]*)", rep, s)


def key(r):
    return (r["design"], round(float(r["inlet_velocity_m_s"]), 3), tuple(parse_cells(r["heat"])))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("other"); ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    O = Path(a.other).resolve()
    if (O / "manifold_agent").is_dir():
        O = O / "manifold_agent"
    if not (O / "data" / "direct_runs.csv").exists():
        sys.exit(f"{O} 에 data/direct_runs.csv 가 없음 (manifold_agent 폴더를 지정)")
    log = [f"\n---\n# 합친 기록: {O}\n"]

    # 1) 사진
    mine = {md5(p): int(p.stem) for p in IMAGES.glob("*.png") if p.stem.isdigit()}
    nxt = max(mine.values(), default=0) + 1
    mp, n_new, n_same = {}, 0, 0
    for p in sorted((O / "images").glob("*.png"), key=lambda x: int(x.stem) if x.stem.isdigit() else 0):
        if not p.stem.isdigit():
            continue
        h = md5(p); n = int(p.stem)
        if h in mine:
            n_same += 1
            if mine[h] != n:
                mp[n] = mine[h]
            continue
        new = n if not (IMAGES / f"{n}.png").exists() else nxt
        if new == nxt:
            nxt += 1
        if not a.dry_run:
            shutil.copy(p, IMAGES / f"{new}.png")
        mine[h] = new; n_new += 1
        if new != n:
            mp[n] = new
    print(f"사진: 새로 {n_new}장, 같은 사진 {n_same}장, 번호 바뀐 것 {len([k for k in mp])}개")
    if mp:
        log.append("사진 번호 바뀜 (다른 쪽 번호 → 여기 번호): " + ", ".join(f"{k}→{v}" for k, v in sorted(mp.items())) + "\n")

    # 2) Run
    runs = rd(DATA / "direct_runs.csv"); fields = list(runs[0].keys())
    have = {key(r): r for r in runs}
    added, dup, conflict = 0, 0, []
    for r in rd(O / "data" / "direct_runs.csv"):
        r = dict(r); r["note"] = remap_text(r.get("note", ""), mp)
        k = key(r)
        if k in have:
            m = have[k]
            dT = abs(float(m["Tmax_bottom_C"]) - float(r["Tmax_bottom_C"]))
            dp = abs(float(m["p_max_Pa"]) - float(r["p_max_Pa"])) / float(m["p_max_Pa"])
            if dT <= 0.5 and dp <= 0.01:
                dup += 1
            else:
                conflict.append((k, m["Tmax_bottom_C"], m["p_max_Pa"], r["Tmax_bottom_C"], r["p_max_Pa"]))
            continue
        runs.append(r); have[k] = r; added += 1
    print(f"Run: 새로 {added}개, 같은 Run {dup}개, 충돌 {len(conflict)}개 → 합친 뒤 총 {len(runs)}개")
    for c in conflict:
        print(f"  충돌 {c[0]}: 여기 {c[1]} ℃ / {c[2]} Pa  vs  다른 쪽 {c[3]} ℃ / {c[4]} Pa  (여기 값 유지, 확인 필요)")
        log.append(f"- 충돌 {c[0]}: 여기 {c[1]} ℃ / {c[2]} Pa vs 다른 쪽 {c[3]} ℃ / {c[4]} Pa (여기 값 유지)\n")
    if not a.dry_run:
        wr(DATA / "direct_runs.csv", runs, fields)

    # 3) 단면 목록
    sec = rd(DATA / "section_catalog.csv"); sf = list(sec[0].keys())
    have_img = {int(r["img"]) for r in sec}
    s_add = 0
    for r in rd(O / "data" / "section_catalog.csv"):
        n = mp.get(int(r["img"]), int(r["img"]))
        if n in have_img:
            continue
        r = dict(r); r["img"] = n; sec.append(r); have_img.add(n); s_add += 1
    print(f"단면 사진 목록: 새로 {s_add}개")
    if not a.dry_run:
        wr(DATA / "section_catalog.csv", sec, sf)

    # 3-1) 형상 정보(입출구·대칭)
    import json
    mp_meta = DATA / "design_meta.json"; om = O / "data" / "design_meta.json"
    if om.exists():
        me = json.loads(mp_meta.read_text(encoding="utf-8")); ot = json.loads(om.read_text(encoding="utf-8"))
        for k, v in ot.items():
            if k not in me:
                me[k] = v; print(f"형상 정보 추가: {k}")
            elif me[k].get("inlets") != v.get("inlets") or me[k].get("mirror_x") != v.get("mirror_x"):
                print(f"  형상 정보 충돌 {k}: 여기 {me[k]}  vs  다른 쪽 {v} (여기 유지, 확인 필요)")
                log.append(f"- 형상 정보 충돌 {k}: 여기 {me[k]} vs 다른 쪽 {v}\n")
        if not a.dry_run:
            mp_meta.write_text(json.dumps(me, ensure_ascii=False, indent=1), encoding="utf-8")

    # 3-2) 16칸 온도·채널층 표 (코드 목록 BOTTOM/PLAN 대신 결과 표를 합침 — 다른 쪽 사진 번호는 바꾼 번호로)
    for name, keyf in [("cell_temps.csv", ("design", "hotspot", "inlet_v_mps")),
                       ("planview_channels.csv", ("design", "hotspot", "inlet_v_mps", "kind")),
                       ("channel_temps.csv", ("design", "hotspot", "inlet_v_mps"))]:
        mine_t = rd(DATA / "ml" / name); oth = rd(O / "data" / "ml" / name)
        if not oth:
            continue
        have_k = {tuple(r[k] for k in keyf) for r in mine_t}
        add = []
        for r in oth:
            if tuple(r[k] for k in keyf) in have_k:
                continue
            r = dict(r); r["img"] = mp.get(int(r["img"]), int(r["img"])); add.append(r)
        print(f"{name}: 새로 {len(add)}행")
        if add and not a.dry_run:
            fields = list(mine_t[0].keys()) if mine_t else list(add[0].keys())
            wr(DATA / "ml" / name, mine_t + add, fields)
            log.append(f"- {name}: 다른 쪽 {len(add)}행 추가 (재계산하려면 cellmaps.py BOTTOM / planview_batch.py PLAN에도 추가 필요)\n")

    # 4) 기록
    mine_log = (DATA / "runs_log.md").read_text(encoding="utf-8")
    other_log = (O / "data" / "runs_log.md").read_text(encoding="utf-8")
    extra = [ln for ln in other_log.splitlines() if ln.strip() and ln not in mine_log]
    if extra:
        log.append("## 다른 쪽에만 있던 기록 (사진 번호는 위 표로 바꿔 읽을 것)\n" + "\n".join(extra) + "\n")
    if not a.dry_run:
        with open(DATA / "runs_log.md", "a", encoding="utf-8") as f:
            f.write("".join(log))
        with open(DATA / "merge_log.md", "a", encoding="utf-8") as f:
            f.write("".join(log))
    print("완료." if not a.dry_run else "(dry-run: 아무것도 안 바꿈)")
    print("다음: python flowdigit/run_all.py && python ml/dataset.py && python ml/intake.py check")


if __name__ == "__main__":
    main()

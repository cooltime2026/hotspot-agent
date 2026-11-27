"""HTML v17(ML 판)의 자동 설계 모양(0.05 mm 마스크) → STEP.  D0·D1 과 같은 형상 규칙(geometry/build_html.py).

  python geometry/build_v17_auto.py out/step_v17/S1_mask.json S1
입력 json: 페이지에서 꺼낸 g.cav(관통층)·g.gro(덮개 홈) 240×240 (1 = 입구망, 2 = 출구망), pin(입구 포트), pout(출구 포트).
형상: 채널 y 0.6~11.4(헤더 없음), 관통층 z 0.5~1.0, 덮개 홈 1.0~1.35, 덮개 0.15, 포트 지름 0.8.
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geometry import build_html as BH
import cadquery as cq

src, name = sys.argv[1], sys.argv[2]
m = json.load(open(src))
BH.NGRID, BH.RES = 240, 0.05
D = {name: dict(head=0, ext=[0.6, 11.4], ports=m["pin"] + m["pout"], P=m["cav"], U=m["gro"], layers=[dict(h=0.5), dict(h=0.35)])}
fluid, solid, ztop, g = BH.build(name, D)
out = Path("out/step_v17"); out.mkdir(parents=True, exist_ok=True)
asm = cq.Assembly(name=f"manifold_{name}")
asm.add(cq.Workplane().add(fluid), name="fluid", color=cq.Color(0.2, 0.5, 1.0, 1))
asm.add(cq.Workplane().add(solid), name="solid", color=cq.Color(0.75, 0.75, 0.78, 1))
asm.save(str(out / f"{name}.step"), exportType="STEP")
BH.preview(name, fluid, dict(ports=m["pin"] + m["pout"]), out / f"{name}_3d.png")
info = dict(name=name, source=m.get("base"), inlets=m["pin"], outlets=m["pout"], height_mm=round(ztop, 3),
            fluid_solids=len(fluid.Solids()), fluid_mm3=round(fluid.Volume(), 3), solid_mm3=round(solid.Volume(), 3),
            overlap_mm3=round(fluid.intersect(solid).Volume(), 6), bottom_faces=len(BH.bottom_cells(solid)),
            dead_fluid_filled_mm3=g["dropped_mm3"], min_edge_mm=round(min(e.Length() for e in fluid.Edges()), 4))
(out / f"{name}.json").write_text(json.dumps(info, ensure_ascii=False, indent=1))
print(info)

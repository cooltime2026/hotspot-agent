#!/bin/bash
# HTML v17 에서 계산 코드(calcA, calcB)와 미리 푼 유량장(hsdata)을 꺼냄 → node cmp.js 로 SimScale 과 비교
cd "$(dirname "$0")"; F=hotspot_agent_v17.html
sed -n 828,1191p $F > calcA.js; sed -n 1194,1557p $F > calcB.js
sed -n 826p $F | sed 's/<script id="hsdata" type="application\/json">//; s/<\/script>.*//' > hsdata.json
cp ../data/design_meta.json .

// Shared helper: run a query with explain() and print the 5 numbers that matter.
// stages:   the plan, outermost first (COLLSCAN = read every doc, IXSCAN = used an index,
//           SORT = sorted in memory, FETCH = loaded the doc after the index,
//           IDHACK = direct lookup by _id, the fastest path)
// keys:     index entries read      docs: documents read      ms: time
function plan(label, cursor) {
  const e = cursor.explain("executionStats");
  const stages = [];
  let s = e.queryPlanner.winningPlan.queryPlan || e.queryPlanner.winningPlan;
  while (s) { stages.push(s.stage); s = s.inputStage; }
  const x = e.executionStats;
  print(`${label.padEnd(34)} ${stages.join(" <- ").padEnd(28)} keys=${x.totalKeysExamined} docs=${x.totalDocsExamined} returned=${x.nReturned} ms=${x.executionTimeMillis}`);
}

// print any value on one line
function show(x) { print(JSON.stringify(x)); }

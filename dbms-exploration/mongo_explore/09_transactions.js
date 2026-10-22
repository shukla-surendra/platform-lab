// 09 — Atomicity: one document is always atomic; several need a transaction.
//
// Story: moving 100 rupees from Asha's wallet to Ravi's = two documents. If the server dies
// between the two updates, money vanishes. A multi-document transaction makes it all-or-nothing.
// (Needs a replica set — this lab runs a 1-node one.)
load("/lab/lib.js");
db = db.getSiblingDB("shop");
db.wallets.drop();
db.wallets.insertMany([{ _id: "asha", bal: 500 }, { _id: "ravi", bal: 0 }]);

const session = db.getMongo().startSession();
const w = session.getDatabase("shop").wallets;

// 1. Success: both updates commit together
session.startTransaction({ readConcern: { level: "snapshot" }, writeConcern: { w: "majority" } });
w.updateOne({ _id: "asha" }, { $inc: { bal: -100 } });
w.updateOne({ _id: "ravi" }, { $inc: { bal: 100 } });
session.commitTransaction();
show(db.wallets.find().toArray());

// 2. Failure halfway: abort undoes the first update too
session.startTransaction();
w.updateOne({ _id: "asha" }, { $inc: { bal: -1000 } });
show({ inside_txn: w.findOne({ _id: "asha" }).bal, outside_txn: db.wallets.findOne({ _id: "asha" }).bal });
session.abortTransaction();                       // e.g. "insufficient balance" check failed
show(db.wallets.find().toArray());

// 3. Two transactions change the same document -> the second fails AT ONCE with
//    WriteConflict (no waiting, unlike Postgres). The app must retry it.
const other = db.getMongo().startSession();
const w2 = other.getDatabase("shop").wallets;
session.startTransaction();
other.startTransaction();
w.updateOne({ _id: "ravi" }, { $inc: { bal: 1 } });
try { w2.updateOne({ _id: "ravi" }, { $inc: { bal: 1 } }); }
catch (e) { show({ secondTxnError: e.codeName, labels: e.errorLabels }); }
other.abortTransaction();

// 4. A plain (non-transaction) write to that doc WAITS until the transaction ends
try { db.wallets.updateOne({ _id: "ravi" }, { $inc: { bal: 1 } }, { maxTimeMS: 1000 }); }
catch (e) { show({ plainWriteWhileTxnOpen: e.codeName }); }
session.abortTransaction();
session.endSession(); other.endSession();

/* Real output (MongoDB 7.0, after seed.js):
[{"_id":"asha","bal":400},{"_id":"ravi","bal":100}]
{"inside_txn":-600,"outside_txn":400}
[{"_id":"asha","bal":400},{"_id":"ravi","bal":100}]
{"secondTxnError":"WriteConflict","labels":["TransientTransactionError"]}
{"plainWriteWhileTxnOpen":"MaxTimeMSExpired"}
*/

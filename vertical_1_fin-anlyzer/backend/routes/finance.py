"""
Finance routes: dashboard aggregation, CRUD, payment & income processing.
"""

from fastapi import APIRouter, HTTPException
from fastapi.encoders import jsonable_encoder
from datetime import datetime, timedelta

from backend.database import get_db
from backend.models import (
    AssetModel, PayableModel, ReceivableModel, TransactionModel,
    AddEntryRequest, ProcessPaymentRequest, ProcessIncomeRequest, PaymentAllocation,
)

router = APIRouter()


def _clean(doc: dict) -> dict:
    """Strip MongoDB's internal _id and serialise ObjectId / datetime fields."""
    doc.pop("_id", None)
    return doc


def _clean_many(docs: list[dict]) -> list[dict]:
    return [_clean(d) for d in docs]


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def get_dashboard():
    """
    Returns a single aggregated payload:
      assets, payables (pending), receivables (pending),
      a 30-day liquidity projection array, and a summary block.
    """
    db = get_db()

    assets      = _clean_many(await db.assets.find().to_list(500))
    payables    = _clean_many(await db.payables.find({"status": "Pending"}).to_list(500))
    receivables = _clean_many(await db.receivables.find({"status": "Pending"}).to_list(500))

    # ── 30-day projection ────────────────────────────────────────────────────
    # Seed: sum of assets with liquidity_score >= 3 (convertible within a month)
    liquid_total = sum(a["value"] for a in assets if a.get("liquidity_score", 0) >= 3)

    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    projection: list[dict] = []
    running = liquid_total

    for day_offset in range(31):
        day = today + timedelta(days=day_offset)

        # Subtract payables due on this day
        for p in payables:
            due = p.get("due_date")
            if isinstance(due, datetime) and due.date() == day.date():
                running -= p["amount"]

        # Add high/med-confidence receivables expected on this day
        for r in receivables:
            exp = r.get("expected_date")
            if (
                isinstance(exp, datetime)
                and exp.date() == day.date()
                and r.get("confidence") in ("High", "Med")
            ):
                running += r["amount"]

        projection.append({
            "date": day.strftime("%Y-%m-%d"),
            "balance": round(running, 2),
        })

    summary = {
        "total_assets":      round(sum(a["value"] for a in assets), 2),
        "total_payables":    round(sum(p["amount"] for p in payables), 2),
        "total_receivables": round(sum(r["amount"] for r in receivables), 2),
    }

    return jsonable_encoder({
        "assets":      assets,
        "payables":    payables,
        "receivables": receivables,
        "projection":  projection,
        "summary":     summary,
    })


# ── Add entry (polymorphic) ───────────────────────────────────────────────────

@router.post("/add_entry", status_code=201)
async def add_entry(request: AddEntryRequest):
    db = get_db()
    entry_type = request.entry_type.strip().lower()
    data = request.data

    # Coerce ISO-string dates → datetime objects for Pydantic
    for date_key in ("due_date", "expected_date"):
        if isinstance(data.get(date_key), str):
            try:
                data[date_key] = datetime.fromisoformat(data[date_key].replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid date format for '{date_key}'. Use ISO 8601."
                )

    if entry_type == "asset":
        model = AssetModel(**data)
        await db.assets.insert_one(model.model_dump())
    elif entry_type == "payable":
        model = PayableModel(**data)
        await db.payables.insert_one(model.model_dump())
    elif entry_type == "receivable":
        model = ReceivableModel(**data)
        await db.receivables.insert_one(model.model_dump())
    else:
        raise HTTPException(status_code=400, detail=f"Unknown entry_type: '{entry_type}'")

    return {"message": f"{entry_type.capitalize()} added successfully", "id": model.id}


# ── Process payment ───────────────────────────────────────────────────────────

@router.post("/process_payment")
async def process_payment(request: ProcessPaymentRequest):
    """
    Multi-asset split payment.
    Validates:
      1. Payable exists and is Pending.
      2. Sum of allocations == payable.amount (within ₹0.01 tolerance).
      3. Every referenced asset exists and has sufficient balance.
    Then executes all deductions + status update atomically inside a single
    MongoDB transaction (all-or-nothing).
    """
    db = get_db()

    payable = await db.payables.find_one({"id": request.payable_id})
    if not payable:
        raise HTTPException(status_code=404, detail="Payable not found")
    if payable["status"] == "Paid":
        raise HTTPException(status_code=400, detail="This payable has already been settled")

    total_allocated = round(sum(a.amount for a in request.allocations), 2)
    payable_amount  = round(payable["amount"], 2)

    if abs(total_allocated - payable_amount) > 0.01:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Allocation mismatch: allocations total ₹{total_allocated:,.2f} "
                f"but payable requires ₹{payable_amount:,.2f}"
            ),
        )

    # Pre-fetch and validate every asset before touching the DB
    asset_docs: dict[str, dict] = {}
    for alloc in request.allocations:
        if alloc.asset_id in asset_docs:
            continue  # already validated
        asset = await db.assets.find_one({"id": alloc.asset_id})
        if not asset:
            raise HTTPException(status_code=404, detail=f"Asset '{alloc.asset_id}' not found")
        asset_docs[alloc.asset_id] = asset

    # Accumulate required amount per asset (handles duplicate asset_ids)
    required: dict[str, float] = {}
    for alloc in request.allocations:
        required[alloc.asset_id] = round(required.get(alloc.asset_id, 0) + alloc.amount, 2)

    for asset_id, needed in required.items():
        asset = asset_docs[asset_id]
        if asset["value"] < needed:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient funds in asset '{asset['name']}': "
                    f"balance ₹{asset['value']:,.2f} < required ₹{needed:,.2f}"
                ),
            )

    # Build transaction records
    transactions = [
        TransactionModel(
            type="payment",
            amount=round(required[asset_id], 2),
            asset_id=asset_id,
            description=f"Split payment to {payable['creditor']}",
        )
        for asset_id in required
    ]

    # ── Atomic commit ────────────────────────────────────────────────────────
    async with await db.client.start_session() as session:
        async with session.start_transaction():
            for asset_id, needed in required.items():
                new_bal = round(asset_docs[asset_id]["value"] - needed, 2)
                await db.assets.update_one(
                    {"id": asset_id},
                    {"$set": {"value": new_bal}},
                    session=session,
                )
            await db.payables.update_one(
                {"id": request.payable_id},
                {"$set": {"status": "Paid"}},
                session=session,
            )
            for tx in transactions:
                await db.transactions.insert_one(tx.model_dump(), session=session)

    return {
        "message":        "Payment processed successfully",
        "payable_id":     request.payable_id,
        "total_paid":     payable_amount,
        "splits":         len(required),
        "transaction_ids": [tx.id for tx in transactions],
    }


# ── Process income ────────────────────────────────────────────────────────────

@router.post("/process_income")
async def process_income(request: ProcessIncomeRequest):
    db = get_db()

    asset      = await db.assets.find_one({"id": request.asset_id})
    receivable = await db.receivables.find_one({"id": request.receivable_id})

    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    if not receivable:
        raise HTTPException(status_code=404, detail="Receivable not found")
    if receivable["status"] == "Received":
        raise HTTPException(status_code=400, detail="This receivable has already been collected")

    new_balance = round(asset["value"] + receivable["amount"], 2)

    # ── Atomic transaction — all-or-nothing ──────────────────────────────────
    tx = TransactionModel(
        type="income",
        amount=receivable["amount"],
        asset_id=request.asset_id,
        description=f"Income from {receivable['source']}",
    )
    async with await db.client.start_session() as session:
        async with session.start_transaction():
            await db.assets.update_one(
                {"id": request.asset_id},
                {"$set": {"value": new_balance}},
                session=session,
            )
            await db.receivables.update_one(
                {"id": request.receivable_id},
                {"$set": {"status": "Received"}},
                session=session,
            )
            await db.transactions.insert_one(tx.model_dump(), session=session)

    return {
        "message": "Income recorded successfully",
        "new_balance": new_balance,
        "transaction_id": tx.id,
    }
import os
import sys
import re

# ── ensure dash/ is on PYTHONPATH so import db_helpers works ───────
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date
import pandas as pd
from webapp.db_helpers import get_db_connection

def fetch_ar_aging_report(
    as_of: date | None = None,
    channels: list[str] | None = None,
    debug: bool = True,
) -> pd.DataFrame:
    """
    Build the delivery-level DataFrame with one row per delivery (shipped or unshipped),
    including invoice + payment info, and write it to output/delivery_level.csv.
    """
    if as_of is None:
        as_of = date.today()
    if channels is None:
        channels = ["Faire", "Wholesale"]
    if debug:
        print(f"[debug] as_of    → {as_of}")
        print(f"[debug] channels → {channels}")

    conn = get_db_connection()
    if debug:
        print(f"[debug] Connected to DB (ENV={os.getenv('ENV')})")

    # ── 1) Orders
    orders_sql = """
        SELECT
            order_id,
            amount_total   AS order_amount,
            channel,
            payment_terms
        FROM raw_odoo_orders
        WHERE state = 'sale'
          AND channel IN %(channels)s
    """
    df_orders = pd.read_sql(orders_sql, conn, params={"channels": tuple(channels)})
    if debug:
        print(f"[debug] df_orders {df_orders.shape}")

    # ── 2) All pickings
    pick_sql = """
        SELECT
            stock_picking_id,
            sale_order_reference,
            date_done,
            scheduled_date,
            state
        FROM raw_odoo_stock_pickings
        WHERE picking_type = 'Delivery Orders'
    """
    df_pick = pd.read_sql(pick_sql, conn)
    # normalize dates
    df_pick[["date_done", "scheduled_date"]] = df_pick[["date_done", "scheduled_date"]].apply(
        lambda s: pd.to_datetime(s, errors="coerce")
    )
    # strip & uppercase SO refs for deterministic join
    df_pick["sale_order_reference"] = (
        df_pick["sale_order_reference"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    if debug:
        print(f"[debug] df_pick {df_pick.shape}")

    # ── 3) Invoices
    inv_sql = """
        SELECT
            move_id,
            invoice_number_ref AS invoice_number,
            sale_order_refs,
            amount_residual,
            invoice_date_due
        FROM raw_odoo_account_moves
        WHERE move_type = 'out_invoice'
          AND state = 'posted'
    """
    df_inv = pd.read_sql(inv_sql, conn)
    # normalize invoice_date_due
    df_inv["invoice_date_due"] = pd.to_datetime(df_inv["invoice_date_due"], errors="coerce")
    # explode sale_order_refs → one row per SO, then strip/upper
    df_inv["sale_order_refs"] = (
        df_inv["sale_order_refs"]
        .str.strip("[]")
        .str.replace("'", "", regex=False)
    )
    df_inv = (
        df_inv
        .assign(sale_order_reference=lambda d: d["sale_order_refs"].str.split(","))
        .explode("sale_order_reference")
        .drop(columns=["sale_order_refs"])
    )
    df_inv["sale_order_reference"] = (
        df_inv["sale_order_reference"]
        .astype(str)
        .str.strip()
        .str.upper()
    )
    # cast move_id to int for matching
    df_inv["move_id"] = df_inv["move_id"].astype(int)
    if debug:
        print(f"[debug] df_inv exploded {df_inv.shape}")

    # ── 4) Payments
    pay_sql = """
        SELECT
            payment_id,
            invoice_move_id,
            invoice_number_ref,
            amount   AS payment_amount
        FROM raw_odoo_account_payments
    """
    df_pay = pd.read_sql(pay_sql, conn)
    # cast invoice_move_id to int
    df_pay["invoice_move_id"] = df_pay["invoice_move_id"].astype(int)
    # group to get list of payments + total paid per invoice_id
    df_pay_grp = (
        df_pay
        .groupby("invoice_move_id", as_index=False)
        .agg({
            "payment_id":    lambda ids: [int(i) for i in ids],
            "payment_amount": "sum"
        })
        .rename(columns={
            "payment_id":   "payment_ids",
            "payment_amount": "total_paid"
        })
    )
    if debug:
        print(f"[debug] df_pay_grp {df_pay_grp.shape}")

    # also prepare fallback by invoice_number_ref
    df_pay_num = (
        df_pay
        .groupby("invoice_number_ref", as_index=True)
        .agg({
            "payment_id":    lambda ids: [int(i) for i in ids],
            "payment_amount": "sum"
        })
        .rename(columns={
            "payment_id":   "payment_ids_num",
            "payment_amount": "total_paid_num"
        })
    )

    conn.close()
    if debug:
        print("[debug] Closed DB connection")

    # ── 5) Match invoices → pickings (only shipped)
    df_ship_pick = df_pick[df_pick["state"] == "done"].copy()
    df_cand = df_inv.merge(
        df_ship_pick,
        on="sale_order_reference",
        how="inner",
        suffixes=("_inv", "_pick")
    )
    if debug:
        print(f"[debug] df_cand sample:\n{df_cand.head()}")
    # choose best invoice for each move_id by minimal |date_done - invoice_date_due|
    df_cand["diff_days"] = (df_cand["date_done"] - df_cand["invoice_date_due"]).abs().dt.days
    best = df_cand.groupby("move_id")["diff_days"].idxmin()
    df_match = df_cand.loc[best].copy()

    # ── 6) Build shipped deliveries
    df_ship = df_match.rename(columns={
        "sale_order_reference":   "order_id",
        "stock_picking_id":       "delivery_id",
        "date_done":              "ship_date",
        "move_id":                "invoice_id",
        "invoice_number":         "invoice_number",
        "amount_residual":        "invoice_amount_residual",
        "invoice_date_due":       "due_date"
    })[[
        "order_id", "delivery_id", "ship_date", "scheduled_date",
        "invoice_id", "invoice_number", "invoice_amount_residual", "due_date"
    ]]
    df_ship["invoice_id"] = df_ship["invoice_id"].astype(int)
    df_ship = df_ship.merge(
        df_orders[["order_id","channel","payment_terms","order_amount"]],
        on="order_id", how="left"
    )
    # primary join on invoice_id
    df_ship = df_ship.merge(
        df_pay_grp,
        left_on="invoice_id", right_on="invoice_move_id",
        how="left"
    )
    # fill in missing
    df_ship["payment_ids"]  = df_ship["payment_ids"].apply(lambda x: x if isinstance(x, list) else [])
    df_ship["total_paid"]   = df_ship["total_paid"].fillna(0.0)
    # fallback join on invoice_number
    mask = df_ship["total_paid"] == 0
    if mask.any():
        fb = df_ship[mask].merge(
            df_pay_num,
            left_on="invoice_number", right_index=True,
            how="left"
        )
        df_ship.loc[mask, "payment_ids"] = fb["payment_ids_num"].apply(lambda x: x if isinstance(x, list) else [])
        df_ship.loc[mask, "total_paid"]  = fb["total_paid_num"].fillna(0.0)
    # calculate final amount_residual
    df_ship["amount_residual"] = df_ship["invoice_amount_residual"] - df_ship["total_paid"]

    # ── 7) Build unshipped deliveries
    df_unsh = df_pick[df_pick["state"] != "done"].copy()
    df_unsh["ship_date"] = df_unsh["scheduled_date"]
    df_unsh = df_unsh.rename(columns={
        "sale_order_reference": "order_id",
        "stock_picking_id":     "delivery_id"
    })[["order_id", "delivery_id", "ship_date", "scheduled_date"]]
    df_unsh = df_unsh.merge(
        df_orders[["order_id","channel","payment_terms","order_amount"]],
        on="order_id", how="left"
    )
    df_unsh["invoice_id"]              = None
    df_unsh["invoice_number"]          = None
    df_unsh["invoice_amount_residual"] = None
    df_unsh["payment_ids"]             = [[] for _ in range(len(df_unsh))]
    df_unsh["total_paid"]              = 0.0
    df_unsh["amount_residual"]         = df_unsh["order_amount"]

    # ── 8) Compute due_date for both streams
    def parse_terms(term: str) -> int:
        term = str(term) if term is not None and not pd.isna(term) else ""
        m = re.search(r"(\d+)", term)
        return int(m.group(1)) if m else 0

    for df in (df_ship, df_unsh):
        df["terms_days"] = df["payment_terms"].map(parse_terms)
        df["due_date"]   = df["ship_date"] + pd.to_timedelta(df["terms_days"], unit="d")
        df.drop(columns=["terms_days","order_amount"], inplace=True)

    # ── 9) Combine and save
    df_all = pd.concat([df_ship, df_unsh], ignore_index=True)
    os.makedirs("output", exist_ok=True)
    df_all.to_csv("output/delivery_level.csv", index=False)
    if debug:
        print("[debug] Wrote output/delivery_level.csv")

    return df_all


if __name__ == "__main__":
    os.environ["ENV"] = "test"
    df = fetch_ar_aging_report(debug=True)
    print("\nDelivery‑level sample:")
    print(df.head().to_string(index=False))
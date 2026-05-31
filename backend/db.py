import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# pre populate the order id for assigning to a random driver
ORDER_IDS = [f"order-{idx:03d}" for idx in range(1, 11)]
DRIVER_IDS = [f"driver-{idx:03d}" for idx in range(1, 6)]
ORDER_DRIVER_MAP = {
    order_id: DRIVER_IDS[(idx - 1) % len(DRIVER_IDS)]
    for idx, order_id in enumerate(ORDER_IDS, start=1)
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(database_path: str) -> sqlite3.Connection:
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(database_path: str) -> None:
    with connect(database_path) as conn:
        conn.execute(
            """
            create table if not exists orders (
                order_id text primary key,
                driver_id text not null,
                status text not null,
                created_at text not null,
                updated_at text not null
            )
            """
        )
        conn.execute(
            """
            create table if not exists app_state (
                key text primary key,
                value text not null
            )
            """
        )
        now = utc_now()
        for order_id, driver_id in ORDER_DRIVER_MAP.items():
            conn.execute(
                """
                insert into orders (order_id, driver_id, status, created_at, updated_at)
                values (?, ?, 'available', ?, ?)
                on conflict(order_id) do nothing
                """,
                (order_id, driver_id, now, now),
            )
        conn.execute(
            """
            insert into app_state (key, value)
            values ('next_order_index', '0')
            on conflict(key) do nothing
            """
        )


def assign_next_order(database_path: str) -> sqlite3.Row:
    with connect(database_path) as conn:
        conn.execute("begin immediate")
        state = conn.execute(
            "select value from app_state where key = 'next_order_index'"
        ).fetchone()
        next_index = int(state["value"]) if state else 0
        order_id = ORDER_IDS[next_index % len(ORDER_IDS)]
        now = utc_now()
        conn.execute(
            """
            update orders
            set status = 'active', updated_at = ?
            where order_id = ?
            """,
            (now, order_id),
        )
        conn.execute(
            """
            update app_state
            set value = ?
            where key = 'next_order_index'
            """,
            (str((next_index + 1) % len(ORDER_IDS)),),
        )
        row = conn.execute(
            """
            select order_id, driver_id, status, created_at, updated_at
            from orders
            where order_id = ?
            """,
            (order_id,),
        ).fetchone()
        conn.commit()
        return row


def get_order(database_path: str, order_id: str) -> Optional[sqlite3.Row]:
    with connect(database_path) as conn:
        return conn.execute(
            """
            select order_id, driver_id, status, created_at, updated_at
            from orders
            where order_id = ?
            """,
            (order_id,),
        ).fetchone()


def get_active_orders_for_driver(database_path: str, driver_id: str) -> list[sqlite3.Row]:
    with connect(database_path) as conn:
        return conn.execute(
            """
            select order_id, driver_id, status, created_at, updated_at
            from orders
            where driver_id = ?
              and status = 'active'
            order by created_at
            """,
            (driver_id,),
        ).fetchall()

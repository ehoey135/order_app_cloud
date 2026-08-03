from datetime import datetime
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class OrderServiceError(Exception):
    """Base class for all order_service errors."""
    pass


class ValidationError(OrderServiceError):
    """Raised when a caller-supplied value fails validation."""
    pass


class NotFoundError(OrderServiceError):
    """Raised when the target record (order/wafer/chip/etc.) doesn't exist."""
    pass


class DuplicateError(OrderServiceError):
    """Raised when an edit would violate a UNIQUE constraint."""
    pass


PG_INT_MIN = -2147483648
PG_INT_MAX = 2147483647


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def validate_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        raise ValidationError(f"'{value}' is not a valid date (expected YYYY-MM-DD).")


def validate_int(value, field_name):
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a whole number, got {value!r}.")
    if value < PG_INT_MIN or value > PG_INT_MAX:
        raise ValidationError(
            f"{field_name} is out of range for a database INT column "
            f"(must be between {PG_INT_MIN} and {PG_INT_MAX})."
        )
    return value


def validate_non_empty_str(value, field_name):
    if value is None or not str(value).strip():
        raise ValidationError(f"{field_name} is required and cannot be blank.")
    return str(value).strip()


def _apply_partial_update(conn, table, id_column, id_value, fields, returning="*"):
    provided = {k: v for k, v in fields.items() if v is not None}
    if not provided:
        raise ValidationError("No fields were provided to update.")

    set_clause = ", ".join(f"{col} = :{col}" for col in provided)
    provided["id_value"] = id_value

    query = text(
        f"UPDATE {table} SET {set_clause} WHERE {id_column} = :id_value RETURNING {returning}"
    )
    result = conn.execute(query, provided)
    row = result.first()
    if row is None:
        raise NotFoundError(f"No row in {table} with {id_column} = {id_value}.")
    return row


# ---------------------------------------------------------------------------
# Companies (read-only lookup for the dropdown)
# ---------------------------------------------------------------------------
def list_companies(conn):
    rows = conn.execute(
        text("SELECT company_id, company_name FROM company ORDER BY company_name")
    ).all()
    return [{"company_id": row.company_id, "company_name": row.company_name} for row in rows]


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def get_or_create_customer(conn, customer_name):
    customer_name = validate_non_empty_str(customer_name, "customer_name")
    customer_id = conn.execute(
        text("SELECT customer_id FROM customer WHERE customer_name = :name"),
        {"name": customer_name},
    ).scalar()

    if customer_id is None:
        customer_id = conn.execute(
            text("INSERT INTO customer (customer_name) VALUES (:name) RETURNING customer_id"),
            {"name": customer_name},
        ).scalar()

    return customer_id


def update_customer_name(conn, customer_id, customer_name):
    customer_name = validate_non_empty_str(customer_name, "customer_name")
    try:
        return _apply_partial_update(
            conn, "customer", "customer_id", customer_id, {"customer_name": customer_name}
        )
    except IntegrityError as e:
        raise DuplicateError(f"A customer named '{customer_name}' already exists.") from e


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------
def create_dispatch(conn, delivery_date, route, cut_location):
    delivery_date = validate_date(delivery_date)
    route = validate_non_empty_str(route, "route")
    cut_location = validate_non_empty_str(cut_location, "cut_location")
    dispatch_id = conn.execute(
        text(
            """INSERT INTO dispatch (customer_delivery_date, route, cut_location)
               VALUES (:date, :route, :cut)
               RETURNING dispatch_id"""
        ),
        {"date": delivery_date, "route": route, "cut": cut_location},
    ).scalar()
    return dispatch_id


def update_dispatch_for_order(conn, order_id, delivery_date=None, route=None, cut_location=None):
    dispatch_id = conn.execute(
        text("SELECT dispatch_id FROM orders WHERE order_id = :id"),
        {"id": order_id},
    ).scalar()
    if dispatch_id is None:
        raise NotFoundError(f"No order with order_id = {order_id}.")

    fields = {}
    if delivery_date is not None:
        fields["customer_delivery_date"] = validate_date(delivery_date)
    if route is not None:
        fields["route"] = validate_non_empty_str(route, "route")
    if cut_location is not None:
        fields["cut_location"] = validate_non_empty_str(cut_location, "cut_location")

    return _apply_partial_update(conn, "dispatch", "dispatch_id", dispatch_id, fields)


# ---------------------------------------------------------------------------
# Wafers
# ---------------------------------------------------------------------------
def get_wafer(conn, wafer_id):
    row = conn.execute(
        text("SELECT * FROM wafers WHERE wafer_id = :id"), {"id": wafer_id}
    ).mappings().first()
    return dict(row) if row else None


def insert_wafer(conn, wafer_number, wafer_name=None, wafer_number_2=None, wafer_part_id=None):
    wafer_number = validate_non_empty_str(wafer_number, "wafer_number")
    wafer_id = conn.execute(
        text(
            """INSERT INTO wafers (wafer_number, wafer_name, wafer_number_2, wafer_part_id)
               VALUES (:num, :name, :num2, :part_id)
               RETURNING wafer_id"""
        ),
        {
            "num": wafer_number,
            "name": (wafer_name or None),
            "num2": (wafer_number_2 or None),
            "part_id": (wafer_part_id or None),
        },
    ).scalar()
    return wafer_id


def update_wafer(conn, wafer_id, wafer_number=None, wafer_name=None,
                  wafer_number_2=None, wafer_part_id=None):
    fields = {}
    if wafer_number is not None:
        fields["wafer_number"] = validate_non_empty_str(wafer_number, "wafer_number")
    if wafer_name is not None:
        fields["wafer_name"] = wafer_name.strip() or None
    if wafer_number_2 is not None:
        fields["wafer_number_2"] = wafer_number_2.strip() or None
    if wafer_part_id is not None:
        fields["wafer_part_id"] = wafer_part_id.strip() or None

    try:
        return _apply_partial_update(conn, "wafers", "wafer_id", wafer_id, fields)
    except IntegrityError as e:
        raise DuplicateError(f"A wafer with number '{wafer_number}' already exists.") from e


def link_wafer_to_order(conn, order_id, wafer_id):
    conn.execute(
        text(
            """INSERT INTO order_wafers (order_id, wafer_id) VALUES (:oid, :wid)
               ON CONFLICT (order_id, wafer_id) DO NOTHING"""
        ),
        {"oid": order_id, "wid": wafer_id},
    )


def remove_wafer_from_order(conn, order_id, wafer_id):
    result = conn.execute(
        text("DELETE FROM order_wafers WHERE order_id = :oid AND wafer_id = :wid"),
        {"oid": order_id, "wid": wafer_id},
    )
    if result.rowcount == 0:
        raise NotFoundError(f"Wafer {wafer_id} is not linked to order {order_id}.")


# ---------------------------------------------------------------------------
# Chips
# ---------------------------------------------------------------------------
def get_chip(conn, chip_id):
    row = conn.execute(
        text("SELECT * FROM chips WHERE chip_id = :id"), {"id": chip_id}
    ).mappings().first()
    return dict(row) if row else None


def insert_chip(conn, chip_number, chip_name=None, chip_numb_2=None, chip_part_id=None):
    chip_number = validate_non_empty_str(chip_number, "chip_number")
    chip_id = conn.execute(
        text(
            """INSERT INTO chips (chip_number, chip_name, chip_numb_2, chip_part_id)
               VALUES (:num, :name, :num2, :part_id)
               RETURNING chip_id"""
        ),
        {
            "num": chip_number,
            "name": (chip_name or None),
            "num2": (chip_numb_2 or None),
            "part_id": (chip_part_id or None),
        },
    ).scalar()
    return chip_id


def update_chip(conn, chip_id, chip_number=None, chip_name=None,
                 chip_numb_2=None, chip_part_id=None):
    fields = {}
    if chip_number is not None:
        fields["chip_number"] = validate_non_empty_str(chip_number, "chip_number")
    if chip_name is not None:
        fields["chip_name"] = chip_name.strip() or None
    if chip_numb_2 is not None:
        fields["chip_numb_2"] = chip_numb_2.strip() or None
    if chip_part_id is not None:
        fields["chip_part_id"] = chip_part_id.strip() or None

    try:
        return _apply_partial_update(conn, "chips", "chip_id", chip_id, fields)
    except IntegrityError as e:
        raise DuplicateError(f"A chip with number '{chip_number}' already exists.") from e


def link_chip_to_order(conn, order_id, chip_id):
    conn.execute(
        text(
            """INSERT INTO order_chips (order_id, chip_id) VALUES (:oid, :cid)
               ON CONFLICT (order_id, chip_id) DO NOTHING"""
        ),
        {"oid": order_id, "cid": chip_id},
    )


def remove_chip_from_order(conn, order_id, chip_id):
    result = conn.execute(
        text("DELETE FROM order_chips WHERE order_id = :oid AND chip_id = :cid"),
        {"oid": order_id, "cid": chip_id},
    )
    if result.rowcount == 0:
        raise NotFoundError(f"Chip {chip_id} is not linked to order {order_id}.")


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
def get_order(conn, order_id):
    row = conn.execute(
        text("SELECT * FROM orders WHERE order_id = :id"),
        {"id": order_id},
    ).mappings().first()
    return dict(row) if row else None


def create_order(conn, customer_id, company_id, bag, dispatch_id, wafer_quantity, chip_quantity):
    bag = validate_non_empty_str(bag, "bag")
    wafer_quantity = validate_int(wafer_quantity, "wafer_quantity")
    chip_quantity = validate_int(chip_quantity, "chip_quantity")

    try:
        order_id = conn.execute(
            text(
                """INSERT INTO orders
                       (customer_id, company_id, bag, dispatch_id, wafer_quantity, chip_quantity)
                   VALUES (:customer_id, :company_id, :bag, :dispatch_id, :wafer_qty, :chip_qty)
                   RETURNING order_id"""
            ),
            {
                "customer_id": customer_id,
                "company_id": company_id,
                "bag": bag,
                "dispatch_id": dispatch_id,
                "wafer_qty": wafer_quantity,
                "chip_qty": chip_quantity,
            },
        ).scalar()
    except IntegrityError as e:
        # Most likely a bad company_id/customer_id/dispatch_id foreign key.
        raise ValidationError(f"Order violates a database constraint: {e.orig}") from e

    return order_id


def update_order(conn, order_id, bag=None, wafer_quantity=None, chip_quantity=None,
                  company_id=None, customer_id=None):
    fields = {}
    if bag is not None:
        fields["bag"] = validate_non_empty_str(bag, "bag")
    if wafer_quantity is not None:
        fields["wafer_quantity"] = validate_int(wafer_quantity, "wafer_quantity")
    if chip_quantity is not None:
        fields["chip_quantity"] = validate_int(chip_quantity, "chip_quantity")
    if company_id is not None:
        fields["company_id"] = validate_int(company_id, "company_id")
    if customer_id is not None:
        fields["customer_id"] = validate_int(customer_id, "customer_id")

    try:
        return _apply_partial_update(conn, "orders", "order_id", order_id, fields)
    except IntegrityError as e:
        raise ValidationError(f"Update violates a database constraint: {e.orig}") from e


# ---------------------------------------------------------------------------
# High-level: create a full order (customer + dispatch + order + wafers/chips)
# in one call, mirroring Phase 2 of the old CLI script.
# ---------------------------------------------------------------------------
def create_full_order(conn, customer_name, delivery_date, route, cut_location,
                       bag, company_id, wafer_quantity, chip_quantity,
                       wafers=None, chips=None):
    wafers = wafers or []
    chips = chips or []

    customer_id = get_or_create_customer(conn, customer_name)
    dispatch_id = create_dispatch(conn, delivery_date, route, cut_location)
    order_id = create_order(
        conn, customer_id, company_id, bag, dispatch_id, wafer_quantity, chip_quantity
    )

    wafer_ids = []
    for w in wafers:
        wafer_id = insert_wafer(
            conn,
            w.get("wafer_number"),
            w.get("wafer_name"),
            w.get("wafer_number_2"),
            w.get("wafer_part_id"),
        )
        link_wafer_to_order(conn, order_id, wafer_id)
        wafer_ids.append(wafer_id)

    chip_ids = []
    for c in chips:
        chip_id = insert_chip(
            conn,
            c.get("chip_number"),
            c.get("chip_name"),
            c.get("chip_numb_2"),
            c.get("chip_part_id"),
        )
        link_chip_to_order(conn, order_id, chip_id)
        chip_ids.append(chip_id)

    return {
        "order_id": order_id,
        "customer_id": customer_id,
        "dispatch_id": dispatch_id,
        "wafer_ids": wafer_ids,
        "chip_ids": chip_ids,
    }
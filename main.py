"""
FastAPI backend for the New Order form.

Run with:
    uvicorn main:app --host 0.0.0.0 --port 8000

Then open http://127.0.0.1:8000/ in your browser.
"""

from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from db import engine
import order_service as svc

app = FastAPI(title="Order Entry API")


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------
class WaferIn(BaseModel):
    wafer_number: str
    wafer_name: Optional[str] = None
    wafer_number_2: Optional[str] = None
    wafer_part_id: Optional[str] = None


class ChipIn(BaseModel):
    chip_number: str
    chip_name: Optional[str] = None
    chip_numb_2: Optional[str] = None
    chip_part_id: Optional[str] = None


class OrderIn(BaseModel):
    customer_name: str
    delivery_date: str  # "YYYY-MM-DD"
    route: str
    cut_location: str
    bag: str
    company_id: int
    wafer_quantity: int
    chip_quantity: int
    wafers: List[WaferIn] = []
    chips: List[ChipIn] = []


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------
@app.get("/companies")
def get_companies():
    with engine.connect() as conn:
        return svc.list_companies(conn)


@app.post("/orders")
def submit_order(order: OrderIn):
    with engine.connect() as conn:
        try:
            result = svc.create_full_order(
                conn,
                customer_name=order.customer_name,
                delivery_date=order.delivery_date,
                route=order.route,
                cut_location=order.cut_location,
                bag=order.bag,
                company_id=order.company_id,
                wafer_quantity=order.wafer_quantity,
                chip_quantity=order.chip_quantity,
                wafers=[w.dict() for w in order.wafers],
                chips=[c.dict() for c in order.chips],
            )
            conn.commit()
            return result
        except svc.ValidationError as e:
            conn.rollback()
            raise HTTPException(status_code=400, detail=str(e))
        except svc.NotFoundError as e:
            conn.rollback()
            raise HTTPException(status_code=404, detail=str(e))
        except svc.DuplicateError as e:
            conn.rollback()
            raise HTTPException(status_code=409, detail=str(e))


@app.get("/orders/{order_id}")
def read_order(order_id: int):
    with engine.connect() as conn:
        order = svc.get_order(conn, order_id)
        if order is None:
            raise HTTPException(status_code=404, detail=f"No order with id {order_id}")
        return order


# ---------------------------------------------------------------------------
# Serve the frontend (index.html / styles.css / app.js) from the same origin
# so the browser fetch() calls above don't need CORS at all.
# ---------------------------------------------------------------------------
@app.get("/")
def serve_index():
    return FileResponse("static/index.html")


app.mount("/", StaticFiles(directory="static"), name="static")
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class Item(BaseModel):
    id: UUID
    name: str
    category: str
    description: str
    price: int


ITEMS = []


@router.post("/")
def create_item(item: Item):
    ITEMS.append(item)
    return item


@router.get("/")
def get_items():
    return ITEMS


@router.put("/{id}")
def update_item(id: UUID, item: Item):
    for i, existing_item in enumerate(ITEMS):
        if existing_item.id == id:
            ITEMS[i] = item
            return item

    raise HTTPException(status_code=404, detail=f"ID {id} : Item not found")


@router.delete("/{id}")
def delete_item(id: UUID):
    for i, existing_item in enumerate(ITEMS):
        if existing_item.id == id:
            del ITEMS[i]
            return {"message": "Item deleted"}

    raise HTTPException(status_code=404, detail=f"ID {id} : Item not found")

from typing import TypeVar, Generic, List
from pydantic import BaseModel, Field
from scim.config import settings

T = TypeVar("T")


class PaginationParams(BaseModel):
    start_index: int = Field(1, ge=1, alias="startIndex")
    count: int = Field(settings.default_page_size, ge=0, le=settings.max_page_size)
    
    @property
    def offset(self) -> int:
        return self.start_index - 1  # SCIM uses 1-based indexing
    
    @property
    def limit(self) -> int:
        return min(self.count, settings.max_page_size)


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total_results: int
    start_index: int
    items_per_page: int
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total_results: int,
        pagination: PaginationParams
    ) -> "PaginatedResponse[T]":
        return cls(
            items=items,
            total_results=total_results,
            start_index=pagination.start_index,
            items_per_page=len(items)
        )
from pydantic import BaseModel, validator
from typing import List, Optional, Literal

class PropertyInput(BaseModel):
    total_area: float
    kitchen_area: float
    floor: int
    floors_total: Optional[int] = None  # Сделаем опциональным
    rooms: str
    renovation: Literal['дизайнерский', 'евро', 'требует ремонта', 'косметический']
    house_type: Literal['монолитный', 'панельный', 'кирпичный', 'монолитно-кирпичный', 'блочный', 'деревянный']
    city: Literal['Москва', 'Питер', 'Казань', 'Нижний', 'Новосиб', 'ЕКБ']
    passenger_lift: str
    cargo_lift: str
    parking: Literal['подземная', 'открытая во дворе', 'наземная многоуровневая', 'за шлагбаумом во дворе']
    build_year: int
    
    @validator('floors_total', always=True)
    def set_total_floor_default(cls, v, values):
        """Устанавливает floors_total = floor если не указано"""
        if v is None and 'floor' in values:
            return values['floor']
        return v
    
    @validator('floors_total')
    def validate_total_floor(cls, v, values):
        """Проверяет что floors_total >= floor"""
        if 'floor' in values and v < values['floor']:
            raise ValueError('floors_total cannot be less than floor')
        return v
    
    @validator('total_area')
    def validate_total_area(cls, v):
        if v <= 0:
            raise ValueError('Total area must be positive')
        if v > 1000:
            raise ValueError('Total area seems too large')
        return v
    
    @validator('floor')
    def validate_floor(cls, v, values):
        if 'floors_total' in values and v > values['floors_total']:
            raise ValueError('Floor cannot be greater than total floors')
        return v

class SimilarListing(BaseModel):
    link: str
    price: float
    rooms: int
    total_area: float

class PredictionResponse(BaseModel):
    predicted_price: float
    status: str
    message: str
    similar_listings: List[SimilarListing]
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator

# Calculation schemas
class CalculateRequest(BaseModel):
    origin: str = "caba"  # 'caba' or 'mdp'
    destination_id: Optional[int] = None
    destination: Optional[str] = None  # city name alternative to destination_id
    weight: float = Field(..., gt=0, description="Peso en kilogramos")
    carrier_id: Optional[int] = None
    carrier: Optional[str] = None  # carrier name alternative (e.g. 'OCA', 'TyT')

class CarrierQuoteItem(BaseModel):
    carrier_id: int
    carrier_name: str
    carrier_color: str
    service_label: str = "Entrega en Domicilio"
    base_price: float
    extra_kg: float
    extra_kg_rate: float
    extra_cost: float
    total_price: float
    bracket_desc: str
    estimated_days: str
    is_cheapest: bool = False

class UnavailableCarrierItem(BaseModel):
    carrier_id: int
    carrier_name: str
    feasible: bool = False
    status: str = "no_factible"
    reason_code: str
    reason: str

class CalculateResponse(BaseModel):
    origin_name: str
    destination_name: str
    destination_province: Optional[str] = ""
    zone_label: str
    zone_code: str
    weight: float
    service_mode: str = "Entrega en Domicilio"
    results: List[CarrierQuoteItem]
    feasible: bool = True
    status: str = "factible"
    unavailable: List[UnavailableCarrierItem] = Field(default_factory=list)

# Matrix schemas (Domicilio)
class MatrixRowSchema(BaseModel):
    id: Optional[int] = None
    service_type: str = "domicilio"
    is_extra_kg: bool = False
    min_weight: float = Field(0.0, ge=0, allow_inf_nan=False)
    max_weight: float = Field(1.0, ge=0, allow_inf_nan=False)
    price_local: float = Field(0.0, ge=0, allow_inf_nan=False)
    price_regional: float = Field(0.0, ge=0, allow_inf_nan=False)
    price_nacional_1: float = Field(0.0, ge=0, allow_inf_nan=False)
    price_nacional_2: float = Field(0.0, ge=0, allow_inf_nan=False)
    order_index: int = 0

class MatrixSaveRequest(BaseModel):
    rows: List[MatrixRowSchema]

    @model_validator(mode="after")
    def validate_ranges(self):
        regular = sorted((r for r in self.rows if not r.is_extra_kg), key=lambda r: r.min_weight)
        if not regular:
            raise ValueError("Agregá al menos un rango de peso.")
        if sum(r.is_extra_kg for r in self.rows) > 1:
            raise ValueError("Solo puede haber una fila de kg excedente.")
        for row in regular:
            if row.min_weight >= row.max_weight:
                raise ValueError("El límite superior debe ser mayor al inferior.")
        for previous, current in zip(regular, regular[1:]):
            if current.min_weight < previous.max_weight:
                raise ValueError("Los rangos no pueden superponerse.")
        self.rows = regular + [r for r in self.rows if r.is_extra_kg]
        return self


class BulkAdjustRequest(BaseModel):
    percentage: float
    carrier_id: Optional[int] = None

# Carrier schemas
class CarrierCreate(BaseModel):
    name: str
    code: Optional[str] = None
    logo_color: Optional[str] = "#7C3AED"
    description: Optional[str] = ""

class CarrierUpdate(CarrierCreate):
    is_active: bool = True

# Location schemas
class LocationCreate(BaseModel):
    name: str
    province: Optional[str] = ""
    zone_from_caba: str = "regional"
    zone_from_mdp: str = "regional"

class LocationUpdate(LocationCreate):
    pass

# Auth schemas
class LoginRequest(BaseModel):
    username: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

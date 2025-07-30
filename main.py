import os
from fastapi import FastAPI, Request
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# --- Configuración ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Inicializar Supabase y FastAPI
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
app = FastAPI()

# --- Modelos de Datos (para validar la info de Telegram) ---
class User(BaseModel):
    id: int
    first_name: str
    username: Optional[str] = None

class OrderInfo(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

class SuccessfulPayment(BaseModel):
    currency: str
    total_amount: int
    invoice_payload: str # Aquí vendrá el ID de la rifa y el número
    order_info: Optional[OrderInfo] = None
    telegram_payment_charge_id: str
    provider_payment_charge_id: str

class Update(BaseModel):
    update_id: int
    message: Optional[dict] = None
    pre_checkout_query: Optional[dict] = None
    # Añadimos los campos que nos interesan
    successful_payment: Optional[SuccessfulPayment] = Field(None, alias="successful_payment")

# --- Endpoints de la API ---
@app.get("/")
def read_root():
    return {"Status": "BitGo Payment Handler is running!"}

@app.post("/webhook")
async def process_webhook(request: Request):
    data = await request.json()
    
    # Imprimimos en la consola para depurar y ver qué llega
    print("--- Webhook Recibido ---")
    print(data)
    print("------------------------")

    # Verificamos si es un pago exitoso
    if "message" in data and "successful_payment" in data["message"]:
        payment_data = data["message"]["successful_payment"]
        user_data = data["message"]["from"]

        try:
            # 1. Extraer la información
            payload = payment_data.get("invoice_payload").split('_') # Ej: "rifaID_numeroComprado"
            rifa_id = payload[0]
            numero_comprado = payload[1]
            jugador_id = user_data.get("id")
            username = user_data.get("username")
            first_name = user_data.get("first_name")
            payment_charge_id = payment_data.get("telegram_payment_charge_id")

            # 2. Insertar o actualizar el jugador
            # La función 'upsert' inserta si no existe, o actualiza si ya existe.
            supabase.table("jugadores").upsert({
                "id": jugador_id,
                "username": username,
                "first_name": first_name
            }).execute()

            # 3. Insertar el boleto comprado
            supabase.table("boletos").insert({
                "rifa_id": rifa_id,
                "jugador_id": jugador_id,
                "numero_comprado": numero_comprado,
                "telegram_payment_charge_id": payment_charge_id
            }).execute()
            
            print(f"✅ Pago procesado: Jugador {first_name} compró el número {numero_comprado} para la rifa {rifa_id}")

        except Exception as e:
            print(f"🚨 Error procesando el pago: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "ok"}
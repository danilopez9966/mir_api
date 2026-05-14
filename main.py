from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os
import time

load_dotenv()

app = FastAPI(title="API REST Robot MiR + Supabase")

MIR_BASE_URL = os.getenv("MIR_BASE_URL")
MIR_TOKEN = os.getenv("MIR_TOKEN")
MIR_AUTH_PREFIX = os.getenv("MIR_AUTH_PREFIX", "Bearer")

SUPABASE_URL = os.getenv("VITE_SUPABASE_URL")
SUPABASE_KEY = os.getenv("VITE_SUPABASE_ANON_KEY")

class MissionRequest(BaseModel):
    mission_id: str


class ProductsRequest(BaseModel):
    products: list[str]


def mir_headers():

    return {
        "Authorization": MIR_TOKEN,
        "Content-Type": "application/json",
        "Accept-Language": "en_US"
    }


def supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }


@app.get("/")
def home():
    return {
        "message": "API REST para controlar robot MiR con Supabase funcionando"
    }


@app.post("/robot/send-mission")
def send_mission(mission: MissionRequest):
    body = {
        "mission_id": mission.mission_id
    }

    response = requests.post(
        f"{MIR_BASE_URL}/mission_queue",
        json=body,
        headers=mir_headers()
    )

    if response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return {
        "message": "Misión enviada correctamente al robot",
        "robot_response": response.json()
    }

def esperar():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/missions?goal=eq.espera&select=guid",
        headers=supabase_headers()
    )

    missions = response.json()

    if not missions:
        raise Exception("No existe misión de recepción")

    mission_guid = missions[0]["guid"]

    body = {
        "mission_id": mission_guid
    }

    # Enviar misión al robot
    robot_response = requests.post(
        f"{MIR_BASE_URL}/mission_queue",
        json=body,
        headers=mir_headers()
    )

    return robot_response.json()

def enviar_a_recepcion():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/missions?goal=eq.recepcion&select=guid",
        headers=supabase_headers()
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    missions = response.json()

    if not missions:
        raise HTTPException(
            status_code=404,
            detail="No existe una misión asociada a recepción"
        )

    mission_guid = missions[0]["guid"]

    robot_response = requests.post(
        f"{MIR_BASE_URL}/mission_queue",
        json={"mission_id": mission_guid},
        headers=mir_headers(),
        timeout=10
    )

    if robot_response.status_code not in [200, 201]:
        raise HTTPException(
            status_code=robot_response.status_code,
            detail=robot_response.text
        )

    return {
        "goal": "recepcion",
        "mission_guid": mission_guid,
        "robot_response": robot_response.json()
    }

@app.get("/products")
def get_products():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?select=*",
        headers=supabase_headers()
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


@app.get("/products/{product_id}")
def get_product_by_id(product_id: int):
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?id=eq.{product_id}&select=*",
        headers=supabase_headers()
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    products = response.json()

    if not products:
        raise HTTPException(
            status_code=404,
            detail="Producto no encontrado"
        )

    return products[0]


@app.get("/products/search/{product_name}")
def search_product(product_name: str):
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/products?name=ilike.*{product_name}*&select=*",
        headers=supabase_headers()
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


@app.get("/missions-db")
def get_missions_from_db():
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/missions?select=*",
        headers=supabase_headers()
    )

    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    return response.json()


@app.post("/robot/send-products")
def send_multiple_products(data: ProductsRequest):
    sent_missions = []

    for product_name in data.products:
        product_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?name=ilike.*{product_name}*&select=*",
            headers=supabase_headers()
        )

        products = product_response.json()

        if not products:
            sent_missions.append({
                "product": product_name,
                "status": "Producto no encontrado"
            })
            continue

        selected_product = products[0]
        product_goal = selected_product["goal"]

        mission_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/missions?goal=eq.{product_goal}&select=*",
            headers=supabase_headers()
        )

        missions = mission_response.json()

        if not missions:
            sent_missions.append({
                "product": product_name,
                "goal": product_goal,
                "status": "Misión no encontrada"
            })
            continue

        mission_guid = missions[0]["guid"]

        robot_response = requests.post(
            f"{MIR_BASE_URL}/mission_queue",
            json={"mission_id": mission_guid},
            headers=mir_headers()
        )

        sent_missions.append({
            "product": product_name,
            "goal": product_goal,
            "mission_guid": mission_guid,
            "robot_status": robot_response.status_code
        })

        esperar();
    
    recepcion_result = enviar_a_recepcion()

    return {
    "message": "Productos enviados y misión de recepción añadida",
    "results": sent_missions,
    "recepcion": recepcion_result
}
    sent_missions = []

    for product_name in data.products:
        product_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/products?name=ilike.*{product_name}*&select=*",
            headers=supabase_headers()
        )

        products = product_response.json()

        if not products:
            sent_missions.append({
                "product": product_name,
                "status": "Producto no encontrado"
            })
            continue

        selected_product = products[0]
        product_goal = selected_product["goal"]

        mission_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/missions?goal=eq.{product_goal}&select=*",
            headers=supabase_headers()
        )

        missions = mission_response.json()

        if not missions:
            sent_missions.append({
                "product": product_name,
                "goal": product_goal,
                "status": "Misión no encontrada"
            })
            continue

        mission_guid = missions[0]["guid"]

        robot_response = requests.post(
            f"{MIR_BASE_URL}/mission_queue",
            json={"mission_id": mission_guid},
            headers=mir_headers()
        )

        sent_missions.append({
            "product": product_name,
            "goal": product_goal,
            "mission_guid": mission_guid,
            "robot_status": robot_response.status_code
        })

    return {
        "message": "Procesamiento de productos terminado",
        "results": sent_missions
    }
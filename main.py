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
    order_id :int | None = None

class ClarificationRequest(BaseModel):
    order_id: int
    message: str

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

def save_mission_history(mission_queue_id, order_id=None):
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    payload = {
        "state": "pending",
        "mission_queue_id": mission_queue_id,
        "order_id": order_id
    }

    response = requests.post(
        f"{supabase_url}/rest/v1/mission_histories",
        headers=headers,
        json=payload
    )

    print("MISSION HISTORY STATUS:", response.status_code)
    print("MISSION HISTORY RESPONSE:", response.text)

    return response

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
        
        robot_data = robot_response.json()

        mission_queue_id = robot_data.get("id")

        save_mission_history(
            mission_queue_id=mission_queue_id,
            order_id=data.order_id
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

@app.post("/check-products")
def check_products(data: ProductsRequest):
    try:
        valid_products = []
        ambiguous_products = []
        missing_products = []

        for product_name in data.products:
            product_name = product_name.strip()

            if not product_name:
                continue

            response = requests.get(
                f"{SUPABASE_URL}/rest/v1/products?name=ilike.*{product_name}*&select=id,name,goal",
                headers=supabase_headers(),
                timeout=10
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=response.text
                )

            products = response.json()

            if len(products) == 0:
                missing_products.append({
                    "requested": product_name,
                    "message": f"No existe ningún producto relacionado con '{product_name}'."
                })

            elif len(products) == 1:
                valid_products.append({
                    "requested": product_name,
                    "selected_product": products[0]
                })

            else:
                ambiguous_products.append({
                    "requested": product_name,
                    "message": f"He encontrado varios productos para '{product_name}'. ¿Cuál quieres?",
                    "options": [
                        {
                            "number": index + 1,
                            "id": product.get("id"),
                            "name": product.get("name"),
                            "goal": product.get("goal")
                        }
                        for index, product in enumerate(products)
                    ]
                })

        if missing_products:
            return {
                "status": "missing_products",
                "message": "Algunos productos no existen en la base de datos.",
                "valid_products": valid_products,
                "ambiguous_products": ambiguous_products,
                "missing_products": missing_products
            }

        if ambiguous_products:
            first_ambiguous = ambiguous_products[0]

            options_text = "\n".join([
                f"{option['number']}. {option['name']}"
                for option in first_ambiguous["options"]
         ])

            return {
                    "status": "clarification_required",
                    "message": (
                         f"He encontrado varios productos para '{first_ambiguous['requested']}'. "
                        f"¿Cuál quieres?\n\n{options_text}"
                    ),
                     "current_ambiguous": first_ambiguous,
                    "valid_products": valid_products,
                    "ambiguous_products": ambiguous_products,
                    "missing_products": missing_products
                    }

        return {
            "status": "ready_to_send",
            "message": "Todos los productos existen y son concretos.",
            "valid_products": valid_products,
            "ambiguous_products": [],
            "missing_products": []
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno en /check-products: {str(e)}"
        )

@app.post("/resolve-clarification")
def resolve_clarification(data: ClarificationRequest):
    try:
        order_response = requests.get(
            f"{SUPABASE_URL}/rest/v1/orders"
            f"?id=eq.{data.order_id}"
            f"&select=*",
            headers=supabase_headers(),
            timeout=10
        )

        if order_response.status_code != 200:
            raise HTTPException(
                status_code=order_response.status_code,
                detail=order_response.text
            )

        orders = order_response.json()

        if not orders:
            raise HTTPException(
                status_code=404,
                detail="No se ha encontrado el pedido indicado."
            )

        order = orders[0]

        if order["status"] != "clarification_required":
            raise HTTPException(
                status_code=400,
                detail=f"El pedido no está pendiente de aclaración. Estado actual: {order['status']}"
            )

        order_id = order["id"]
        order_data = order["data"]

        valid_products = order_data.get("valid_products", [])
        ambiguous_products = order_data.get("ambiguous_products", [])
        missing_products = order_data.get("missing_products", [])

        user_message = data.message.lower().strip()

        selected_product = None
        resolved_ambiguous = None

        if not ambiguous_products:
            raise HTTPException(
                status_code=400,
                detail="Este pedido no tiene productos ambiguos pendientes."
            )

        resolved_ambiguous = ambiguous_products[0]
        options = resolved_ambiguous.get("options", [])

        for option in options:
            option_number = str(option.get("number", "")).strip()
            option_name = option.get("name", "").lower().strip()

            if user_message == option_number:
                selected_product = option
                break

            if user_message in option_name or option_name in user_message:
                selected_product = option
                break
        ambiguous_products = ambiguous_products[1:]

        if len(ambiguous_products) == 0 and len(missing_products) == 0:
                new_status = "ready_to_send"
                next_message = "Aclaración resuelta. El pedido ya está listo para enviarse al robot."
        else:
                new_status = "clarification_required"

                next_ambiguous = ambiguous_products[0]
                options_text = "\n".join([
                    f"{option['number']}. {option['name']}"
                    for option in next_ambiguous["options"]
                ])

                next_message = (
                    f"Perfecto. Ahora necesito aclarar '{next_ambiguous['requested']}'. "
                    f"¿Cuál quieres?\n\n{options_text}"
                )

        if not selected_product:
            return {
                "status": "clarification_required",
                "message": "No he encontrado ese producto entre las opciones disponibles. Por favor, elige una de las opciones mostradas.",
                "order_id": order_id,
                "valid_products": valid_products,
                "ambiguous_products": ambiguous_products,
                "missing_products": missing_products
            }

        valid_products.append({
            "requested": resolved_ambiguous.get("requested"),
            "selected_product": {
                "id": selected_product.get("id"),
                "name": selected_product.get("name"),
                "goal": selected_product.get("goal")
            }
        })

        ambiguous_products = [
            item for item in ambiguous_products
            if item.get("requested") != resolved_ambiguous.get("requested")
        ]

        if len(ambiguous_products) == 0 and len(missing_products) == 0:
            new_status = "ready_to_send"
            message = "Aclaración resuelta. El pedido ya está listo para enviarse al robot."
        else:
            new_status = "clarification_required"
            message = "Aclaración resuelta parcialmente. Todavía quedan productos por aclarar."

        new_data = {
            "valid_products": valid_products,
            "ambiguous_products": ambiguous_products,
            "missing_products": missing_products,
            "message": next_message
        }

        update_response = requests.patch(
            f"{SUPABASE_URL}/rest/v1/orders?id=eq.{order_id}",
            headers={
                **supabase_headers(),
                "Prefer": "return=representation"
            },
            json={
                "status": new_status,
                "data": new_data
            },
            timeout=10
        )

        if update_response.status_code not in [200, 204]:
            raise HTTPException(
                status_code=update_response.status_code,
                detail=update_response.text
            )

        return {
            "status": new_status,
            "message": next_message,
            "order_id": order_id,
            "valid_products": valid_products,
            "ambiguous_products": ambiguous_products,
            "missing_products": missing_products,
            "products_to_send": [
                item["selected_product"]["name"]
                for item in valid_products
    ]
}

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno en /resolve-clarification: {str(e)}"
        )
from datetime import datetime, timezone

def update_mission_history(mission_queue_id, state_text):
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")

    now = datetime.now(timezone.utc).isoformat()

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    payload = None

    if state_text in ["Executing", "Moving", "Running"]:
        payload = {
            "state": "executing",
            "started_at": now
        }

    elif state_text in ["Done", "Completed"]:
        payload = {
            "state": "complete",
            "completed_at": now
        }

    elif state_text in ["Aborted", "Error"]:
        payload = {
            "state": "aborted",
            "completed_at": now
        }

    if payload is None:
        return

    response = requests.patch(
        f"{supabase_url}/rest/v1/mission_histories?mission_queue_id=eq.{mission_queue_id}",
        headers=headers,
        json=payload
    )

    print("UPDATE MISSION HISTORY:", response.status_code, response.text)

from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc).isoformat()


def sync_current_mission(current_mission_queue_id):
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    if not current_mission_queue_id:
        return

    current_mission_queue_id = int(current_mission_queue_id)

    # 1. Buscar la misión que está actualmente en executing
    executing_response = requests.get(
        f"{supabase_url}/rest/v1/mission_histories"
        f"?state=eq.executing"
        f"&completed_at=is.null"
        f"&order=started_at.desc"
        f"&limit=1"
        f"&select=*",
        headers=headers,
        timeout=10
    )

    executing_missions = executing_response.json()

    # 2. Si hay una executing y es distinta a la actual, completar SOLO esa
    if executing_missions:
        executing = executing_missions[0]

        if int(executing["mission_queue_id"]) != current_mission_queue_id:
            requests.patch(
                f"{supabase_url}/rest/v1/mission_histories?id=eq.{executing['id']}",
                headers=headers,
                json={
                    "state": "complete",
                    "completed_at": now_utc()
                },
                timeout=10
            )

    # 3. Marcar la misión actual como executing SOLO si está pending
    requests.patch(
        f"{supabase_url}/rest/v1/mission_histories"
        f"?mission_queue_id=eq.{current_mission_queue_id}"
        f"&state=eq.pending",
        headers=headers,
        json={
            "state": "executing",
            "started_at": now_utc()
        },
        timeout=10
    )
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")
    now = datetime.now(timezone.utc).isoformat()

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # Buscar última misión en ejecución
    running_response = requests.get(
        f"{supabase_url}/rest/v1/mission_histories"
        f"?state=eq.executing"
        f"&completed_at=is.null"
        f"&order=started_at.desc"
        f"&limit=1"
        f"&select=*",
        headers=headers,
        timeout=10
    )

    running_missions = running_response.json()

    if running_missions:
        running_mission = running_missions[0]
        running_id = str(running_mission["mission_queue_id"])

        # Si el robot ya está ejecutando otra misión, cerramos la anterior
        if str(current_mission_queue_id) != running_id:
            requests.patch(
                f"{supabase_url}/rest/v1/mission_histories?id=eq.{running_mission['id']}",
                headers=headers,
                json={
                    "state": "complete",
                    "completed_at": now
                },
                timeout=10
            )

    # Marcar la misión actual como executing
    if current_mission_queue_id:
        requests.patch(
            f"{supabase_url}/rest/v1/mission_histories"
            f"?mission_queue_id=eq.{current_mission_queue_id}"
            f"&state=eq.pending",
            headers=headers,
            json={
                "state": "executing",
                "started_at": now
            },
            timeout=10
        )
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")
    now = datetime.now(timezone.utc).isoformat()

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    # 1. Buscar SOLO la última misión executing sin completar
    get_response = requests.get(
        f"{supabase_url}/rest/v1/mission_histories"
        f"?state=eq.executing"
        f"&completed_at=is.null"
        f"&order=started_at.desc"
        f"&limit=1"
        f"&select=*",
        headers=headers
    )

    missions = get_response.json()

    if not missions:
        return

    mission = missions[0]
    mission_id = mission["id"]

    # 2. Completar SOLO esa misión
    patch_response = requests.patch(
        f"{supabase_url}/rest/v1/mission_histories?id=eq.{mission_id}",
        headers=headers,
        json={
            "state": "complete",
            "completed_at": now
        }
    )

    print("MISSION COMPLETED:", patch_response.status_code, patch_response.text)
    supabase_url = os.getenv("VITE_SUPABASE_URL")
    supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")
    now = datetime.now(timezone.utc).isoformat()

    headers = {
        "apikey": supabase_key,
        "Authorization": f"Bearer {supabase_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    response = requests.patch(
        f"{supabase_url}/rest/v1/mission_histories"
        f"?state=eq.executing&completed_at=is.null",
        headers=headers,
        json={
            "state": "complete",
            "completed_at": now
        }
    )

    print("COMPLETE LAST EXECUTING:", response.status_code, response.text)
        
@app.get("/status")
def get_robot_status():

    response = requests.get(
        f"{MIR_BASE_URL}/status",
        headers=mir_headers()
    )

    # Si MiR devuelve error
    if response.status_code != 200:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text
        )

    # Datos del robot
    data = response.json()
    
    current_mission_queue_id = data.get("mission_queue_id")

    if current_mission_queue_id:
        sync_current_mission(current_mission_queue_id)

    try:

        # Variables de entorno
        supabase_url = os.getenv("VITE_SUPABASE_URL")
        supabase_key = os.getenv("VITE_SUPABASE_ANON_KEY")

        # Headers Supabase
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }

        # Payload para la tabla public.data
        payload = {
            "battery": data.get("battery_percentage"),
            "mission_text": data.get("mission_text"),
            "state": data.get("state_text"),
            "velocity_linear": data.get("velocity", {}).get("linear"),
            "velocity_angular": data.get("velocity", {}).get("angular")
        }

        # Insert en Supabase
        insert_response = requests.post(
            f"{supabase_url}/rest/v1/data",
            headers=headers,
            json=payload
        )

        # Logs para debug
        print("SUPABASE STATUS:", insert_response.status_code)
        print("SUPABASE RESPONSE:", insert_response.text)

    except Exception as e:
        print("Error guardando estado del robot:", e)

    # Devuelve el estado del robot igualmente
    return data
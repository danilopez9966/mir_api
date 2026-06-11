# <div align="center"> ✧ Automatización Logística con IA y Robot MiR250 ✧ </div>
### <div align="center"> - Belén Ruiz & Daniel López - </div>

## 📝 Descripción del Proyecto
Este proyecto presenta un sistema logístico automatizado basado en 
inteligencia artificial y robótica móvil. El entorno simulado representa 
un pequeño almacén de una tienda especializada en productos tecnológicos 
(cables, mandos, consolas...).

El sistema permite que un usuario solicite productos mediante lenguaje 
natural a través de un chat conversacional. La petición es procesada por 
un agente de IA que extrae los productos, valida su existencia en la base 
de datos y genera automáticamente las misiones necesarias para el robot 
autónomo MiR250, encargado de desplazarse hasta la estantería 
correspondiente. Además, se monitoriza en tiempo real el estado del robot 
y las misiones activas mediante dashboards en Grafana.
<br><br>

## 🛠️ Tecnologías
- **n8n** – Orquestador principal. Gestiona el chat, el agente IA y la comunicación con la API REST.
- **FastAPI (Python)** – Núcleo de la lógica de negocio. Valida productos, gestiona pedidos y envía misiones al robot.
- **Supabase (PostgreSQL)** – Base de datos principal. Almacena productos, pedidos, misiones y métricas del robot.
- **Grafana** – Dashboard de monitorización en tiempo real.
- **Google Gemini API** – Modelo de IA para procesamiento de lenguaje natural.
- **Robot MiR250** – Robot móvil autónomo que ejecuta las misiones.
- **Docker** – Contenedorización del entorno.
<br><br>

## 🔄 Flujo del Sistema
1. El usuario envía una petición en lenguaje natural por el chat.
2. El agente IA extrae los productos solicitados.
3. La API `/check-products` valida los productos en la base de datos.
   - Si hay **productos ambiguos**, se pide aclaración al usuario.
   - Si todo es **válido**, se procede al envío de misiones.
4. La API `/robot/send-products` envía las misiones al MiR250.
5. El robot ejecuta las misiones y el sistema registra el historial.
<br><br>

## 📡 Endpoints
| Endpoint | Método | Descripción |
|---|---|---|
| `/products` | GET | Obtiene todos los productos |
| `/products/search/{name}` | GET | Busca productos por nombre |
| `/check-products` | POST | Valida productos y detecta ambigüedades |
| `/robot/send-products` | POST | Envía misiones necesarias al robot |
| `/resolve-clarification` | POST | Resuelve productos ambiguos |
| `/status` | GET | Consulta y almacena estado del robot |
| `/missions-db` | GET | Lista las misiones posibles |

<br>

## 📖 Instalación y Configuración
```bash
# Clonar el repositorio
git clone https://github.com/danilopez9966/mir_api.git

# Ingresar al directorio
cd mir_api

# Copiar variables de entorno
cp .env.example .env
# Editar .env con tus claves de Supabase y la IP del robot

# Levantar los servicios con Docker
docker compose up -d
```

Accede a n8n en http://localhost:5678 y a la API en http://localhost:8000.
Para clonar la base de datos ejecuta el script SQL (bd_mir250.sql)

```bash
# Copiar el workflow  de n8n dentro del contenedor
docker cp .\workflows.json n8n_mir:/home/node/.n8n/workflows.json

# Importar el workflow mediante CLI
docker exec -it n8n_mir n8n import:workflow --input=/home/node/.n8n/workflows.json

# Revisar credenciales y variables
- Añadir API KEY de Gemini
- Crendenciales Postgres y Supabase
- Revisar llamada correcta a tablas y columnas de la bd
```

Para ver los datos en tiempo real conecta tu bd a Grafana e importa el dashboard desde el JSON dashboard-grafana-mir250.json
<br>

## 🗄️ Base de Datos
- **products** – Productos del almacén y su ubicación (estantería).
- **missions** – Misiones disponibles y su guid para el MiR250.
- **orders** – Pedidos realizados y su estado.
- **mission_histories** – Historial de misiones enviadas al robot.
- **data** – Métricas periódicas del robot (batería, velocidad, estado...).
<br><br>

## 📊 Dashboard
El dashboard de Grafana se divide en tres secciones:
- **Estado del robot** – Batería, estado actual, velocidad y misiones por día.
- **Análisis de misiones** – Historial, cantidad diaria y tiempo medio por pedido.
- **Ventas del almacén** – Productos más vendidos y estanterías más visitadas.
<br><br>

## 👥 Autores
**Belén Ruiz** – [LinkedIn](https://www.linkedin.com/in/bel%C3%A9n-ruiz-morales/) · belenrumo2005@gmail.com

**Daniel López** – [LinkedIn](https://www.linkedin.com/in/daniel-lopez-arcos-b11168303/) · danidemurcia@gmail.com

## Licencia
Este proyecto está licenciado bajo 
[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/).  

© 2026 beelenruiz & danilopez9966

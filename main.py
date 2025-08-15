from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import subprocess
import platform
from datetime import datetime
from typing import List, Dict

app = FastAPI()

# Хранилище данных в памяти
devices_data: List[Dict] = []


def get_mac_address(ip: str) -> str:
    """Получаем MAC-адрес по IP с помощью ARP-запроса"""
    try:
        if platform.system() == "Windows":
            cmd = f"arp -a {ip}"
            output = subprocess.check_output(cmd, shell=True).decode('cp866')
            # Парсим вывод ARP для Windows
            for line in output.split('\n'):
                if ip in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[1]
        else:  # Linux/MacOS
            cmd = f"arp -n {ip}"
            output = subprocess.check_output(cmd, shell=True).decode()
            # Парсим вывод ARP для Linux/Mac
            for line in output.split('\n'):
                if ip in line:
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
    except Exception as e:
        print(f"Error getting MAC: {e}")
    return "Unknown"


@app.get("/", response_class=HTMLResponse)
async def get_client_info(request: Request):
    """Основная страница, которая показывает информацию об устройстве"""
    client_ip = request.client.host
    mac_address = get_mac_address(client_ip)
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Сохраняем данные
    device_info = {
        "ip": client_ip,
        "mac": mac_address,
        "time": current_time,
        "user_agent": request.headers.get("user-agent")
    }
    devices_data.append(device_info)

    # Формируем HTML ответ
    html_content = f"""
    <html>
    <head><title>Device Info</title></head>
    <body>
        <h1>Информация об устройстве</h1>
        <p><strong>IP-адрес:</strong> {client_ip}</p>
        <p><strong>MAC-адрес:</strong> {mac_address}</p>
        <p><strong>Время запроса:</strong> {current_time}</p>
        <p><strong>User Agent:</strong> {device_info['user_agent']}</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/all-devices")
async def get_all_devices():
    """Возвращает список всех обнаруженных устройств"""
    return {"devices": devices_data}


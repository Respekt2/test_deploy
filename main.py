from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import requests
from datetime import datetime

app = FastAPI()


def is_russian_ip(ip: str) -> bool:
    """Проверяет, является ли IP российским"""
    try:
        response = requests.get(f"http://ip-api.com/json/{ip}?fields=countryCode")
        data = response.json()
        return data.get("countryCode") == "RU"
    except:
        return False


@app.get("/", response_class=HTMLResponse)
async def check_ip(request: Request):
    client_ip = request.client.host

    if not is_russian_ip(client_ip):
        return HTMLResponse("""
        <html>
        <head><title>Доступ запрещен</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1 style="color: red;">Офай VPN, долбаеб!</h1>
            <p style="font-size: 24px;">Доступ разрешен только с российских IP-адресов</p>
            <p>Ваш IP: {}</p>
            <img src="https://i.imgur.com/8KM6PVx.jpg" style="max-width: 500px; margin-top: 30px;">
        </body>
        </html>
        """.format(client_ip))

    # Основная страница для российских IP
    return HTMLResponse("""
    <html>
    <head><title>Добро пожаловать</title></head>
    <body style="font-family: Arial; text-align: center; padding: 50px;">
        <h1 style="color: green;">Доступ разрешен</h1>
        <p style="font-size: 24px;">Вы используете российский IP: {}</p>
        <p>Время входа: {}</p>
    </body>
    </html>
    """.format(client_ip, datetime.now().strftime("%d.%m.%Y %H:%M:%S")))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
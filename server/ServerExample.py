# Тестовый HTTP-сервер для ESP32 на MicroPython.
# Принимает JSON и отдаёт JSON. Нужен, чтобы проверить,
# что связь с устройством по сети работает.

import network
import socket
import json

# Данные для подключения к Wi-Fi. Замени на свои.
SSID = "dobriyden"
PASSWORD = "dendobriy"

# Порт, на котором будет работать сервер.
# 80 — стандартный для HTTP, поэтому в адресе его можно не писать.
PORT = 80


def connect_wifi():
    """Подключаемся к Wi-Fi как обычный клиент (как телефон или ноутбук)."""
    wlan = network.WLAN(network.WLAN.IF_STA)  # IF_STA = режим клиента
    wlan.active(True)  # включаем Wi-Fi модуль
    if not wlan.isconnected():
        print("подключаемся к", SSID)
        wlan.connect(SSID, PASSWORD)
        # Ждём, пока не подключимся. Без этого код пойдёт дальше слишком рано.
        while not wlan.isconnected():
            pass
    # Печатаем IP-адрес — по нему будем стучаться к серверу с ноутбука.
    print("ip:", wlan.ifconfig()[0])


def parse_request(raw):
    """Разбираем сырые байты HTTP-запроса на части.

    HTTP-запрос выглядит примерно так:

        POST /echo HTTP/1.1\r\n
        Host: 192.168.1.42\r\n
        Content-Length: 17\r\n
        \r\n
        {"hello": "world"}

    Сначала идут строки с заголовками, потом пустая строка,
    потом тело запроса (если есть).
    """
    # Разделяем заголовки и тело по пустой строке.
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")

    # Первая строка — это "POST /echo HTTP/1.1". Берём метод и путь.
    method, path, _ = lines[0].decode().split(" ", 2)

    # Остальные строки — заголовки вида "Имя: значение".
    # Складываем их в словарь, имена приводим к нижнему регистру,
    # чтобы потом не думать про "Content-Length" vs "content-length".
    headers = {}
    for line in lines[1:]:
        k, _, v = line.decode().partition(":")
        headers[k.strip().lower()] = v.strip()

    return method, path, headers, body


def read_full_body(client, body, headers):
    """Дочитываем тело запроса до конца.

    Первый recv() мог получить не всё тело, особенно если оно большое.
    В заголовке Content-Length написано, сколько байт всего должно быть,
    поэтому читаем из сокета, пока не наберём нужное количество.
    """
    length = int(headers.get("content-length", "0"))
    while len(body) < length:
        body += client.recv(min(1024, length - len(body)))
    return body


def respond(client, status, payload):
    """Отправляем клиенту ответ в формате JSON.

    HTTP-ответ устроен так же, как и запрос:
    строка статуса, заголовки, пустая строка, тело.
    """
    body = json.dumps(payload).encode()  # превращаем словарь в JSON-байты
    client.send(b"HTTP/1.0 " + status.encode() + b"\r\n")
    client.send(b"Content-Type: application/json\r\n")
    # Content-Length нужен, чтобы клиент понял, где заканчивается ответ.
    client.send(b"Content-Length: " + str(len(body)).encode() + b"\r\n\r\n")
    client.send(body)


def handle(client):
    """Обрабатываем один входящий запрос."""
    raw = client.recv(2048)
    if not raw:
        return  # клиент отвалился, не успев ничего прислать
    method, path, headers, body = parse_request(raw)
    print(method, path)  # для удобства видим в консоли, что пришло

    # GET / — простая проверка, что сервер живой.
    # Открой http://<ip-устройства>/ в браузере и увидишь JSON.
    if method == "GET" and path == "/":
        return respond(
            client, "200 OK", {"ok": True, "msg": "spectrometer test server"}
        )

    # POST /echo — принимаем JSON и возвращаем его обратно с приписками.
    # Проверить можно так:
    #   curl -X POST http://<ip>/echo -d '{"x": 1}'
    if method == "POST" and path == "/echo":
        body = read_full_body(client, body, headers)
        try:
            data = json.loads(body)  # пытаемся разобрать JSON
        except ValueError:
            # JSON оказался кривой — честно сообщаем об ошибке.
            return respond(client, "400 Bad Request", {"error": "invalid json"})
        return respond(client, "200 OK", {"received": data, "length": len(body)})

    # Если путь не совпал ни с одним из наших — отвечаем 404.
    respond(client, "404 Not Found", {"error": "not found"})


def serve():
    """Запускаем сервер: открываем сокет и в цикле принимаем клиентов."""
    # 0.0.0.0 значит "слушать на всех сетевых интерфейсах".
    addr = socket.getaddrinfo("0.0.0.0", PORT)[0][-1]
    s = socket.socket()
    # SO_REUSEADDR позволяет перезапустить сервер сразу после падения,
    # без него порт остаётся "занят" ещё какое-то время.
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(2)  # очередь до 2 ожидающих подключений
    print("слушаем порт :%d" % PORT)

    # Главный цикл: ждём клиента, обрабатываем, закрываем соединение.
    while True:
        client, _ = s.accept()
        try:
            handle(client)
        except Exception as e:
            # Один кривой запрос не должен ронять весь сервер.
            print("ошибка:", e)
        finally:
            client.close()

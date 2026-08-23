"""
auth.py — Проверка пользователей (Аутентификация).

Что такое Middleware (Охранник)?
Представьте, что наш сервер — это закрытый клуб. Эндпоинты — это VIP-комнаты.
Middleware — это охранник на входе в клуб. 
Прежде чем пустить запрос к коду, охранник просит показать пропуск (Токен).
Если пропуска нет или он поддельный — охранник разворачивает запрос (ошибка 401), 
и основной код даже не узнает о попытке входа.
"""

# HTTPException нужен, чтобы прервать запрос и вернуть ошибку (например, 401 - Нет доступа).
# Request содержит всю информацию о входящем запросе от пользователя.
from fastapi import HTTPException, Request

# auth из firebase_admin умеет проверять подлинность пропусков (токенов).
from firebase_admin import auth


async def get_current_user(request: Request) -> dict:
    """
    Эта функция работает как охранник. 
    Она берет токен из заголовка запроса и расшифровывает его.
    """
    
    # 1. Запрашиваем пропуск. 
    # Фронтенд обычно присылает его в заголовке "Authorization".
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        # Пропуска нет? Выгоняем (ошибка 401).
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Нет заголовка авторизации"}}
        )

    # 2. Проверяем формат. Правильный формат: "Bearer <длинный_набор_букв>"
    # "Bearer" означает "Предъявитель" (кто предъявил токен, тот и владелец).
    parts = auth_header.split(" ")

    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Неправильный формат токена"}}
        )

    token = parts[1] # Это и есть наш пропуск (JWT токен)

    # 3. Проверка подлинности (Защита от подделки).
    # JWT токен имеет криптографическую подпись. 
    # Мы просим Google (Firebase) проверить, действительно ли этот токен выдали они.
    try:
        decoded_token = auth.verify_id_token(token)
    except auth.ExpiredIdTokenError:
        # Срок действия пропуска истек (пользователю нужно залогиниться заново)
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Токен устарел"}}
        )
    except Exception:
        # Пропуск поддельный или поврежден
        raise HTTPException(
            status_code=401,
            detail={"error": {"code": "UNAUTHORIZED", "message": "Недействительный токен"}}
        )

    # 4. Проверка пройдена!
    # Возвращаем словарь с главной информацией о человеке. 
    # Теперь любой эндпоинт может узнать, кто именно к нему пришел (uid).
    return {
        "uid": decoded_token["uid"],
        "email": decoded_token.get("email", ""),
        "name": decoded_token.get("name", ""),
    }

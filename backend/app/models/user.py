"""
user.py — Форматы данных (схемы) для работы с пользователями.

Зачем нам несколько разных схем для одного пользователя?
Частая ошибка новичков — создать одну гигантскую схему `User` и использовать ее везде.
Но давайте подумаем:
1. Когда пользователь только регистрируется (Request), мы требуем от него указать имя и цель.
2. Когда мы возвращаем данные (Response), мы добавляем туда уникальный ID (uid) и дату регистрации.
Поэтому мы разделяем входящие данные (Request) и исходящие (Response). Это делает API безопасным и предсказуемым.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

# Field из Pydantic позволяет добавлять дополнительные правила (например, минимальную длину строки).
from pydantic import BaseModel, Field


class IntensityLevel(str, Enum):
    """
    Что такое Enum (Перечисление)?
    Это жесткий список разрешенных вариантов. 
    Если бы мы оставили просто `intensity: str`, фронтенд мог бы прислать "очень жестко".
    С Enum сервер примет только "chill", "normal" или "brutal", а на все остальное выдаст ошибку.
    """
    CHILL = "chill"
    NORMAL = "normal"
    BRUTAL = "brutal"


class Language(str, Enum):
    """Доступные языки интерфейса."""
    EN = "en"
    RU = "ru"


class CreateProfileRequest(BaseModel):
    """
    Схема для создания пользователя (отправляется с фронтенда при первом входе).
    Слово "Request" в названии подсказывает, что эти данные приходят к нам от клиента.
    
    Field(...) с троеточием означает, что поле ОБЯЗАТЕЛЬНО для заполнения.
    """
    displayName: str = Field(..., min_length=1, max_length=100, description="Имя пользователя")
    goal: str = Field(..., description="Цель обучения (например, 'job' - найти работу)")
    intensity: IntensityLevel = Field(..., description="Как часто агент должен писать")
    language: Language = Field(default=Language.EN, description="Язык (по умолчанию английский)")


class UpdateProfileRequest(BaseModel):
    """
    Схема для обновления профиля.
    
    Что такое Optional? 
    Это значит "может быть заполнено, а может быть пустым (None)".
    Если пользователь хочет поменять только имя, ему не нужно заново отправлять цель и язык.
    """
    displayName: Optional[str] = Field(None, min_length=1, max_length=100)
    goal: Optional[str] = None
    intensity: Optional[IntensityLevel] = None
    language: Optional[Language] = None

    # extra = "forbid" означает "запретить лишнее". 
    # Если хакер попытается прислать поле "isAdmin": True, сервер выдаст ошибку, 
    # так как этого поля нет в нашем списке.
    model_config = {"extra": "forbid"}


class UserProfile(BaseModel):
    """
    Полная информация о пользователе, которую сервер ОТПРАВЛЯЕТ на фронтенд.
    Обратите внимание: здесь есть поля `uid` и `createdAt`. Пользователь не может 
    их прислать при создании — их генерирует сервер.
    """
    uid: str
    email: str
    displayName: str
    goal: str
    intensity: IntensityLevel
    language: Language = Language.EN
    telegramLinked: bool = False             # Привязан ли Телеграм?
    telegramUserId: Optional[int] = None     # ID пользователя в Телеграме
    telegramUsername: Optional[str] = None   # Ник в Телеграме (если есть)
    githubConnected: bool = False            # Подключен ли GitHub?
    githubUsername: Optional[str] = None     # Ник в GitHub (если есть)
    createdAt: datetime                      # Когда аккаунт был создан
    updatedAt: datetime                      # Когда аккаунт обновлялся последний раз
    onboardingCompleted: bool = False        # Прошел ли пользователь начальную настройку

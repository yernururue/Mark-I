"""
user_service.py — Бизнес-логика и работа с базой данных (Service Layer).

Зачем нужен Сервисный Слой?
В программировании принято разделять обязанности (Layered Architecture):
1. API (эндпоинты) — только принимают запросы и отдают ответы (как официант в ресторане).
2. Service (сервисы) — выполняют саму работу, пишут в базу (как повар на кухне).
3. Database (база данных) — хранит информацию (как холодильник).

Если бы "официант" сам готовил еду (если бы мы писали запросы к базе прямо в эндпоинте),
то при появлении бота в Телеграме нам пришлось бы писать этот же код заново.
А так — и API, и бот просто просят "повара" (UserService) сделать работу.
"""
from datetime import datetime, timezone
from typing import Optional

# Импортируем тип FirestoreClient для подсказок в коде
from google.cloud.firestore_v1.client import Client as FirestoreClient

from app.models.user import CreateProfileRequest, UpdateProfileRequest, UserProfile


class UserService:
    """
    Класс, который умеет делать CRUD операции с пользователями.
    CRUD = Create (Создать), Read (Прочитать), Update (Обновить), Delete (Удалить).
    """

    def __init__(self, db: FirestoreClient):
        """
        Инициализация. Когда мы создаем "повара", мы даем ему доступ к "холодильнику" (базе db).
        В Firestore таблицы называются "коллекциями" (collection), а строки — "документами" (document).
        """
        self._db = db
        # Сохраняем ссылку на коллекцию "users", чтобы каждый раз не писать db.collection("users")
        self._collection = db.collection("users")

    def get_profile(self, uid: str) -> Optional[UserProfile]:
        """
        READ: Чтение профиля из базы по его уникальному ID (uid).
        """
        # Просим базу найти документ с названием `uid`
        doc = self._collection.document(uid).get()

        # Если документа нет — возвращаем пустоту (None)
        if not doc.exists:
            return None

        # Превращаем данные из базы в наш красивый класс UserProfile
        data = doc.to_dict()
        return self._firestore_to_profile(data)

    def create_profile(self, uid: str, email: str, request: CreateProfileRequest) -> UserProfile:
        """
        CREATE: Создание нового профиля.
        """
        # Получаем текущее время в стандарте UTC (единое мировое время)
        now = datetime.now(timezone.utc)

        # Собираем все данные в один большой словарь (документ).
        # Обратите внимание: мы заранее прописываем все поля (skills, telegramUserId), 
        # даже если они пока пустые. Это называется "Schema-first" — мы держим порядок в базе.
        doc_data = {
            "uid": uid,
            "email": email,
            "displayName": request.displayName,
            "goal": request.goal,
            "intensity": request.intensity.value, # Перечисления Enum нужно превращать в строки
            "language": request.language.value,
            "telegramUserId": None,
            "telegramUsername": None,
            "telegramChatId": None,
            "linkCode": None,
            "linkCodeExpiresAt": None,
            "githubConnected": False,
            "githubUsername": None,
            "githubTokenSecretName": None,
            "connectedRepos": [],
            "webhookIds": {},
            "skills": {},
            "onboardingCompleted": True,
            "createdAt": now,
            "updatedAt": now,
        }

        # Метод set() кладет наш словарь в базу. При этом мы сами задаем ID документа (uid).
        self._collection.document(uid).set(doc_data)

        # Возвращаем созданный профиль обратно (чтобы API могло отдать его фронтенду)
        return self._firestore_to_profile(doc_data)

    def update_profile(self, uid: str, request: UpdateProfileRequest) -> Optional[UserProfile]:
        """
        UPDATE: Обновление профиля.
        Важно: мы обновляем только те поля, которые прислал пользователь.
        """
        # Превращаем модель UpdateProfileRequest обратно в словарь.
        # exclude_none=True означает: "если поле пустое (пользователь его не менял) — выброси его".
        update_data = request.model_dump(exclude_none=True)

        # Если пользователь не прислал никаких изменений — просто возвращаем текущий профиль.
        if not update_data:
            return self.get_profile(uid)

        # Снова распаковываем Enum в строки
        if "intensity" in update_data:
            update_data["intensity"] = update_data["intensity"].value
        if "language" in update_data:
            update_data["language"] = update_data["language"].value

        # Обновляем дату последнего изменения
        update_data["updatedAt"] = datetime.now(timezone.utc)

        # Метод update() бережно заменяет только те поля, которые мы передали, 
        # не удаляя остальные данные документа (в отличие от set()).
        self._collection.document(uid).update(update_data)

        # Отдаем свежую версию профиля из базы
        return self.get_profile(uid)

    def get_user_by_telegram_id(self, telegram_user_id: int) -> Optional[str]:
        """
        Ищет пользователя по telegramUserId и возвращает его uid.
        """
        # В Firestore можно использовать query
        users_ref = self._collection.where(filter=("telegramUserId", "==", telegram_user_id)).limit(1).get()
        if not users_ref:
            return None
        return users_ref[0].id

    def _firestore_to_profile(self, data: dict) -> UserProfile:
        """
        Вспомогательная внутренняя функция (начинается с нижнего подчеркивания).
        База данных Firestore отдает время в своем собственном формате (Timestamp).
        Эта функция переводит время из формата базы в формат Питона (datetime) 
        и упаковывает все данные в модель UserProfile.
        """
        created_at = data.get("createdAt")
        updated_at = data.get("updatedAt")

        if hasattr(created_at, "timestamp"):
            created_at = datetime.fromtimestamp(created_at.timestamp(), tz=timezone.utc)
        if hasattr(updated_at, "timestamp"):
            updated_at = datetime.fromtimestamp(updated_at.timestamp(), tz=timezone.utc)

        return UserProfile(
            uid=data["uid"],
            email=data.get("email", ""),
            displayName=data.get("displayName", ""),
            goal=data.get("goal", ""),
            intensity=data.get("intensity", "normal"),
            language=data.get("language", "en"),
            telegramLinked=data.get("telegramUserId") is not None, # Если ID есть — значит телеграм привязан
            telegramUsername=data.get("telegramUsername"),
            githubConnected=data.get("githubConnected", False),
            githubUsername=data.get("githubUsername"),
            createdAt=created_at,
            updatedAt=updated_at,
            onboardingCompleted=data.get("onboardingCompleted", False),
        )

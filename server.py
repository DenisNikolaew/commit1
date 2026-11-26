import uuid
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import engine, SessionLocal, init_db, User, UserSession, Character, Location, Item, Inventory
from game_logic import player_attack, player_move, use_item, add_item

app = FastAPI(title="Text RPG Server")
init_db()

WORLD_CHAT = ["[СИСТЕМА]: Сервер запущен!"]
LAST_SEEN = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class AuthReq(BaseModel):
    username: str
    password: str


class MoveReq(BaseModel):
    token: str
    location_id: int


class AttackReq(BaseModel):
    token: str
    damage: int
    enemy_key: str


class ItemReq(BaseModel):
    token: str
    item_id: int


class LogoutReq(BaseModel):
    token: str

class ChatReq(BaseModel):
    token: str
    comment: str

@app.post("/chat/send")
def send_chat_message(data: ChatReq, db: Session = Depends(get_db)):
    user = get_current_user(data, db)
    text = data.comment.strip()
    
    if not text:
        raise HTTPException(status_code=401, detail="Ошибка")
    
    char_user = user.character.character_name if user.character else user.username
    WORLD_CHAT.append(f"{char_user}: {text}")
    
    if len(WORLD_CHAT) >= 50:
        del WORLD_CHAT[:-50]
        
    return {"status": "ok"}

def get_current_user(token: str, db: Session) -> User:
    session = db.query(UserSession).filter(UserSession.session_token == token).first()
    if not session:
        raise HTTPException(
            status_code=401,
            detail="Сессия не найдена. Войдите заново."
        )
    return session.user

@app.post("/register")
def register(data: AuthReq, db: Session = Depends(get_db)):
    if not data.username.strip() or not data.password.strip():
        raise HTTPException(status_code=400, detail="Пустой логин или пароль")

    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким именем уже существует")

    loc = db.query(Location).first()
    if not loc:
        loc = Location(location_name="Таверна")
        db.add(loc)
        db.flush()

    char = Character(
        character_name=data.username,
        character_health=100,
        character_level=1
    )
    db.add(char)
    db.flush()

    new_user = User(
        username=data.username,
        userpassword=data.password,
        character_id=char.character_id,
        location_id=loc.location_id
    )
    db.add(new_user)
    db.commit()

    return {"status": "ok", "message": "Персонаж успешно зарегистрирован!"}


@app.post("/login")
def login(data: AuthReq, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        User.username == data.username,
        User.userpassword == data.password
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")

    db.query(UserSession).filter(UserSession.user_id == user.user_id).delete()
    token = str(uuid.uuid4())
    new_session = UserSession(
        session_token=token,
        user_id=user.user_id,
        created_at=datetime.utcnow(),
        expires_at=None
    )
    db.add(new_session)
    db.commit()

    LAST_SEEN[user.username] = datetime.utcnow()
    return {"token": token, "username": user.username}


@app.get("/state/{token}")
def get_state(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    char = user.character

    now = datetime.utcnow()
    LAST_SEEN[user.username] = now

    online_names = [
        uname for uname, last_time in list(LAST_SEEN.items())
        if (now - last_time).total_seconds() <= 4
    ]

    leaders = db.query(Character).order_by(Character.character_level.desc()).limit(5).all()
    locations = db.query(Location).all()

    return {
        "player": {
            "username": char.character_name,
            "hp": char.character_health,
            "level": char.character_level,
            "location": user.location.location_name if user.location else "Таверна",
            "inventory": [
                {"id": inv.item.item_id, "name": inv.item.item_name, "count": inv.quantity}
                for inv in char.inventory_items if inv.item
            ]
        },
        "locations": [{"id": l.location_id, "name": l.location_name} for l in locations],
        "online_players": online_names,
        "leaderboard": [
            {"username": c.character_name, "score": f"Ур. {c.character_level}"}
            for c in leaders
        ],
        "logs": WORLD_CHAT[-10:]
    }


@app.post("/user/logout")
def logout(user: LogoutReq, db: Session = Depends(get_db)):
    session = db.query(UserSession).filter(UserSession.session_token == user.token).first()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")

    if session.user:
        LAST_SEEN.pop(session.user.username, None)

    db.delete(session)
    db.commit()
    return {"status": "ok", "message": "Токен был удален"}


@app.post("/user/move")
def player_server_move(data: MoveReq, db: Session = Depends(get_db)):
    user = get_current_user(data.token, db)
    message = player_move(user, data.location_id, db)

    WORLD_CHAT.append(
        f"[МИР]: {user.character.character_name} перешел в новую локацию."
    )
    return {"status": "ok", "message": message}


@app.post("/user/attack")
def player_server_attack(data: AttackReq, db: Session = Depends(get_db)):
    user = get_current_user(data.token, db)
    battle_result = player_attack(user, data.enemy_key, data.damage, db)
    return {"status": "ok", **battle_result}


@app.post("/user/use_item")
def player_sever_use_item(data: ItemReq, db: Session = Depends(get_db)):
    user = get_current_user(data.token, db)
    result = use_item(user, db, data.item_id)
    return {"status": "ok", "result": result}

def seed_locations():
    db = SessionLocal()
    try:
        default_locations = [
            "Таверна",
            "Тёмный лес",
            "Старая мельница",
            "Заброшенные руины",
            "Замок Камелот"
        ]
        for name in default_locations:
            if not db.query(Location).filter(Location.location_name == name).first():
                db.add(Location(location_name=name))
        db.commit()
    finally:
        db.close()

@app.get("/online/{token}")     
def show_users(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    char = user.character
    
    now = datetime.utcnow()
    LAST_SEEN[user.username] = now
    
    online_names = [
        uname for uname, last_time in list(LAST_SEEN.items())
        if (now - last_time).total_seconds() <= 4
    ]
    
    return {
        "player": {
                    "username": char.character_name,
                    "level": char.character_level,
                },
                "online_players": online_names,
    }
    
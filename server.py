import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import engine, SessionLocal, init_db, User, UserSession, Character, Location, Item, Inventory
from game_logic import player_attack, player_move, use_item, add_item

app = FastAPI(title="Text RPG Server")
init_db()

WORLD_CHAT = ["[СИСТЕМА]: Сервер запущен!"]


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
    token: int
    damage: int
    enemy_key: int
    
class ItemReq(BaseModel):
    token: str
    item_id: int

def get_current_user(token: str, db: Session) -> User:
    session = db.query(UserSession).filter(UserSession.session_token == token).first()
    if not session or (session.expires_at and session.expires_at < datetime.utcnow()):
        raise HTTPException(
            status_code=401,
            detail="Сессия истекла или не найдена. Войдите заново."
        )

    session.expires_at = datetime.utcnow() + timedelta(minutes=5)
    db.commit()
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

    token = str(uuid.uuid4())
    new_session = UserSession(
        session_token=token,
        user_id=user.user_id,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(new_session)
    db.commit()

    return {"token": token, "username": user.username}


@app.get("/state/{token}")
def get_state(token: str, db: Session = Depends(get_db)):
    user = get_current_user(token, db)
    char = user.character

    now = datetime.utcnow()
    active_sessions = db.query(UserSession).filter(UserSession.expires_at >= now).all()
    online_names = list({s.user.username for s in active_sessions if s.user})

    leaders = db.query(Character).order_by(Character.character_level.desc()).limit(5).all()
    locations = db.query(Location).all()

    return {
        "player": {
            "username": char.character_name,
            "hp": char.character_health,
            "level": char.character_level,
            "location": user.location.location_name if user.location else "Таверна",
            "inventory": [
                {"name": inv.item.item_name, "count": inv.quantity}
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
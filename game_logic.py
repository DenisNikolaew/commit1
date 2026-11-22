import random
from sqlalchemy.orm import Session
from fastapi import FastAPI, HTTPException
from models import User, Character, Item, Inventory, Location

app = FastAPI()

enemy_list = {
    "bandits": 
        {
        "name": "Разбойник",
        "health": 60,
        "damage": 10,
        "exp": 50
        },
    "dark knight":
        {
            "name": "Темный рыцарь",
            "health": 80,
            "damage": 20,
            "exp": 70
        },
    "wolf": 
        {
            "name": "Волк",
            "health": 70,
            "damage": 15,
            "exp": 60
        }
}


def player_move(user: User, location_id: Location,db: Session):
    location = db.query(Location).filter(Location.location_id == location_id).first()
    if not location:
        raise HTTPException (status_code=401, detail="Локация не найдена")
    
    user.user_id = location.location_id
    db.commit()
    
    return f"Вы находитесь в локации {location.location_name}"

def player_health(user: User, amount: int,db: Session):
    char = user.character
    char.character_health = min(100, char.character_health + amount)
    db.commit()
    return char.character_health

def player_attack(user: User, enemy_key, amount: int, db: Session):
    
    if enemy_key not in enemy_list:
        raise HTTPException(status_code=401, detail="нет такого врага")
    
    enemy_data = enemy_list[enemy_key]
    enemy_name = enemy_list["name"]
    enemy_health = enemy_list["health"]
    enemy_base_dmg = enemy_data["damage"]
    
    char = user.character
    logs = [f"Вы вступили в бой с врагом: {enemy_name} (HP: {enemy_health})!"]
    
    
    while enemy_health > 0 and char.character_health > 0:
        
        base_damage = char.character_level + amount
        player_dmg = random.randint(base_damage, base_damage + 3)
        enemy_hp -= player_dmg
        logs.append(f"{char.character_name} наносит {player_dmg} урона. У врага осталось {max(0, enemy_hp)} HP")

        if enemy_hp <= 0:
            char.character_level += 1
            logs.append(f"Победа! {enemy_name} повержен. Ваш уровень теперь {char.character_level}!")
            break

        enemy_dmg = random.randint(max(1, enemy_base_dmg - 2), enemy_base_dmg + 2)
        char.character_health = max(0, char.char.character_health - enemy_dmg)
        logs.append(f"{enemy_name} бьет в ответ на {enemy_dmg} урона. Ваше HP: {char.character_health}")

        if char.character_health == 0:
            char.character_health = 100
            logs.append("Вы погибли")
            break

    db.commit()

    return {
        "player_hp": char.character_health,
        "level": char.character_level,
        "logs": logs
    }
    
def player_inventory(user: User):
    char = user.character
    if not char.inventory_items:
        return "В инвентаре ничего нет"
    
    return [
        {"id": inv.item.item_id, "name": inv.item.item_name, "count": inv.quantity}
        for inv in char.inventory_items if inv.item
    ]

def add_item(user: User, Item_id: int, count: int, db: Session):
    char = user.character
    
    item = db.query(Item).filter(Item.item_id == item.Item_id).first()
    
    if not item:
        raise HTTPException(status_code=401, detail="нет")
    
    inv_record = db.query(Inventory).filter(Inventory.character_id == char.character_id, Inventory.item_id == Item_id).first()
    
    if inv_record:
        inv_record.quantity += count
    else:
        new_inv = Inventory(
            character_id=char.character_id,
            item_id=Item_id,
            quantity=count
        )
        db.add(new_inv)
        
    db.commit()
    return f"Получен предмет: {item.item_name} (x{count})"

def use_item(user: User, db: Session, item_id: int):
    char = user.character
    
    inv_record = db.query(Inventory).filter(Inventory.character_id == char.character_id, Inventory.item_id == item_id).first()
    
    if not inv_record or inv_record.quantity <= 0:
        raise HTTPException(status_code=401, detail="таклго предмета нет")
    
    item_name = inv_record.item.item_name
    
    inv_record.quantity -= 1
    if inv_record.quantity == 0:
        db.delete(item_name)
        
    char.character_health = min(100, char.character_health + 30)
    
    db.commit()
    return f"Вы использовали {item_name}. Текущее здоровье: {char.character_health} HP"
import tkinter as tk
from tkinter import messagebox
import requests

BASE_URL = "http://127.0.0.1:8000"
token = None

root = tk.Tk()
root.title("Король Артур и священный кубок")
root.geometry("560x620")


def clear_screen():
  for widget in root.winfo_children():
    widget.destroy()


def login_screen():
  clear_screen()

  tk.Label(root, text="Логин:").pack(pady=5)
  user_entry = tk.Entry(root)
  user_entry.pack()

  tk.Label(root, text="Пароль:").pack(pady=5)
  pass_entry = tk.Entry(root, show="*")
  pass_entry.pack()

  def do_login():
    global token
    try:
      resp = requests.post(
          f"{BASE_URL}/login",
          json={"username": user_entry.get(), "password": pass_entry.get()},
          timeout=3,
      )
      if resp.status_code == 200:
        token = resp.json()["token"]
        game_screen()
      else:
        messagebox.showerror(
            "Ошибка", resp.json().get("detail", "Ошибка входа")
        )
    except Exception as e:
      messagebox.showerror("Ошибка соединения", f"Сервер недоступен:\n{e}")

  def do_register():
    try:
      resp = requests.post(
          f"{BASE_URL}/register",
          json={"username": user_entry.get(), "password": pass_entry.get()},
          timeout=3,
      )
      if resp.status_code == 200:
        messagebox.showinfo("Успех", resp.json()["message"])
      else:
        messagebox.showerror(
            "Ошибка", resp.json().get("detail", "Ошибка регистрации")
        )
    except Exception as e:
      messagebox.showerror("Ошибка соединения", f"Сервер недоступен:\n{e}")

  tk.Button(root, text="Войти", command=do_login, width=15).pack(pady=10)
  tk.Button(root, text="Регистрация", command=do_register, width=15).pack()


def game_screen():
  clear_screen()

  stats_label = tk.Label(root, text="Загрузка...", font=("Arial", 10, "bold"))
  stats_label.pack(pady=5)

  inv_label = tk.Label(root, text="Инвентарь: пусто", wraplength=520)
  inv_label.pack(pady=2)


  btn_frame = tk.Frame(root)
  btn_frame.pack(pady=5)

  log_text = tk.Text(root, height=12, width=65, state=tk.DISABLED)
  log_text.pack(pady=5)
  log_text.tag_config("error", foreground="red")
  log_text.tag_config("info", foreground="blue")

  def append_log(text, tag=None):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, text + "\n", tag)
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)

  def do_show_users():
    if not token:
      return
    try:
      resp = requests.get(f"{BASE_URL}/online/{token}", timeout=2)
      if resp.status_code == 200:
        data = resp.json()
        users = data.get("online_players", [])
        if users:
          users_str = ", ".join(users)
          append_log(f"[Онлайн ({len(users)})]: {users_str}", "info")
          messagebox.showinfo(
              "Игроки в сети",
              f"Всего в сети: {len(users)}\n\n"
              + "\n".join(f"• {u}" for u in users),
          )
        else:
          append_log("[Онлайн]: Никого нет в сети.", "info")
      else:
        append_log("[Ошибка]: Не удалось получить список игроков.", "error")
    except Exception as e:
      append_log(f"[Ошибка сети]: {e}", "error")

  def do_logout():
    global token
    if token:
      try:
        requests.post(
            f"{BASE_URL}/user/logout", json={"token": token}, timeout=1
        )
      except Exception:
        pass
    token = None
    login_screen()

  tk.Button(btn_frame, text="Онлайн", command=do_show_users, width=10).pack(
      side=tk.LEFT, padx=4
  )
  tk.Button(btn_frame, text="Выйти", command=do_logout, width=10).pack(
      side=tk.LEFT, padx=4
  )

  def update_state():
    global token
    if not token:
      return
    try:
      resp = requests.get(f"{BASE_URL}/state/{token}", timeout=1)
      if resp.status_code != 200:
        token = None
        messagebox.showwarning("Сессия", "Сессия истекла")
        login_screen()
        return

      state = resp.json()
      p = state["player"]

      inv_list = []
      for item in p.get("inventory", []):
        prefix = f"[{item['id']}] " if "id" in item else ""
        inv_list.append(f"{prefix}{item['name']} (x{item['count']})")
      inv_text = ", ".join(inv_list) if inv_list else "пусто"

      inv_label.config(text=f"Инвентарь: {inv_text}")
      stats_label.config(
          text=(
              f"{p['username']} | Ур: {p['level']} | HP: {p['hp']} | Локация:"
              f" {p['location']} | Онлайн: {len(state['online_players'])}"
          )
      )
    except Exception:
      pass

  def poll():
    if token:
      update_state()
      root.after(1000, poll)

  poll()


def on_closing():
  global token
  if token:
    try:
      requests.post(f"{BASE_URL}/user/logout", json={"token": token}, timeout=2)
    except Exception:
      pass
  root.destroy()


root.protocol("WM_DELETE_WINDOW", on_closing)
login_screen()
root.mainloop()

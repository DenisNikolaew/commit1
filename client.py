import tkinter as tk
from tkinter import messagebox
import requests

BASE_URL = "http://127.0.0.1:8000"
token = None 

root = tk.Tk()
root.title("Король Артур и священный кубок")
root.geometry("500x450")


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
      )
      if resp.status_code == 200:
        messagebox.showinfo("Успех", resp.json()["message"])
      else:
        messagebox.showerror(
            "Ошибка", resp.json().get("detail", "Ошибка регистрации")
        )
    except Exception as e:
      messagebox.showerror("Ошибка соединения", f"Сервер недоступен:\n{e}")

  tk.Button(root, text="Войти", command=do_login).pack(pady=10)
  tk.Button(root, text="Регистрация", command=do_register).pack()


def game_screen():
  clear_screen()

  stats_label = tk.Label(root, text="Загрузка...", font=("Arial", 10, "bold"))
  stats_label.pack(pady=5)

  btn_frame = tk.Frame(root)
  btn_frame.pack(pady=5)

  log_text = tk.Text(root, height=15, width=58, state=tk.DISABLED)
  log_text.pack(pady=10)

  def append_log(text):
    log_text.config(state=tk.NORMAL)
    log_text.insert(tk.END, text + "\n")
    log_text.see(tk.END)
    log_text.config(state=tk.DISABLED)

  def update_state():
    global token
    if not token:
      return
    try:
      resp = requests.get(f"{BASE_URL}/state/{token}")
      if resp.status_code != 200:
        token = None
        messagebox.showwarning("Сессия", "Сессия истекла")
        login_screen()
        return

      state = resp.json()
      p = state["player"]
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
      root.after(3000, poll)

  poll()


login_screen()
root.mainloop()

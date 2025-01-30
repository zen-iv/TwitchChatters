import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
from multiprocessing import Process, Queue
import time
from pynput import keyboard 
from shared import BROADCAST_COMMAND

BROADCAST_COMMAND = "broadcast_plus"

class BotGUI(tk.Tk):
    def __init__(self, config, audio_proc, shared_queue):
        super().__init__()
        self.title("Twitch Bot Controller")
        self.geometry("800x600")
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        self.config = config
        self.audio_proc = audio_proc
        self.shared_queue = shared_queue
        self.running = True
        self.bot_processes = {}

        self.stats = {
            'messages_sent': 0,
            'laughter_detected': 0,
            'last_action': 'Нет действий',
            'model_status': '✔️ Подключена' if os.path.exists(config['stt']['model_path']) else '❌ Ошибка'
        }

        if self.stats['model_status'].startswith('❌'):
            messagebox.showerror("Ошибка", f"Модель STT не найдена по пути: {config['stt']['model_path']}")

        self.create_widgets()
        self.setup_hotkeys()
        self.update_stats()

    def create_widgets(self):
        self.notebook = ttk.Notebook(self)
        
        # Вкладка управления
        self.control_frame = ttk.Frame(self.notebook)
        self.create_control_tab()
        
        # Вкладка статистики
        self.stats_frame = ttk.Frame(self.notebook)
        self.create_stats_tab()
        
        # Горячие клавиши
        self.hotkeys_frame = ttk.Frame(self.notebook)
        self.create_hotkeys_tab()

        self.notebook.add(self.control_frame, text="Управление")
        self.notebook.add(self.stats_frame, text="Статистика")
        self.notebook.add(self.hotkeys_frame, text="Горячие клавиши")
        self.notebook.pack(expand=True, fill='both')

    def create_control_tab(self):
        self.start_btn = ttk.Button(self.control_frame, text="Старт", command=self.start_bots)
        self.start_btn.grid(row=0, column=0, padx=10, pady=5)
        
        self.stop_btn = ttk.Button(self.control_frame, text="Стоп", command=self.stop_bots, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=10, pady=5)

        ttk.Label(self.control_frame, text="Статус модели:").grid(row=1, column=0, sticky='w', padx=10)
        self.model_status_label = ttk.Label(self.control_frame, text=self.stats['model_status'])
        self.model_status_label.grid(row=1, column=1, sticky='w')

        self.status_labels = {}
        for idx, acc in enumerate(self.config['accounts']):
            lbl = ttk.Label(self.control_frame, text=f"{acc['username']}: Неактивен")
            lbl.grid(row=idx+2, column=0, sticky='w', padx=10)
            self.status_labels[acc['username']] = lbl

    def create_stats_tab(self):
        self.stats_vars = {
            'messages_sent': tk.StringVar(value="0"),
            'laughter_detected': tk.StringVar(value="0"),
            'last_action': tk.StringVar(value="Нет действий")
        }

        for idx, (key, var) in enumerate(self.stats_vars.items()):
            ttk.Label(self.stats_frame, text=key.replace('_', ' ').title()+":").grid(row=idx, column=0, sticky='w', padx=10)
            ttk.Label(self.stats_frame, textvariable=var).grid(row=idx, column=1, sticky='w')

    def create_hotkeys_tab(self):
        ttk.Label(self.hotkeys_frame, text="Горячие клавиши:").grid(row=0, column=0, sticky='w', padx=10)
        
        self.emote_btn = ttk.Button(
            self.hotkeys_frame, 
            text="Спам смайлами (F13)", 
            command=self.send_emotes_spam
        )
        self.emote_btn.grid(row=1, column=0, padx=10, pady=5, sticky='w')
        
        self.plus_btn = ttk.Button(
            self.hotkeys_frame,
            text="Принудительный + (F14)",
            command=self.force_plus
        )
        self.plus_btn.grid(row=2, column=0, padx=10, pady=5, sticky='w')

    def setup_hotkeys(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f13:
                    print("[HOTKEY] Нажата F13 - Спам смайлами")
                    self.send_emotes_spam()
                elif key == keyboard.Key.f14:
                    print("[HOTKEY] Нажата F14 - Принудительный +")
                    self.force_plus()
            except Exception as e:
                print(f"[HOTKEY] Ошибка: {e}")

        listener = keyboard.Listener(on_press=on_press)
        listener.daemon = True
        listener.start()

    def send_emotes_spam(self):
        print("[ACTION] Запущен спам смайлами")
        self.shared_queue.put(('emote_spam', None))
        self.stats['last_action'] = "Спам смайлами"
        self.stats['messages_sent'] += 5

    def force_plus(self):
        print("[ACTION] Принудительная отправка '+'")
        self.shared_queue.put((BROADCAST_COMMAND, None))
        self.stats['last_action'] = "Принудительный +"

    def update_stats(self):
        if not self.running: return
        
        try:
            for acc in self.config['accounts']:
                username = acc['username']
                process = self.bot_processes.get(username)
                status = "Неактивен"
                if process and process.is_alive():
                    status = "Активен"
                self.status_labels[username].config(text=f"{username}: {status}")
        except Exception as e:
            print(f"Ошибка обновления статусов: {e}")

        for key, var in self.stats_vars.items():
            var.set(str(self.stats[key]))

        self.after(1000, self.update_stats)

    def start_bots(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        threading.Thread(target=self.activate_bots, daemon=True).start()

    def activate_bots(self):
        try:
            from main import bot_runner  # Импорт внутри метода
            for acc in self.config['accounts']:
                username = acc['username']
                if username not in self.bot_processes:
                    personality = next(p for p in self.config['personalities'] if p['name'] == acc['personality'])
                    
                    p = Process(
                        target=bot_runner,
                        args=(
                            acc,
                            personality,
                            self.config['ai'],
                            self.shared_queue,
                            len(self.config['accounts'])
                        ),
                        daemon=True
                    )
                    self.bot_processes[username] = p
                    p.start()
                    time.sleep(1)
        except Exception as e:
            print(f"Ошибка активации ботов: {e}")

    def stop_bots(self):
        try:
            if self.audio_proc and hasattr(self.audio_proc, 'terminate'):
                self.audio_proc.terminate()
                self.audio_proc.join()
            
            for username, process in self.bot_processes.items():
                if process and process.is_alive():
                    process.terminate()
                    process.join()
            
            self.bot_processes.clear()
        except Exception as e:
            print(f"Ошибка остановки: {e}")
        finally:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def on_close(self):
        self.running = False
        self.stop_bots()
        self.destroy()
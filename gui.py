import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import random
from multiprocessing import Process, Queue
import time
from pynput import keyboard
from shared import BROADCAST_COMMAND
from modules.twitch_bot import bot_runner

class BotGUI(tk.Tk):
    def __init__(self, config, audio_proc, shared_queue):
        super().__init__()
        self.title("Twitch Bot Controller")
        self.geometry("800x400")
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.config = config
        self.audio_proc = audio_proc
        self.shared_queue = shared_queue
        self.running = True
        self.bot_processes = {}
        self.bot_states = {}
        self.create_widgets()
        self.setup_hotkeys()

    def create_widgets(self):
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        control_panel = ttk.LabelFrame(main_frame, text="Управление ботами")
        control_panel.pack(fill='x', pady=5)

        self.start_btn = ttk.Button(control_panel, text="Старт", command=self.start_bots)
        self.start_btn.pack(side='left', padx=5)
        
        self.stop_btn = ttk.Button(control_panel, text="Стоп", command=self.stop_bots, state=tk.DISABLED)
        self.stop_btn.pack(side='left', padx=5)

        bots_frame = ttk.LabelFrame(main_frame, text="Аккаунты")
        bots_frame.pack(fill='both', expand=True, pady=5)

        self.bot_checkboxes = {}
        for idx, acc in enumerate(self.config['accounts']):
            frame = ttk.Frame(bots_frame)
            frame.pack(fill='x', pady=2)
            
            var = tk.BooleanVar(value=True)
            cb = ttk.Checkbutton(frame, text=acc['username'], variable=var)
            cb.pack(side='left')
            self.bot_checkboxes[acc['username']] = var
            
            status_lbl = ttk.Label(frame, text="Неактивен")
            status_lbl.pack(side='right')
            self.bot_states[acc['username']] = status_lbl

        action_panel = ttk.LabelFrame(main_frame, text="Быстрые действия")
        action_panel.pack(fill='x', pady=5)

        self.plus_btn = ttk.Button(action_panel, text="Отправить + (F13)", command=self.force_plus)
        self.plus_btn.pack(side='left', padx=5)
        
        self.laugh_btn = ttk.Button(action_panel, text="Смех (F15)", command=self.send_laughter)
        self.laugh_btn.pack(side='left', padx=5)

    def setup_hotkeys(self):
        def on_press(key):
            try:
                if key == keyboard.Key.f13:
                    self.force_plus()
                elif key == keyboard.Key.f15:
                    self.send_laughter()
            except Exception as e:
                print(f"Ошибка в обработчике горячих клавиш: {e}")
        
        self.listener = keyboard.Listener(on_press=on_press)
        self.listener.daemon = True
        self.listener.start()

    def send_laughter(self):
        self.shared_queue.put(('laughter', None))
        print("Триггер смеха активирован")

    def force_plus(self):
        self.shared_queue.put(BROADCAST_COMMAND)
        print("Триггер + активирован")

    def start_bots(self):
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        threading.Thread(target=self.activate_bots, daemon=True).start()

    def activate_bots(self):
        try:
            accounts = [acc for acc in self.config['accounts'] 
                       if self.bot_checkboxes[acc['username']].get()]
            
            random.shuffle(accounts)
            delay_config = self.config.get('behavior', {}).get('activation_delay', 0.5)
            
            for acc in accounts:
                username = acc['username']
                if username not in self.bot_processes:
                    personality = self.config['personalities'].get(acc['personality'])
                    if not personality:
                        raise ValueError(f"Персонаж {acc['personality']} не найден")
                        
                    p = Process(target=bot_runner, 
                                args=(acc, personality, self.config['ai'], self.shared_queue))
                    self.bot_processes[username] = p
                    p.start()
                    self.bot_states[username].config(text="Запускается...")
                    time.sleep(random.uniform(delay_config*0.8, delay_config*1.2))

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка запуска ботов: {str(e)}")

    def stop_bots(self):
        try:
            for username, process in self.bot_processes.items():
                if process.is_alive():
                    process.terminate()
                    process.join()
                self.bot_states[username].config(text="Неактивен")
            self.bot_processes.clear()
        except Exception as e:
            print(f"Ошибка остановки: {e}")     
        finally:
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def on_close(self):
        self.running = False
        self.stop_bots()
        if self.audio_proc:
            self.audio_proc.terminate()
        self.listener.stop()
        self.destroy()
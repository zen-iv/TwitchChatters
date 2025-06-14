from multiprocessing import Process, Manager
from modules.stt import audio_capture_process
from modules.utils import load_config
from gui import BotGUI
from dotenv import load_dotenv

if __name__ == "__main__":
    load_dotenv()
    config = load_config()

    manager = Manager()
    queue = manager.Queue()

    audio_proc = Process(target=audio_capture_process, args=(queue, config['stt']))
    audio_proc.start()

    gui = BotGUI(config, audio_proc, queue)
    gui.mainloop()

    audio_proc.terminate()

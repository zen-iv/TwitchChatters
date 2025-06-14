import whisper
import numpy as np
import pyaudio
import time
import torch
import resampy
from threading import Thread, Event
from collections import deque

# Конфигурация
WHISPER_MODEL = "small"
INPUT_RATE = 48000
TARGET_RATE = 16000
CHANNELS = 2
CHUNK = 4096
ENERGY_THRESHOLD = 0.01  # Порог активации голоса
SILENCE_TIMEOUT = 6.0    # Таймаут молчания для отправки фразы

class VoiceProcessor:
    def __init__(self, queue):
        self.queue = queue
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = whisper.load_model(WHISPER_MODEL, device=self.device)
        
        # Аудиопоток
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=CHANNELS,
            rate=INPUT_RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=self._callback
        )
        
        # БУФЕРЫ
        self.raw_buffer = deque(maxlen=30)  # Хранит последние 30 секунд аудио
        self.active_buffer = []
        self.last_voice_time = time.time()
        self.is_recording = False
        
        # ФЛАГИ
        self.running = Event()
        self.running.set()

    def _callback(self, in_data, frame_count, time_info, status):
        # Конвертация и предобработка аудио
        audio = np.frombuffer(in_data, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Стерео в моно + ресемплинг
        if CHANNELS == 2:
            audio = audio.reshape(-1, 2).mean(axis=1)
        audio = resampy.resample(audio, INPUT_RATE, TARGET_RATE)
        
        # Анализ энергии сигнала
        energy = np.sqrt(np.mean(audio**2))
        if energy > ENERGY_THRESHOLD:
            self.last_voice_time = time.time()
            if not self.is_recording:
                self._start_recording()
        
        # Сохранение в буферы
        self.raw_buffer.extend(audio)
        if self.is_recording:
            self.active_buffer.extend(audio)
        
        return (in_data, pyaudio.paContinue)

    def _start_recording(self):
        print("\nНачало записи фразы")
        self.is_recording = True
        # Добавляем 0.5 сек перед активацией из raw_buffer
        pre_buffer = list(self.raw_buffer)[-int(TARGET_RATE*0.5):]
        self.active_buffer = pre_buffer.copy()

    def _process_phrase(self):
        print(f"\nОтправка фразы ({len(self.active_buffer)/TARGET_RATE:.1f} сек)")
        audio = np.array(self.active_buffer)
        
        result = self.model.transcribe(
            audio,
            language='ru',
            fp16=(self.device == "cuda"),
            temperature=0.0
        )
        
        text = result["text"].strip()
        if text:
            print(f"РАСПОЗНАНО: {text}")
            self.queue.put(text)
        
        self.active_buffer.clear()
        self.is_recording = False

    def monitor_silence(self):
        while self.running.is_set():
            silence_duration = time.time() - self.last_voice_time
            
            if self.is_recording:
                if silence_duration >= SILENCE_TIMEOUT:
                    self._process_phrase()
                else:
                    # Рассчитываем оставшееся время до отправки
                    remaining = SILENCE_TIMEOUT - silence_duration
                    print(f" Молчание: {remaining:.1f} сек ", end='\r')
            
            time.sleep(0.1)

    def start(self):
        Thread(target=self.monitor_silence, daemon=True).start()

    def stop(self):
        self.running.clear()
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()

def audio_capture_process(queue, stt_config):
    processor = None
    try:
        processor = VoiceProcessor(queue)
        processor.start()
        
        while processor.running.is_set():
            time.sleep(1)
            
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        if processor:
            processor.stop()


'''import json
import numpy as np
import pyaudio
import random
import time
from vosk import KaldiRecognizer, Model
from pyAudioAnalysis import ShortTermFeatures as stf

AUDIO_BUFFER_SIZE = 3 * 16000  # Используйте sample rate модели (обычно 16000 Гц)
FRAME_SIZE = 2048
PHRASE_TIMEOUT = 7

def analyze_audio(buffer: np.ndarray, sample_rate: int) -> bool:
    try:
        features, _ = stf.feature_extraction(
            buffer.astype(np.float32),
            sample_rate,
            int(0.050 * sample_rate),
            int(0.025 * sample_rate)
        )
        spectral_contrast = np.mean(features[3, :])
        energy = np.mean(features[0, :])
        zcr = np.mean(features[1, :])
        return spectral_contrast > 10 and energy > 0.01 and zcr > 0.05
    except Exception as e:
        print(f"[ANALYZER] Ошибка анализа аудио: {e}")
        return False

def audio_capture_process(queue, stt_config):
    try:
        print("[AUDIO] Захват аудио запущен")
        # Важно: убедитесь, что модель оптимизирована для русского языка, например:
        # stt_config['model_path'] = "vosk-model-ru-0.22"
        model = Model(stt_config['model_path'])
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=stt_config['sample_rate'],
            input=True,
            frames_per_buffer=FRAME_SIZE
        )
        # Если ожидается ограниченный набор фраз, можно задать грамматику:
        # grammar = '["привет", "как дела", "до свидания"]'
        # recognizer = KaldiRecognizer(model, stt_config['sample_rate'], grammar)
        recognizer = KaldiRecognizer(model, stt_config['sample_rate'])
        recognizer.SetWords(True)  # Вывод подробной информации по словам
        audio_buffer = np.array([], dtype=np.int16)
        phrase_buffer = []
        last_speech_time = time.time()

        while True:
            data = stream.read(FRAME_SIZE, exception_on_overflow=False)
            np_data = np.frombuffer(data, dtype=np.int16)
            audio_buffer = np.concatenate((audio_buffer, np_data))

            # Полное распознавание
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    print(f"[STT] Распознано: {text}")
                    phrase_buffer.append(text)
                    last_speech_time = time.time()
            else:
                # Обработка промежуточного результата для более оперативного реагирования
                partial_result = json.loads(recognizer.PartialResult())
                partial = partial_result.get("partial", "").strip()
                if partial:
                    print(f"[STT] Частичный результат: {partial}")

            if time.time() - last_speech_time > PHRASE_TIMEOUT and phrase_buffer:
                full_text = " ".join(phrase_buffer)
                print(f"[STT] Фраза завершена: {full_text}")
                queue.put(full_text)
                phrase_buffer = []

            if len(audio_buffer) >= AUDIO_BUFFER_SIZE:
                if analyze_audio(audio_buffer[-AUDIO_BUFFER_SIZE:], stt_config['sample_rate']):
                    print("[ANALYZER] Обнаружен смех!")
                    time.sleep(random.uniform(0.2, 1.5))
                    queue.put(('laughter', None))
                # Сохраняем последние данные, чтобы не потерять актуальный аудиопоток
                audio_buffer = audio_buffer[-AUDIO_BUFFER_SIZE // 2:]
    
    except Exception as e:
        print(f"[AUDIO] Критическая ошибка: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
        print("[AUDIO] Захват аудио завершен")'''

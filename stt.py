import json
import numpy as np
import pyaudio
from vosk import KaldiRecognizer, Model
from pyAudioAnalysis import ShortTermFeatures as stf

AUDIO_BUFFER_SIZE = 3 * 16000

def analyze_audio(buffer: np.ndarray, sample_rate: int) -> bool:
    try:
        features, _ = stf.feature_extraction(buffer, sample_rate, int(0.050 * sample_rate), int(0.025 * sample_rate))
        spectral_contrast = np.mean(features[3, :])
        energy = np.mean(features[0, :])
        zcr = np.mean(features[1, :])

        is_laughter = (
            spectral_contrast > 10 and 
            energy > 0.01 and 
            zcr > 0.05
        )
        return is_laughter
    except Exception as e:
        print(f"[ANALYZER] Ошибка: {e}")
        return False

def audio_capture_process(queue, stt_config):
    try:
        print("[AUDIO] Захват аудио запущен")
        model = Model(stt_config['model_path'])
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=stt_config['sample_rate'],
            input=True,
            frames_per_buffer=2048
        )
        recognizer = KaldiRecognizer(model, stt_config['sample_rate'])
        audio_buffer = np.array([], dtype=np.int16)

        while True:
            data = stream.read(2048, exception_on_overflow=False)
            
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                if text := result.get("text", "").strip():
                    print(f"[STT] Распознано: {text}")
                    queue.put(text)

            np_data = np.frombuffer(data, dtype=np.int16)
            audio_buffer = np.concatenate((audio_buffer, np_data))

            if len(audio_buffer) >= AUDIO_BUFFER_SIZE:
                if analyze_audio(audio_buffer[-AUDIO_BUFFER_SIZE:], stt_config['sample_rate']):
                    print("[ANALYZER] Обнаружен смех!")
                    queue.put(('laughter', None))
                audio_buffer = audio_buffer[-AUDIO_BUFFER_SIZE // 2:]

    except Exception as e:
        print(f"[AUDIO] Критическая ошибка: {e}")
    finally:
        stream.stop_stream()
        stream.close()
        audio.terminate()
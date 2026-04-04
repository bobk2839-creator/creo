"""
Сервис для генерации аудио с использованием OmniVoice
"""
import tempfile
import os
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

try:
    import torch
    import torchaudio
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None
    torchaudio = None

try:
    from omnivoice import OmniVoice
    OMNIVOICE_AVAILABLE = True
except ImportError:
    OMNIVOICE_AVAILABLE = False
    OmniVoice = None


class OmniVoiceService:
    """Сервис для работы с моделью OmniVoice"""
    
    def __init__(self, model_name: str = "k2-fsa/OmniVoice", device: str = "cuda"):
        self.model_name = model_name
        
        # Проверка доступности библиотек
        if not TORCH_AVAILABLE:
            raise ImportError("torch и torchaudio не установлены. Установите их: pip install torch torchaudio")
        
        if not OMNIVOICE_AVAILABLE:
            raise ImportError("omnivoice не установлен. Установите его: pip install omnivoice")
        
        # Выбор устройства
        if device == "cuda" and not torch.cuda.is_available():
            device = "mps" if torch.backends.mps.is_available() else "cpu"
        
        self.device = device
        self.dtype = torch.float16 if device != "cpu" else torch.float32
        
        self.model = None
        self._model_loaded = False
    
    def load_model(self):
        """Загрузить модель (ленивая загрузка)"""
        if not self._model_loaded:
            print(f"🔄 Загрузка модели {self.model_name} на устройство {self.device}...")
            
            self.model = OmniVoice.from_pretrained(
                self.model_name,
                device_map=self.device,
                dtype=self.dtype
            )
            
            self._model_loaded = True
            print("✅ Модель загружена!")
    
    async def generate_audio(
        self,
        text: str,
        mode: str = "auto",
        ref_audio_path: Optional[str] = None,
        ref_text: Optional[str] = None,
        voice_instruct: Optional[str] = None,
        num_step: int = 32,
        speed: float = 1.0,
        duration: Optional[float] = None
    ) -> Tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Сгенерировать аудио по тексту
        
        Args:
            text: Текст для синтеза
            mode: Режим генерации (auto, clone, design)
            ref_audio_path: Путь к аудио-референсу (для клонирования)
            ref_text: Текст референса (для клонирования)
            voice_instruct: Инструкция для дизайна голоса
            num_step: Количество шагов диффузии
            speed: Фактор скорости
            duration: Фиксированная длительность в секундах
        
        Returns:
            Tuple[путь_к_файлу, длительность_в_секундах, ошибка]
        """
        try:
            # Ленивая загрузка модели
            self.load_model()
            
            # Подготовка параметров
            kwargs = {
                "text": text,
                "num_step": num_step,
                "speed": speed
            }
            
            if duration:
                kwargs["duration"] = duration
            
            # Режим генерации
            if mode == "clone":
                if not ref_audio_path:
                    return None, None, "❌ Для клонирования голоса необходим аудио-референс"
                
                kwargs["ref_audio"] = ref_audio_path
                if ref_text:
                    kwargs["ref_text"] = ref_text
                # Если ref_text не указан, модель использует Whisper для автотранскрибации
                
            elif mode == "design":
                if not voice_instruct:
                    return None, None, "❌ Для дизайна голоса необходима инструкция"
                
                kwargs["instruct"] = voice_instruct
            
            # Генерация аудио
            print(f"🎤 Генерация аудио: {len(text)} символов, режим={mode}")
            start_time = datetime.utcnow()
            
            audio_tensors = self.model.generate(**kwargs)
            
            if not audio_tensors or len(audio_tensors) == 0:
                return None, None, "❌ Ошибка генерации: пустой результат"
            
            audio_tensor = audio_tensors[0]  # Берем первый результат
            
            # Расчет длительности
            output_duration = audio_tensor.shape[-1] / 24000  # 24 kHz sample rate
            
            # Сохранение в временный файл
            temp_file = tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
                dir=tempfile.gettempdir()
            )
            temp_path = temp_file.name
            temp_file.close()
            
            # Сохранение аудио
            torchaudio.save(temp_path, audio_tensor, 24000)
            
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            print(f"✅ Аудио сгенерировано: {output_duration:.2f} сек, время обработки: {processing_time:.2f} сек")
            
            return temp_path, output_duration, None
            
        except Exception as e:
            error_msg = f"❌ Ошибка генерации: {str(e)}"
            print(error_msg)
            return None, None, error_msg
    
    async def estimate_duration(self, text: str) -> float:
        """
        Оценить длительность аудио по тексту (приблизительно)
        
        Примерная оценка: 150 слов в минуту для английского,
        180 иероглифов/слов в минуту для китайского
        """
        # Подсчет примерного количества слов
        words = len(text.split())
        chars = len(text)
        
        # Эвристика: для смешанного текста
        # Средняя скорость речи ~150 слов/минуту = 2.5 слова/секунду
        estimated_seconds = max(words / 2.5, chars / 15)
        
        return estimated_seconds
    
    def cleanup_temp_file(self, file_path: str):
        """Удалить временный файл"""
        try:
            if file_path and os.path.exists(file_path):
                os.unlink(file_path)
                print(f"🗑️ Временный файл удален: {file_path}")
        except Exception as e:
            print(f"⚠️ Ошибка удаления файла: {e}")


# Глобальный экземпляр сервиса (будет инициализирован при старте)
tts_service: Optional[OmniVoiceService] = None


def get_tts_service(model_name: str = "k2-fsa/OmniVoice", device: str = "cuda") -> OmniVoiceService:
    """Получить или создать экземпляр сервиса TTS"""
    global tts_service
    if tts_service is None:
        tts_service = OmniVoiceService(model_name=model_name, device=device)
    return tts_service

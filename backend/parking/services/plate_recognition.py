import cv2
import numpy as np
import os
from datetime import datetime
from django.conf import settings

class PlateRecognizer:
    """
    Сервис распознавания автомобильных номеров через OpenCV
    """
    
    def __init__(self):
        # Загрузка каскадов для детекции
        self.plate_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_russian_plate_number.xml'
        )
        
        # Параметры
        self.min_area = 500
        self.confidence_threshold = 0.5
        
    def detect_plate_in_frame(self, frame):
        """
        Detect license plate in a single frame
        Returns: (plate_image, bounding_box) or (None, None)
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Детекция номеров
        plates = self.plate_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        
        if len(plates) > 0:
            # Берём первый найденный номер (самый крупный)
            x, y, w, h = plates[0]
            plate_img = frame[y:y+h, x:x+w]
            return plate_img, (x, y, w, h)
        
        return None, None
    
    def recognize_plate(self, plate_image):
        """
        Распознать текст номера (заглушка - будет Tesseract OCR)
        Returns: (plate_text, confidence)
        """
        # TODO: Интеграция с Tesseract OCR или ALPR
        # Сейчас возвращаем заглушку
        
        if plate_image is None:
            return None, 0.0
        
        # Имитация распознавания (для тестов)
        # В продакшене здесь будет реальный OCR
        height, width = plate_image.shape[:2]
        
        # Простая эвристика для демонстрации
        if width > 50 and height > 20:
            return "X000XX 00", 0.75  # Заглушка
        
        return None, 0.0
    
    def process_video(self, video_path, output_dir=None):
        """
        Обработать видеофайл и распознать номера
        Returns: list of detected plates with timestamps
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        detected_plates = []
        frame_interval = int(fps)  # Проверяем каждый 1 секунду
        
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % frame_interval == 0:
                plate_img, bbox = self.detect_plate_in_frame(frame)
                
                if plate_img is not None:
                    plate_text, confidence = self.recognize_plate(plate_img)
                    
                    if plate_text and confidence > self.confidence_threshold:
                        timestamp = frame_count / fps
                        detected_plates.append({
                            'plate': plate_text,
                            'confidence': confidence,
                            'timestamp': timestamp,
                            'bbox': bbox
                        })
            
            frame_count += 1
        
        cap.release()
        
        return {
            'duration': duration,
            'plates': detected_plates,
            'total_frames': total_frames
        }
    
    def process_rtsp_stream(self, rtsp_url, duration_seconds=30, output_path=None):
        """
        Записать RTSP поток и обработать
        Returns: path to saved video + detected plates
        """
        cap = cv2.VideoCapture(rtsp_url)
        
        if not cap.isOpened():
            raise Exception(f"Cannot open RTSP stream: {rtsp_url}")
        
        # Параметры записи
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Создаём файл для записи
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(settings.MEDIA_ROOT, 'recordings', f'{timestamp}.mp4')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        detected_plates = []
        frame_count = 0
        max_frames = int(fps * duration_seconds)
        frame_interval = int(fps)  # Проверка раз в секунду
        
        while frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            out.write(frame)
            
            # Проверка на номер
            if frame_count % frame_interval == 0:
                plate_img, bbox = self.detect_plate_in_frame(frame)
                
                if plate_img is not None:
                    plate_text, confidence = self.recognize_plate(plate_img)
                    
                    if plate_text and confidence > self.confidence_threshold:
                        detected_plates.append({
                            'plate': plate_text,
                            'confidence': confidence,
                            'timestamp': frame_count / fps
                        })
            
            frame_count += 1
        
        cap.release()
        out.release()
        
        return {
            'video_path': output_path,
            'duration': frame_count / fps,
            'plates': detected_plates
        }
    
    def match_plate(self, detected_plate, expected_plate):
        """
        Сверить распознанный номер с ожидаемым
        Returns: (is_match, similarity_score)
        """
        if not detected_plate or not expected_plate:
            return False, 0.0
        
        # Нормализация (убираем пробелы, дефисы, приводим к верхнему регистру)
        d = detected_plate.replace(' ', '').replace('-', '').upper()
        e = expected_plate.replace(' ', '').replace('-', '').upper()
        
        # Точное совпадение
        if d == e:
            return True, 1.0
        
        # Частичное совпадение (если 6+ символов совпадают)
        common = sum(1 for a, b in zip(d, e) if a == b)
        similarity = common / max(len(d), len(e))
        
        return similarity >= 0.8, similarity


# Глобальный экземпляр
plate_recognizer = PlateRecognizer()
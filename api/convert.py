from http.server import BaseHTTPRequestHandler
import re
from io import BytesIO
from openpyxl import Workbook

class SubtitleConverter:
    @staticmethod
    def parse_ass(content):
        """Парсит ASS файл"""
        lines = content.splitlines()
        result = []
        in_events = False
        
        for line in lines:
            line = line.strip()
            if line == "[Events]":
                in_events = True
                continue
            if in_events and line.startswith("Dialogue:"):
                parts = line.split(",", 9)
                time = parts[1].strip()
                text = re.sub(r'\{.*?\}', '', parts[9]).replace("\\N", " ")
                result.append([time, text])
        return result

    @staticmethod
    def parse_srt(content):
        """Парсит SRT файл"""
        blocks = re.split(r'\n\s*\n', content)
        result = []
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                timecode = lines[1].strip()
                text = ' '.join(lines[2:]).replace('\n', ' ')
                result.append([timecode, text])
        return result

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            file_data = self.rfile.read(content_length)
            
            # Извлекаем файл из запроса
            boundary = self.headers['Content-Type'].split('=')[1].encode()
            file_part = [p for p in file_data.split(boundary) if b'filename="' in p][0]
            content = file_part.split(b'\r\n\r\n')[1].rstrip(b'\r\n--').decode('utf-8')
            
            # Определяем тип файла
            if 'Dialogue:' in content:  # ASS файл
                data = SubtitleConverter.parse_ass(content)
            else:  # SRT файл
                data = SubtitleConverter.parse_srt(content)
            
            # Создаем Excel
            wb = Workbook()
            ws = wb.active
            ws.append(["Время", "Текст"])
            
            for row in data:
                ws.append(row)
            
            # Отправляем файл
            output = BytesIO()
            wb.save(output)
            output.seek(0)
            
            self.send_response(200)
            self.send_header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            self.send_header('Content-Disposition', 'attachment; filename="subtitles.xlsx"')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(output.getvalue())
            
        except Exception as e:
            self.send_error(500, f"Ошибка: {str(e)}")

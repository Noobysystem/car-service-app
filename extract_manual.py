import fitz  # PyMuPDF
import os
import glob

output_dir = os.path.join("app", "static", "manual_img")
os.makedirs(output_dir, exist_ok=True)

# Поиск файла мануала
pdf_candidates = glob.glob("*manual*.pdf") + glob.glob("../*manual*.pdf")
if not pdf_candidates:
    print("Внимание: PDF мануала не найден в папке проекта или на Рабочем столе. Создаем структуру.")
    exit(0)

pdf_path = pdf_candidates[0]
print(f"Обработка мануала: {pdf_path}")
doc = fitz.open(pdf_path)

# Страницы ключевых визуальных разделов руководства N-WGN (1-indexed в PDF)
target_pages = {
    "cockpit_overview": 1,       # Общий вид передней панели
    "steering_switches": 2,      # Кнопки руля и подрулевые лепестки
    "controls_lower": 3,         # Нижняя панель (CTBA, VSA, корректор)
    "interior_layout": 4,        # Салон и сиденья
    "exterior_overview": 5,      # Внешний вид и точки обслуживания
    "dashboard_custom": 7,       # Щиток приборов Custom
    "dashboard_standard": 8,     # Щиток приборов Standard
    "climate_controls": 11,      # Блок климат-контроля
    "cvt_selector": 14,          # Селектор вариатора
    "fuel_cap": 15,              # Лючок и пробка бака
    "engine_bay_visual": 16,     # Подкапотное пространство
    "emergency_situations": 17,  # Аварийные процедуры
}

for name, page_num in target_pages.items():
    if page_num <= len(doc):
        page = doc[page_num - 1]
        pix = page.get_pixmap(dpi=150)
        img_path = os.path.join(output_dir, f"{name}.png")
        pix.save(img_path)
        print(f"Сохранена схема: {img_path}")

doc.close()
print("Все иллюстрации успешно извлечены!")

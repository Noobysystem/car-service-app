import fitz
import os
import glob

output_dir = os.path.join("app", "static", "manual_img")
os.makedirs(output_dir, exist_ok=True)

pdf_candidates = glob.glob("*manual*.pdf") + glob.glob("../*manual*.pdf")
if not pdf_candidates:
    print("PDF не найден!")
    exit(1)

doc = fitz.open(pdf_candidates[0])

# Точное соответствие страниц PDF (1-based index) разделам Honda N-WGN:
exact_pages = {
    "sec1_cockpit": 2,       # Быстрый гид: общий вид кокпита
    "sec1_steering": 3,      # Рулевое колесо и подрулевые лепестки
    "sec1_lower_panel": 4,   # Нижний блок (CTBA, VSA, корректор)
    "sec2_safety_belts": 6,  # Безопасность: ремни и посадка
    "sec3_dashboard_custom": 7, # Приборная панель Custom (тахометр, индикаторы)
    "sec3_indicators": 8,    # Все контрольные лампы и индикация
    "sec4_climate": 11,      # Климат-контроль и дефростер
    "sec4_lights_wiper": 9,  # Управление светом и дворниками
    "sec5_audio": 12,        # Аудиосистема и дисплей
    "sec6_cvt": 14,          # Вариатор, режимы D/S/L
    "sec6_fuel": 15,         # Заправка, лючок бензобака
    "sec7_engine_bay": 16,   # Подкапотное пространство и жидкости
    "sec8_emergency": 17,    # Аварийные ситуации, пуск без батарейки
    "sec8_towing": 18,       # Буксировка 4WD и колеса
}

for name, page_num in exact_pages.items():
    if page_num <= len(doc):
        page = doc[page_num - 1]
        # Масштаб для четкого отображения схем
        pix = page.get_pixmap(dpi=150)
        pix.save(os.path.join(output_dir, f"{name}.png"))
        print(f"Экспортирована страница {page_num} -> {name}.png")

doc.close()
print("Все схемы успешно обновлены под разделы!")

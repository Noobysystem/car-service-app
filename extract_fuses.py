import fitz
import os
import glob

output_dir = os.path.join("app", "static", "manual_img")
os.makedirs(output_dir, exist_ok=True)

pdf_files = glob.glob("*manual*.pdf") + glob.glob("../*manual*.pdf")
if not pdf_files:
    print("PDF-файл руководства не найден!")
    exit(1)

doc = fitz.open(pdf_files[0])
print(f"Поиск разделов предохранителей в {pdf_files[0]}...")

fuse_pages = []
for i in range(len(doc)):
    text = doc[i].get_text()
    if "ヒューズボックス" in text or "ヒューズが切れた" in text:
        fuse_pages.append(i + 1)

print(f"Найдены страницы предохранителей: {fuse_pages}")

# Сохраняем схемы подкапотного и салонного блоков (обычно страницы 333-337 руководства)
scale = 2.0
mat = fitz.Matrix(scale, scale)

engine_saved = False
cabin_saved = False

for p_num in fuse_pages:
    page = doc[p_num - 1]
    text = page.get_text()
    pix = page.get_pixmap(matrix=mat)
    
    if "エンジンルーム" in text and not engine_saved:
        pix.save(os.path.join(output_dir, "fuses_engine_diagram.png"))
        print(f"Схема подкапотного блока сохранена (стр. {p_num})")
        engine_saved = True
    elif ("室内" in text or "運転席" in text) and not cabin_saved:
        pix.save(os.path.join(output_dir, "fuses_cabin_diagram.png"))
        print(f"Схема салонного блока сохранена (стр. {p_num})")
        cabin_saved = True

# Резервное сохранение, если ключевые слова в оглавлении отличались
if not engine_saved and len(fuse_pages) >= 1:
    doc[fuse_pages[0]-1].get_pixmap(matrix=mat).save(os.path.join(output_dir, "fuses_engine_diagram.png"))
if not cabin_saved and len(fuse_pages) >= 2:
    doc[fuse_pages[1]-1].get_pixmap(matrix=mat).save(os.path.join(output_dir, "fuses_cabin_diagram.png"))

doc.close()
print("Схемы предохранителей успешно извлечены!")

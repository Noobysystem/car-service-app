from datetime import date
from fastapi import FastAPI, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import models
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

templates.env.filters["currency"] = lambda val: f"{val:,.0f}".replace(",", " ") + " ₽"

def migrate_and_seed_data(db: Session):
    # Удаляем лишние авто (если остались)
    cars_to_remove = db.query(models.Vehicle).filter(
        (models.Vehicle.name.contains("Калина")) | (models.Vehicle.name.contains("Prado"))
    ).all()
    for c in cars_to_remove:
        db.delete(c)
    db.commit()

    nwgn = db.query(models.Vehicle).filter(models.Vehicle.name.contains("N-WGN")).first()
    if not nwgn:
        nwgn = models.Vehicle(name="Honda N-WGN Custom", engine="0.66 Атмо 4WD (S07A)", current_mileage=125000)
        db.add(nwgn)
        db.commit()
    else:
        nwgn.engine = "0.66 Атмо 4WD (S07A)"
        db.commit()

    # Корректировка пробегов прошлых ТО
    cvt_rule = db.query(models.MaintenanceRule).filter(
        models.MaintenanceRule.vehicle_id == nwgn.id,
        models.MaintenanceRule.title.contains("вариатора")
    ).first()
    if cvt_rule and cvt_rule.last_mileage != 100000:
        cvt_rule.last_mileage = 100000

    diff_rule = db.query(models.MaintenanceRule).filter(
        models.MaintenanceRule.vehicle_id == nwgn.id,
        models.MaintenanceRule.title.contains("редуктор")
    ).first()
    if diff_rule and diff_rule.last_mileage != 90000:
        diff_rule.last_mileage = 90000
    db.commit()

    # ПОЛНАЯ БАЗА РАСХОДНИКОВ HONDA N-WGN JH2 (S07A NA 4WD)
    # Перезаписываем список, чтобы гарантировать полноту данных
    if db.query(models.PartReference).filter(models.PartReference.vehicle_id == nwgn.id).count() < 15:
        db.query(models.PartReference).filter(models.PartReference.vehicle_id == nwgn.id).delete()
        
        full_parts_catalog = [
            # Двигатель и фильтры
            models.PartReference(
                vehicle_id=nwgn.id, category="Моторное масло (4л)", part_number="08227-99974", 
                brand="Honda Ultra LEO SP 0W-20", 
                description="Синтетика API SP/GF-6. Заливка: 2.4 л (без фильтра), 2.6 л (с фильтром)"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Масляный фильтр (OEM)", part_number="15400-RTA-003", 
                brand="Honda OEM", 
                description="Оригинал. Взаимозаменяем с 15400-PFB-004 и H1540-RTA-505 (HAMP)"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Масляный фильтр (Аналог)", part_number="C-809", 
                brand="VIC (Япония)", 
                description="Высокое качество очистки. Также подходят Nitto 4HM-113, MANN W 67/1"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Шайба сливной пробки ДВС", part_number="94109-14000", 
                brand="Honda OEM", 
                description="Алюминиевая прокладка под болт 14 мм (одноразовая при каждой замене)"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Воздушный фильтр ДВС (Атмо)", part_number="17220-5Z1-003", 
                brand="Honda OEM", 
                description="Именно для атмосферного S07A. Проверенный аналог: VIC A-8001V"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Салонный фильтр", part_number="80291-TY0-941", 
                brand="Honda OEM", 
                description="Аналоги: VIC AC-808E (угольный), Sakura CA-16130, Nitto 25-010D"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Свечи зажигания (комплект 3 шт.)", part_number="12290-5R0-003", 
                brand="NGK DILZKAR7C11S", 
                description="Иридий, калильное 7 под NA мотор. Премиум: NGK LKAR7BRX11PS (97544)"
            ),

            # Вариатор (CVT)
            models.PartReference(
                vehicle_id=nwgn.id, category="Жидкость вариатора (4л)", part_number="08260-99964", 
                brand="Honda Ultra HCF-2", 
                description="Только спецжидкость 2-го поколения HCF-2! Частичная замена: ~2.4–2.6 л"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Шайба сливной пробки CVT", part_number="90471-PX4-000", 
                brand="Honda OEM", 
                description="Алюминиевая уплотнительная шайба 18 мм"
            ),

            # Полный привод (4WD)
            models.PartReference(
                vehicle_id=nwgn.id, category="Масло заднего редуктора (4л)", part_number="08262-99964", 
                brand="Honda Ultra DPSF-II", 
                description="Спецжидкость Dual Pump II для заднего дифференциала 4WD. Заливка: ~1.0–1.2 л"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Шайбы пробок редуктора", part_number="94109-20000 / 90471-PX4-000", 
                brand="Honda OEM", 
                description="Шайба 20 мм (заливная/уровневая) и 18 мм (сливная)"
            ),

            # Тормозная система
            models.PartReference(
                vehicle_id=nwgn.id, category="Передние тормозные колодки", part_number="45022-T6G-000", 
                brand="Honda OEM", 
                description="Комплект на переднюю ось. Японские аналоги: Akebono AN-769WK, Nisshinbo NP8048"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Задние тормозные колодки", part_number="43153-TY0-003", 
                brand="Honda OEM", 
                description="Барабанные колодки задней оси. Японский аналог: Akebono NN4526"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Тормозная жидкость (1л)", part_number="08203-99931", 
                brand="Honda Ultra BF DOT 4", 
                description="Спецификация DOT 4. Объем полной прокачки системы: ~0.8-1.0 л"
            ),

            # Охлаждение и ремни навесного
            models.PartReference(
                vehicle_id=nwgn.id, category="Антифриз (4л)", part_number="08234-99901", 
                brand="Honda Long Life Coolant Type 2", 
                description="Синий готовый антифриз (-37°C). Объем системы охлаждения: ~3.2-3.5 л"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Ремень генератора и помпы", part_number="31110-R9G-004", 
                brand="Honda OEM (Bando)", 
                description="Поликлиновой ремень привода генератора и водяного насоса"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Ремень кондиционера", part_number="19230-5Z1-004", 
                brand="Honda OEM (Mitsuboshi)", 
                description="Ремень привода компрессора кондиционера для атмосферного S07A"
            ),

            # Электрика и дворники
            models.PartReference(
                vehicle_id=nwgn.id, category="Аккумулятор EFB (Start-Stop)", part_number="M-42R", 
                brand="GS Yuasa / Furukawa ECHNO", 
                description="Типоразмер 55B20R / M-42R. Усиленный под частые пуски системы Idling Stop"
            ),
            models.PartReference(
                vehicle_id=nwgn.id, category="Щетки стеклоочистителя", part_number="DU-053L + DU-035L", 
                brand="Denso Hybrid", 
                description="Комплект на лобовое стекло: водительская 525 мм (21\") и пассажирская 350 мм (14\")"
            ),
        ]
        db.add_all(full_parts_catalog)
        db.commit()

def calculate_status(current_km: int, last_km: int, interval_km: int):
    passed = current_km - last_km
    remaining = interval_km - passed
    if remaining <= 0:
        return {"status": "overdue", "color": "text-red-600 bg-red-100", "remaining": remaining}
    elif remaining <= 1000:
        return {"status": "soon", "color": "text-amber-600 bg-amber-100", "remaining": remaining}
    return {"status": "ok", "color": "text-emerald-600 bg-emerald-100", "remaining": remaining}

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    migrate_and_seed_data(db)
    vehicles = db.query(models.Vehicle).all()
    today_date = date.today()
    today_str = today_date.isoformat()
    current_year = today_date.year

    total_spent_all = 0.0
    year_spent_all = 0.0
    overdue_rules_count = 0
    soon_rules_count = 0

    car_cards = []
    for v in vehicles:
        rules_status = []
        for r in v.rules:
            stat = calculate_status(v.current_mileage, r.last_mileage, r.interval_km)
            if stat["status"] == "overdue":
                overdue_rules_count += 1
            elif stat["status"] == "soon":
                soon_rules_count += 1
            rules_status.append({"rule": r, "calc": stat})
        
        services = sorted(v.services, key=lambda s: (s.date, s.mileage), reverse=True)
        car_total_cost = sum(s.cost for s in services if s.cost)
        car_year_cost = sum(s.cost for s in services if s.cost and s.date and s.date.year == current_year)

        total_spent_all += car_total_cost
        year_spent_all += car_year_cost

        car_cards.append({
            "vehicle": v,
            "rules": rules_status,
            "services": services,
            "parts": v.parts,
            "total_cost": car_total_cost,
            "year_cost": car_year_cost
        })

    stats = {
        "total_spent": total_spent_all,
        "year_spent": year_spent_all,
        "current_year": current_year,
        "overdue_count": overdue_rules_count,
        "soon_count": soon_rules_count
    }

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"cars": car_cards, "today": today_str, "stats": stats}
    )

# --- Добавление и удаление авто ---
@app.post("/vehicles/add")
def add_vehicle(
    name: str = Form(...),
    engine: str = Form(""),
    plate_number: str = Form(""),
    current_mileage: int = Form(0),
    db: Session = Depends(get_db)
):
    car = models.Vehicle(
        name=name.strip(),
        engine=engine.strip(),
        plate_number=plate_number.strip(),
        current_mileage=current_mileage
    )
    db.add(car)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/vehicles/{vehicle_id}/delete")
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if vehicle:
        db.delete(vehicle)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# --- Управление регламентами ---
@app.post("/vehicles/{vehicle_id}/add-rule")
def add_rule(
    vehicle_id: int,
    title: str = Form(...),
    interval_km: int = Form(...),
    last_mileage: int = Form(...),
    db: Session = Depends(get_db)
):
    rule = models.MaintenanceRule(
        vehicle_id=vehicle_id,
        title=title.strip(),
        interval_km=interval_km,
        last_mileage=last_mileage
    )
    db.add(rule)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/rules/{rule_id}/edit")
def edit_rule(
    rule_id: int,
    title: str = Form(...),
    interval_km: int = Form(...),
    last_mileage: int = Form(...),
    db: Session = Depends(get_db)
):
    rule = db.query(models.MaintenanceRule).filter(models.MaintenanceRule.id == rule_id).first()
    if rule:
        rule.title = title.strip()
        rule.interval_km = interval_km
        rule.last_mileage = last_mileage
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/rules/{rule_id}/delete")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.MaintenanceRule).filter(models.MaintenanceRule.id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# --- Одометр, ТО, Расходники ---
@app.post("/vehicles/{vehicle_id}/update-mileage")
def update_mileage(vehicle_id: int, mileage: int = Form(...), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.id == vehicle_id).first()
    if vehicle:
        vehicle.current_mileage = mileage
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/vehicles/{vehicle_id}/add-service")
def add_service(
    vehicle_id: int,
    title: str = Form(...),
    mileage: int = Form(...),
    service_date: str = Form(None),
    cost: float = Form(0.0),
    notes: str = Form(""),
    rule_id: str = Form(""),
    db: Session = Depends(get_db)
):
    try:
        parsed_date = date.fromisoformat(service_date) if service_date else date.today()
    except ValueError:
        parsed_date = date.today()

    log = models.ServiceLog(
        vehicle_id=vehicle_id,
        date=parsed_date,
        mileage=mileage,
        title=title,
        notes=notes,
        cost=cost
    )
    db.add(log)
    
    vehicle = db.query(models.Vehicle).get(vehicle_id)
    if vehicle and mileage > vehicle.current_mileage:
        vehicle.current_mileage = mileage

    if rule_id and rule_id.strip().isdigit():
        rule = db.query(models.MaintenanceRule).get(int(rule_id))
        if rule:
            rule.last_mileage = mileage

    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/services/{service_id}/delete")
def delete_service(service_id: int, db: Session = Depends(get_db)):
    log = db.query(models.ServiceLog).filter(models.ServiceLog.id == service_id).first()
    if log:
        db.delete(log)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/vehicles/{vehicle_id}/add-part")
def add_part(
    vehicle_id: int,
    category: str = Form(...),
    part_number: str = Form(...),
    brand: str = Form(""),
    description: str = Form(""),
    db: Session = Depends(get_db)
):
    part = models.PartReference(
        vehicle_id=vehicle_id,
        category=category,
        part_number=part_number.strip(),
        brand=brand.strip(),
        description=description.strip()
    )
    db.add(part)
    db.commit()
    return RedirectResponse(url="/", status_code=303)

@app.post("/parts/{part_id}/delete")
def delete_part(part_id: int, db: Session = Depends(get_db)):
    part = db.query(models.PartReference).filter(models.PartReference.id == part_id).first()
    if part:
        db.delete(part)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

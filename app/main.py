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
    # 1. Удаляем Калину и Прадо по запросу
    cars_to_remove = db.query(models.Vehicle).filter(
        (models.Vehicle.name.contains("Калина")) | (models.Vehicle.name.contains("Prado"))
    ).all()
    for c in cars_to_remove:
        db.delete(c)
    db.commit()

    # 2. Убеждаемся, что Honda N-WGN настроена корректно
    nwgn = db.query(models.Vehicle).filter(models.Vehicle.name.contains("N-WGN")).first()
    if not nwgn:
        nwgn = models.Vehicle(name="Honda N-WGN Custom", engine="0.66 Атмо 4WD (S07A)", current_mileage=125000)
        db.add(nwgn)
        db.commit()
    else:
        nwgn.engine = "0.66 Атмо 4WD (S07A)"
        db.commit()

    # Проверяем базовые регламенты для Honda N-WGN
    existing_rule_titles = [r.title for r in nwgn.rules]
    new_rules = []
    if not any("масла ДВС" in t for t in existing_rule_titles):
        new_rules.append(models.MaintenanceRule(vehicle_id=nwgn.id, title="Замена масла ДВС (малый картер)", interval_km=5000, last_mileage=nwgn.current_mileage))
    if not any("вариатора" in t for t in existing_rule_titles):
        new_rules.append(models.MaintenanceRule(vehicle_id=nwgn.id, title="Замена спецжидкости вариатора (HCF-2)", interval_km=25000, last_mileage=nwgn.current_mileage))
    if not any("редуктор" in t for t in existing_rule_titles):
        new_rules.append(models.MaintenanceRule(vehicle_id=nwgn.id, title="Масло в заднем редукторе 4WD (DPSF-II)", interval_km=40000, last_mileage=nwgn.current_mileage))
    if new_rules:
        db.add_all(new_rules)
        db.commit()

    # Проверяем базовые артикулы Honda N-WGN
    if not nwgn.parts:
        db.add_all([
            models.PartReference(vehicle_id=nwgn.id, category="Масляный фильтр", part_number="15400-RTA-003", brand="Honda OEM", description="Аналоги: Mahle OC617, VIC C-809"),
            models.PartReference(vehicle_id=nwgn.id, category="Моторное масло", part_number="08218-99974", brand="Honda Ultra Leo 0W-20", description="Объем: ~2.6 л с фильтром"),
            models.PartReference(vehicle_id=nwgn.id, category="Жидкость вариатора", part_number="08260-99964", brand="Honda Ultra HCF-2", description="Объем частичной замены: ~2.4 л"),
            models.PartReference(vehicle_id=nwgn.id, category="Масло в задний редуктор 4WD", part_number="08262-99964", brand="Honda Ultra DPSF-II", description="Объем: ~1.0-1.2 л"),
            models.PartReference(vehicle_id=nwgn.id, category="Аккумулятор", part_number="M-42R", brand="Furukawa / GS Yuasa", description="EFB под систему Start-Stop"),
        ])
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

@app.post("/rules/{rule_id}/delete")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(models.MaintenanceRule).filter(models.MaintenanceRule.id == rule_id).first()
    if rule:
        db.delete(rule)
        db.commit()
    return RedirectResponse(url="/", status_code=303)

# --- Пробег, ТО, Артикулы ---
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

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

# Фильтр для красивого вывода рублей (например, 12 500 ₽)
templates.env.filters["currency"] = lambda val: f"{val:,.0f}".replace(",", " ") + " ₽"

def migrate_and_seed_data(db: Session):
    # Корректировка Prado под бензин
    prado = db.query(models.Vehicle).filter(models.Vehicle.name.contains("Prado")).first()
    if prado and "Дизель" in (prado.engine or ""):
        prado.engine = "2.7 Бензин (2TR-FE)"
        db.query(models.PartReference).filter(
            models.PartReference.vehicle_id == prado.id,
            models.PartReference.category.in_(["Моторное масло", "Топливный фильтр", "Масляный фильтр"])
        ).delete(synchronize_session=False)
        db.add_all([
            models.PartReference(vehicle_id=prado.id, category="Масляный фильтр", part_number="90915-YZZD2", brand="Toyota OEM", description="Для 2TR-FE"),
            models.PartReference(vehicle_id=prado.id, category="Моторное масло", part_number="08880-80845", brand="Toyota 5W-30 / 0W-20", description="Объем: ~5.6-5.9 л (API SP, ILSAC GF-6)"),
            models.PartReference(vehicle_id=prado.id, category="Свечи зажигания", part_number="90919-01191", brand="Denso SK20HR11", description="Иридиевые свечи, комплект 4 шт."),
            models.PartReference(vehicle_id=prado.id, category="Смазка карданов", part_number="NLGI-2 EP", brand="Castrol / Ravenol", description="Литиевая смазка для крестовин и шлицев"),
            models.PartReference(vehicle_id=prado.id, category="Масло в мосты/раздатку", part_number="75W-90 GL-5", brand="Toyota / Kixx", description="Раздатка: 1.4 л, передний: 1.4 л, задний: 2.7 л"),
        ])
        db.commit()

    # Корректировка N-WGN под Атмо 4WD
    nwgn = db.query(models.Vehicle).filter(models.Vehicle.name.contains("N-WGN")).first()
    if nwgn and ("Turbo" in (nwgn.engine or "") or "4WD" not in (nwgn.engine or "")):
        nwgn.engine = "0.66 Атмо 4WD (S07A)"
        has_diff_rule = db.query(models.MaintenanceRule).filter(
            models.MaintenanceRule.vehicle_id == nwgn.id,
            models.MaintenanceRule.title.contains("редуктор")
        ).first()
        if not has_diff_rule:
            db.add(models.MaintenanceRule(
                vehicle_id=nwgn.id,
                title="Масло в заднем редукторе 4WD (DPSF-II)",
                interval_km=40000,
                last_mileage=nwgn.current_mileage
            ))
        has_diff_part = db.query(models.PartReference).filter(
            models.PartReference.vehicle_id == nwgn.id,
            models.PartReference.category.contains("редуктор")
        ).first()
        if not has_diff_part:
            db.add_all([
                models.PartReference(vehicle_id=nwgn.id, category="Масляный фильтр", part_number="15400-RTA-003", brand="Honda OEM", description="Аналог: Mahle OC617, VIC C-809"),
                models.PartReference(vehicle_id=nwgn.id, category="Моторное масло", part_number="08218-99974", brand="Honda Ultra Leo 0W-20", description="Объем: 2.6 л с фильтром"),
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
        
        # Расчет расходов по конкретной машине
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

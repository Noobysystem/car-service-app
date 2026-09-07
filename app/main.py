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
    vehicles = db.query(models.Vehicle).all()
    today_str = date.today().isoformat()
    car_cards = []
    
    for v in vehicles:
        rules_status = []
        for r in v.rules:
            stat = calculate_status(v.current_mileage, r.last_mileage, r.interval_km)
            rules_status.append({"rule": r, "calc": stat})
        
        # Сортировка истории ТО: свежие сверху
        services = sorted(v.services, key=lambda s: (s.date, s.mileage), reverse=True)
        
        car_cards.append({
            "vehicle": v,
            "rules": rules_status,
            "services": services
        })

    return templates.TemplateResponse(
        request=request, 
        name="index.html", 
        context={"cars": car_cards, "today": today_str}
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

    # Если выбран регламент — сбрасываем счетчик последнего ТО
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

from database import SessionLocal, engine
import models

models.Base.metadata.create_all(bind=engine)
db = SessionLocal()

if not db.query(models.Vehicle).first():
    prado = models.Vehicle(name="Toyota Land Cruiser Prado", engine="2.8 Дизель (1GD-FTV)", current_mileage=95000)
    nwgn = models.Vehicle(name="Honda N-WGN Custom", engine="0.66 Turbo (S07A)", current_mileage=62000)
    kalina = models.Vehicle(name="Лада Калина", engine="1.6 8V", current_mileage=140000)
    db.add_all([prado, nwgn, kalina])
    db.commit()

    prado_rules = [
        models.MaintenanceRule(vehicle_id=prado.id, title="Замена масла ДВС + фильтры", interval_km=10000, last_mileage=90000),
        models.MaintenanceRule(vehicle_id=prado.id, title="Шприцевание карданов", interval_km=10000, last_mileage=90000),
        models.MaintenanceRule(vehicle_id=prado.id, title="Масло в мостах и раздатке", interval_km=40000, last_mileage=80000),
    ]
    nwgn_rules = [
        models.MaintenanceRule(vehicle_id=nwgn.id, title="Замена масла ДВС (малый картер)", interval_km=5000, last_mileage=60000),
        models.MaintenanceRule(vehicle_id=nwgn.id, title="Замена спецжидкости вариатора (HCF-2)", interval_km=25000, last_mileage=50000),
    ]
    kalina_rules = [
        models.MaintenanceRule(vehicle_id=kalina.id, title="Замена масла ДВС", interval_km=8000, last_mileage=135000),
        models.MaintenanceRule(vehicle_id=kalina.id, title="Комплект ремня ГРМ и помпа", interval_km=50000, last_mileage=110000),
        models.MaintenanceRule(vehicle_id=kalina.id, title="Регулировка клапанов", interval_km=30000, last_mileage=120000),
    ]
    db.add_all(prado_rules + nwgn_rules + kalina_rules)
    db.commit()
    print("База успешно заполнена тестовыми данными.")
else:
    print("Данные уже существуют.")
db.close()

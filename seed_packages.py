from app import create_app
from app.extensions import db
from app.models import Package

app = create_app()

PACKAGES = [
    ("daily_1",   "Daily - 1 User (24 Hours)",   1440,  50,  "1user_daily"),
    ("daily_2",   "Daily - 2 Users (24 Hours)",  1440,  80,  "2users_daily"),
    ("daily_5",   "Daily - 5 Users (24 Hours)",  1440, 150,  "5users_daily"),

    ("weekly_1",  "Weekly - 1 User (7 Days)",   10080, 100,  "1user_weekly"),
    ("weekly_2",  "Weekly - 2 Users (7 Days)",  10080, 160,  "2users_weekly"),
    ("weekly_5",  "Weekly - 5 Users (7 Days)",  10080, 300,  "5users_weekly"),

    ("monthly_1", "Monthly - 1 User (30 Days)", 43200, 300,  "1user_monthly"),
    ("monthly_2", "Monthly - 2 Users (30 Days)",43200, 480,  "2users_monthly"),
    ("monthly_5", "Monthly - 5 Users (30 Days)",43200, 900,  "5users_monthly"),
]

with app.app_context():
    db.create_all()
    for code, name, mins, price, profile in PACKAGES:
        exists = Package.query.filter_by(code=code).first()
        if not exists:
            db.session.add(Package(code=code, name=name, duration_minutes=mins, price_kes=price, mikrotik_profile=profile))
    db.session.commit()
    print("Seeded packages ✅")

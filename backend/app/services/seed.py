from app.models.models import *
from app.security.auth import hash_password
USERS=[("admin@example.com","Admin User","admin","Admin123!"),("operator@example.com","Operator User","operator","Operator123!"),("technician@example.com","Technician User","technician","Technician123!"),("viewer@example.com","Viewer User","viewer","Viewer123!")]
ZONES=["Storage Zone A","Storage Zone B","Packing Area","Loading Dock","Maintenance Bay"]
def seed(db, count: int = 10):
    if not db.query(User).first():
        for email,name,role,pw in USERS: db.add(User(email=email,name=name,role=RoleName(role),hashed_password=hash_password(pw)))
    if not db.query(Robot).first():
        for i in range(1,count+1): db.add(Robot(code=f"RBT-{i:03}",name=f"Robot {i}",serial_number=f"SIM-{1000+i}",model="AMR-X" if i%2 else "LiftBot-L",battery_percentage=55+i*3,x=80+i*65,y=80+(i%5)*85,heading=i*25,zone=ZONES[i%len(ZONES)],ip_address=f"10.0.1.{20+i}"))
    if not db.query(FleetTask).first():
        for i in range(1,21): db.add(FleetTask(code=f"TSK-{i:04}",title=f"Move pallet batch {i}",priority=["low","normal","high","critical"][i%4],destination_x=150+(i%6)*90,destination_y=120+(i%4)*110))
    db.commit(); robots=db.query(Robot).all()
    if not db.query(Alert).first() and robots:
        db.add(Alert(robot_id=robots[0].id,code="BATTERY_LOW",title="Battery below threshold",message="Robot battery is below 20%",severity=AlertSeverity.warning))
        db.add(Alert(robot_id=robots[1].id,code="TEMP_HIGH",title="Temperature warning",message="Robot temperature is elevated",severity=AlertSeverity.warning))
    if not db.query(MaintenanceRecord).first() and robots: db.add(MaintenanceRecord(robot_id=robots[2].id,title="Quarterly inspection",issue_description="Scheduled preventive inspection",technician="Technician User"))
    db.commit()


from app import create_app, db
from app.models import Room, Floor, Building

app = create_app()

def add_lifts():
    with app.app_context():
        print("Checking for Lifts...")
        
        # Ensure Vyas building exists
        building = Building.query.filter_by(name='Vyas').first()
        if not building:
            print("Error: Vyas building not found!")
            return

        floors = Floor.query.filter_by(building_id=building.id).all()
        
        added_count = 0
        
        for floor in floors:
            # Lifts 1-8 for each floor
            for i in range(1, 9):
                lift_number = f"VY{floor.level}Lift{i}"
                
                # Check if it already exists
                existing = Room.query.filter_by(number=lift_number).first()
                
                if not existing:
                    print(f"Adding {lift_number} to Floor {floor.level}")
                    lift = Room(
                        floor_id=floor.id,
                        number=lift_number,
                        name=f"Lift {i} - Floor {floor.level}",
                        room_type='lift'
                    )
                    db.session.add(lift)
                    added_count += 1
        
        if added_count > 0:
            db.session.commit()
            print(f"Successfully added {added_count} lifts!")
        else:
            print("All lifts already exist.")

if __name__ == "__main__":
    add_lifts()

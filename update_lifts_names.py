
from app import create_app, db
from app.models import Room, Floor, Building

app = create_app()

def update_lift_names():
    with app.app_context():
        print("Updating Lift Names...")
        
        # Lift 4 and 5 are Faculty/Staff
        # Others are Student
        
        lifts = Room.query.filter(Room.room_type == 'lift').all()
        
        for lift in lifts:
            # Check the lift number suffix (e.g., VY0Lift4)
            # Last char is the number
            lift_num_char = lift.number[-1]
            try:
                lift_num = int(lift_num_char)
                
                if lift_num in [4, 5]:
                    lift.name = f"Faculty/Staff Lift {lift_num}"
                    # We can also update the number to be more descriptive if the system allows, 
                    # but 'number' is often used as ID. Let's keep VY#Lift# format for stability 
                    # but update the NAME which should be shown in the UI.
                else:
                    lift.name = f"Student Lift {lift_num}"
                    
                db.session.add(lift)
                print(f"Updated {lift.number} to {lift.name}")
                
            except ValueError:
                print(f"Skipping {lift.number}")
        
        db.session.commit()
        print("Lifts updated successfully.")

if __name__ == "__main__":
    update_lift_names()

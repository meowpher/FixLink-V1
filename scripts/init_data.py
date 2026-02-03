#!/usr/bin/env python3
"""
MIT-WPU Vyas Smart-Room Maintenance Tracker
Database Initialization Script

This script creates the Vyas building with:
- 8 Floors (Ground [0] to 7th Floor)
- 4th Floor with detailed layout matching the floor plan image
- Generic rooms for other floors
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Building, Floor, Room, Asset


def create_vyas_data():
    """Create Vyas building with floors and rooms."""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("MIT-WPU Vyas Tracker - Database Initialization")
        print("=" * 60)
        
        # Check if data already exists
        existing = Building.query.filter_by(name='Vyas').first()
        if existing:
            print(f"\n⚠️  Vyas building already exists.")
            response = input("Do you want to reset and recreate all data? (y/N): ")
            if response.lower() != 'y':
                print("Operation cancelled.")
                return
            
            # Clear existing data
            print("\n🗑️  Clearing existing data...")
            Asset.query.delete()
            Room.query.delete()
            Floor.query.delete()
            Building.query.delete()
            db.session.commit()
            print("✅ Existing data cleared.")
        
        # Create Vyas Building
        print("\n🏢 Creating Vyas Building...")
        vyas = Building(
            name='Vyas',
            description='Academic building with classrooms and laboratories'
        )
        db.session.add(vyas)
        db.session.commit()
        print(f"  ✅ Created: {vyas.name}")
        

        # Create 8 Floors (Ground to 7th)
        print("\n🏢 Creating Floors...")
        floors = []
        floor_names = [
            'Ground Floor',
            '1st Floor',
            '2nd Floor',
            '3rd Floor',
            '4th Floor',
            '5th Floor',
            '6th Floor',
            '7th Floor'
        ]
        
        for level, name in enumerate(floor_names):
            floor = Floor(
                building_id=vyas.id,
                level=level,
                name=name
            )
            db.session.add(floor)
            floors.append(floor)
            print(f"  ✅ Created: {name}")
        
        db.session.commit()
        
        # Create rooms for each floor
        print("\n🚪 Creating Rooms...")
        
        # Define floors that should have the detailed layout
        detailed_floors = [1, 2, 3, 4, 5, 7]
        
        for floor in floors:
            print(f"\n  📍 Creating rooms for {floor.name}...")
            
            if floor.level in detailed_floors:
                # DETAILED LAYOUT (Same as 4th Floor)
                level_digit = str(floor.level)
                
                # Room Templates (using placeholders X for level)
                # We'll replace 'VY4' with 'VY{level}' and '401' with '{level}01'
                room_templates = [
                    # Left Column (Classrooms - Blue)
                    {'suffix': '01', 'type': Room.ROOM_TYPE_CLASSROOM, 'name_suffix': '01'},
                    {'suffix': '02', 'type': Room.ROOM_TYPE_CLASSROOM, 'name_suffix': '02'},
                    {'suffix': '03', 'type': Room.ROOM_TYPE_CLASSROOM, 'name_suffix': '03'},
                    {'suffix': '04', 'type': Room.ROOM_TYPE_CLASSROOM, 'name_suffix': '04'},
                    
                    # Center Column (Labs - Teal)
                    {'suffix': '26', 'type': Room.ROOM_TYPE_LAB, 'name': 'Computer Lab'},
                    {'suffix': '27', 'type': Room.ROOM_TYPE_LAB, 'name': 'Computer Lab'},
                    {'suffix': '28', 'type': Room.ROOM_TYPE_LAB, 'name': 'Computer Lab'},
                    {'suffix': '29', 'type': Room.ROOM_TYPE_LAB, 'name': 'Computer Lab'},
                    
                    # Top/Right Section
                    {'suffix': '24', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': 'Large Classroom'},
                    {'suffix': '22', 'type': Room.ROOM_TYPE_LAB, 'name': 'Lab'},
                    
                    # Right Column (Classrooms - Blue)
                    {'suffix': '14', 'type': Room.ROOM_TYPE_CLASSROOM, 'name_suffix': '14'},
                    {'suffix': '13', 'type': Room.ROOM_TYPE_CLASSROOM, 'name_suffix': '13'},
                    
                    # Right Edge (Washrooms/Staff - Red)
                    {'suffix': '19', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Staff/Storage'},
                    {'suffix': '18', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Staff/Storage'},
                    {'suffix': '17', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Staff/Storage'},
                    {'suffix': '16', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Washroom'},
                    {'suffix': '15', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Washroom'},
                    {'suffix': '08', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Washroom'},
                    {'suffix': '07', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Washroom'},
                ]
                
                for tmpl in room_templates:
                    room_number = f"VY{level_digit}{tmpl['suffix']}"
                    
                    if 'name_suffix' in tmpl:
                        room_name = f"Classroom {level_digit}{tmpl['name_suffix']}"
                    elif 'name' in tmpl:
                         # e.g., "Computer Lab 426" -> "Computer Lab {level}26"
                         room_name = f"{tmpl['name']} {level_digit}{tmpl['suffix']}"
                    
                    room = Room(
                        floor_id=floor.id,
                        number=room_number,
                        name=room_name,
                        room_type=tmpl['type']
                    )
                    db.session.add(room)
                    print(f"    ✅ Created: {room_number} - {room_name}")

            elif floor.level == 0:
                # GROUND FLOOR (Detailed Layout)
                # Left Column: VY001-VY004
                # Center: VY024, VY026, VY027-VY030
                # Right: VY016-VY014
                # Breakout: VY007
                
                gf_rooms = [
                    # Left
                    {'suffix': '01', 'type': 'management', 'name': 'Management Office 001'},
                    {'suffix': '02', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': 'Classroom 002'},
                    {'suffix': '03', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': 'Classroom 003'},
                    {'suffix': '04', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': 'Classroom 004'},
                    
                    # Top Center
                    {'suffix': '24', 'type': 'management', 'name': 'Management Office 024'},
                    {'suffix': '26', 'type': 'faculty', 'name': 'Faculty Area 026'},
                    
                    # Center Block
                    {'suffix': '27', 'type': 'management', 'name': 'Management Office 027'},
                    {'suffix': '28', 'type': Room.ROOM_TYPE_LAB, 'name': 'Lab 028'},
                    {'suffix': '29', 'type': Room.ROOM_TYPE_LAB, 'name': 'Lab 029'},
                    {'suffix': '30', 'type': Room.ROOM_TYPE_LAB, 'name': 'Lab 030'},
                    
                    # Right Column
                    {'suffix': '16', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': 'Classroom 016'},
                    {'suffix': '15', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': 'Classroom 015'},
                    {'suffix': '14', 'type': Room.ROOM_TYPE_LAB, 'name': 'Lab 014'},
                    
                    # Bottom Right
                    {'suffix': '07', 'type': 'breakout', 'name': 'Breakout Area 007'},
                ]
                
                for config in gf_rooms:
                    room_number = f"VY0{config['suffix']}"
                    room = Room(
                        floor_id=floor.id,
                        number=room_number,
                        name=config['name'],
                        room_type=config['type']
                    )
                    db.session.add(room)
                    print(f"    ✅ Created: {room_number} - {config['name']}")

            else:
                # GENERIC LAYOUT (6th)
                floor_prefix = f"VY{floor.level}"
                
                room_configs = [
                    {'suffix': '01', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': f'Classroom {floor.level}01'},
                    {'suffix': '02', 'type': Room.ROOM_TYPE_CLASSROOM, 'name': f'Classroom {floor.level}02'},
                    {'suffix': '05', 'type': Room.ROOM_TYPE_LAB, 'name': f'Lab {floor.level}05'},
                    {'suffix': '10', 'type': Room.ROOM_TYPE_WASHROOM, 'name': 'Washroom'},
                ]
                
                for config in room_configs:
                    room = Room(
                        floor_id=floor.id,
                        number=f"{floor_prefix}{config['suffix']}",
                        name=config['name'],
                        room_type=config['type']
                    )
                    db.session.add(room)
                    print(f"    ✅ Created: {floor_prefix}{config['suffix']}")
            
        db.session.commit()
        
        # Create assets for rooms
        print("\n📦 Creating Assets...")
        all_rooms = Room.query.all()
        
        for room in all_rooms:
            # Add assets based on room type
            if room.room_type == Room.ROOM_TYPE_CLASSROOM:
                assets = [
                    {'name': 'Projector', 'type': 'projector'},
                    {'name': 'Whiteboard', 'type': 'whiteboard'},
                    {'name': 'AC Unit', 'type': 'ac'},
                    {'name': 'Ceiling Lights', 'type': 'light'},
                ]
            elif room.room_type == Room.ROOM_TYPE_LAB:
                assets = [
                    {'name': 'Projector', 'type': 'projector'},
                    {'name': 'Whiteboard', 'type': 'whiteboard'},
                    {'name': 'AC Unit', 'type': 'ac'},
                    {'name': 'Ceiling Lights', 'type': 'light'},
                    {'name': 'Computer Workstations', 'type': 'computer'},
                ]
            else:
                assets = [
                    {'name': 'Lights', 'type': 'light'},
                    {'name': 'Exhaust Fan', 'type': 'fan'},
                ]
            
            for asset_data in assets:
                asset = Asset(
                    room_id=room.id,
                    name=asset_data['name'],
                    asset_type=asset_data['type'],
                    status=Asset.STATUS_WORKING
                )
                db.session.add(asset)
            
            print(f"  ✅ Created {len(assets)} assets for {room.number}")
        
        db.session.commit()
        
        # Summary
        room_count = Room.query.count()
        asset_count = Asset.query.count()
        
        print("\n" + "=" * 60)
        print("DATABASE INITIALIZATION COMPLETE")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Building: Vyas")
        print(f"   Floors: {len(floors)}")
        print(f"   Rooms: {room_count}")
        print(f"   Assets: {asset_count}")
        
        print("\n✨ Vyas building data created successfully!")
        print("   You can now start the server with: python run.py")
        print("=" * 60)


if __name__ == '__main__':
    create_vyas_data()

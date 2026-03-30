"""
Script to add sample professionals to the database.
Run: python scripts/add_sample_professionals.py
"""
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Professional

def add_sample_professionals():
    """Add sample professionals for each category."""
    app = create_app()
    
    with app.app_context():
        # Check if professionals already exist
        existing_count = Professional.query.count()
        if existing_count > 0:
            print(f"Found {existing_count} existing professionals. Skipping sample data creation.")
            print("If you want to add more, use the admin dashboard.")
            return
        
        # Sample professionals data
        professionals_data = [
            {
                'name': 'Rahul Sharma',
                'email': 'rahul.sharma@fixlink.com',
                'phone': '9876543210',
                'category': Professional.CATEGORY_IT,
                'password': 'password123'
            },
            {
                'name': 'Priya Patel',
                'email': 'priya.patel@fixlink.com',
                'phone': '9876543211',
                'category': Professional.CATEGORY_IT,
                'password': 'password123'
            },
            {
                'name': 'Amit Kumar',
                'email': 'amit.kumar@fixlink.com',
                'phone': '9876543212',
                'category': Professional.CATEGORY_ELECTRICIAN,
                'password': 'password123'
            },
            {
                'name': 'Sunita Devi',
                'email': 'sunita.devi@fixlink.com',
                'phone': '9876543213',
                'category': Professional.CATEGORY_ELECTRICIAN,
                'password': 'password123'
            },
            {
                'name': 'Rajesh Gupta',
                'email': 'rajesh.gupta@fixlink.com',
                'phone': '9876543214',
                'category': Professional.CATEGORY_PLUMBER,
                'password': 'password123'
            },
            {
                'name': 'Anita Verma',
                'email': 'anita.verma@fixlink.com',
                'phone': '9876543215',
                'category': Professional.CATEGORY_PLUMBER,
                'password': 'password123'
            },
            {
                'name': 'Mohan Lal',
                'email': 'mohan.lal@fixlink.com',
                'phone': '9876543216',
                'category': Professional.CATEGORY_CARPENTER,
                'password': 'password123'
            },
            {
                'name': 'Geeta Rani',
                'email': 'geeta.rani@fixlink.com',
                'phone': '9876543217',
                'category': Professional.CATEGORY_CARPENTER,
                'password': 'password123'
            }
        ]
        
        print("Creating sample professionals...")
        
        for prof_data in professionals_data:
            # Check if email already exists
            existing = Professional.query.filter_by(email=prof_data['email']).first()
            if existing:
                print(f"  Skipping {prof_data['email']} - already exists")
                continue
            
            professional = Professional(
                name=prof_data['name'],
                email=prof_data['email'],
                phone=prof_data['phone'],
                category=prof_data['category'],
                is_active=True
            )
            professional.set_password(prof_data['password'])
            db.session.add(professional)
            print(f"  Added {prof_data['name']} ({prof_data['category']})")
        
        db.session.commit()
        print(f"\nSample professionals created successfully!")
        print(f"\nYou can log in with any of these credentials:")
        print(f"  Email: rahul.sharma@fixlink.com")
        print(f"  Password: password123")
        print(f"\nOr use the admin dashboard to manage professionals.")

if __name__ == '__main__':
    add_sample_professionals()

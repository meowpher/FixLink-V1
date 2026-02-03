"""
SQLAlchemy Models for MIT-WPU Vyas Smart-Room Tracker
"""
from datetime import datetime
from . import db


class Building(db.Model):
    """Building model - Vyas building."""
    __tablename__ = 'buildings'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    floors = db.relationship('Floor', backref='building', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Building {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Floor(db.Model):
    """Floor model - floors in Vyas building (0-7)."""
    __tablename__ = 'floors'
    
    id = db.Column(db.Integer, primary_key=True)
    building_id = db.Column(db.Integer, db.ForeignKey('buildings.id'), nullable=False)
    level = db.Column(db.Integer, nullable=False)  # 0=Ground, 1-7=Floors
    name = db.Column(db.String(50), nullable=False)  # e.g., '4th Floor'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    rooms = db.relationship('Room', backref='floor', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Floor {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'building_id': self.building_id,
            'level': self.level,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Room(db.Model):
    """Room model - rooms on each floor."""
    __tablename__ = 'rooms'
    
    ROOM_TYPE_CLASSROOM = 'class'
    ROOM_TYPE_LAB = 'lab'
    ROOM_TYPE_WASHROOM = 'washroom'
    ROOM_TYPE_STORAGE = 'storage'
    ROOM_TYPE_OTHER = 'other'
    
    ROOM_TYPES = [ROOM_TYPE_CLASSROOM, ROOM_TYPE_LAB, ROOM_TYPE_WASHROOM, ROOM_TYPE_STORAGE, ROOM_TYPE_OTHER]
    
    id = db.Column(db.Integer, primary_key=True)
    floor_id = db.Column(db.Integer, db.ForeignKey('floors.id'), nullable=False)
    number = db.Column(db.String(20), nullable=False)  # e.g., 'VY401'
    name = db.Column(db.String(100), nullable=True)  # e.g., 'Classroom 401'
    room_type = db.Column(db.String(20), default=ROOM_TYPE_CLASSROOM, nullable=False)
    map_coords = db.Column(db.String(255), nullable=True)  # Optional: SVG coords or grid position
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    assets = db.relationship('Asset', backref='room', lazy=True, cascade='all, delete-orphan')
    tickets = db.relationship('Ticket', backref='room', lazy=True)
    
    def __repr__(self):
        return f'<Room {self.number}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'floor_id': self.floor_id,
            'number': self.number,
            'name': self.name,
            'room_type': self.room_type,
            'map_coords': self.map_coords,
            'floor_name': self.floor.name if self.floor else None,
            'building_name': self.floor.building.name if self.floor and self.floor.building else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @property
    def has_open_tickets(self):
        """Check if room has any open or in-progress tickets."""
        return any(t.status in [Ticket.STATUS_OPEN, Ticket.STATUS_IN_PROGRESS] for t in self.tickets)
    
    @property
    def has_broken_assets(self):
        """Check if room has any broken assets."""
        return any(a.status == Asset.STATUS_BROKEN for a in self.assets)
    
    @property
    def status(self):
        """Get room status based on tickets and assets."""
        if self.has_open_tickets or self.has_broken_assets:
            return 'issue'
        return 'normal'


class Asset(db.Model):
    """Asset model - equipment in rooms."""
    __tablename__ = 'assets'
    
    STATUS_WORKING = 'working'
    STATUS_BROKEN = 'broken'
    STATUS_MAINTENANCE = 'maintenance'
    
    STATUS_CHOICES = [STATUS_WORKING, STATUS_BROKEN, STATUS_MAINTENANCE]
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    asset_type = db.Column(db.String(50), nullable=False)  # e.g., 'projector', 'ac', 'computer'
    status = db.Column(db.String(20), default=STATUS_WORKING, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    tickets = db.relationship('Ticket', backref='asset', lazy=True)
    
    def __repr__(self):
        return f'<Asset {self.name} ({self.status})>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'asset_type': self.asset_type,
            'room_id': self.room_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Ticket(db.Model):
    """Ticket model - maintenance requests."""
    __tablename__ = 'tickets'
    
    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in-progress'
    STATUS_FIXED = 'fixed'
    
    STATUS_CHOICES = [STATUS_OPEN, STATUS_IN_PROGRESS, STATUS_FIXED]
    
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('rooms.id'), nullable=False)
    asset_id = db.Column(db.Integer, db.ForeignKey('assets.id'), nullable=True)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    
    # Reporter info
    reporter_name = db.Column(db.String(100), nullable=False)
    prn = db.Column(db.String(20), nullable=False)
    reporter_email = db.Column(db.String(120), nullable=False)
    
    # Status tracking
    status = db.Column(db.String(20), default=STATUS_OPEN, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    fixed_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<Ticket #{self.id} - {self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'room_id': self.room_id,
            'room_number': self.room.number if self.room else None,
            'floor_name': self.room.floor.name if self.room and self.room.floor else None,
            'asset_id': self.asset_id,
            'asset_name': self.asset.name if self.asset else None,
            'issue_type': self.issue_type,
            'description': self.description,
            'image_filename': self.image_filename,
            'reporter_name': self.reporter_name,
            'prn': self.prn,
            'reporter_email': self.reporter_email,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'fixed_at': self.fixed_at.isoformat() if self.fixed_at else None
        }

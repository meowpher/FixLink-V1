"""
Analytics Engine for FixLink - Predictive Maintenance & Performance Tracking
"""
from datetime import datetime, timedelta
from sqlalchemy import func
from . import db
from .models import Ticket, Asset, Professional

def calculate_asset_health(asset_id):
    """
    Calculate a health score (0-100) for a specific asset.
    (Individual calculation - uses DB)
    """
    asset = Asset.query.get(asset_id)
    if not asset:
        return 0
    
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)
    recent_tickets = Ticket.query.filter(
        Ticket.asset_id == asset_id,
        Ticket.created_at >= sixty_days_ago
    ).all()
    
    return _compute_score_logic(asset, recent_tickets)

def _compute_score_logic(asset, recent_tickets):
    """
    Core scoring algorithm.
    Decoupled from DB for bulk processing.
    """
    score = 100
    
    # 1. Lifecycle Depreciation (Age-based)
    if asset.installation_date:
        age_delta = datetime.utcnow() - asset.installation_date
        age_years = age_delta.days / 365.25
        DEPRECIATION_CONSTANT = 5
        depreciation_penalty = age_years * DEPRECIATION_CONSTANT
        score -= depreciation_penalty
    
    # 2. Current Status Penalty
    if asset.status == Asset.STATUS_BROKEN:
        score -= 50
    elif asset.status == Asset.STATUS_MAINTENANCE:
        score -= 20
        
    # 3. Repair Frequency Penalty (Last 60 days)
    score -= (len(recent_tickets) * 10)
    
    # 4. Complexity Penalty
    for ticket in recent_tickets:
        if ticket.complexity == Ticket.COMPLEXITY_HIGH:
            score -= 10
        elif ticket.complexity == Ticket.COMPLEXITY_MEDIUM:
            score -= 5
            
    return max(0, min(100, score))

def get_technician_efficiency():
    """
    Calculate performance metrics for all professionals.
    Metrics: Average Time to Repair (MTTR), Completion Rate, Active Load.
    """
    professionals = Professional.query.all()
    stats = []
    
    # Bulk fetch fixed tickets and active status
    all_fixed = Ticket.query.filter(Ticket.status == Ticket.STATUS_FIXED).all()
    all_active = Ticket.query.filter(Ticket.status.in_([Ticket.STATUS_ASSIGNED, Ticket.STATUS_IN_PROGRESS])).all()
    
    fixed_by_pro = {}
    for t in all_fixed:
        if t.assigned_professional_id not in fixed_by_pro:
            fixed_by_pro[t.assigned_professional_id] = []
        fixed_by_pro[t.assigned_professional_id].append(t)
        
    active_by_pro = {}
    for t in all_active:
        active_by_pro[t.assigned_professional_id] = active_by_pro.get(t.assigned_professional_id, 0) + 1

    for pro in professionals:
        pro_fixed = fixed_by_pro.get(pro.id, [])
        ttr_list = []
        for t in pro_fixed:
            if t.job_started_at and t.fixed_at:
                delta = t.fixed_at - t.job_started_at
                ttr_list.append(delta.total_seconds() / 3600)
                
        avg_ttr = sum(ttr_list) / len(ttr_list) if ttr_list else 0
        
        stats.append({
            'id': pro.id,
            'name': pro.name,
            'category': pro.category,
            'fixed_count': len(pro_fixed),
            'avg_ttr_hours': round(avg_ttr, 1),
            'active_tasks': active_by_pro.get(pro.id, 0)
        })
        
    return sorted(stats, key=lambda x: x['fixed_count'], reverse=True)

def get_system_trends(days=7):
    """
    Get ticket volume trends for the last X days.
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    tickets = Ticket.query.filter(Ticket.created_at >= start_date).all()
    
    trend_data = {}
    for i in range(days):
        date_str = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
        trend_data[date_str] = 0
        
    for t in tickets:
        date_str = t.created_at.strftime('%Y-%m-%d')
        if date_str in trend_data:
            trend_data[date_str] += 1
            
    # Sort by date
    sorted_labels = sorted(trend_data.keys())
    sorted_values = [trend_data[k] for k in sorted_labels]
    
    return {
        'labels': sorted_labels,
        'values': sorted_values
    }

def get_critical_assets(limit=5):
    """
    Find assets with lowest health scores using optimized batch processing.
    Eliminates N+1 query issue by pre-fetching tickets.
    """
    from sqlalchemy.orm import joinedload
    assets = Asset.query.options(joinedload(Asset.room)).all()
    
    # 1. Fetch ALL relevant tickets in ONE query
    sixty_days_ago = datetime.utcnow() - timedelta(days=60)
    all_recent_tickets = Ticket.query.filter(Ticket.created_at >= sixty_days_ago).all()
    
    # 2. Map tickets to assets in memory
    ticket_map = {}
    for t in all_recent_tickets:
        if t.asset_id:
            if t.asset_id not in ticket_map:
                ticket_map[t.asset_id] = []
            ticket_map[t.asset_id].append(t)
            
    # 3. Calculate scores
    health_list = []
    for a in assets:
        score = _compute_score_logic(a, ticket_map.get(a.id, []))
        # Flag anything with issues or low score
        if score < 95 or a.status != Asset.STATUS_WORKING:
            health_list.append({
                'id': a.id,
                'name': a.name,
                'room': a.room.number if a.room else 'N/A',
                'type': a.asset_type,
                'score': round(score, 1),
                'status': a.status
            })
            
    return sorted(health_list, key=lambda x: x['score'])[:limit]

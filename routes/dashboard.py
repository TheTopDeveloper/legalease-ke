import logging
from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from models import Case, Document, Contract, Event, Client
from sqlalchemy import func
from datetime import datetime, timedelta
from app import db

logger = logging.getLogger(__name__)

# Create dashboard blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

@dashboard_bp.route('/')
@login_required
def index():
    """Main dashboard"""
    # Get recent cases
    recent_cases = Case.query.filter_by(user_id=current_user.id).order_by(Case.created_at.desc()).limit(5).all()
    
    # Get recent documents
    recent_documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.created_at.desc()).limit(5).all()
    
    # Get upcoming events
    now = datetime.utcnow()
    upcoming_events = Event.query.filter(
        Event.user_id == current_user.id,
        Event.start_time > now
    ).order_by(Event.start_time).limit(5).all()
    
    # Get case statistics
    case_count = Case.query.filter_by(user_id=current_user.id).count()
    active_case_count = Case.query.filter_by(user_id=current_user.id, status='Active').count()
    
    # Get document statistics
    document_count = Document.query.filter_by(user_id=current_user.id).count()
    
    # Get contract statistics
    contract_count = Contract.query.filter_by(user_id=current_user.id).count()
    active_contract_count = Contract.query.filter_by(user_id=current_user.id, status='Active').count()
    
    # Get client count
    client_count = Client.query.count()
    
    return render_template('dashboard/index.html',
                          recent_cases=recent_cases,
                          recent_documents=recent_documents,
                          upcoming_events=upcoming_events,
                          case_count=case_count,
                          active_case_count=active_case_count,
                          document_count=document_count,
                          contract_count=contract_count,
                          active_contract_count=active_contract_count,
                          client_count=client_count)

@dashboard_bp.route('/calendar')
@login_required
def calendar():
    """Calendar view of events"""
    # Default to month view for dashboard
    view_type = request.args.get('view', 'month')
    
    # Get date parameters
    date_str = request.args.get('date')
    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = datetime.now().date()
    else:
        current_date = datetime.now().date()
    
    # For month view, always start at the first day of the month
    if view_type == 'month':
        # Calculate date range for month view
        start_date = current_date.replace(day=1)
        if start_date.month == 12:
            end_date = datetime(start_date.year + 1, 1, 1).date() - timedelta(days=1)
        else:
            end_date = datetime(start_date.year, start_date.month + 1, 1).date() - timedelta(days=1)
            
        # Include days from previous/next months to fill calendar grid
        first_day_weekday = start_date.weekday()
        start_range = start_date - timedelta(days=first_day_weekday)
        
        last_day_weekday = end_date.weekday()
        days_to_next_month = 6 - last_day_weekday
        end_range = end_date + timedelta(days=days_to_next_month)
        
    elif view_type == 'week':
        # Calculate date range for week view
        start_date = current_date - timedelta(days=current_date.weekday())
        end_date = start_date + timedelta(days=6)
        start_range = start_date
        end_range = end_date
        
    else:  # day view
        start_date = current_date
        end_date = current_date
        start_range = start_date
        end_range = end_date
    
    # Get events for the date range
    events = Event.query.filter(
        Event.user_id == current_user.id,
        func.date(Event.start_time) >= start_range,
        func.date(Event.start_time) <= end_range
    ).order_by(Event.start_time).all()
    
    # Group events by date for easier rendering
    events_by_date = {}
    for event in events:
        event_date = event.start_time.date()
        if event_date not in events_by_date:
            events_by_date[event_date] = []
        events_by_date[event_date].append(event)
    
    # Get conflicts (events on the same day that overlap)
    conflicts = []
    for date_events in events_by_date.values():
        for i, event1 in enumerate(date_events):
            for event2 in date_events[i+1:]:
                if event1.overlaps_with(event2):
                    conflicts.append((event1.id, event2.id))
                    # Update conflict status if not already set
                    if not event1.conflict_status:
                        event1.conflict_status = 'potential'
                    if not event2.conflict_status:
                        event2.conflict_status = 'potential'
    
    # Commit any changes to conflict status
    if conflicts:
        db.session.commit()
    
    # Calculate navigation dates
    if view_type == 'month':
        if current_date.month == 1:
            prev_date = datetime(current_date.year - 1, 12, 1).date()
        else:
            prev_date = datetime(current_date.year, current_date.month - 1, 1).date()
            
        if current_date.month == 12:
            next_date = datetime(current_date.year + 1, 1, 1).date()
        else:
            next_date = datetime(current_date.year, current_date.month + 1, 1).date()
    elif view_type == 'week':
        prev_date = current_date - timedelta(days=7)
        next_date = current_date + timedelta(days=7)
    else:  # day view
        prev_date = current_date - timedelta(days=1)
        next_date = current_date + timedelta(days=1)
    
    # Get cases for the filter sidebar
    cases = Case.query.filter_by(user_id=current_user.id).order_by(Case.title).all()
    
    # Calculate days in month for calendar grid
    days_in_month = (end_date - start_date).days + 1
    
    return render_template(
        'events/calendar.html',
        view_type=view_type,
        current_date=current_date,
        start_date=start_date,
        end_date=end_date,
        start_range=start_range,
        end_range=end_range,
        events_by_date=events_by_date,
        conflicts=conflicts,
        prev_date=prev_date,
        next_date=next_date,
        cases=cases,
        days_in_month=days_in_month,
        first_day_weekday=first_day_weekday,
        timedelta=timedelta
    )

# No need to import request here, already imported at the top

import logging
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Case, Document, Contract, Event, Client
from sqlalchemy import func
from datetime import datetime, timedelta

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
    # Get start and end date from query params, default to current month
    today = datetime.utcnow().date()
    start_date_str = request.args.get('start_date')
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
    else:
        start_date = today.replace(day=1)
    
    # Get end date (start date + 1 month)
    if start_date.month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=start_date.month + 1)
    
    # Get events for the selected month
    events = Event.query.filter(
        Event.user_id == current_user.id,
        func.date(Event.start_time) >= start_date,
        func.date(Event.start_time) < end_date
    ).order_by(Event.start_time).all()
    
    # Organize events by date
    events_by_date = {}
    for event in events:
        event_date = event.start_time.date()
        if event_date not in events_by_date:
            events_by_date[event_date] = []
        events_by_date[event_date].append(event)
    
    # Generate calendar days
    first_day_weekday = start_date.weekday()
    days_in_month = (end_date - start_date).days
    
    # Previous and next month links
    prev_month = start_date - timedelta(days=1)
    prev_month = prev_month.replace(day=1)
    
    next_month = end_date
    
    return render_template('events/calendar.html',
                          start_date=start_date,
                          end_date=end_date,
                          first_day_weekday=first_day_weekday,
                          days_in_month=days_in_month,
                          events_by_date=events_by_date,
                          prev_month=prev_month,
                          next_month=next_month,
                          view_type='month',
                          current_date=start_date,
                          cases=Case.query.filter_by(user_id=current_user.id).all(),
                          timedelta=timedelta)

# Import request here to avoid circular imports
from flask import request

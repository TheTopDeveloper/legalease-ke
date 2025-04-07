"""
Routes for event management and advanced calendar functionality.
"""
import logging
import json
from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, or_, and_
from app import db
from models import Event, Case

logger = logging.getLogger(__name__)

# Create blueprint
events_bp = Blueprint('events', __name__, url_prefix='/events')

@events_bp.route('/')
@login_required
def index():
    """List all events for the user"""
    # Get filter parameters
    event_type = request.args.get('event_type')
    case_id = request.args.get('case_id')
    priority = request.args.get('priority')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Base query - all events for the current user
    query = Event.query.filter(Event.user_id == current_user.id)
    
    # Apply filters
    if event_type:
        query = query.filter(Event.event_type == event_type)
    
    if case_id:
        query = query.filter(Event.case_id == case_id)
    
    if priority:
        query = query.filter(Event.priority == priority)
    
    # Date filtering
    today = datetime.utcnow().date()
    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            start_date = today
    else:
        start_date = today
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            end_date = today + timedelta(days=30)
    else:
        end_date = today + timedelta(days=30)
    
    # Apply date filters
    query = query.filter(
        func.date(Event.start_time) >= start_date,
        func.date(Event.start_time) <= end_date
    )
    
    # Get results ordered by start time
    events = query.order_by(Event.start_time).all()
    
    # Get cases for filtering dropdown
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Get event types for filtering dropdown
    event_types = db.session.query(Event.event_type).distinct().all()
    event_types = [et[0] for et in event_types if et[0]]
    
    return render_template(
        'events/index.html',
        events=events,
        cases=cases,
        event_types=event_types,
        current_filters={
            'event_type': event_type,
            'case_id': case_id,
            'priority': priority,
            'start_date': start_date_str,
            'end_date': end_date_str
        }
    )

@events_bp.route('/calendar')
@login_required
def calendar():
    """Advanced calendar view of events"""
    # Get view type (month, week, day)
    view_type = request.args.get('view', 'month')
    
    # Get date parameters
    date_str = request.args.get('date')
    if date_str:
        try:
            current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            current_date = date.today()
    else:
        current_date = date.today()
    
    # Calculate date range based on view type
    if view_type == 'month':
        start_date = current_date.replace(day=1)
        if start_date.month == 12:
            end_date = date(start_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(start_date.year, start_date.month + 1, 1) - timedelta(days=1)
        
        # We need to include the days from the previous and next months to fill the calendar grid
        # In Python, weekday() returns 0 for Monday, 6 for Sunday
        # For calendar display with Sunday as first day (US/local format)
        weekday_mapping = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}  # Map Monday(0)→1, Tuesday(1)→2, ..., Sunday(6)→0
        first_day_weekday = weekday_mapping[start_date.weekday()]  # Sunday-first
        
        # Calculate days needed from previous month to fill first row
        days_to_previous_month = first_day_weekday
        start_range = start_date - timedelta(days=days_to_previous_month)
        
        # Calculate days needed from next month to fill last row
        last_day_weekday = weekday_mapping[end_date.weekday()]  # Sunday-first
        days_to_next_month = 6 - last_day_weekday
        end_range = end_date + timedelta(days=days_to_next_month)
        
        # Log for debugging
        logger.debug(f"Month view: start_date={start_date}, end_date={end_date}")
        logger.debug(f"Current date: {current_date}, today: {date.today()}")
        logger.debug(f"First day weekday: {first_day_weekday}, Last day weekday: {last_day_weekday}")
        logger.debug(f"Calendar range: {start_range} to {end_range}")
        
    elif view_type == 'week':
        # Get the start of the week (Monday)
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
            prev_month = date(current_date.year - 1, 12, 1)
        else:
            prev_month = date(current_date.year, current_date.month - 1, 1)
            
        if current_date.month == 12:
            next_month = date(current_date.year + 1, 1, 1)
        else:
            next_month = date(current_date.year, current_date.month + 1, 1)
            
        prev_date = prev_month
        next_date = next_month
        
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
    
    # Adjust for Sunday-first calendar when passing to template
    template_first_day_weekday = (start_date.weekday() + 1) % 7
    
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
        first_day_weekday=template_first_day_weekday,
        timedelta=timedelta
    )

@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new event"""
    if request.method == 'POST':
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description')
        event_type = request.form.get('event_type')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        location = request.form.get('location')
        case_id = request.form.get('case_id') or None
        priority = request.form.get('priority', '2')
        is_all_day = 'is_all_day' in request.form
        is_recurring = 'is_recurring' in request.form
        recurrence_pattern = request.form.get('recurrence_pattern')
        recurrence_end_date_str = request.form.get('recurrence_end_date')
        reminder_time = request.form.get('reminder_time', '24')
        
        # Validate form data
        if not title or not event_type or not start_time_str:
            flash('Title, event type, and start time are required', 'error')
            return redirect(url_for('events.create'))
        
        # Parse dates
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None
            recurrence_end_date = datetime.strptime(recurrence_end_date_str, '%Y-%m-%d').date() if recurrence_end_date_str and is_recurring else None
        except ValueError as e:
            flash(f'Invalid date format: {str(e)}', 'error')
            return redirect(url_for('events.create'))
        
        # Get advanced scheduling parameters
        buffer_before = request.form.get('buffer_before', '0')
        buffer_after = request.form.get('buffer_after', '0')
        travel_time_minutes = request.form.get('travel_time_minutes', '0')
        is_flexible = 'is_flexible' in request.form
        court_reference_number = request.form.get('court_reference_number', '')
        participants = request.form.get('participants', '')
        related_event_id = request.form.get('related_event_id') or None
        notification_preferences = request.form.get('notification_preferences', '')
        
        # Create new event
        new_event = Event(
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            case_id=case_id,
            user_id=current_user.id,
            priority=int(priority),
            is_all_day=is_all_day,
            is_recurring=is_recurring,
            recurrence_pattern=recurrence_pattern if is_recurring else None,
            recurrence_end_date=recurrence_end_date,
            reminder_time=int(reminder_time),
            # Advanced scheduling fields
            buffer_before=int(buffer_before),
            buffer_after=int(buffer_after),
            travel_time_minutes=int(travel_time_minutes),
            is_flexible=is_flexible,
            court_reference_number=court_reference_number,
            participants=participants,
            related_event_id=related_event_id,
            notification_preferences=notification_preferences
        )
        
        # Check for conflicts
        conflicts, conflict_details = check_conflicts(new_event)
        if conflicts:
            # Create a more detailed conflict warning if we have details
            if conflict_details:
                # Count severity levels
                critical = sum(1 for c in conflict_details if c['severity'] == 'critical')
                significant = sum(1 for c in conflict_details if c['severity'] == 'significant')
                minor = sum(1 for c in conflict_details if c['severity'] == 'minor')
                
                if critical > 0:
                    conflict_warning = f"Warning: This event has {critical} critical conflicts that require attention."
                    flash(conflict_warning, 'danger')
                elif significant > 0:
                    conflict_warning = f"Warning: This event has {significant} significant conflicts that should be reviewed."
                    flash(conflict_warning, 'warning')
                else:
                    conflict_warning = f"Notice: This event has {minor} minor conflicts."
                    flash(conflict_warning, 'info')
            else:
                conflict_warning = f"Warning: This event conflicts with {len(conflicts)} existing events."
                flash(conflict_warning, 'warning')
                
            new_event.conflict_status = 'potential'
        
        # Save to database
        db.session.add(new_event)
        try:
            db.session.commit()
            logger.info(f"Created event: {new_event.title}")
            
            # If this is a court date and has a case, update the case's next court date
            if event_type in ['Court Appearance', 'Hearing', 'Mention'] and case_id:
                case = Case.query.get(case_id)
                if case and (not case.next_court_date or case.next_court_date < start_time):
                    case.next_court_date = start_time
                    db.session.commit()
                    logger.info(f"Updated next court date for case {case.title}")
            
            flash('Event created successfully', 'success')
            
            # Create recurring instances if needed
            if is_recurring and recurrence_pattern and recurrence_end_date:
                create_recurring_events(new_event)
                flash('Recurring events created successfully', 'success')
                
            return redirect(url_for('events.calendar'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating event: {str(e)}")
            flash(f'Error creating event: {str(e)}', 'error')
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # For GET request or if POST fails, render the form
    return render_template(
        'events/create.html',
        cases=cases,
        event_types=[
            'Court Appearance', 'Hearing', 'Mention', 'Filing', 
            'Client Meeting', 'Team Meeting', 'Deadline', 'Reminder',
            'Case Review', 'Document Preparation', 'Other'
        ]
    )

@events_bp.route('/<int:event_id>', methods=['GET'])
@login_required
def view(event_id):
    """View a specific event"""
    event = Event.query.get_or_404(event_id)
    
    # Check permission
    if event.user_id != current_user.id:
        flash('You do not have permission to view this event', 'error')
        return redirect(url_for('events.index'))
    
    # Check for conflicts with enhanced conflict detection
    conflicts, conflict_details = check_conflicts(event)
    
    return render_template(
        'events/view.html',
        event=event,
        conflicts=conflicts,
        conflict_details=conflict_details
    )

@events_bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(event_id):
    """Edit an event"""
    event = Event.query.get_or_404(event_id)
    
    # Check permission
    if event.user_id != current_user.id:
        flash('You do not have permission to edit this event', 'error')
        return redirect(url_for('events.index'))
    
    if request.method == 'POST':
        # Get form data
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.event_type = request.form.get('event_type')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        event.location = request.form.get('location')
        event.case_id = request.form.get('case_id') or None
        event.priority = int(request.form.get('priority', '2'))
        event.is_all_day = 'is_all_day' in request.form
        event.is_recurring = 'is_recurring' in request.form
        event.recurrence_pattern = request.form.get('recurrence_pattern') if event.is_recurring else None
        recurrence_end_date_str = request.form.get('recurrence_end_date')
        event.reminder_time = int(request.form.get('reminder_time', '24'))
        
        # Reset reminder_sent status if the event time changes
        original_event = Event.query.get(event_id)
        if original_event.start_time != datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M'):
            event.reminder_sent = False
        
        # Parse dates
        try:
            event.start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            event.end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None
            event.recurrence_end_date = datetime.strptime(recurrence_end_date_str, '%Y-%m-%d').date() if recurrence_end_date_str and event.is_recurring else None
        except ValueError as e:
            flash(f'Invalid date format: {str(e)}', 'error')
            return redirect(url_for('events.edit', event_id=event.id))
        
        # Get advanced scheduling parameters
        event.buffer_before = int(request.form.get('buffer_before', '0'))
        event.buffer_after = int(request.form.get('buffer_after', '0'))
        event.travel_time_minutes = int(request.form.get('travel_time_minutes', '0'))
        event.is_flexible = 'is_flexible' in request.form
        event.court_reference_number = request.form.get('court_reference_number', '')
        event.participants = request.form.get('participants', '')
        event.related_event_id = request.form.get('related_event_id') or None
        event.notification_preferences = request.form.get('notification_preferences', '')
        
        # Check for conflicts with enhanced conflict detection
        conflicts, conflict_details = check_conflicts(event)
        if conflicts:
            # Create a more detailed conflict warning if we have details
            if conflict_details:
                # Count severity levels
                critical = sum(1 for c in conflict_details if c['severity'] == 'critical')
                significant = sum(1 for c in conflict_details if c['severity'] == 'significant')
                minor = sum(1 for c in conflict_details if c['severity'] == 'minor')
                
                if critical > 0:
                    conflict_warning = f"Warning: This event has {critical} critical conflicts that require attention."
                    flash(conflict_warning, 'danger')
                elif significant > 0:
                    conflict_warning = f"Warning: This event has {significant} significant conflicts that should be reviewed."
                    flash(conflict_warning, 'warning')
                else:
                    conflict_warning = f"Notice: This event has {minor} minor conflicts."
                    flash(conflict_warning, 'info')
            else:
                conflict_warning = f"Warning: This event conflicts with {len(conflicts)} existing events."
                flash(conflict_warning, 'warning')
                
            event.conflict_status = 'potential'
        else:
            event.conflict_status = None
        
        # Save changes
        try:
            db.session.commit()
            logger.info(f"Updated event: {event.title}")
            
            # If this is a court date and has a case, update the case's next court date
            if event.event_type in ['Court Appearance', 'Hearing', 'Mention'] and event.case_id:
                case = Case.query.get(event.case_id)
                if case and (not case.next_court_date or case.next_court_date < event.start_time):
                    case.next_court_date = event.start_time
                    db.session.commit()
                    logger.info(f"Updated next court date for case {case.title}")
            
            flash('Event updated successfully', 'success')
            return redirect(url_for('events.view', event_id=event.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating event: {str(e)}")
            flash(f'Error updating event: {str(e)}', 'error')
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # For GET request or if POST fails, render the form
    return render_template(
        'events/edit.html',
        event=event,
        cases=cases,
        event_types=[
            'Court Appearance', 'Hearing', 'Mention', 'Filing', 
            'Client Meeting', 'Team Meeting', 'Deadline', 'Reminder',
            'Case Review', 'Document Preparation', 'Other'
        ]
    )

@events_bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete(event_id):
    """Delete an event"""
    event = Event.query.get_or_404(event_id)
    
    # Check permission
    if event.user_id != current_user.id:
        flash('You do not have permission to delete this event', 'error')
        return redirect(url_for('events.index'))
    
    try:
        db.session.delete(event)
        db.session.commit()
        logger.info(f"Deleted event: {event.title}")
        flash('Event deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting event: {str(e)}")
        flash(f'Error deleting event: {str(e)}', 'error')
    
    return redirect(url_for('events.calendar'))

@events_bp.route('/<int:event_id>/resolve-conflict', methods=['POST'])
@login_required
def resolve_conflict(event_id):
    """Mark a conflict as resolved"""
    event = Event.query.get_or_404(event_id)
    
    # Check permission
    if event.user_id != current_user.id:
        flash('You do not have permission to update this event', 'error')
        return redirect(url_for('events.index'))
    
    event.conflict_status = 'resolved'
    
    try:
        db.session.commit()
        flash('Conflict marked as resolved', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating conflict status: {str(e)}")
        flash(f'Error updating conflict: {str(e)}', 'error')
    
    return redirect(url_for('events.view', event_id=event.id))

@events_bp.route('/suggest-times', methods=['POST'])
@login_required
def suggest_times():
    """Suggest available times for scheduling with advanced conflict detection"""
    # Get parameters from request
    data = request.get_json()
    date_str = data.get('date')
    duration_minutes = int(data.get('duration', 60))
    case_id = data.get('case_id')
    event_type = data.get('event_type')
    location = data.get('location')
    buffer_before = int(data.get('buffer_before', 0))
    buffer_after = int(data.get('buffer_after', 0))
    travel_time = int(data.get('travel_time', 0))
    court_priority = data.get('court_priority', False)  # Whether to prioritize court schedules
    
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid date format'}), 400
    
    # Get existing events for the user on the specified date
    existing_events = Event.query.filter(
        Event.user_id == current_user.id,
        func.date(Event.start_time) == target_date
    ).order_by(Event.start_time).all()
    
    # Court operational hours might be different from business hours
    court_start_hour = 8  # Courts typically start at 8:00 AM
    court_end_hour = 16   # Courts typically end by 4:00 PM
    
    # Business hours (8:00 AM to 5:00 PM, adjust as needed)
    business_start_hour = 8
    business_end_hour = 17
    
    # Choose the appropriate hours based on event type
    is_court_related = event_type in ['Court Appearance', 'Hearing', 'Mention', 'Filing']
    
    if is_court_related and court_priority:
        start_hour = court_start_hour
        end_hour = court_end_hour
    else:
        start_hour = business_start_hour
        end_hour = business_end_hour
    
    # Total time needed including buffers and travel time
    total_minutes_needed = duration_minutes + buffer_before + buffer_after + travel_time
    
    # Create list of available time slots (30-minute increments)
    day_start = datetime.combine(target_date, datetime.min.time().replace(hour=start_hour))
    day_end = datetime.combine(target_date, datetime.min.time().replace(hour=end_hour))
    
    # Generate potential time slots (30-minute intervals)
    time_slots = []
    current_time = day_start
    while current_time < day_end:
        # The actual event window including buffers
        event_start = current_time
        event_end = current_time + timedelta(minutes=total_minutes_needed)
        
        # Only include slots that fit within the day
        if event_end <= day_end:
            time_slots.append({
                'start': current_time,
                'end': current_time + timedelta(minutes=duration_minutes),  # Just the event itself
                'buffer_start': current_time - timedelta(minutes=buffer_before) if buffer_before > 0 else current_time,
                'buffer_end': event_end,
                'available': True,
                'conflicts': []
            })
        current_time += timedelta(minutes=30)
    
    # Mark slots as unavailable if they overlap with existing events
    for event in existing_events:
        for slot in time_slots:
            # Skip if the slot is already marked as unavailable
            if not slot['available']:
                continue
            
            # Get the complete time range for the existing event including buffers and travel time
            existing_event_start = event.start_time - timedelta(minutes=event.buffer_before or 0)
            
            if event.end_time:
                existing_event_end = event.end_time + timedelta(minutes=event.buffer_after or 0)
            else:
                # Default duration of 1 hour if no end time
                existing_event_end = event.start_time + timedelta(hours=1) + timedelta(minutes=event.buffer_after or 0)
            
            # Check for overlap between the slot (including buffers) and the existing event
            if (slot['buffer_start'] < existing_event_end and 
                slot['buffer_end'] > existing_event_start):
                # There's an overlap - the slot conflicts with an existing event
                slot['available'] = False
                slot['conflicts'].append({
                    'event_id': event.id,
                    'title': event.title,
                    'type': event.event_type,
                    'time': event.start_time.strftime('%H:%M')
                })
    
    # Filter to only available slots
    available_slots = [slot for slot in time_slots if slot['available']]
    
    # Format slots for response
    formatted_slots = [{
        'start_time': slot['start'].strftime('%H:%M'),
        'end_time': slot['end'].strftime('%H:%M'),
        'formatted_time': f"{slot['start'].strftime('%I:%M %p')} - {slot['end'].strftime('%I:%M %p')}",
        'with_buffers': f"{slot['buffer_start'].strftime('%I:%M %p')} - {slot['buffer_end'].strftime('%I:%M %p')}" if buffer_before > 0 or buffer_after > 0 else None
    } for slot in available_slots]
    
    # Special case: court hearings are typically scheduled in the morning
    if is_court_related:
        # Prioritize morning slots for court events (court hearings typically happen in the morning)
        morning_slots = [slot for slot in formatted_slots if datetime.strptime(slot['start_time'], '%H:%M').hour < 12]
        afternoon_slots = [slot for slot in formatted_slots if datetime.strptime(slot['start_time'], '%H:%M').hour >= 12]
        
        # Reorder to show morning slots first, but still include afternoon slots
        formatted_slots = morning_slots + afternoon_slots
    
    return jsonify({
        'available_slots': formatted_slots,
        'date': target_date.strftime('%Y-%m-%d'),
        'total_slots': len(formatted_slots),
        'duration_minutes': duration_minutes,
        'total_time_needed': total_minutes_needed,
        'is_court_related': is_court_related
    })

# Helper functions
def check_conflicts(event):
    """Check if an event has conflicts with existing events and provide detailed conflict info"""
    # Skip conflict check for the same event (in case of edit)
    query = Event.query.filter(
        Event.user_id == current_user.id,
        Event.id != event.id,
        func.date(Event.start_time) == event.start_time.date()
    )
    
    same_day_events = query.all()
    conflicts = []
    conflict_details = []
    
    # Also check for events +/- 1 day if this is a multi-day event or has significant buffer/travel time
    total_time_with_buffers = (event.get_duration_minutes() + 
                              (event.buffer_before or 0) + 
                              (event.buffer_after or 0) + 
                              (event.travel_time_minutes or 0))
    
    # If total time exceeds 12 hours, check adjacent days too
    if total_time_with_buffers > 720:  # 12 hours in minutes
        adjacent_day_events = Event.query.filter(
            Event.user_id == current_user.id,
            Event.id != event.id,
            or_(
                func.date(Event.start_time) == event.start_time.date() - timedelta(days=1),
                func.date(Event.start_time) == event.start_time.date() + timedelta(days=1)
            )
        ).all()
        same_day_events.extend(adjacent_day_events)
    
    for existing_event in same_day_events:
        if event.overlaps_with(existing_event):
            conflicts.append(existing_event)
            
            # Determine conflict severity based on overlap duration
            # Calculate overlap duration
            existing_start = existing_event.start_time - timedelta(minutes=existing_event.buffer_before or 0)
            if existing_event.end_time:
                existing_end = existing_event.end_time + timedelta(minutes=existing_event.buffer_after or 0)
            else:
                existing_end = existing_event.start_time + timedelta(hours=1)
            
            event_start = event.start_time - timedelta(minutes=event.buffer_before or 0)
            if event.end_time:
                event_end = event.end_time + timedelta(minutes=event.buffer_after or 0)
            else:
                event_end = event.start_time + timedelta(hours=1)
            
            # Calculate overlap in minutes
            overlap_start = max(existing_start, event_start)
            overlap_end = min(existing_end, event_end)
            overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
            
            # Determine conflict severity based on overlap and priority
            if overlap_minutes > 30 and (existing_event.priority == 1 or event.priority == 1):
                severity = "critical"
            elif overlap_minutes > 15:
                severity = "significant"
            else:
                severity = "minor"
            
            # Note if both are court-related events (most critical)
            is_double_court = existing_event.is_court_related() and event.is_court_related()
            
            conflict_details.append({
                'event_id': existing_event.id,
                'title': existing_event.title,
                'event_type': existing_event.event_type,
                'start_time': existing_event.start_time.strftime('%H:%M'),
                'end_time': existing_event.end_time.strftime('%H:%M') if existing_event.end_time else None,
                'priority': existing_event.priority,
                'overlap_minutes': int(overlap_minutes),
                'severity': severity,
                'is_double_court': is_double_court
            })
    
    return conflicts, conflict_details if conflict_details else None

def create_recurring_events(base_event):
    """Create recurring instances of an event"""
    if not base_event.is_recurring or not base_event.recurrence_pattern or not base_event.recurrence_end_date:
        return
    
    start_date = base_event.start_time.date()
    end_date = base_event.recurrence_end_date
    
    # Skip the first occurrence (it's the base event)
    current_date = start_date
    
    # Define time deltas for different recurrence patterns
    delta = None
    month_delta = None
    
    if base_event.recurrence_pattern == 'daily':
        delta = timedelta(days=1)
    elif base_event.recurrence_pattern == 'weekly':
        delta = timedelta(weeks=1)
    elif base_event.recurrence_pattern == 'biweekly':
        delta = timedelta(weeks=2)
    elif base_event.recurrence_pattern == 'monthly':
        # Monthly is special - we'll advance by same day each month
        month_delta = 1
    else:
        return  # Unsupported pattern
    
    # Time delta between start and end time
    time_delta = base_event.end_time - base_event.start_time if base_event.end_time else timedelta(hours=1)
    
    # Create recurring instances
    while current_date < end_date:
        if base_event.recurrence_pattern == 'monthly' and month_delta is not None:
            # Monthly recurrence - try to keep the same day of month
            month = current_date.month + month_delta
            year = current_date.year
            
            # Handle year rollover
            while month > 12:
                month -= 12
                year += 1
            
            # Try to create the same day in the next month, handling shorter months
            try:
                current_date = date(year, month, current_date.day)
            except ValueError:
                # If day doesn't exist in this month, use last day of month
                if month == 2 and current_date.day > 28:
                    current_date = date(year, month, 28 if not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 29)
                else:
                    # For other months, use the last day of the month
                    if month in [4, 6, 9, 11] and current_date.day > 30:
                        current_date = date(year, month, 30)
        elif delta is not None:
            # For daily, weekly, biweekly
            current_date += delta
        
        # Skip if we've exceeded the end date
        if current_date > end_date:
            break
        
        # Create a new event instance
        new_start_time = datetime.combine(current_date, base_event.start_time.time())
        new_end_time = new_start_time + time_delta if base_event.end_time else None
        
        new_event = Event(
            title=base_event.title,
            description=base_event.description,
            event_type=base_event.event_type,
            start_time=new_start_time,
            end_time=new_end_time,
            location=base_event.location,
            case_id=base_event.case_id,
            user_id=base_event.user_id,
            priority=base_event.priority,
            is_all_day=base_event.is_all_day,
            is_recurring=False,  # Child events are not recurring themselves
            reminder_time=base_event.reminder_time,
            # Copy advanced scheduling fields
            buffer_before=base_event.buffer_before,
            buffer_after=base_event.buffer_after,
            travel_time_minutes=base_event.travel_time_minutes,
            is_flexible=base_event.is_flexible,
            court_reference_number=base_event.court_reference_number,
            participants=base_event.participants,
            related_event_id=base_event.related_event_id,
            notification_preferences=base_event.notification_preferences
        )
        
        # Check for conflicts
        conflicts, conflict_details = check_conflicts(new_event)
        if conflicts:
            new_event.conflict_status = 'potential'
        
        db.session.add(new_event)
    
    # Commit all new events
    db.session.commit()
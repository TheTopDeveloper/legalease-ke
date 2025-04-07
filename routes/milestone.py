"""
Routes for managing case milestones in the Kenya Legal Assistant system.
This module provides functionality for creating, updating, and displaying case milestones.
"""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError

from app import db
from models import Case, CaseMilestone, Document, Event
from utils.permissions import check_case_access, check_permission

milestone_bp = Blueprint('milestone', __name__)

@milestone_bp.route('/case/<int:case_id>/milestones')
@login_required
def list_milestones(case_id):
    """Display all milestones for a case"""
    case = Case.query.get_or_404(case_id)
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        flash('You do not have permission to view this case', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get all milestones ordered by order_index
    milestones = CaseMilestone.query.filter_by(case_id=case_id).order_by(CaseMilestone.order_index).all()
    
    return render_template('case/milestones.html', 
                           case=case, 
                           milestones=milestones,
                           title=f"Milestones for {case.title}")

@milestone_bp.route('/case/<int:case_id>/milestones/new', methods=['GET', 'POST'])
@login_required
def create_milestone(case_id):
    """Create a new milestone for a case"""
    case = Case.query.get_or_404(case_id)
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        flash('You do not have permission to modify this case', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        milestone_type = request.form.get('milestone_type', '').strip()
        status = request.form.get('status', 'pending')
        order_index = request.form.get('order_index', 0)
        is_critical = bool(request.form.get('is_critical'))
        event_id = request.form.get('event_id')
        document_id = request.form.get('document_id')
        
        target_date = None
        if request.form.get('target_date'):
            try:
                target_date = datetime.strptime(request.form.get('target_date'), '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for target date', 'danger')
        
        if not title:
            flash('Milestone title is required', 'danger')
            return redirect(url_for('milestone.create_milestone', case_id=case_id))
        
        try:
            # Create new milestone
            milestone = CaseMilestone(
                title=title,
                description=description,
                milestone_type=milestone_type,
                status=status,
                order_index=order_index,
                target_date=target_date,
                is_critical=is_critical,
                case_id=case_id
            )
            
            # Add event association if provided
            if event_id:
                event = Event.query.get(event_id)
                if event and event.case_id == case_id:
                    milestone.event_id = event_id
            
            # Add document association if provided
            if document_id:
                document = Document.query.get(document_id)
                # Check if document is associated with the case
                if document:
                    milestone.document_id = document_id
            
            db.session.add(milestone)
            db.session.commit()
            
            flash('Milestone added successfully', 'success')
            return redirect(url_for('milestone.list_milestones', case_id=case_id))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error adding milestone: {str(e)}', 'danger')
    
    # For GET request or form errors
    events = Event.query.filter_by(case_id=case_id).all()
    documents = Document.query.join(Document.cases).filter(Case.id == case_id).all()
    milestone_types = ['Filing', 'Hearing', 'Mention', 'Decision', 'Pleadings', 'Evidence', 'Appeal']
    status_options = ['pending', 'in_progress', 'completed', 'delayed']
    
    return render_template('case/create_milestone.html', 
                           case=case,
                           events=events,
                           documents=documents,
                           milestone_types=milestone_types,
                           status_options=status_options,
                           title="Add New Milestone")

@milestone_bp.route('/case/<int:case_id>/milestones/<int:milestone_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_milestone(case_id, milestone_id):
    """Edit an existing milestone"""
    case = Case.query.get_or_404(case_id)
    milestone = CaseMilestone.query.get_or_404(milestone_id)
    
    # Check if milestone belongs to the case
    if milestone.case_id != case_id:
        flash('Milestone does not belong to this case', 'danger')
        return redirect(url_for('milestone.list_milestones', case_id=case_id))
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        flash('You do not have permission to modify this case', 'danger')
        return redirect(url_for('dashboard.index'))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        milestone_type = request.form.get('milestone_type', '').strip()
        status = request.form.get('status', 'pending')
        order_index = request.form.get('order_index', 0)
        is_critical = bool(request.form.get('is_critical'))
        event_id = request.form.get('event_id')
        document_id = request.form.get('document_id')
        
        target_date = None
        if request.form.get('target_date'):
            try:
                target_date = datetime.strptime(request.form.get('target_date'), '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for target date', 'danger')
        
        completion_date = None
        if request.form.get('completion_date'):
            try:
                completion_date = datetime.strptime(request.form.get('completion_date'), '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for completion date', 'danger')
        
        if not title:
            flash('Milestone title is required', 'danger')
            return redirect(url_for('milestone.edit_milestone', case_id=case_id, milestone_id=milestone_id))
        
        try:
            # Update milestone
            milestone.title = title
            milestone.description = description
            milestone.milestone_type = milestone_type
            milestone.status = status
            milestone.order_index = order_index
            milestone.target_date = target_date
            milestone.completion_date = completion_date
            milestone.is_critical = is_critical
            
            # Update event association if provided
            if event_id:
                event = Event.query.get(event_id)
                if event and event.case_id == case_id:
                    milestone.event_id = event_id
            else:
                milestone.event_id = None
            
            # Update document association if provided
            if document_id:
                document = Document.query.get(document_id)
                if document:
                    milestone.document_id = document_id
            else:
                milestone.document_id = None
            
            db.session.commit()
            
            flash('Milestone updated successfully', 'success')
            return redirect(url_for('milestone.list_milestones', case_id=case_id))
        
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating milestone: {str(e)}', 'danger')
    
    # For GET request or form errors
    events = Event.query.filter_by(case_id=case_id).all()
    documents = Document.query.join(Document.cases).filter(Case.id == case_id).all()
    milestone_types = ['Filing', 'Hearing', 'Mention', 'Decision', 'Pleadings', 'Evidence', 'Appeal']
    status_options = ['pending', 'in_progress', 'completed', 'delayed']
    
    return render_template('case/edit_milestone.html', 
                           case=case,
                           milestone=milestone,
                           events=events,
                           documents=documents,
                           milestone_types=milestone_types,
                           status_options=status_options,
                           title="Edit Milestone")

@milestone_bp.route('/case/<int:case_id>/milestones/<int:milestone_id>/delete', methods=['POST'])
@login_required
def delete_milestone(case_id, milestone_id):
    """Delete a milestone"""
    case = Case.query.get_or_404(case_id)
    milestone = CaseMilestone.query.get_or_404(milestone_id)
    
    # Check if milestone belongs to the case
    if milestone.case_id != case_id:
        flash('Milestone does not belong to this case', 'danger')
        return redirect(url_for('milestone.list_milestones', case_id=case_id))
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        flash('You do not have permission to modify this case', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        db.session.delete(milestone)
        db.session.commit()
        flash('Milestone deleted successfully', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error deleting milestone: {str(e)}', 'danger')
    
    return redirect(url_for('milestone.list_milestones', case_id=case_id))

@milestone_bp.route('/case/<int:case_id>/milestones/<int:milestone_id>/complete', methods=['POST'])
@login_required
def complete_milestone(case_id, milestone_id):
    """Mark a milestone as completed"""
    case = Case.query.get_or_404(case_id)
    milestone = CaseMilestone.query.get_or_404(milestone_id)
    
    # Check if milestone belongs to the case
    if milestone.case_id != case_id:
        flash('Milestone does not belong to this case', 'danger')
        return redirect(url_for('milestone.list_milestones', case_id=case_id))
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        flash('You do not have permission to modify this case', 'danger')
        return redirect(url_for('dashboard.index'))
    
    try:
        milestone.status = 'completed'
        milestone.completion_date = datetime.utcnow()
        db.session.commit()
        flash('Milestone marked as completed', 'success')
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f'Error updating milestone: {str(e)}', 'danger')
    
    return redirect(url_for('milestone.list_milestones', case_id=case_id))

@milestone_bp.route('/case/<int:case_id>/milestones/reorder', methods=['POST'])
@login_required
def reorder_milestones(case_id):
    """Update the order of milestones"""
    case = Case.query.get_or_404(case_id)
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        return jsonify({"success": False, "message": "Permission denied"}), 403
    
    try:
        milestone_order = request.json.get('milestone_order', [])
        
        for index, milestone_id in enumerate(milestone_order):
            milestone = CaseMilestone.query.get(milestone_id)
            if milestone and milestone.case_id == case_id:
                milestone.order_index = index
        
        db.session.commit()
        return jsonify({"success": True})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "message": str(e)}), 500

@milestone_bp.route('/case/<int:case_id>/timeline')
@login_required
def case_timeline(case_id):
    """Display an interactive timeline of case milestones"""
    case = Case.query.get_or_404(case_id)
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        flash('You do not have permission to view this case', 'danger')
        return redirect(url_for('dashboard.index'))
    
    # Get all milestones ordered by order_index
    milestones = CaseMilestone.query.filter_by(case_id=case_id).order_by(CaseMilestone.order_index).all()
    
    # Get all events for this case
    events = Event.query.filter_by(case_id=case_id).order_by(Event.start_time).all()
    
    return render_template('case/timeline.html', 
                           case=case, 
                           milestones=milestones,
                           events=events,
                           title=f"Timeline for {case.title}")

@milestone_bp.route('/api/case/<int:case_id>/milestone_stats')
@login_required
def milestone_stats(case_id):
    """Return milestone statistics for a case in JSON format"""
    case = Case.query.get_or_404(case_id)
    
    # Check if user has access to this case
    if not check_case_access(case, current_user):
        return jsonify({"error": "Permission denied"}), 403
    
    # Get milestone data
    milestones = CaseMilestone.query.filter_by(case_id=case_id).all()
    
    # Calculate statistics
    total_count = len(milestones)
    completed_count = sum(1 for m in milestones if m.status == 'completed')
    in_progress_count = sum(1 for m in milestones if m.status == 'in_progress')
    pending_count = sum(1 for m in milestones if m.status == 'pending')
    delayed_count = sum(1 for m in milestones if m.is_delayed())
    critical_count = sum(1 for m in milestones if m.is_critical)
    
    # Prepare milestone data for timeline
    timeline_data = []
    for milestone in milestones:
        milestone_data = {
            'id': milestone.id,
            'title': milestone.title,
            'type': milestone.milestone_type,
            'status': milestone.status,
            'target_date': milestone.target_date.isoformat() if milestone.target_date else None,
            'completion_date': milestone.completion_date.isoformat() if milestone.completion_date else None,
            'is_critical': milestone.is_critical,
            'is_delayed': milestone.is_delayed(),
            'days_remaining': milestone.days_remaining(),
            'order_index': milestone.order_index
        }
        timeline_data.append(milestone_data)
    
    return jsonify({
        'total_count': total_count,
        'completed_count': completed_count,
        'in_progress_count': in_progress_count,
        'pending_count': pending_count,
        'delayed_count': delayed_count,
        'critical_count': critical_count,
        'timeline_data': timeline_data,
        'completion_percentage': round((completed_count / total_count) * 100) if total_count > 0 else 0
    })
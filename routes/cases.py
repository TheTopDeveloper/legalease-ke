import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import Case, Client, Document, Event, db
import config

logger = logging.getLogger(__name__)

# Create cases blueprint
cases_bp = Blueprint('cases', __name__, url_prefix='/cases')

@cases_bp.route('/')
@login_required
def index():
    """List all cases"""
    cases = Case.query.filter_by(user_id=current_user.id).order_by(Case.created_at.desc()).all()
    return render_template('cases/index.html', cases=cases)

@cases_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new case"""
    if request.method == 'POST':
        title = request.form.get('title')
        case_number = request.form.get('case_number')
        description = request.form.get('description')
        court_level = request.form.get('court_level')
        case_type = request.form.get('case_type')
        practice_area = request.form.get('practice_area')
        filing_date_str = request.form.get('filing_date')
        status = request.form.get('status')
        court_stage = request.form.get('court_stage')
        
        # Validate form data
        if not title or not case_number or not court_level:
            flash('Title, case number, and court level are required', 'error')
            return render_template('cases/create.html', 
                                  court_levels=config.COURT_LEVELS,
                                  case_types=config.CASE_TYPES,
                                  practice_areas=config.PRACTICE_AREAS)
        
        # Parse filing date
        filing_date = None
        if filing_date_str:
            try:
                filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid filing date format', 'error')
                return render_template('cases/create.html',
                                      court_levels=config.COURT_LEVELS,
                                      case_types=config.CASE_TYPES,
                                      practice_areas=config.PRACTICE_AREAS)
        
        # Create new case
        new_case = Case(
            title=title,
            case_number=case_number,
            description=description,
            court_level=court_level,
            case_type=case_type,
            practice_area=practice_area,
            filing_date=filing_date,
            status=status,
            court_stage=court_stage,
            user_id=current_user.id
        )
        
        # Add clients if selected
        client_ids = request.form.getlist('clients')
        if client_ids:
            clients = Client.query.filter(Client.id.in_(client_ids)).all()
            new_case.clients.extend(clients)
        
        # Save to database
        db.session.add(new_case)
        try:
            db.session.commit()
            logger.info(f"Created new case: {new_case.title} ({new_case.case_number})")
            flash('Case created successfully', 'success')
            return redirect(url_for('cases.view', case_id=new_case.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating case: {str(e)}")
            flash(f'Error creating case: {str(e)}', 'error')
    
    # Get clients for selection
    clients = Client.query.all()
    
    return render_template('cases/create.html',
                          court_levels=config.COURT_LEVELS,
                          case_types=config.CASE_TYPES,
                          practice_areas=config.PRACTICE_AREAS,
                          clients=clients)

@cases_bp.route('/<int:case_id>')
@login_required
def view(case_id):
    """View a specific case"""
    case = Case.query.get_or_404(case_id)
    
    # Check permission
    if case.user_id != current_user.id:
        flash('You do not have permission to view this case', 'error')
        return redirect(url_for('cases.index'))
    
    # Get associated documents
    documents = case.documents
    
    # Get upcoming events
    events = Event.query.filter_by(case_id=case_id).order_by(Event.start_time).all()
    
    # Get case milestones
    from models import CaseMilestone
    milestones = CaseMilestone.query.filter_by(case_id=case_id).order_by(CaseMilestone.order_index).all()
    
    return render_template('cases/view.html', case=case, documents=documents, events=events, milestones=milestones)

@cases_bp.route('/<int:case_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(case_id):
    """Edit a case"""
    case = Case.query.get_or_404(case_id)
    
    # Check permission
    if case.user_id != current_user.id:
        flash('You do not have permission to edit this case', 'error')
        return redirect(url_for('cases.index'))
    
    if request.method == 'POST':
        case.title = request.form.get('title')
        case.case_number = request.form.get('case_number')
        case.description = request.form.get('description')
        case.court_level = request.form.get('court_level')
        case.case_type = request.form.get('case_type')
        case.practice_area = request.form.get('practice_area')
        case.status = request.form.get('status')
        case.court_stage = request.form.get('court_stage')
        
        # Handle outcome for closed cases
        if case.status == 'Closed':
            case.outcome = request.form.get('outcome')
            closing_date_str = request.form.get('closing_date')
            if closing_date_str:
                try:
                    case.closing_date = datetime.strptime(closing_date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Invalid closing date format', 'error')
                    return render_template('cases/edit.html', 
                                         case=case,
                                         court_levels=config.COURT_LEVELS,
                                         case_types=config.CASE_TYPES,
                                         practice_areas=config.PRACTICE_AREAS)
        
        filing_date_str = request.form.get('filing_date')
        if filing_date_str:
            try:
                case.filing_date = datetime.strptime(filing_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid filing date format', 'error')
                return render_template('cases/edit.html', 
                                     case=case,
                                     court_levels=config.COURT_LEVELS,
                                     case_types=config.CASE_TYPES,
                                     practice_areas=config.PRACTICE_AREAS)
        
        # Update clients
        client_ids = request.form.getlist('clients')
        if client_ids:
            clients = Client.query.filter(Client.id.in_(client_ids)).all()
            case.clients = clients
        else:
            case.clients = []
        
        # Save changes
        case.updated_at = datetime.utcnow()
        try:
            db.session.commit()
            logger.info(f"Updated case: {case.title} ({case.case_number})")
            flash('Case updated successfully', 'success')
            return redirect(url_for('cases.view', case_id=case.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating case: {str(e)}")
            flash(f'Error updating case: {str(e)}', 'error')
    
    # Get clients for selection
    clients = Client.query.all()
    case_client_ids = [client.id for client in case.clients]
    
    return render_template('cases/edit.html', 
                          case=case, 
                          court_levels=config.COURT_LEVELS,
                          case_types=config.CASE_TYPES,
                          practice_areas=config.PRACTICE_AREAS,
                          clients=clients,
                          case_client_ids=case_client_ids)

@cases_bp.route('/<int:case_id>/delete', methods=['POST'])
@login_required
def delete(case_id):
    """Delete a case"""
    case = Case.query.get_or_404(case_id)
    
    # Check permission
    if case.user_id != current_user.id:
        flash('You do not have permission to delete this case', 'error')
        return redirect(url_for('cases.index'))
    
    try:
        db.session.delete(case)
        db.session.commit()
        logger.info(f"Deleted case: {case.title} ({case.case_number})")
        flash('Case deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting case: {str(e)}")
        flash(f'Error deleting case: {str(e)}', 'error')
    
    return redirect(url_for('cases.index'))

@cases_bp.route('/<int:case_id>/add_document', methods=['GET', 'POST'])
@login_required
def add_document(case_id):
    """Add a document to a case"""
    case = Case.query.get_or_404(case_id)
    
    # Check permission
    if case.user_id != current_user.id:
        flash('You do not have permission to add documents to this case', 'error')
        return redirect(url_for('cases.index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        document_type = request.form.get('document_type')
        content = request.form.get('content')
        status = request.form.get('status', 'Draft')
        
        # Validate form data
        if not title or not document_type:
            flash('Title and document type are required', 'error')
            return render_template('cases/add_document.html', 
                                  case=case, 
                                  document_types=config.DOCUMENT_TYPES)
        
        # Create new document
        new_document = Document(
            title=title,
            document_type=document_type,
            content=content,
            status=status,
            user_id=current_user.id
        )
        
        # Associate with case
        new_document.cases.append(case)
        
        # Save to database
        db.session.add(new_document)
        try:
            db.session.commit()
            logger.info(f"Added document {new_document.title} to case {case.title}")
            flash('Document added successfully', 'success')
            return redirect(url_for('cases.view', case_id=case.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding document: {str(e)}")
            flash(f'Error adding document: {str(e)}', 'error')
    
    return render_template('cases/add_document.html', 
                          case=case, 
                          document_types=config.DOCUMENT_TYPES)

@cases_bp.route('/<int:case_id>/add_event', methods=['GET', 'POST'])
@login_required
def add_event(case_id):
    """Add an event to a case"""
    case = Case.query.get_or_404(case_id)
    
    # Check permission
    if case.user_id != current_user.id:
        flash('You do not have permission to add events to this case', 'error')
        return redirect(url_for('cases.index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        event_type = request.form.get('event_type')
        start_time_str = request.form.get('start_time')
        end_time_str = request.form.get('end_time')
        location = request.form.get('location')
        
        # Validate form data
        if not title or not event_type or not start_time_str:
            flash('Title, event type, and start time are required', 'error')
            return render_template('cases/add_event.html', case=case)
        
        # Parse dates
        try:
            start_time = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
            end_time = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M') if end_time_str else None
        except ValueError:
            flash('Invalid date format', 'error')
            return render_template('cases/add_event.html', case=case)
        
        # Create new event
        new_event = Event(
            title=title,
            description=description,
            event_type=event_type,
            start_time=start_time,
            end_time=end_time,
            location=location,
            case_id=case.id,
            user_id=current_user.id
        )
        
        # Save to database
        db.session.add(new_event)
        try:
            db.session.commit()
            logger.info(f"Added event {new_event.title} to case {case.title}")
            
            # If this is a court date, update the case's next court date
            if event_type in ['Court Appearance', 'Hearing', 'Mention']:
                case.next_court_date = start_time
                db.session.commit()
            
            flash('Event added successfully', 'success')
            return redirect(url_for('cases.view', case_id=case.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding event: {str(e)}")
            flash(f'Error adding event: {str(e)}', 'error')
    
    return render_template('cases/add_event.html', case=case)

@cases_bp.route('/clients', methods=['GET', 'POST'])
@login_required
def clients():
    """Manage clients"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        client_type = request.form.get('client_type')
        
        # Validate form data
        if not name:
            flash('Client name is required', 'error')
            return redirect(url_for('cases.clients'))
        
        # Create new client
        new_client = Client(
            name=name,
            email=email,
            phone=phone,
            address=address,
            client_type=client_type
        )
        
        # Save to database
        db.session.add(new_client)
        try:
            db.session.commit()
            logger.info(f"Created new client: {new_client.name}")
            flash('Client created successfully', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating client: {str(e)}")
            flash(f'Error creating client: {str(e)}', 'error')
    
    # Get all clients
    clients = Client.query.order_by(Client.name).all()
    
    return render_template('cases/clients.html', clients=clients)

@cases_bp.route('/clients/<int:client_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_client(client_id):
    """Edit a client"""
    client = Client.query.get_or_404(client_id)
    
    if request.method == 'POST':
        client.name = request.form.get('name')
        client.email = request.form.get('email')
        client.phone = request.form.get('phone')
        client.address = request.form.get('address')
        client.client_type = request.form.get('client_type')
        
        # Save changes
        try:
            db.session.commit()
            logger.info(f"Updated client: {client.name}")
            flash('Client updated successfully', 'success')
            return redirect(url_for('cases.clients'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating client: {str(e)}")
            flash(f'Error updating client: {str(e)}', 'error')
    
    return render_template('cases/edit_client.html', client=client)

@cases_bp.route('/clients/<int:client_id>/delete', methods=['POST'])
@login_required
def delete_client(client_id):
    """Delete a client"""
    client = Client.query.get_or_404(client_id)
    
    try:
        # Note: This will not delete associated cases, just remove the association
        db.session.delete(client)
        db.session.commit()
        logger.info(f"Deleted client: {client.name}")
        flash('Client deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting client: {str(e)}")
        flash(f'Error deleting client: {str(e)}', 'error')
    
    return redirect(url_for('cases.clients'))

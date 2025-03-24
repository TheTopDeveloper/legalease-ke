import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import Document, Case, db
from utils.document_generator import DocumentGenerator
import config

logger = logging.getLogger(__name__)

# Create documents blueprint
documents_bp = Blueprint('documents', __name__, url_prefix='/documents')

@documents_bp.route('/')
@login_required
def index():
    """List all documents"""
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.created_at.desc()).all()
    return render_template('documents/index.html', documents=documents)

@documents_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new document"""
    if request.method == 'POST':
        title = request.form.get('title')
        document_type = request.form.get('document_type')
        content = request.form.get('content')
        status = request.form.get('status', 'Draft')
        
        # Validate form data
        if not title or not document_type:
            flash('Title and document type are required', 'error')
            return render_template('documents/create.html', document_types=config.DOCUMENT_TYPES)
        
        # Create new document
        new_document = Document(
            title=title,
            document_type=document_type,
            content=content,
            status=status,
            user_id=current_user.id
        )
        
        # Associate with case if selected
        case_id = request.form.get('case_id')
        if case_id:
            case = Case.query.get(case_id)
            if case and case.user_id == current_user.id:
                new_document.cases.append(case)
        
        # Save to database
        db.session.add(new_document)
        try:
            db.session.commit()
            logger.info(f"Created new document: {new_document.title}")
            flash('Document created successfully', 'success')
            return redirect(url_for('documents.view', document_id=new_document.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating document: {str(e)}")
            flash(f'Error creating document: {str(e)}', 'error')
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Check if we're creating a document for a specific case
    case_id = request.args.get('case_id')
    selected_case = None
    if case_id:
        selected_case = Case.query.get(case_id)
    
    return render_template('documents/create.html', 
                          document_types=config.DOCUMENT_TYPES,
                          cases=cases,
                          selected_case=selected_case)

@documents_bp.route('/<int:document_id>')
@login_required
def view(document_id):
    """View a specific document"""
    document = Document.query.get_or_404(document_id)
    
    # Check permission
    if document.user_id != current_user.id:
        flash('You do not have permission to view this document', 'error')
        return redirect(url_for('documents.index'))
    
    return render_template('documents/view.html', document=document)

@documents_bp.route('/<int:document_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(document_id):
    """Edit a document"""
    document = Document.query.get_or_404(document_id)
    
    # Check permission
    if document.user_id != current_user.id:
        flash('You do not have permission to edit this document', 'error')
        return redirect(url_for('documents.index'))
    
    if request.method == 'POST':
        document.title = request.form.get('title')
        document.document_type = request.form.get('document_type')
        document.content = request.form.get('content')
        document.status = request.form.get('status')
        
        # Update version
        document.version += 1
        
        # Save changes
        try:
            db.session.commit()
            logger.info(f"Updated document: {document.title} (version {document.version})")
            flash('Document updated successfully', 'success')
            return redirect(url_for('documents.view', document_id=document.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating document: {str(e)}")
            flash(f'Error updating document: {str(e)}', 'error')
    
    return render_template('documents/edit.html', 
                          document=document, 
                          document_types=config.DOCUMENT_TYPES)

@documents_bp.route('/<int:document_id>/delete', methods=['POST'])
@login_required
def delete(document_id):
    """Delete a document"""
    document = Document.query.get_or_404(document_id)
    
    # Check permission
    if document.user_id != current_user.id:
        flash('You do not have permission to delete this document', 'error')
        return redirect(url_for('documents.index'))
    
    try:
        db.session.delete(document)
        db.session.commit()
        logger.info(f"Deleted document: {document.title}")
        flash('Document deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting document: {str(e)}")
        flash(f'Error deleting document: {str(e)}', 'error')
    
    return redirect(url_for('documents.index'))

@documents_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    """Generate a document using templates"""
    if request.method == 'POST':
        template_type = request.form.get('template_type')
        
        # Get document generator
        document_generator = DocumentGenerator()
        
        # Generate document based on template type
        if template_type == 'pleading':
            case_info = {
                'court_level': request.form.get('court_level'),
                'court_location': request.form.get('court_location'),
                'case_type': request.form.get('case_type'),
                'case_number': request.form.get('case_number'),
                'plaintiff': request.form.get('plaintiff'),
                'defendant': request.form.get('defendant')
            }
            
            document_info = {
                'title': request.form.get('document_title'),
                'content': request.form.get('document_content'),
                'city': request.form.get('city'),
                'party': request.form.get('party'),
                'law_firm': request.form.get('law_firm'),
                'address': request.form.get('address'),
                'contact_info': request.form.get('contact_info')
            }
            
            document_content = document_generator.generate_pleading(case_info, document_info)
            document_title = request.form.get('document_title')
            document_type = 'Pleadings'
            
        elif template_type == 'contract':
            contract_info = {
                'title': request.form.get('contract_title'),
                'party1_name': request.form.get('party1_name'),
                'party1_address': request.form.get('party1_address'),
                'party1_reference': request.form.get('party1_reference'),
                'party2_name': request.form.get('party2_name'),
                'party2_address': request.form.get('party2_address'),
                'party2_reference': request.form.get('party2_reference'),
                'recitals': request.form.get('recitals'),
                'contract_clauses': request.form.get('contract_clauses')
            }
            
            document_content = document_generator.generate_contract(contract_info)
            document_title = request.form.get('contract_title')
            document_type = 'Contracts'
            
        elif template_type == 'legal_opinion':
            opinion_info = {
                'law_firm_letterhead': request.form.get('law_firm_letterhead'),
                'client_name': request.form.get('client_name'),
                'client_address': request.form.get('client_address'),
                'client_salutation': request.form.get('client_salutation'),
                'subject': request.form.get('opinion_subject'),
                'reference_date': request.form.get('reference_date'),
                'background': request.form.get('background'),
                'issues': request.form.get('issues'),
                'applicable_law': request.form.get('applicable_law'),
                'analysis': request.form.get('analysis'),
                'opinion': request.form.get('opinion'),
                'lawyer_name': request.form.get('lawyer_name'),
                'lawyer_title': request.form.get('lawyer_title'),
                'law_firm': request.form.get('law_firm')
            }
            
            document_content = document_generator.generate_legal_opinion(opinion_info)
            document_title = f"Legal Opinion - {request.form.get('opinion_subject')}"
            document_type = 'Legal Opinions'
            
        elif template_type == 'ai_document':
            doc_type = request.form.get('ai_document_type')
            instructions = request.form.get('ai_instructions')
            context = {
                'case_info': request.form.get('ai_case_info'),
                'client_info': request.form.get('ai_client_info'),
                'additional_context': request.form.get('ai_additional_context')
            }
            
            document_content = document_generator.generate_ai_document(doc_type, instructions, context)
            document_title = f"{doc_type} - AI Generated"
            document_type = doc_type
            
        else:
            flash('Invalid template type', 'error')
            return redirect(url_for('documents.generate'))
        
        # Create new document
        new_document = Document(
            title=document_title,
            document_type=document_type,
            content=document_content,
            status='Draft',
            user_id=current_user.id
        )
        
        # Associate with case if selected
        case_id = request.form.get('case_id')
        if case_id:
            case = Case.query.get(case_id)
            if case and case.user_id == current_user.id:
                new_document.cases.append(case)
        
        # Save to database
        db.session.add(new_document)
        try:
            db.session.commit()
            logger.info(f"Generated document: {new_document.title}")
            flash('Document generated successfully', 'success')
            return redirect(url_for('documents.view', document_id=new_document.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving generated document: {str(e)}")
            flash(f'Error saving document: {str(e)}', 'error')
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    return render_template('documents/generate.html', 
                          court_levels=config.COURT_LEVELS,
                          document_types=config.DOCUMENT_TYPES,
                          cases=cases)

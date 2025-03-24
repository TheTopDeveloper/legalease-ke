import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import Contract, Client, db
from utils.document_generator import DocumentGenerator
import config
from datetime import datetime

logger = logging.getLogger(__name__)

# Create contracts blueprint
contracts_bp = Blueprint('contracts', __name__, url_prefix='/contracts')

@contracts_bp.route('/')
@login_required
def index():
    """List all contracts"""
    contracts = Contract.query.filter_by(user_id=current_user.id).order_by(Contract.created_at.desc()).all()
    return render_template('contracts/index.html', contracts=contracts)

@contracts_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new contract"""
    if request.method == 'POST':
        title = request.form.get('title')
        contract_type = request.form.get('contract_type')
        client_id = request.form.get('client_id')
        content = request.form.get('content')
        status = request.form.get('status', 'Draft')
        key_terms = request.form.get('key_terms')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        # Validate form data
        if not title or not contract_type:
            flash('Title and contract type are required', 'error')
            return render_template('contracts/create.html', 
                                  contract_types=config.CONTRACT_TYPES)
        
        # Parse dates
        start_date = None
        end_date = None
        
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format', 'error')
                return render_template('contracts/create.html',
                                      contract_types=config.CONTRACT_TYPES)
        
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid end date format', 'error')
                return render_template('contracts/create.html',
                                      contract_types=config.CONTRACT_TYPES)
        
        # Get client
        client = None
        if client_id:
            client = Client.query.get(client_id)
        
        # Create new contract
        new_contract = Contract(
            title=title,
            contract_type=contract_type,
            content=content,
            status=status,
            start_date=start_date,
            end_date=end_date,
            key_terms=key_terms,
            user_id=current_user.id,
            client_id=client.id if client else None
        )
        
        # Save to database
        db.session.add(new_contract)
        try:
            db.session.commit()
            logger.info(f"Created new contract: {new_contract.title}")
            flash('Contract created successfully', 'success')
            return redirect(url_for('contracts.view', contract_id=new_contract.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating contract: {str(e)}")
            flash(f'Error creating contract: {str(e)}', 'error')
    
    # Get clients for selection
    clients = Client.query.all()
    
    return render_template('contracts/create.html',
                          contract_types=config.CONTRACT_TYPES,
                          clients=clients)

@contracts_bp.route('/<int:contract_id>')
@login_required
def view(contract_id):
    """View a specific contract"""
    contract = Contract.query.get_or_404(contract_id)
    
    # Check permission
    if contract.user_id != current_user.id:
        flash('You do not have permission to view this contract', 'error')
        return redirect(url_for('contracts.index'))
    
    return render_template('contracts/view.html', contract=contract)

@contracts_bp.route('/<int:contract_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(contract_id):
    """Edit a contract"""
    contract = Contract.query.get_or_404(contract_id)
    
    # Check permission
    if contract.user_id != current_user.id:
        flash('You do not have permission to edit this contract', 'error')
        return redirect(url_for('contracts.index'))
    
    if request.method == 'POST':
        contract.title = request.form.get('title')
        contract.contract_type = request.form.get('contract_type')
        contract.content = request.form.get('content')
        contract.status = request.form.get('status')
        contract.key_terms = request.form.get('key_terms')
        
        client_id = request.form.get('client_id')
        if client_id:
            client = Client.query.get(client_id)
            if client:
                contract.client_id = client.id
        else:
            contract.client_id = None
        
        # Parse dates
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        
        if start_date_str:
            try:
                contract.start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid start date format', 'error')
                return render_template('contracts/edit.html',
                                      contract=contract,
                                      contract_types=config.CONTRACT_TYPES)
        else:
            contract.start_date = None
        
        if end_date_str:
            try:
                contract.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid end date format', 'error')
                return render_template('contracts/edit.html',
                                      contract=contract,
                                      contract_types=config.CONTRACT_TYPES)
        else:
            contract.end_date = None
        
        # Save changes
        try:
            db.session.commit()
            logger.info(f"Updated contract: {contract.title}")
            flash('Contract updated successfully', 'success')
            return redirect(url_for('contracts.view', contract_id=contract.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating contract: {str(e)}")
            flash(f'Error updating contract: {str(e)}', 'error')
    
    # Get clients for selection
    clients = Client.query.all()
    
    return render_template('contracts/edit.html',
                          contract=contract,
                          contract_types=config.CONTRACT_TYPES,
                          clients=clients)

@contracts_bp.route('/<int:contract_id>/delete', methods=['POST'])
@login_required
def delete(contract_id):
    """Delete a contract"""
    contract = Contract.query.get_or_404(contract_id)
    
    # Check permission
    if contract.user_id != current_user.id:
        flash('You do not have permission to delete this contract', 'error')
        return redirect(url_for('contracts.index'))
    
    try:
        db.session.delete(contract)
        db.session.commit()
        logger.info(f"Deleted contract: {contract.title}")
        flash('Contract deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting contract: {str(e)}")
        flash(f'Error deleting contract: {str(e)}', 'error')
    
    return redirect(url_for('contracts.index'))

@contracts_bp.route('/generate', methods=['GET', 'POST'])
@login_required
def generate():
    """Generate a contract using AI or templates"""
    if request.method == 'POST':
        generation_method = request.form.get('generation_method')
        
        if generation_method == 'template':
            # Using template-based generation
            contract_title = request.form.get('contract_title')
            contract_type = request.form.get('contract_type')
            party1_name = request.form.get('party1_name')
            party1_address = request.form.get('party1_address')
            party1_reference = request.form.get('party1_reference')
            party2_name = request.form.get('party2_name')
            party2_address = request.form.get('party2_address')
            party2_reference = request.form.get('party2_reference')
            recitals = request.form.get('recitals')
            contract_clauses = request.form.get('contract_clauses')
            
            # Validate required fields
            if not contract_title or not party1_name or not party2_name:
                flash('Contract title, first party, and second party are required', 'error')
                return redirect(url_for('contracts.generate'))
            
            # Generate contract using template
            document_generator = DocumentGenerator()
            contract_content = document_generator.generate_contract({
                'title': contract_title,
                'party1_name': party1_name,
                'party1_address': party1_address,
                'party1_reference': party1_reference or 'First Party',
                'party2_name': party2_name,
                'party2_address': party2_address,
                'party2_reference': party2_reference or 'Second Party',
                'recitals': recitals,
                'contract_clauses': contract_clauses
            })
            
        else:
            # Using AI-based generation
            contract_type = request.form.get('ai_contract_type')
            contract_title = request.form.get('ai_contract_title')
            contract_purpose = request.form.get('ai_contract_purpose')
            parties_info = request.form.get('ai_parties_info')
            key_terms = request.form.get('ai_key_terms')
            special_clauses = request.form.get('ai_special_clauses')
            
            # Validate required fields
            if not contract_type or not contract_title or not contract_purpose:
                flash('Contract type, title, and purpose are required', 'error')
                return redirect(url_for('contracts.generate'))
            
            # Generate contract using AI
            document_generator = DocumentGenerator()
            instructions = f"""
            Create a {contract_type} contract titled "{contract_title}".
            
            Purpose of the contract: {contract_purpose}
            
            Information about the parties: {parties_info}
            
            Include these key terms: {key_terms}
            
            Include these special clauses: {special_clauses}
            
            The contract should follow Kenyan contract law standards and be legally sound.
            """
            
            contract_content = document_generator.generate_ai_document(
                contract_type, 
                instructions, 
                {
                    'contract_type': contract_type,
                    'title': contract_title,
                    'purpose': contract_purpose
                }
            )
        
        # Create new contract
        client_id = request.form.get('client_id')
        client = Client.query.get(client_id) if client_id else None
        
        new_contract = Contract(
            title=contract_title,
            contract_type=contract_type,
            content=contract_content,
            status='Draft',
            key_terms=key_terms if generation_method == 'ai' else '',
            user_id=current_user.id,
            client_id=client.id if client else None
        )
        
        # Save to database
        db.session.add(new_contract)
        try:
            db.session.commit()
            logger.info(f"Generated contract: {new_contract.title}")
            flash('Contract generated successfully', 'success')
            return redirect(url_for('contracts.view', contract_id=new_contract.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving generated contract: {str(e)}")
            flash(f'Error saving contract: {str(e)}', 'error')
    
    # Get clients for selection
    clients = Client.query.all()
    
    return render_template('contracts/generate.html',
                          contract_types=config.CONTRACT_TYPES,
                          clients=clients)

@contracts_bp.route('/analyze', methods=['GET', 'POST'])
@login_required
def analyze():
    """Analyze a contract with AI"""
    if request.method == 'POST':
        contract_id = request.form.get('contract_id')
        contract_text = request.form.get('contract_text')
        
        if not contract_id and not contract_text:
            flash('Either select a contract or paste contract text for analysis', 'error')
            return redirect(url_for('contracts.analyze'))
        
        # Get contract text
        if contract_id:
            contract = Contract.query.get(contract_id)
            if not contract or contract.user_id != current_user.id:
                flash('Invalid contract selection', 'error')
                return redirect(url_for('contracts.analyze'))
            contract_text = contract.content
        
        # Initialize research assistant for analysis
        from utils.research_assistant import LegalResearchAssistant
        research_assistant = LegalResearchAssistant()
        
        # Analyze contract
        analysis_results = research_assistant.analyze_legal_document(contract_text)
        
        return render_template('contracts/analyze_results.html', 
                             analysis=analysis_results,
                             contract_text=contract_text)
    
    # Get contracts for selection
    contracts = Contract.query.filter_by(user_id=current_user.id).all()
    
    return render_template('contracts/analyze.html', contracts=contracts)

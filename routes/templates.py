import logging
import json
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import DocumentTemplate, Document, Case, db
import config
import jinja2

logger = logging.getLogger(__name__)

# Create templates blueprint
templates_bp = Blueprint('templates', __name__, url_prefix='/templates')

@templates_bp.route('/')
@login_required
def index():
    """List document templates"""
    # Get user's templates
    user_templates = DocumentTemplate.query.filter_by(user_id=current_user.id).order_by(DocumentTemplate.created_at.desc()).all()
    
    # Get public templates (created by others)
    public_templates = DocumentTemplate.query.filter(
        DocumentTemplate.is_public == True,
        DocumentTemplate.user_id != current_user.id
    ).order_by(DocumentTemplate.created_at.desc()).all()
    
    return render_template('templates/index.html', 
                          user_templates=user_templates, 
                          public_templates=public_templates)

@templates_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new document template"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        template_type = request.form.get('template_type')
        content = request.form.get('content')
        is_public = request.form.get('is_public') == 'on'
        
        # Extract variables from template content - look for patterns like {{variable_name}}
        import re
        variables = re.findall(r'{{(.*?)}}', content)
        variables = [var.strip() for var in variables if var.strip()]
        placeholder_vars = json.dumps(variables) if variables else None
        
        # Create new template
        new_template = DocumentTemplate(
            title=title,
            description=description,
            template_type=template_type,
            content=content,
            is_public=is_public,
            placeholder_vars=placeholder_vars,
            user_id=current_user.id
        )
        
        # Save to database
        db.session.add(new_template)
        try:
            db.session.commit()
            logger.info(f"Created template: {new_template.title}")
            flash('Template created successfully', 'success')
            return redirect(url_for('templates.index'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating template: {str(e)}")
            flash(f'Error creating template: {str(e)}', 'error')
    
    return render_template('templates/create.html', 
                          document_types=config.DOCUMENT_TYPES)

@templates_bp.route('/<int:template_id>')
@login_required
def view(template_id):
    """View a document template"""
    template = DocumentTemplate.query.get_or_404(template_id)
    
    # Check permission - only allow viewing if it's the user's template or it's public
    if template.user_id != current_user.id and not template.is_public:
        flash('You do not have permission to view this template', 'error')
        return redirect(url_for('templates.index'))
    
    variables = template.get_variables()
    
    return render_template('templates/view.html', 
                          template=template,
                          variables=variables)

@templates_bp.route('/<int:template_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(template_id):
    """Edit a document template"""
    template = DocumentTemplate.query.get_or_404(template_id)
    
    # Check permission
    if template.user_id != current_user.id:
        flash('You do not have permission to edit this template', 'error')
        return redirect(url_for('templates.index'))
    
    if request.method == 'POST':
        template.title = request.form.get('title')
        template.description = request.form.get('description')
        template.template_type = request.form.get('template_type')
        template.content = request.form.get('content')
        template.is_public = request.form.get('is_public') == 'on'
        
        # Extract variables from template content
        import re
        variables = re.findall(r'{{(.*?)}}', template.content)
        variables = [var.strip() for var in variables if var.strip()]
        template.placeholder_vars = json.dumps(variables) if variables else None
        
        # Save changes
        try:
            db.session.commit()
            logger.info(f"Updated template: {template.title}")
            flash('Template updated successfully', 'success')
            return redirect(url_for('templates.view', template_id=template.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating template: {str(e)}")
            flash(f'Error updating template: {str(e)}', 'error')
    
    return render_template('templates/edit.html', 
                          template=template, 
                          document_types=config.DOCUMENT_TYPES)

@templates_bp.route('/<int:template_id>/delete', methods=['POST'])
@login_required
def delete(template_id):
    """Delete a document template"""
    template = DocumentTemplate.query.get_or_404(template_id)
    
    # Check permission
    if template.user_id != current_user.id:
        flash('You do not have permission to delete this template', 'error')
        return redirect(url_for('templates.index'))
    
    # Check if there are documents using this template
    document_count = Document.query.filter_by(template_id=template.id).count()
    if document_count > 0:
        flash(f'This template is used by {document_count} documents and cannot be deleted', 'error')
        return redirect(url_for('templates.index'))
    
    try:
        db.session.delete(template)
        db.session.commit()
        logger.info(f"Deleted template: {template.title}")
        flash('Template deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting template: {str(e)}")
        flash(f'Error deleting template: {str(e)}', 'error')
    
    return redirect(url_for('templates.index'))

@templates_bp.route('/<int:template_id>/use', methods=['GET', 'POST'])
@login_required
def use_template(template_id):
    """Use a template to create a new document"""
    template = DocumentTemplate.query.get_or_404(template_id)
    
    # Check permission - only allow using if it's the user's template or it's public
    if template.user_id != current_user.id and not template.is_public:
        flash('You do not have permission to use this template', 'error')
        return redirect(url_for('templates.index'))
    
    variables = template.get_variables()
    
    if request.method == 'POST':
        # Create a context dictionary from form inputs
        context = {}
        for var in variables:
            context[var] = request.form.get(var, '')
        
        # Apply the context to the template to create document content
        jinja_env = jinja2.Environment(autoescape=True)
        try:
            template_obj = jinja_env.from_string(template.content)
            document_content = template_obj.render(**context)
        except Exception as e:
            logger.error(f"Error rendering template: {str(e)}")
            flash(f'Error rendering template: {str(e)}', 'error')
            return redirect(url_for('templates.use_template', template_id=template.id))
        
        # Create new document
        title = request.form.get('document_title', template.title)
        new_document = Document(
            title=title,
            document_type=template.template_type,
            content=document_content,
            status='Draft',
            user_id=current_user.id,
            template_id=template.id
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
            logger.info(f"Created document from template: {new_document.title}")
            flash('Document created successfully', 'success')
            return redirect(url_for('documents.view', document_id=new_document.id))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating document from template: {str(e)}")
            flash(f'Error creating document: {str(e)}', 'error')
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    return render_template('templates/use.html', 
                          template=template,
                          variables=variables,
                          cases=cases)
"""
Routes for the rulings database and judicial trend analysis.
"""
import os
import json
from datetime import datetime, date
from typing import Dict, List, Any, Optional

from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc, func, and_, or_
from werkzeug.utils import secure_filename

from app import db
from models import Ruling, Judge, Tag, RulingReference, RulingAnnotation, RulingAnalysis
from utils.scraper import KenyaLawScraper
from utils.ruling_analyzer import RulingAnalyzer
from utils.permissions import has_permission, Permissions, role_required
from utils.gamification import GamificationService

rulings_bp = Blueprint('rulings', __name__)

# Initialize services
scraper = KenyaLawScraper()
analyzer = RulingAnalyzer()

# Define courts and categories
COURTS = [
    'Supreme Court', 'Court of Appeal', 'High Court', 'Employment and Labour Relations Court',
    'Environment and Land Court', 'Magistrate Court'
]

CATEGORIES = [
    'Constitutional', 'Criminal', 'Civil', 'Commercial', 'Family', 'Employment',
    'Environment', 'Land', 'Intellectual Property', 'Administrative', 'Other'
]

OUTCOMES = [
    'Allowed', 'Dismissed', 'Partially Allowed', 'Settled', 'Withdrawn', 'Other'
]

@rulings_bp.route('/')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def index():
    """Rulings database main page with search and filters"""
    # Get recent rulings
    recent_rulings = Ruling.query.order_by(desc(Ruling.date_of_ruling)).limit(10).all()
    
    # Get landmark cases
    landmark_cases = Ruling.query.filter_by(is_landmark=True).order_by(desc(Ruling.date_of_ruling)).limit(5).all()
    
    # Get courts with counts
    courts = db.session.query(
        Ruling.court, func.count(Ruling.id).label('count')
    ).group_by(Ruling.court).order_by(desc('count')).all()
    
    # Get categories with counts
    categories = db.session.query(
        Ruling.category, func.count(Ruling.id).label('count')
    ).group_by(Ruling.category).order_by(desc('count')).all()
    
    # Get top tags
    top_tags = db.session.query(
        Tag.id, Tag.name, func.count(Ruling.id).label('count')
    ).join(Tag.rulings).group_by(Tag.id, Tag.name).order_by(desc('count')).limit(20).all()
    
    # Get total count of rulings
    total_rulings = Ruling.query.count()
    
    return render_template('rulings/index.html',
                          recent_rulings=recent_rulings,
                          landmark_cases=landmark_cases,
                          courts=courts,
                          categories=categories,
                          top_tags=top_tags,
                          total_rulings=total_rulings,
                          COURTS=COURTS,
                          CATEGORIES=CATEGORIES,
                          OUTCOMES=OUTCOMES)

@rulings_bp.route('/search')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def search():
    """Search rulings with filters"""
    # Get search parameters
    query = request.args.get('query', '')
    court = request.args.get('court', '')
    category = request.args.get('category', '')
    outcome = request.args.get('outcome', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    tags = request.args.getlist('tags')
    judge_id = request.args.get('judge_id', '')
    is_landmark = request.args.get('is_landmark', '')
    
    # Start building the query
    rulings_query = Ruling.query
    
    # Apply filters
    if query:
        rulings_query = rulings_query.filter(
            or_(
                Ruling.title.ilike(f'%{query}%'),
                Ruling.case_number.ilike(f'%{query}%'),
                Ruling.summary.ilike(f'%{query}%'),
                Ruling.full_text.ilike(f'%{query}%')
            )
        )
    
    if court:
        rulings_query = rulings_query.filter(Ruling.court == court)
    
    if category:
        rulings_query = rulings_query.filter(Ruling.category == category)
    
    if outcome:
        rulings_query = rulings_query.filter(Ruling.outcome == outcome)
    
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            rulings_query = rulings_query.filter(Ruling.date_of_ruling >= date_from_obj)
        except ValueError:
            # Invalid date format, ignore this filter
            pass
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
            rulings_query = rulings_query.filter(Ruling.date_of_ruling <= date_to_obj)
        except ValueError:
            # Invalid date format, ignore this filter
            pass
    
    if tags:
        # Filter by tags
        for tag_id in tags:
            try:
                rulings_query = rulings_query.join(Ruling.tags).filter(Tag.id == int(tag_id))
            except ValueError:
                # Invalid tag ID format, ignore this filter
                pass
    
    if judge_id:
        try:
            rulings_query = rulings_query.join(Ruling.judges).filter(Judge.id == int(judge_id))
        except ValueError:
            # Invalid judge ID format, ignore this filter
            pass
    
    if is_landmark:
        rulings_query = rulings_query.filter(Ruling.is_landmark == (is_landmark.lower() == 'true'))
    
    # Paginate results
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    rulings = rulings_query.order_by(desc(Ruling.date_of_ruling)).paginate(page=page, per_page=per_page)
    
    # Get tags for filtering
    all_tags = Tag.query.order_by(Tag.name).all()
    
    # Get judges for filtering
    all_judges = Judge.query.order_by(Judge.name).all()
    
    return render_template('rulings/search.html',
                          rulings=rulings,
                          query=query,
                          court=court,
                          category=category,
                          outcome=outcome,
                          date_from=date_from,
                          date_to=date_to,
                          selected_tags=tags,
                          judge_id=judge_id,
                          is_landmark=is_landmark,
                          all_tags=all_tags,
                          all_judges=all_judges,
                          COURTS=COURTS,
                          CATEGORIES=CATEGORIES,
                          OUTCOMES=OUTCOMES)

@rulings_bp.route('/ruling/<int:ruling_id>')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def view_ruling(ruling_id):
    """View a specific ruling"""
    ruling = Ruling.query.get_or_404(ruling_id)
    
    # Get user's annotations for this ruling
    annotations = RulingAnnotation.query.filter_by(
        ruling_id=ruling_id,
        user_id=current_user.id
    ).order_by(RulingAnnotation.created_at.desc()).all()
    
    # Get references made by this ruling
    outgoing_refs = RulingReference.query.filter_by(source_ruling_id=ruling_id).all()
    
    # Get references to this ruling
    incoming_refs = RulingReference.query.filter_by(target_ruling_id=ruling_id).all()
    
    # Check if analysis exists
    analysis = RulingAnalysis.query.filter_by(
        ruling_id=ruling_id,
        analysis_type='comprehensive'
    ).first()
    
    analysis_data = None
    if analysis and analysis.result:
        try:
            analysis_data = json.loads(analysis.result)
        except:
            # If JSON parsing fails, set to None
            pass
    
    # Get similar rulings
    similar_rulings = analyzer.analyze_ruling_similarity(ruling_id, limit=5)
    
    # Record activity for gamification
    GamificationService.record_activity(current_user, 'view_ruling', f"Viewed ruling: {ruling.title}")
    
    return render_template('rulings/view_ruling.html',
                          ruling=ruling,
                          annotations=annotations,
                          outgoing_refs=outgoing_refs,
                          incoming_refs=incoming_refs,
                          analysis=analysis_data,
                          similar_rulings=similar_rulings)

@rulings_bp.route('/ruling/<int:ruling_id>/analyze', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.ADVANCED_RESEARCH)
def analyze_ruling(ruling_id):
    """Analyze a ruling or view analysis results"""
    ruling = Ruling.query.get_or_404(ruling_id)
    
    if request.method == 'POST':
        # Trigger analysis
        analysis_result = analyzer.analyze_ruling(ruling_id)
        
        if 'error' in analysis_result:
            flash(f"Analysis failed: {analysis_result['error']}", 'danger')
        else:
            flash("Ruling analysis completed successfully", 'success')
            
            # Record activity for gamification
            GamificationService.record_activity(
                current_user, 'analyze_ruling', 
                f"Analyzed ruling: {ruling.title}", 
                points_earned=10
            )
        
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    # Check if analysis exists
    analysis = RulingAnalysis.query.filter_by(
        ruling_id=ruling_id,
        analysis_type='comprehensive'
    ).first()
    
    analysis_data = None
    if analysis and analysis.result:
        try:
            analysis_data = json.loads(analysis.result)
        except:
            # If JSON parsing fails, set to None
            pass
    
    return render_template('rulings/analyze_ruling.html',
                          ruling=ruling,
                          analysis=analysis_data)

@rulings_bp.route('/ruling/<int:ruling_id>/annotate', methods=['POST'])
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def add_annotation(ruling_id):
    """Add an annotation to a ruling"""
    ruling = Ruling.query.get_or_404(ruling_id)
    
    text = request.form.get('annotation_text', '').strip()
    is_private = request.form.get('is_private', 'true').lower() == 'true'
    
    if not text:
        flash("Annotation text cannot be empty", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    # Create annotation
    annotation = RulingAnnotation(
        ruling_id=ruling_id,
        user_id=current_user.id,
        text=text,
        is_private=is_private
    )
    
    db.session.add(annotation)
    db.session.commit()
    
    flash("Annotation added successfully", 'success')
    
    # Record activity for gamification
    GamificationService.record_activity(
        current_user, 'create_annotation', 
        f"Added annotation to ruling: {ruling.title}", 
        points_earned=5
    )
    
    return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))

@rulings_bp.route('/ruling/<int:ruling_id>/annotation/<int:annotation_id>/delete', methods=['POST'])
@login_required
def delete_annotation(ruling_id, annotation_id):
    """Delete an annotation"""
    annotation = RulingAnnotation.query.get_or_404(annotation_id)
    
    # Check if user owns this annotation
    if annotation.user_id != current_user.id and not current_user.has_permission(Permissions.ADMIN_ACCESS):
        flash("You don't have permission to delete this annotation", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    db.session.delete(annotation)
    db.session.commit()
    
    flash("Annotation deleted successfully", 'success')
    return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))

@rulings_bp.route('/ruling/create', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.CREATE_CASE)
def create_ruling():
    """Create a new ruling manually"""
    if request.method == 'POST':
        # Get form data
        case_number = request.form.get('case_number', '').strip()
        title = request.form.get('title', '').strip()
        court = request.form.get('court', '').strip()
        date_of_ruling_str = request.form.get('date_of_ruling', '').strip()
        citation = request.form.get('citation', '').strip()
        url = request.form.get('url', '').strip()
        summary = request.form.get('summary', '').strip()
        full_text = request.form.get('full_text', '').strip()
        outcome = request.form.get('outcome', '').strip()
        category = request.form.get('category', '').strip()
        importance_score = request.form.get('importance_score', '5')
        is_landmark = request.form.get('is_landmark', 'false').lower() == 'true'
        
        # Validate required fields
        if not case_number or not title or not court:
            flash("Case number, title, and court are required fields", 'danger')
            return redirect(url_for('rulings.create_ruling'))
        
        # Parse date
        try:
            date_of_ruling = datetime.strptime(date_of_ruling_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD", 'danger')
            return redirect(url_for('rulings.create_ruling'))
        
        # Parse importance score
        try:
            importance_score = int(importance_score)
            if importance_score < 1 or importance_score > 10:
                raise ValueError("Importance score must be between 1 and 10")
        except ValueError:
            flash("Importance score must be a number between 1 and 10", 'danger')
            return redirect(url_for('rulings.create_ruling'))
        
        # Create ruling
        ruling = Ruling(
            case_number=case_number,
            title=title,
            court=court,
            date_of_ruling=date_of_ruling,
            citation=citation,
            url=url,
            summary=summary,
            full_text=full_text,
            outcome=outcome,
            category=category,
            importance_score=importance_score,
            is_landmark=is_landmark,
            user_id=current_user.id
        )
        
        # Add judges
        judge_ids = request.form.getlist('judges')
        if judge_ids:
            judges = Judge.query.filter(Judge.id.in_(judge_ids)).all()
            ruling.judges = judges
        
        # Add tags
        tag_ids = request.form.getlist('tags')
        if tag_ids:
            tags = Tag.query.filter(Tag.id.in_(tag_ids)).all()
            ruling.tags = tags
        
        # Add new tags if specified
        new_tags = request.form.get('new_tags', '').strip()
        if new_tags:
            for tag_name in [t.strip() for t in new_tags.split(',') if t.strip()]:
                # Check if tag already exists
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    # Create new tag
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                
                ruling.tags.append(tag)
        
        db.session.add(ruling)
        db.session.commit()
        
        flash("Ruling created successfully", 'success')
        
        # Record activity for gamification
        GamificationService.record_activity(
            current_user, 'create_ruling', 
            f"Created ruling: {ruling.title}", 
            points_earned=20
        )
        
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling.id))
    
    # Get all judges for selection
    judges = Judge.query.order_by(Judge.name).all()
    
    # Get all tags for selection
    tags = Tag.query.order_by(Tag.name).all()
    
    return render_template('rulings/create_ruling.html',
                          judges=judges,
                          tags=tags,
                          COURTS=COURTS,
                          CATEGORIES=CATEGORIES,
                          OUTCOMES=OUTCOMES)

@rulings_bp.route('/ruling/<int:ruling_id>/edit', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.EDIT_CASE)
def edit_ruling(ruling_id):
    """Edit an existing ruling"""
    ruling = Ruling.query.get_or_404(ruling_id)
    
    # Check if user can edit this ruling
    if ruling.user_id != current_user.id and not current_user.has_permission(Permissions.ADMIN_ACCESS):
        flash("You don't have permission to edit this ruling", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    if request.method == 'POST':
        # Update ruling with form data
        ruling.case_number = request.form.get('case_number', '').strip()
        ruling.title = request.form.get('title', '').strip()
        ruling.court = request.form.get('court', '').strip()
        
        # Parse date
        date_of_ruling_str = request.form.get('date_of_ruling', '').strip()
        try:
            ruling.date_of_ruling = datetime.strptime(date_of_ruling_str, '%Y-%m-%d').date()
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD", 'danger')
            return redirect(url_for('rulings.edit_ruling', ruling_id=ruling_id))
        
        ruling.citation = request.form.get('citation', '').strip()
        ruling.url = request.form.get('url', '').strip()
        ruling.summary = request.form.get('summary', '').strip()
        ruling.full_text = request.form.get('full_text', '').strip()
        ruling.outcome = request.form.get('outcome', '').strip()
        ruling.category = request.form.get('category', '').strip()
        
        # Parse importance score
        importance_score = request.form.get('importance_score', '5')
        try:
            ruling.importance_score = int(importance_score)
            if ruling.importance_score < 1 or ruling.importance_score > 10:
                raise ValueError("Importance score must be between 1 and 10")
        except ValueError:
            flash("Importance score must be a number between 1 and 10", 'danger')
            return redirect(url_for('rulings.edit_ruling', ruling_id=ruling_id))
        
        ruling.is_landmark = request.form.get('is_landmark', 'false').lower() == 'true'
        
        # Update judges
        judge_ids = request.form.getlist('judges')
        judges = Judge.query.filter(Judge.id.in_(judge_ids)).all() if judge_ids else []
        ruling.judges = judges
        
        # Update tags
        tag_ids = request.form.getlist('tags')
        tags = Tag.query.filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
        ruling.tags = tags
        
        # Add new tags if specified
        new_tags = request.form.get('new_tags', '').strip()
        if new_tags:
            for tag_name in [t.strip() for t in new_tags.split(',') if t.strip()]:
                # Check if tag already exists
                tag = Tag.query.filter_by(name=tag_name).first()
                if not tag:
                    # Create new tag
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                
                ruling.tags.append(tag)
        
        db.session.commit()
        
        flash("Ruling updated successfully", 'success')
        
        # Record activity for gamification
        GamificationService.record_activity(
            current_user, 'edit_ruling', 
            f"Edited ruling: {ruling.title}", 
            points_earned=5
        )
        
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    # Get all judges for selection
    judges = Judge.query.order_by(Judge.name).all()
    
    # Get all tags for selection
    tags = Tag.query.order_by(Tag.name).all()
    
    # Get IDs of currently associated judges and tags
    current_judge_ids = [j.id for j in ruling.judges]
    current_tag_ids = [t.id for t in ruling.tags]
    
    return render_template('rulings/edit_ruling.html',
                          ruling=ruling,
                          judges=judges,
                          tags=tags,
                          current_judge_ids=current_judge_ids,
                          current_tag_ids=current_tag_ids,
                          COURTS=COURTS,
                          CATEGORIES=CATEGORIES,
                          OUTCOMES=OUTCOMES)

@rulings_bp.route('/ruling/<int:ruling_id>/delete', methods=['POST'])
@login_required
@has_permission(Permissions.DELETE_CASE)
def delete_ruling(ruling_id):
    """Delete a ruling"""
    ruling = Ruling.query.get_or_404(ruling_id)
    
    # Check if user can delete this ruling
    if ruling.user_id != current_user.id and not current_user.has_permission(Permissions.ADMIN_ACCESS):
        flash("You don't have permission to delete this ruling", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    # Store title for activity log
    title = ruling.title
    
    db.session.delete(ruling)
    db.session.commit()
    
    flash("Ruling deleted successfully", 'success')
    
    # Record activity for gamification
    GamificationService.record_activity(
        current_user, 'delete_ruling', 
        f"Deleted ruling: {title}"
    )
    
    return redirect(url_for('rulings.index'))

@rulings_bp.route('/ruling/<int:ruling_id>/reference', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CASE)
def add_reference(ruling_id):
    """Add a reference to another ruling"""
    source_ruling = Ruling.query.get_or_404(ruling_id)
    
    target_ruling_id = request.form.get('target_ruling_id')
    reference_type = request.form.get('reference_type', '').strip()
    context = request.form.get('context', '').strip()
    
    # Validate target ruling
    try:
        target_ruling_id = int(target_ruling_id)
        target_ruling = Ruling.query.get(target_ruling_id)
        if not target_ruling:
            raise ValueError("Target ruling not found")
    except (ValueError, TypeError):
        flash("Invalid target ruling", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    # Check if reference already exists
    existing = RulingReference.query.filter_by(
        source_ruling_id=ruling_id,
        target_ruling_id=target_ruling_id
    ).first()
    
    if existing:
        flash("This reference already exists", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    # Create reference
    reference = RulingReference(
        source_ruling_id=ruling_id,
        target_ruling_id=target_ruling_id,
        reference_type=reference_type,
        context=context
    )
    
    db.session.add(reference)
    db.session.commit()
    
    flash("Reference added successfully", 'success')
    
    # Record activity for gamification
    GamificationService.record_activity(
        current_user, 'add_reference', 
        f"Added reference from {source_ruling.title} to {target_ruling.title}", 
        points_earned=5
    )
    
    return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))

@rulings_bp.route('/ruling/<int:ruling_id>/reference/<int:reference_id>/delete', methods=['POST'])
@login_required
@has_permission(Permissions.EDIT_CASE)
def delete_reference(ruling_id, reference_id):
    """Delete a reference"""
    reference = RulingReference.query.get_or_404(reference_id)
    
    # Check if user can edit this ruling
    ruling = Ruling.query.get_or_404(ruling_id)
    if ruling.user_id != current_user.id and not current_user.has_permission(Permissions.ADMIN_ACCESS):
        flash("You don't have permission to delete this reference", 'danger')
        return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))
    
    db.session.delete(reference)
    db.session.commit()
    
    flash("Reference deleted successfully", 'success')
    return redirect(url_for('rulings.view_ruling', ruling_id=ruling_id))

@rulings_bp.route('/import', methods=['GET', 'POST'])
@login_required
@has_permission(Permissions.CREATE_CASE)
def import_rulings():
    """Import rulings from the Kenya Law website"""
    if request.method == 'POST':
        import_type = request.form.get('import_type')
        
        if import_type == 'case_url':
            # Import from specific URL
            url = request.form.get('case_url', '').strip()
            if not url:
                flash("URL is required", 'danger')
                return redirect(url_for('rulings.import_rulings'))
            
            try:
                # Get case details from URL
                case_details = scraper.get_case_details(url)
                
                if not case_details:
                    flash("Failed to retrieve case details from the provided URL", 'danger')
                    return redirect(url_for('rulings.import_rulings'))
                
                # Extract case information
                case_number = case_details.get('case_number', '')
                title = case_details.get('title', '')
                court = case_details.get('court', '')
                date_str = case_details.get('date', '')
                judges = case_details.get('judges', [])
                citation = case_details.get('citation', '')
                summary = case_details.get('summary', '')
                full_text = case_details.get('content', '')
                
                # Parse date
                date_of_ruling = None
                if date_str:
                    try:
                        # Try various date formats
                        for fmt in ['%d %B %Y', '%B %d, %Y', '%Y-%m-%d']:
                            try:
                                date_of_ruling = datetime.strptime(date_str, fmt).date()
                                break
                            except ValueError:
                                continue
                    except Exception:
                        # If all formats fail, use current date
                        date_of_ruling = date.today()
                else:
                    date_of_ruling = date.today()
                
                # Create the ruling
                ruling = Ruling(
                    case_number=case_number,
                    title=title,
                    court=court,
                    date_of_ruling=date_of_ruling,
                    citation=citation,
                    url=url,
                    summary=summary,
                    full_text=full_text,
                    user_id=current_user.id
                )
                
                db.session.add(ruling)
                db.session.flush()  # Get ID without committing
                
                # Add judges
                for judge_name in judges:
                    # Check if judge already exists
                    judge = Judge.query.filter_by(name=judge_name).first()
                    if not judge:
                        # Create new judge
                        judge = Judge(
                            name=judge_name,
                            court=court,
                            is_active=True
                        )
                        db.session.add(judge)
                    
                    ruling.judges.append(judge)
                
                db.session.commit()
                
                flash(f"Successfully imported ruling: {title}", 'success')
                
                # Record activity for gamification
                GamificationService.record_activity(
                    current_user, 'import_ruling', 
                    f"Imported ruling: {title}", 
                    points_earned=15
                )
                
                return redirect(url_for('rulings.view_ruling', ruling_id=ruling.id))
                
            except Exception as e:
                flash(f"Error importing ruling: {str(e)}", 'danger')
                return redirect(url_for('rulings.import_rulings'))
            
        elif import_type == 'court_batch':
            # Import batch from court
            court = request.form.get('court', '')
            limit = request.form.get('limit', '10')
            
            if not court:
                flash("Court is required", 'danger')
                return redirect(url_for('rulings.import_rulings'))
            
            try:
                limit = int(limit)
                if limit < 1 or limit > 50:
                    limit = 10
            except ValueError:
                limit = 10
            
            try:
                # Get court code based on name
                court_code = None
                if 'supreme' in court.lower():
                    court_code = 'KESC'
                elif 'appeal' in court.lower():
                    court_code = 'KECA'
                elif 'high' in court.lower():
                    court_code = 'KEHC'
                elif 'employment' in court.lower() or 'labour' in court.lower():
                    court_code = 'ELRC'
                elif 'environment' in court.lower() or 'land' in court.lower():
                    court_code = 'ELC'
                else:
                    court_code = 'KEHC'  # Default to High Court
                
                # Get cases from court
                cases = scraper.get_case_law(court_code, limit=limit)
                
                if not cases:
                    flash(f"No cases found for {court}", 'danger')
                    return redirect(url_for('rulings.import_rulings'))
                
                imported_count = 0
                for case in cases:
                    # Check if ruling already exists with this URL
                    existing = Ruling.query.filter_by(url=case['url']).first()
                    if existing:
                        continue
                    
                    # Get full case details
                    case_details = scraper.get_case_details(case['url'])
                    
                    if not case_details:
                        continue
                    
                    # Extract case information
                    case_number = case_details.get('case_number', '')
                    title = case_details.get('title', '')
                    court_name = case_details.get('court', court)
                    date_str = case_details.get('date', '')
                    judges = case_details.get('judges', [])
                    citation = case_details.get('citation', '')
                    summary = case_details.get('summary', '')
                    full_text = case_details.get('content', '')
                    
                    # Parse date
                    date_of_ruling = None
                    if date_str:
                        try:
                            # Try various date formats
                            for fmt in ['%d %B %Y', '%B %d, %Y', '%Y-%m-%d']:
                                try:
                                    date_of_ruling = datetime.strptime(date_str, fmt).date()
                                    break
                                except ValueError:
                                    continue
                        except Exception:
                            # If all formats fail, use current date
                            date_of_ruling = date.today()
                    else:
                        date_of_ruling = date.today()
                    
                    # Create the ruling
                    ruling = Ruling(
                        case_number=case_number,
                        title=title,
                        court=court_name,
                        date_of_ruling=date_of_ruling,
                        citation=citation,
                        url=case['url'],
                        summary=summary,
                        full_text=full_text,
                        user_id=current_user.id
                    )
                    
                    db.session.add(ruling)
                    db.session.flush()  # Get ID without committing
                    
                    # Add judges
                    for judge_name in judges:
                        # Check if judge already exists
                        judge = Judge.query.filter_by(name=judge_name).first()
                        if not judge:
                            # Create new judge
                            judge = Judge(
                                name=judge_name,
                                court=court_name,
                                is_active=True
                            )
                            db.session.add(judge)
                        
                        ruling.judges.append(judge)
                    
                    imported_count += 1
                
                db.session.commit()
                
                flash(f"Successfully imported {imported_count} rulings from {court}", 'success')
                
                # Record activity for gamification
                GamificationService.record_activity(
                    current_user, 'import_batch_rulings', 
                    f"Imported {imported_count} rulings from {court}", 
                    points_earned=25
                )
                
                return redirect(url_for('rulings.index'))
                
            except Exception as e:
                flash(f"Error importing rulings: {str(e)}", 'danger')
                return redirect(url_for('rulings.import_rulings'))
    
    return render_template('rulings/import.html',
                          COURTS=COURTS)

@rulings_bp.route('/judges')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def judges():
    """View all judges"""
    # Get all judges with their ruling counts
    judges = db.session.query(
        Judge, func.count(Ruling.id).label('ruling_count')
    ).outerjoin(Judge.rulings).group_by(Judge.id).order_by(Judge.name).all()
    
    return render_template('rulings/judges.html',
                          judges=judges)

@rulings_bp.route('/judge/<int:judge_id>')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def view_judge(judge_id):
    """View a specific judge and their rulings"""
    judge = Judge.query.get_or_404(judge_id)
    
    # Get rulings by this judge
    rulings = Ruling.query.join(Ruling.judges).filter(
        Judge.id == judge_id
    ).order_by(desc(Ruling.date_of_ruling)).all()
    
    # Get analysis of judge's patterns
    judge_analysis = analyzer.analyze_judge_patterns(judge_id)
    
    return render_template('rulings/view_judge.html',
                          judge=judge,
                          rulings=rulings,
                          judge_analysis=judge_analysis)

@rulings_bp.route('/tags')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def tags():
    """View all tags"""
    # Get all tags with their ruling counts
    tags = db.session.query(
        Tag, func.count(Ruling.id).label('ruling_count')
    ).outerjoin(Tag.rulings).group_by(Tag.id).order_by(Tag.name).all()
    
    return render_template('rulings/tags.html',
                          tags=tags)

@rulings_bp.route('/tag/<int:tag_id>')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def view_tag(tag_id):
    """View a specific tag and rulings with that tag"""
    tag = Tag.query.get_or_404(tag_id)
    
    # Get rulings with this tag
    rulings = Ruling.query.join(Ruling.tags).filter(
        Tag.id == tag_id
    ).order_by(desc(Ruling.date_of_ruling)).all()
    
    # Get analysis of how this legal concept has been treated
    tag_analysis = analyzer.analyze_legal_concept(tag_id)
    
    return render_template('rulings/view_tag.html',
                          tag=tag,
                          rulings=rulings,
                          tag_analysis=tag_analysis)

@rulings_bp.route('/trends')
@login_required
@has_permission(Permissions.ADVANCED_RESEARCH)
def trends():
    """View judicial trends overview"""
    # Get overall trends summary
    trends_summary = analyzer.get_judicial_trends_summary()
    
    # Get citation network for visualization
    citation_network = analyzer.get_citation_network(depth=1)
    
    return render_template('rulings/trends.html',
                          trends_summary=trends_summary,
                          citation_network=citation_network)

@rulings_bp.route('/court_trends/<court>')
@login_required
@has_permission(Permissions.ADVANCED_RESEARCH)
def court_trends(court):
    """View trends for a specific court"""
    # Get time period parameter
    time_period = request.args.get('time_period', '')
    
    # Get court trends
    court_analysis = analyzer.analyze_court_trends(court, time_period)
    
    return render_template('rulings/court_trends.html',
                          court=court,
                          time_period=time_period,
                          court_analysis=court_analysis,
                          COURTS=COURTS)

# API endpoints for charts and visualizations

@rulings_bp.route('/api/ruling/<int:ruling_id>/analysis')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def api_ruling_analysis(ruling_id):
    """API endpoint to get ruling analysis"""
    # Check if analysis exists
    analysis = RulingAnalysis.query.filter_by(
        ruling_id=ruling_id,
        analysis_type='comprehensive'
    ).first()
    
    if analysis and analysis.result:
        try:
            analysis_data = json.loads(analysis.result)
            return jsonify(analysis_data)
        except:
            pass
    
    # If no analysis or parsing fails, return empty result
    return jsonify({
        "error": "No analysis available",
        "message": "Run analysis on this ruling first"
    })

@rulings_bp.route('/api/judge/<int:judge_id>/patterns')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def api_judge_patterns(judge_id):
    """API endpoint to get judge's ruling patterns"""
    # Get analysis of judge's patterns
    judge_analysis = analyzer.analyze_judge_patterns(judge_id)
    return jsonify(judge_analysis)

@rulings_bp.route('/api/tag/<int:tag_id>/analysis')
@login_required
@has_permission(Permissions.BASIC_RESEARCH)
def api_tag_analysis(tag_id):
    """API endpoint to get legal concept analysis"""
    # Get analysis of how this legal concept has been treated
    tag_analysis = analyzer.analyze_legal_concept(tag_id)
    return jsonify(tag_analysis)

@rulings_bp.route('/api/trends')
@login_required
@has_permission(Permissions.ADVANCED_RESEARCH)
def api_trends():
    """API endpoint to get overall judicial trends"""
    # Get overall trends summary
    trends_summary = analyzer.get_judicial_trends_summary()
    return jsonify(trends_summary)

@rulings_bp.route('/api/court/<court>/trends')
@login_required
@has_permission(Permissions.ADVANCED_RESEARCH)
def api_court_trends(court):
    """API endpoint to get court trends"""
    # Get time period parameter
    time_period = request.args.get('time_period', '')
    
    # Get court trends
    court_analysis = analyzer.analyze_court_trends(court, time_period)
    return jsonify(court_analysis)

@rulings_bp.route('/api/citation_network')
@login_required
@has_permission(Permissions.ADVANCED_RESEARCH)
def api_citation_network():
    """API endpoint to get citation network"""
    # Get ruling ID and depth parameters
    ruling_id = request.args.get('ruling_id', type=int)
    depth = request.args.get('depth', 2, type=int)
    
    # Get citation network
    network = analyzer.get_citation_network(ruling_id, depth)
    return jsonify(network)
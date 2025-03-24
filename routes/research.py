import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import LegalResearch, Case, db
from utils.research_assistant import LegalResearchAssistant
from utils.scraper import KenyaLawScraper
from utils.vector_db import VectorDatabase
import json

logger = logging.getLogger(__name__)

# Create research blueprint
research_bp = Blueprint('research', __name__, url_prefix='/research')

@research_bp.route('/')
@login_required
def index():
    """Legal research dashboard"""
    research_history = LegalResearch.query.filter_by(user_id=current_user.id).order_by(LegalResearch.created_at.desc()).all()
    return render_template('research/index.html', research_history=research_history)

@research_bp.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """Search for legal resources"""
    results = None
    query = request.args.get('q', '')
    
    if query:
        # Initialize scraper
        scraper = KenyaLawScraper()
        
        # Search cases
        case_results = scraper.search_cases(query)
        
        # Search legislation
        legislation_results = scraper.get_legislation()
        
        # Prepare results
        results = {
            'query': query,
            'cases': case_results,
            'legislation': legislation_results
        }
        
        # Save search to history
        search_history = LegalResearch(
            title=f"Search: {query[:50]}",
            query=query,
            results=json.dumps(results),
            source="kenyalaw.org",
            user_id=current_user.id
        )
        
        # Save to database if case_id is provided
        case_id = request.args.get('case_id')
        if case_id:
            case = Case.query.get(case_id)
            if case and case.user_id == current_user.id:
                search_history.case_id = case_id
        
        db.session.add(search_history)
        try:
            db.session.commit()
            logger.info(f"Saved search to history: {query}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving search to history: {str(e)}")
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    selected_case_id = request.args.get('case_id')
    
    return render_template('research/search.html', 
                          results=results,
                          query=query,
                          cases=cases,
                          selected_case_id=selected_case_id)

@research_bp.route('/research_issue', methods=['GET', 'POST'])
@login_required
def research_issue():
    """Research a legal issue with AI assistance"""
    results = None
    
    if request.method == 'POST':
        query = request.form.get('query')
        court_filters = request.form.getlist('courts')
        case_id = request.form.get('case_id')
        
        if not query:
            flash('Research query is required', 'error')
            return redirect(url_for('research.research_issue'))
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Research issue
        results = research_assistant.research_legal_issue(query, court_filters)
        
        # Save research to history
        research_history = LegalResearch(
            title=f"Research: {query[:50]}",
            query=query,
            results=json.dumps(results),
            source="ai_research",
            user_id=current_user.id
        )
        
        # Associate with case if selected
        if case_id:
            case = Case.query.get(case_id)
            if case and case.user_id == current_user.id:
                research_history.case_id = case_id
        
        db.session.add(research_history)
        try:
            db.session.commit()
            logger.info(f"Saved research to history: {query}")
            flash('Research completed successfully', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving research to history: {str(e)}")
            flash(f'Error saving research: {str(e)}', 'error')
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Get court levels for filtering
    court_levels = {k: v for k, v in config.COURT_LEVELS.items()}
    
    return render_template('research/issue.html', 
                          results=results,
                          cases=cases,
                          court_levels=court_levels)

@research_bp.route('/analyze_document', methods=['GET', 'POST'])
@login_required
def analyze_document():
    """Analyze a legal document with AI"""
    analysis_results = None
    
    if request.method == 'POST':
        document_text = request.form.get('document_text')
        
        if not document_text:
            flash('Document text is required', 'error')
            return redirect(url_for('research.analyze_document'))
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Analyze document
        analysis_results = research_assistant.analyze_legal_document(document_text)
        
        # Save analysis to history
        document_type = analysis_results.get('document_type', 'Unknown document')
        research_history = LegalResearch(
            title=f"Analysis: {document_type}",
            query=document_text[:200] + "...",
            results=json.dumps(analysis_results),
            source="ai_analysis",
            user_id=current_user.id
        )
        
        db.session.add(research_history)
        try:
            db.session.commit()
            logger.info(f"Saved document analysis to history")
            flash('Document analysis completed successfully', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving document analysis: {str(e)}")
            flash(f'Error saving analysis: {str(e)}', 'error')
    
    return render_template('research/analyze.html', analysis_results=analysis_results)

@research_bp.route('/precedents', methods=['GET', 'POST'])
@login_required
def precedents():
    """Find relevant precedents for a legal issue"""
    results = None
    
    if request.method == 'POST':
        issue = request.form.get('issue')
        court_level = request.form.get('court_level')
        
        if not issue or not court_level:
            flash('Legal issue and court level are required', 'error')
            return redirect(url_for('research.precedents'))
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Find precedents
        results = research_assistant.find_relevant_precedents(issue, court_level)
        
        # Save research to history
        research_history = LegalResearch(
            title=f"Precedents: {issue[:50]}",
            query=f"Issue: {issue}, Court: {court_level}",
            results=json.dumps(results),
            source="precedent_search",
            user_id=current_user.id
        )
        
        db.session.add(research_history)
        try:
            db.session.commit()
            logger.info(f"Saved precedent search to history")
            flash('Precedent search completed successfully', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving precedent search: {str(e)}")
            flash(f'Error saving search: {str(e)}', 'error')
    
    # Get court levels for selection
    court_levels = {k: k for k, v in config.COURT_LEVELS.items()}
    
    return render_template('research/precedents.html', 
                          results=results,
                          court_levels=court_levels)

@research_bp.route('/history')
@login_required
def history():
    """View research history"""
    research_history = LegalResearch.query.filter_by(user_id=current_user.id).order_by(LegalResearch.created_at.desc()).all()
    return render_template('research/history.html', research_history=research_history)

@research_bp.route('/history/<int:research_id>')
@login_required
def view_research(research_id):
    """View a specific research item"""
    research = LegalResearch.query.get_or_404(research_id)
    
    # Check permission
    if research.user_id != current_user.id:
        flash('You do not have permission to view this research', 'error')
        return redirect(url_for('research.history'))
    
    # Parse results
    try:
        results = json.loads(research.results)
    except:
        results = {'error': 'Could not parse results'}
    
    return render_template('research/view_research.html', research=research, results=results)

@research_bp.route('/history/<int:research_id>/delete', methods=['POST'])
@login_required
def delete_research(research_id):
    """Delete a research item"""
    research = LegalResearch.query.get_or_404(research_id)
    
    # Check permission
    if research.user_id != current_user.id:
        flash('You do not have permission to delete this research', 'error')
        return redirect(url_for('research.history'))
    
    try:
        db.session.delete(research)
        db.session.commit()
        logger.info(f"Deleted research: {research.title}")
        flash('Research deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting research: {str(e)}")
        flash(f'Error deleting research: {str(e)}', 'error')
    
    return redirect(url_for('research.history'))

# Import here to avoid circular imports
import config

import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import LegalResearch, Case, db, TokenUsage
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
    court_filter = request.args.get('court', '')
    
    if query:
        # Initialize scraper
        scraper = KenyaLawScraper()
        
        # Search cases
        case_results = scraper.search_cases(query)
        
        # If court filter is specified, filter results
        if court_filter:
            filtered_case_results = []
            for case in case_results:
                # Check if court code is in URL or title
                if court_filter in case.get('link', '') or court_filter in case.get('title', ''):
                    filtered_case_results.append(case)
            case_results = filtered_case_results
        
        # Search legislation
        legislation_results = scraper.get_legislation()
        
        # Filter legislation too if possible
        if query and legislation_results:
            filtered_legislation = []
            for legislation in legislation_results:
                # Simple keyword matching
                if any(keyword.lower() in legislation.get('title', '').lower() for keyword in query.split()):
                    filtered_legislation.append(legislation)
            legislation_results = filtered_legislation[:10]  # Limit to 10 items
        
        # Prepare results
        results = {
            'query': query,
            'cases': case_results,
            'legislation': legislation_results
        }
        
        # Save search to history with new fields
        search_history = LegalResearch(
            title=f"Search: {query[:50]}",
            query=query,
            results=json.dumps(results),
            source="kenyalaw.org",
            court_filter=court_filter,
            result_count=len(case_results) + len(legislation_results),
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
            logger.info(f"Saved search to history: {query}, found {search_history.result_count} results")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving search to history: {str(e)}")
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    selected_case_id = request.args.get('case_id')
    
    # Get court levels for filtering
    try:
        court_levels = {k: v for k, v in config.COURT_LEVELS.items()}
    except:
        # Fallback if config is not properly set up
        court_levels = {
            'KESC': 'Supreme Court',
            'KECA': 'Court of Appeal',
            'KEHC': 'High Court',
            'KEELRC': 'Employment and Labour Relations Court',
            'KEELC': 'Environment and Land Court'
        }
    
    return render_template('research/search.html', 
                          results=results,
                          query=query,
                          cases=cases,
                          court_filter=court_filter,
                          court_levels=court_levels,
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
        
        # Check if user has enough tokens for AI research
        tokens_needed = 10  # Example token cost
        if not current_user.use_tokens(tokens_needed):
            flash(f'You need {tokens_needed} tokens to use AI research. Please upgrade your subscription or buy more tokens.', 'error')
            return redirect(url_for('research.research_issue'))
        
        # Record token usage
        token_usage = TokenUsage(
            user_id=current_user.id,
            tokens_used=tokens_needed,
            feature='ai_research'
        )
        db.session.add(token_usage)
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Log the request
        logger.info(f"Researching issue: {query} with court filters: {court_filters}")
        
        # Research issue
        try:
            results = research_assistant.research_legal_issue(query, court_filters)
            
            # Record success
            result_count = 0
            if results.get('results'):
                result_count = len(results.get('results', []))
            
            # Save research to history with enhanced fields
            research_history = LegalResearch(
                title=f"Research: {query[:50]}",
                query=query,
                results=json.dumps(results),
                source="ai_research",
                court_filter=",".join(court_filters) if court_filters else None,
                result_count=result_count,
                user_id=current_user.id
            )
            
            # Associate with case if selected
            if case_id:
                case = Case.query.get(case_id)
                if case and case.user_id == current_user.id:
                    research_history.case_id = case_id
            
            db.session.add(research_history)
            db.session.commit()
            logger.info(f"Saved research to history: {query}, found {result_count} results")
            flash('Research completed successfully', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in AI research: {str(e)}")
            flash(f'Error in research: {str(e)}', 'error')
            
            # Refund tokens on failure
            current_user.add_tokens(tokens_needed)
            db.session.commit()
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Get court levels for filtering
    try:
        court_levels = {k: v for k, v in config.COURT_LEVELS.items()}
    except:
        # Fallback if config is not properly set up
        court_levels = {
            'KESC': 'Supreme Court',
            'KECA': 'Court of Appeal',
            'KEHC': 'High Court',
            'KEELRC': 'Employment and Labour Relations Court',
            'KEELC': 'Environment and Land Court'
        }
    
    # Check if user has enough tokens
    has_enough_tokens = current_user.tokens_available >= 10  # Example token cost
    
    return render_template('research/issue.html', 
                          results=results,
                          cases=cases,
                          court_levels=court_levels,
                          has_enough_tokens=has_enough_tokens,
                          token_cost=10)

@research_bp.route('/analyze_document', methods=['GET', 'POST'])
@login_required
def analyze_document():
    """Analyze a legal document with AI"""
    analysis_results = None
    
    if request.method == 'POST':
        document_text = request.form.get('document_text')
        case_id = request.form.get('case_id')
        
        if not document_text:
            flash('Document text is required', 'error')
            return redirect(url_for('research.analyze_document'))
        
        # Check if user has enough tokens for document analysis
        tokens_needed = 15  # Example token cost - document analysis costs more than simple search
        if not current_user.use_tokens(tokens_needed):
            flash(f'You need {tokens_needed} tokens to use AI document analysis. Please upgrade your subscription or buy more tokens.', 'error')
            return redirect(url_for('research.analyze_document'))
        
        # Record token usage
        token_usage = TokenUsage(
            user_id=current_user.id,
            tokens_used=tokens_needed,
            feature='document_analysis'
        )
        db.session.add(token_usage)
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Analyze document
        try:
            logger.info(f"Analyzing document of length: {len(document_text)} characters")
            analysis_results = research_assistant.analyze_legal_document(document_text)
            
            # Save analysis to history with enhanced fields
            document_type = analysis_results.get('document_type', 'Unknown document')
            research_history = LegalResearch(
                title=f"Analysis: {document_type}",
                query=document_text[:200] + "...",
                results=json.dumps(analysis_results),
                source="ai_analysis",
                result_count=1,  # Just one document analyzed
                user_id=current_user.id
            )
            
            # Associate with case if selected
            if case_id:
                case = Case.query.get(case_id)
                if case and case.user_id == current_user.id:
                    research_history.case_id = case_id
            
            db.session.add(research_history)
            db.session.commit()
            logger.info(f"Saved document analysis to history: {document_type}")
            flash('Document analysis completed successfully', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in document analysis: {str(e)}")
            flash(f'Error in document analysis: {str(e)}', 'error')
            
            # Refund tokens on failure
            current_user.add_tokens(tokens_needed)
            db.session.commit()
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Check if user has enough tokens
    has_enough_tokens = current_user.tokens_available >= 15  # Example token cost for document analysis
    
    return render_template('research/analyze.html', 
                          analysis_results=analysis_results,
                          cases=cases,
                          has_enough_tokens=has_enough_tokens,
                          token_cost=15)

@research_bp.route('/precedents', methods=['GET', 'POST'])
@login_required
def precedents():
    """Find relevant precedents for a legal issue"""
    results = None
    
    if request.method == 'POST':
        issue = request.form.get('issue')
        court_level = request.form.get('court_level')
        case_id = request.form.get('case_id')
        
        if not issue or not court_level:
            flash('Legal issue and court level are required', 'error')
            return redirect(url_for('research.precedents'))
        
        # Check if user has enough tokens for precedent search
        tokens_needed = 20  # Example token cost - precedent search is most comprehensive
        if not current_user.use_tokens(tokens_needed):
            flash(f'You need {tokens_needed} tokens to search for precedents. Please upgrade your subscription or buy more tokens.', 'error')
            return redirect(url_for('research.precedents'))
        
        # Record token usage
        token_usage = TokenUsage(
            user_id=current_user.id,
            tokens_used=tokens_needed,
            feature='precedent_search'
        )
        db.session.add(token_usage)
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Find precedents
        try:
            logger.info(f"Searching for precedents on issue: {issue} in court level: {court_level}")
            results = research_assistant.find_relevant_precedents(issue, court_level)
            
            # Count results
            binding_count = len(results.get('binding_precedents', []))
            persuasive_count = len(results.get('persuasive_precedents', []))
            vector_count = len(results.get('vector_results', []))
            result_count = binding_count + persuasive_count + vector_count
            
            # Save research to history with enhanced fields
            research_history = LegalResearch(
                title=f"Precedents: {issue[:50]}",
                query=f"Issue: {issue}, Court: {court_level}",
                results=json.dumps(results),
                source="precedent_search",
                court_filter=court_level,
                result_count=result_count,
                user_id=current_user.id
            )
            
            # Associate with case if selected
            if case_id:
                case = Case.query.get(case_id)
                if case and case.user_id == current_user.id:
                    research_history.case_id = case_id
            
            db.session.add(research_history)
            db.session.commit()
            logger.info(f"Saved precedent search to history: found {result_count} results")
            flash('Precedent search completed successfully', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in precedent search: {str(e)}")
            flash(f'Error in precedent search: {str(e)}', 'error')
            
            # Refund tokens on failure
            current_user.add_tokens(tokens_needed)
            db.session.commit()
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Get court levels for selection
    try:
        court_levels = {k: v for k, v in config.COURT_LEVELS.items()}
    except:
        # Fallback if config is not properly set up
        court_levels = {
            'KESC': 'Supreme Court',
            'KECA': 'Court of Appeal',
            'KEHC': 'High Court',
            'KEELRC': 'Employment and Labour Relations Court',
            'KEELC': 'Environment and Land Court'
        }
    
    # Check if user has enough tokens
    has_enough_tokens = current_user.tokens_available >= 20  # Example token cost for precedent search
    
    return render_template('research/precedents.html', 
                          results=results,
                          cases=cases,
                          court_levels=court_levels,
                          has_enough_tokens=has_enough_tokens,
                          token_cost=20)

@research_bp.route('/arguments', methods=['GET', 'POST'])
@login_required
def legal_arguments():
    """Generate legal arguments, evidence, and rebuttals"""
    results = None
    
    if request.method == 'POST':
        issue = request.form.get('issue')
        case_facts = request.form.get('case_facts')
        opposing_arguments = request.form.get('opposing_arguments')
        case_id = request.form.get('case_id')
        
        if not issue or not case_facts:
            flash('Legal issue and case facts are required', 'error')
            return redirect(url_for('research.legal_arguments'))
        
        # Check if user has enough tokens for argument generation
        tokens_needed = 25  # Example token cost - argument generation is most comprehensive
        if not current_user.use_tokens(tokens_needed):
            flash(f'You need {tokens_needed} tokens to generate legal arguments. Please upgrade your subscription or buy more tokens.', 'error')
            return redirect(url_for('research.legal_arguments'))
        
        # Record token usage
        token_usage = TokenUsage(
            user_id=current_user.id,
            tokens_used=tokens_needed,
            feature='legal_arguments'
        )
        db.session.add(token_usage)
        
        # Initialize research assistant
        research_assistant = LegalResearchAssistant()
        
        # Generate legal arguments
        try:
            logger.info(f"Generating legal arguments for issue: {issue}")
            results = research_assistant.generate_legal_arguments(issue, case_facts, opposing_arguments)
            
            # Save research to history with enhanced fields
            research_history = LegalResearch(
                title=f"Arguments: {issue[:50]}",
                query=f"Issue: {issue}\nFacts: {case_facts[:100]}...",
                results=json.dumps(results),
                source="legal_arguments",
                result_count=len(results.get('related_cases', [])) + len(results.get('related_statutes', [])),
                has_arguments=True,
                has_rebuttals=bool(opposing_arguments),
                tokens_used=tokens_needed,
                user_id=current_user.id
            )
            
            # Associate with case if selected
            if case_id:
                case = Case.query.get(case_id)
                if case and case.user_id == current_user.id:
                    research_history.case_id = case_id
            
            db.session.add(research_history)
            db.session.commit()
            logger.info(f"Saved legal arguments to history: {issue}")
            flash('Legal arguments generated successfully', 'success')
            
            # Return the ID of the new research entry for redirect
            return redirect(url_for('research.view_research', research_id=research_history.id))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating legal arguments: {str(e)}")
            flash(f'Error generating legal arguments: {str(e)}', 'error')
            
            # Refund tokens on failure
            current_user.add_tokens(tokens_needed)
            db.session.commit()
    
    # Get cases for selection
    cases = Case.query.filter_by(user_id=current_user.id).all()
    
    # Check if user has enough tokens
    has_enough_tokens = current_user.tokens_available >= 25  # Example token cost for argument generation
    
    return render_template('research/arguments.html', 
                          results=results,
                          cases=cases,
                          has_enough_tokens=has_enough_tokens,
                          token_cost=25)

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
    
    # Parse results using the model's get_results_list method
    try:
        results = research.get_results_list()
        if not results and research.results:
            # Fallback to direct json loading if method returns empty but data exists
            results = json.loads(research.results)
    except Exception as e:
        logger.error(f"Error parsing research results: {str(e)}")
        results = {'error': f'Could not parse results: {str(e)}'}
    
    # Get related case if available
    related_case = None
    if research.case_id:
        related_case = Case.query.get(research.case_id)
    
    # Get formatted context for template
    context = {
        'research': research,
        'results': results,
        'result_count': research.result_count or (len(results.get('results', [])) if isinstance(results, dict) and 'results' in results else 0),
        'court_filter': research.court_filter,
        'related_case': related_case,
        'created_at_formatted': research.created_at.strftime('%Y-%m-%d %H:%M:%S') if research.created_at else 'Unknown'
    }
    
    return render_template('research/view_research.html', **context)

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

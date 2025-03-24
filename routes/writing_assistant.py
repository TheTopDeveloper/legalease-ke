"""
Routes for the AI-powered legal writing assistant functionality.
Provides tools for analyzing and improving legal writing with tone and complexity suggestions.
"""
import json
import logging
from flask import Blueprint, render_template, request, jsonify, flash
from flask_login import login_required, current_user
from app import db
from models import User, TokenUsage
from utils.llm import OllamaClient, LegalAssistant

logger = logging.getLogger(__name__)

# Create blueprint
writing_bp = Blueprint('writing', __name__, url_prefix='/writing')

# Initialize LLM client
try:
    llm_client = OllamaClient()
    legal_assistant = LegalAssistant(llm_client=llm_client)
except Exception as e:
    logger.error(f"Error initializing LLM client: {str(e)}")
    llm_client = None
    legal_assistant = None

@writing_bp.route('/')
@login_required
def index():
    """Writing assistant main page"""
    return render_template(
        'writing/index.html',
        user=current_user
    )

@writing_bp.route('/analyze', methods=['POST'])
@login_required
def analyze_text():
    """Analyze legal text and provide improvement suggestions"""
    # Get request data
    text = request.form.get('text', '')
    analysis_type = request.form.get('analysis_type', 'full')  # full, tone, complexity, clarity
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'No text provided for analysis'
        })
    
    # Check if user has tokens available
    tokens_required = 5  # Base token cost
    if len(text) > 500:
        tokens_required += (len(text) // 500)  # Additional token per 500 chars
    
    if not current_user.use_tokens(tokens_required):
        return jsonify({
            'success': False,
            'error': f'Insufficient tokens. This analysis requires {tokens_required} tokens.'
        })
    
    # Record token usage
    db.session.add(TokenUsage(
        user_id=current_user.id,
        tokens_used=tokens_required,
        feature='writing_assistant'
    ))
    db.session.commit()
    
    try:
        # Perform analysis based on selected type
        results = analyze_legal_writing(text, analysis_type)
        
        return jsonify({
            'success': True,
            'analysis': results,
            'tokens_used': tokens_required
        })
    except Exception as e:
        logger.error(f"Error analyzing text: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error analyzing text: {str(e)}'
        })

@writing_bp.route('/improve', methods=['POST'])
@login_required
def improve_text():
    """Generate improved version of legal text based on suggestions"""
    # Get request data
    text = request.form.get('text', '')
    improvements = request.form.get('improvements', '')
    
    if not text:
        return jsonify({
            'success': False,
            'error': 'No text provided for improvement'
        })
    
    # Check if user has tokens available
    tokens_required = 10  # Higher cost for improvement vs analysis
    if len(text) > 300:
        tokens_required += (len(text) // 300)  # Additional token per 300 chars
    
    if not current_user.use_tokens(tokens_required):
        return jsonify({
            'success': False,
            'error': f'Insufficient tokens. This improvement requires {tokens_required} tokens.'
        })
    
    # Record token usage
    db.session.add(TokenUsage(
        user_id=current_user.id,
        tokens_used=tokens_required,
        feature='writing_assistant_improve'
    ))
    db.session.commit()
    
    try:
        # Generate improved text
        improved_text = improve_legal_writing(text, improvements)
        
        return jsonify({
            'success': True,
            'improved_text': improved_text,
            'tokens_used': tokens_required
        })
    except Exception as e:
        logger.error(f"Error improving text: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error improving text: {str(e)}'
        })

def analyze_legal_writing(text, analysis_type='full'):
    """
    Analyze legal writing text and provide suggestions for improvement
    
    Args:
        text: The legal text to analyze
        analysis_type: Type of analysis to perform (full, tone, complexity, clarity)
        
    Returns:
        Dictionary with analysis results
    """
    if not llm_client:
        raise Exception("LLM client not available")
    
    # Limit text size for analysis
    max_chars = 10000
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    
    # Set up prompt based on analysis type
    if analysis_type == 'tone':
        prompt = f"""Analyze the tone of the following legal text and provide specific suggestions for improvement:
1. Identify the overall tone (formal, informal, authoritative, etc.)
2. Note any inconsistencies in tone
3. Suggest how to adjust tone to be more appropriate for a legal document
4. Highlight any unprofessional or inappropriate language

TEXT TO ANALYZE:
{text}

ANALYSIS:"""
    
    elif analysis_type == 'complexity':
        prompt = f"""Analyze the complexity of the following legal text and provide specific suggestions for improvement:
1. Assess the readability level (simple, moderate, complex)
2. Identify overly complex sentences or paragraphs
3. Suggest simpler alternatives for complex terms where appropriate
4. Note any unnecessary jargon that could be simplified

TEXT TO ANALYZE:
{text}

ANALYSIS:"""
    
    elif analysis_type == 'clarity':
        prompt = f"""Analyze the clarity of the following legal text and provide specific suggestions for improvement:
1. Identify any ambiguous or vague statements
2. Highlight areas where precision could be improved
3. Suggest clearer phrasing for unclear sections
4. Note any potential misinterpretations that could occur

TEXT TO ANALYZE:
{text}

ANALYSIS:"""
    
    else:  # full analysis
        prompt = f"""Analyze the following legal text and provide comprehensive improvement suggestions:
1. TONE ANALYSIS:
   - Overall tone assessment (formal, informal, authoritative, etc.)
   - Tone inconsistencies
   - Appropriateness for legal context

2. COMPLEXITY ANALYSIS:
   - Readability assessment
   - Identification of overly complex sentences
   - Unnecessarily complex terms and suggested alternatives

3. CLARITY ANALYSIS:
   - Ambiguous or vague statements
   - Areas lacking precision
   - Potential for misinterpretation

4. LEGAL FORMALITY:
   - Proper use of legal terminology
   - Consistency with legal writing conventions
   - Appropriate citation style (if present)

TEXT TO ANALYZE:
{text}

ANALYSIS:"""
    
    # Get analysis from LLM
    try:
        analysis_result = llm_client.generate(prompt=prompt, temperature=0.3)
        
        # Structure the response
        result = {
            'original_text': text,
            'analysis': analysis_result,
            'analysis_type': analysis_type
        }
        
        return result
    except Exception as e:
        logger.error(f"Error in LLM analysis: {str(e)}")
        raise Exception(f"Unable to analyze text: {str(e)}")

def improve_legal_writing(text, improvements):
    """
    Generate improved version of legal text based on provided suggestions
    
    Args:
        text: Original legal text
        improvements: Suggestions for improvement
        
    Returns:
        Improved version of the text
    """
    if not llm_client:
        raise Exception("LLM client not available")
    
    # Limit text size
    max_chars = 8000
    if len(text) > max_chars:
        text = text[:max_chars] + "... [truncated]"
    
    prompt = f"""Rewrite the following legal text incorporating these improvement suggestions.
Maintain the same meaning and legal intent, but improve the writing based on the suggestions.

ORIGINAL TEXT:
{text}

IMPROVEMENT SUGGESTIONS:
{improvements}

IMPROVED TEXT:"""
    
    try:
        improved_text = llm_client.generate(prompt=prompt, temperature=0.4, max_tokens=2000)
        return improved_text
    except Exception as e:
        logger.error(f"Error improving text: {str(e)}")
        raise Exception(f"Unable to improve text: {str(e)}")
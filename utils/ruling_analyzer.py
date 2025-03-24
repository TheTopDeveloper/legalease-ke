"""
Utility module for analyzing judicial rulings and identifying trends.
Provides functionality for extracting trends, patterns, and insights from court rulings.
"""
import json
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy import func, desc, and_, or_
from models import db, Ruling, Judge, Tag, RulingReference, RulingAnalysis
from utils.llm import LegalAssistant

class RulingAnalyzer:
    """
    Analyzer for examining patterns and trends in judicial rulings
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize the ruling analyzer
        
        Args:
            llm_client: LLM client for analysis (defaults to LegalAssistant)
        """
        from utils.llm import LegalAssistant
        self.llm = llm_client or LegalAssistant()
    
    def analyze_ruling(self, ruling_id: int) -> Dict[str, Any]:
        """
        Perform comprehensive analysis on a specific ruling
        
        Args:
            ruling_id: ID of the ruling to analyze
            
        Returns:
            Dictionary of analysis results
        """
        ruling = Ruling.query.get(ruling_id)
        if not ruling:
            return {"error": "Ruling not found"}
        
        # Check if analysis already exists
        existing = RulingAnalysis.query.filter_by(
            ruling_id=ruling_id, 
            analysis_type='comprehensive'
        ).first()
        
        if existing and existing.result:
            try:
                return json.loads(existing.result)
            except:
                pass  # If JSON parsing fails, regenerate the analysis
        
        # Analyze the ruling text using LLM
        analysis_input = {
            "case_number": ruling.case_number,
            "title": ruling.title,
            "court": ruling.court,
            "date": str(ruling.date_of_ruling),
            "outcome": ruling.outcome,
            "summary": ruling.summary or "",
            "full_text": ruling.full_text or ""
        }
        
        # Use LLM to analyze the ruling
        analysis_results = self._perform_llm_analysis(analysis_input)
        
        # Store the analysis results
        self._save_analysis_results(ruling_id, 'comprehensive', analysis_results)
        
        return analysis_results
    
    def analyze_judge_patterns(self, judge_id: int) -> Dict[str, Any]:
        """
        Analyze ruling patterns for a specific judge
        
        Args:
            judge_id: ID of the judge to analyze
            
        Returns:
            Dictionary of judge ruling patterns
        """
        judge = Judge.query.get(judge_id)
        if not judge:
            return {"error": "Judge not found"}
        
        # Get rulings by this judge
        rulings = Ruling.query.join(Ruling.judges).filter(Judge.id == judge_id).all()
        
        if not rulings:
            return {
                "judge": judge.name,
                "title": judge.title,
                "court": judge.court,
                "total_rulings": 0,
                "message": "No rulings found for this judge"
            }
        
        # Analyze outcome patterns
        outcomes = db.session.query(
            Ruling.outcome, func.count(Ruling.id)
        ).join(Ruling.judges).filter(
            Judge.id == judge_id
        ).group_by(Ruling.outcome).all()
        
        outcome_stats = {outcome: count for outcome, count in outcomes}
        
        # Analyze category patterns
        categories = db.session.query(
            Ruling.category, func.count(Ruling.id)
        ).join(Ruling.judges).filter(
            Judge.id == judge_id
        ).group_by(Ruling.category).all()
        
        category_stats = {category: count for category, count in categories}
        
        # Get recent rulings
        recent_rulings = Ruling.query.join(Ruling.judges).filter(
            Judge.id == judge_id
        ).order_by(desc(Ruling.date_of_ruling)).limit(5).all()
        
        recent_ruling_data = [{
            "id": r.id,
            "title": r.title,
            "date": str(r.date_of_ruling),
            "outcome": r.outcome,
            "category": r.category
        } for r in recent_rulings]
        
        return {
            "judge": judge.name,
            "title": judge.title,
            "court": judge.court,
            "total_rulings": len(rulings),
            "outcome_stats": outcome_stats,
            "category_stats": category_stats,
            "recent_rulings": recent_ruling_data,
            "average_importance": self._calculate_average_importance(rulings)
        }
    
    def analyze_court_trends(self, court: str, time_period: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze trends for a specific court over a time period
        
        Args:
            court: Name of the court to analyze
            time_period: Time period filter (e.g., '1y', '5y', 'all')
            
        Returns:
            Dictionary of court ruling trends
        """
        # Apply time filter
        date_filter = None
        if time_period:
            now = datetime.utcnow()
            if time_period == '1y':
                # Last year
                date_filter = now.replace(year=now.year-1)
            elif time_period == '5y':
                # Last 5 years
                date_filter = now.replace(year=now.year-5)
            elif time_period == '10y':
                # Last 10 years
                date_filter = now.replace(year=now.year-10)
        
        # Base query
        query = Ruling.query.filter(Ruling.court == court)
        
        # Apply date filter if specified
        if date_filter:
            query = query.filter(Ruling.date_of_ruling >= date_filter)
        
        # Get all rulings for this court in the time period
        rulings = query.all()
        
        if not rulings:
            return {
                "court": court,
                "time_period": time_period or "all time",
                "total_rulings": 0,
                "message": "No rulings found for this court and time period"
            }
        
        # Analyze outcome patterns
        outcomes = db.session.query(
            Ruling.outcome, func.count(Ruling.id)
        ).filter(Ruling.court == court)
        
        if date_filter:
            outcomes = outcomes.filter(Ruling.date_of_ruling >= date_filter)
            
        outcomes = outcomes.group_by(Ruling.outcome).all()
        outcome_stats = {outcome: count for outcome, count in outcomes}
        
        # Analyze category patterns
        categories = db.session.query(
            Ruling.category, func.count(Ruling.id)
        ).filter(Ruling.court == court)
        
        if date_filter:
            categories = categories.filter(Ruling.date_of_ruling >= date_filter)
            
        categories = categories.group_by(Ruling.category).all()
        category_stats = {category: count for category, count in categories}
        
        # Analyze trends over time (yearly counts)
        yearly_counts = db.session.query(
            func.extract('year', Ruling.date_of_ruling).label('year'), 
            func.count(Ruling.id)
        ).filter(Ruling.court == court)
        
        if date_filter:
            yearly_counts = yearly_counts.filter(Ruling.date_of_ruling >= date_filter)
            
        yearly_counts = yearly_counts.group_by('year').order_by('year').all()
        year_stats = {int(year): count for year, count in yearly_counts}
        
        # Get top judges in this court
        top_judges = db.session.query(
            Judge.id, Judge.name, func.count(Ruling.id).label('count')
        ).join(Judge.rulings).filter(Ruling.court == court)
        
        if date_filter:
            top_judges = top_judges.filter(Ruling.date_of_ruling >= date_filter)
            
        top_judges = top_judges.group_by(Judge.id, Judge.name).order_by(desc('count')).limit(5).all()
        
        judge_stats = [{
            "id": id,
            "name": name,
            "ruling_count": count
        } for id, name, count in top_judges]
        
        return {
            "court": court,
            "time_period": time_period or "all time",
            "total_rulings": len(rulings),
            "outcome_stats": outcome_stats,
            "category_stats": category_stats,
            "yearly_trend": year_stats,
            "top_judges": judge_stats,
            "landmark_cases_count": sum(1 for r in rulings if r.is_landmark),
            "average_importance": self._calculate_average_importance(rulings)
        }
    
    def analyze_legal_concept(self, tag_id: int) -> Dict[str, Any]:
        """
        Analyze how a specific legal concept (tag) has been treated in rulings
        
        Args:
            tag_id: ID of the tag to analyze
            
        Returns:
            Dictionary of analysis for the legal concept
        """
        tag = Tag.query.get(tag_id)
        if not tag:
            return {"error": "Tag not found"}
        
        # Get rulings with this tag
        rulings = Ruling.query.join(Ruling.tags).filter(Tag.id == tag_id).all()
        
        if not rulings:
            return {
                "tag": tag.name,
                "description": tag.description,
                "total_rulings": 0,
                "message": "No rulings found for this legal concept"
            }
        
        # Analyze court distribution
        courts = db.session.query(
            Ruling.court, func.count(Ruling.id)
        ).join(Ruling.tags).filter(
            Tag.id == tag_id
        ).group_by(Ruling.court).all()
        
        court_stats = {court: count for court, count in courts}
        
        # Analyze outcome patterns
        outcomes = db.session.query(
            Ruling.outcome, func.count(Ruling.id)
        ).join(Ruling.tags).filter(
            Tag.id == tag_id
        ).group_by(Ruling.outcome).all()
        
        outcome_stats = {outcome: count for outcome, count in outcomes}
        
        # Analyze trends over time (yearly counts)
        yearly_counts = db.session.query(
            func.extract('year', Ruling.date_of_ruling).label('year'), 
            func.count(Ruling.id)
        ).join(Ruling.tags).filter(
            Tag.id == tag_id
        ).group_by('year').order_by('year').all()
        
        year_stats = {int(year): count for year, count in yearly_counts}
        
        # Get landmark cases for this tag
        landmark_cases = Ruling.query.join(Ruling.tags).filter(
            and_(Tag.id == tag_id, Ruling.is_landmark == True)
        ).all()
        
        landmark_data = [{
            "id": r.id,
            "title": r.title,
            "court": r.court,
            "date": str(r.date_of_ruling),
            "outcome": r.outcome
        } for r in landmark_cases]
        
        return {
            "tag": tag.name,
            "description": tag.description,
            "total_rulings": len(rulings),
            "court_distribution": court_stats,
            "outcome_stats": outcome_stats,
            "yearly_trend": year_stats,
            "landmark_cases": landmark_data,
            "average_importance": self._calculate_average_importance(rulings)
        }
    
    def get_citation_network(self, ruling_id: Optional[int] = None, depth: int = 2) -> Dict[str, Any]:
        """
        Build a citation network from ruling references
        
        Args:
            ruling_id: Starting ruling ID (optional)
            depth: Depth of the network to explore
            
        Returns:
            Dictionary with nodes and edges of the citation network
        """
        nodes = []
        edges = []
        explored = set()
        
        # If ruling_id is specified, build network around that ruling
        if ruling_id:
            self._explore_citation_network(ruling_id, nodes, edges, explored, depth)
        else:
            # Get landmark cases and build network around them
            landmark_rulings = Ruling.query.filter(Ruling.is_landmark == True).limit(10).all()
            for ruling in landmark_rulings:
                self._explore_citation_network(ruling.id, nodes, edges, explored, depth)
        
        return {
            "nodes": nodes,
            "edges": edges
        }
    
    def get_judicial_trends_summary(self) -> Dict[str, Any]:
        """
        Get a high-level summary of judicial trends
        
        Returns:
            Dictionary with overall trends in the judicial system
        """
        # Get total counts
        total_rulings = Ruling.query.count()
        total_judges = Judge.query.count()
        total_tags = Tag.query.count()
        
        if total_rulings == 0:
            return {
                "message": "No rulings in the database to analyze"
            }
        
        # Get court distribution
        courts = db.session.query(
            Ruling.court, func.count(Ruling.id)
        ).group_by(Ruling.court).all()
        
        court_stats = {court: count for court, count in courts}
        
        # Get category distribution
        categories = db.session.query(
            Ruling.category, func.count(Ruling.id)
        ).group_by(Ruling.category).all()
        
        category_stats = {category: count for category, count in categories}
        
        # Get outcome distribution
        outcomes = db.session.query(
            Ruling.outcome, func.count(Ruling.id)
        ).group_by(Ruling.outcome).all()
        
        outcome_stats = {outcome: count for outcome, count in outcomes}
        
        # Get yearly trend
        yearly_counts = db.session.query(
            func.extract('year', Ruling.date_of_ruling).label('year'), 
            func.count(Ruling.id)
        ).group_by('year').order_by('year').all()
        
        year_stats = {int(year): count for year, count in yearly_counts}
        
        # Get most active judges
        top_judges = db.session.query(
            Judge.id, Judge.name, func.count(Ruling.id).label('count')
        ).join(Judge.rulings).group_by(Judge.id, Judge.name).order_by(desc('count')).limit(5).all()
        
        judge_stats = [{
            "id": id,
            "name": name,
            "ruling_count": count
        } for id, name, count in top_judges]
        
        # Get most common legal concepts
        top_tags = db.session.query(
            Tag.id, Tag.name, func.count(Ruling.id).label('count')
        ).join(Tag.rulings).group_by(Tag.id, Tag.name).order_by(desc('count')).limit(10).all()
        
        tag_stats = [{
            "id": id,
            "name": name,
            "ruling_count": count
        } for id, name, count in top_tags]
        
        return {
            "total_rulings": total_rulings,
            "total_judges": total_judges,
            "total_tags": total_tags,
            "court_distribution": court_stats,
            "category_distribution": category_stats,
            "outcome_distribution": outcome_stats,
            "yearly_trend": year_stats,
            "top_judges": judge_stats,
            "top_legal_concepts": tag_stats,
            "landmark_cases_count": Ruling.query.filter(Ruling.is_landmark == True).count()
        }
    
    def analyze_ruling_similarity(self, ruling_id: int, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find rulings similar to the given ruling
        
        Args:
            ruling_id: ID of the ruling to find similarities for
            limit: Maximum number of similar rulings to return
            
        Returns:
            List of similar rulings with similarity scores
        """
        ruling = Ruling.query.get(ruling_id)
        if not ruling:
            return []
        
        # Find rulings with similar tags
        similar_rulings = db.session.query(
            Ruling, func.count(Tag.id).label('matching_tags')
        ).join(Ruling.tags).filter(
            Tag.id.in_([tag.id for tag in ruling.tags]),
            Ruling.id != ruling_id
        ).group_by(Ruling.id).order_by(desc('matching_tags')).limit(limit * 2).all()
        
        results = []
        for similar, tag_count in similar_rulings:
            # Calculate similarity score (0-100)
            # Based on matching tags, same court, same outcome, etc.
            score = self._calculate_similarity_score(ruling, similar, tag_count)
            
            results.append({
                "id": similar.id,
                "title": similar.title,
                "court": similar.court,
                "date": str(similar.date_of_ruling),
                "outcome": similar.outcome,
                "similarity_score": score,
                "matching_tags": tag_count
            })
        
        # Sort by similarity score and limit
        results.sort(key=lambda x: x["similarity_score"], reverse=True)
        return results[:limit]
    
    def _perform_llm_analysis(self, ruling_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use LLM to analyze a ruling
        
        Args:
            ruling_data: Dictionary with ruling information
            
        Returns:
            Dictionary with analysis results
        """
        # Extract key information using LLM
        # This is a placeholder - in a real implementation, we would
        # use specific prompts to extract different aspects of the ruling
        
        # Create a prompt for analyzing the ruling
        prompt = f"""
        Please analyze this legal ruling from Kenya and extract key information:
        
        Case Number: {ruling_data['case_number']}
        Title: {ruling_data['title']}
        Court: {ruling_data['court']}
        Date: {ruling_data['date']}
        Outcome: {ruling_data['outcome']}
        
        Summary: {ruling_data['summary']}
        
        Full Text: {ruling_data['full_text'][:5000]}  # Limit text length to avoid token limits
        
        Please provide the following analysis:
        1. Key legal principles established or affirmed
        2. The main legal reasoning applied
        3. Potential precedential value
        4. Impact on Kenyan jurisprudence
        5. Notable concurring or dissenting opinions
        6. Suggested tags (legal concepts) mentioned in the ruling
        
        Format your response as a JSON object with these keys:
        legal_principles, legal_reasoning, precedential_value, impact, 
        notable_opinions, suggested_tags
        """
        
        try:
            # Use LLM to generate response
            response = self.llm.analyze_case(prompt)
            
            # Extract structured analysis
            return {
                "legal_principles": response.get("legal_principles", []),
                "legal_reasoning": response.get("legal_reasoning", ""),
                "precedential_value": response.get("precedential_value", ""),
                "impact": response.get("impact", ""),
                "notable_opinions": response.get("notable_opinions", ""),
                "suggested_tags": response.get("suggested_tags", []),
                "analyzed_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            print(f"Error during LLM analysis: {e}")
            return {
                "error": "Analysis failed",
                "message": str(e)
            }
    
    def _save_analysis_results(self, ruling_id: int, analysis_type: str, results: Dict[str, Any]) -> None:
        """
        Save analysis results to the database
        
        Args:
            ruling_id: ID of the ruling
            analysis_type: Type of analysis performed
            results: Results to save
        """
        # Check if analysis already exists
        existing = RulingAnalysis.query.filter_by(
            ruling_id=ruling_id, 
            analysis_type=analysis_type
        ).first()
        
        if existing:
            # Update existing analysis
            existing.result = json.dumps(results)
            existing.updated_at = datetime.utcnow()
        else:
            # Create new analysis record
            analysis = RulingAnalysis(
                ruling_id=ruling_id,
                analysis_type=analysis_type,
                result=json.dumps(results)
            )
            db.session.add(analysis)
        
        db.session.commit()
    
    def _explore_citation_network(self, ruling_id: int, nodes: List[Dict[str, Any]], 
                                 edges: List[Dict[str, Any]], explored: set, depth: int) -> None:
        """
        Recursively explore the citation network
        
        Args:
            ruling_id: Current ruling ID to explore
            nodes: List of nodes for the network
            edges: List of edges for the network
            explored: Set of already explored ruling IDs
            depth: Remaining depth to explore
        """
        if ruling_id in explored or depth <= 0:
            return
        
        explored.add(ruling_id)
        ruling = Ruling.query.get(ruling_id)
        
        if not ruling:
            return
        
        # Add this ruling as a node
        nodes.append({
            "id": ruling.id,
            "label": ruling.case_number,
            "title": ruling.title,
            "court": ruling.court,
            "date": str(ruling.date_of_ruling),
            "is_landmark": ruling.is_landmark
        })
        
        # Get outgoing references (rulings cited by this ruling)
        outgoing_refs = RulingReference.query.filter_by(source_ruling_id=ruling.id).all()
        for ref in outgoing_refs:
            # Add edge
            edges.append({
                "source": ruling.id,
                "target": ref.target_ruling_id,
                "type": ref.reference_type or "cites"
            })
            
            # Explore the target if depth allows
            if depth > 1:
                self._explore_citation_network(ref.target_ruling_id, nodes, edges, explored, depth - 1)
        
        # Get incoming references (rulings that cite this ruling)
        incoming_refs = RulingReference.query.filter_by(target_ruling_id=ruling.id).all()
        for ref in incoming_refs:
            # Add edge
            edges.append({
                "source": ref.source_ruling_id,
                "target": ruling.id,
                "type": ref.reference_type or "cites"
            })
            
            # Explore the source if depth allows
            if depth > 1:
                self._explore_citation_network(ref.source_ruling_id, nodes, edges, explored, depth - 1)
    
    def _calculate_average_importance(self, rulings: List[Ruling]) -> float:
        """
        Calculate the average importance score for a list of rulings
        
        Args:
            rulings: List of Ruling objects
            
        Returns:
            Average importance score (0-10)
        """
        scores = [r.importance_score for r in rulings if r.importance_score is not None]
        return round(sum(scores) / len(scores), 1) if scores else 0
    
    def _calculate_similarity_score(self, ruling1: Ruling, ruling2: Ruling, matching_tags: int) -> int:
        """
        Calculate similarity score between two rulings (0-100)
        
        Args:
            ruling1: First ruling
            ruling2: Second ruling
            matching_tags: Number of matching tags
            
        Returns:
            Similarity score as an integer (0-100)
        """
        score = 0
        
        # Tags similarity (up to 40 points)
        total_tags = len(set([t.id for t in ruling1.tags] + [t.id for t in ruling2.tags]))
        if total_tags > 0:
            tag_similarity = min(40, int((matching_tags / total_tags) * 40))
        else:
            tag_similarity = 0
        score += tag_similarity
        
        # Same court (10 points)
        if ruling1.court == ruling2.court:
            score += 10
        
        # Same outcome (10 points)
        if ruling1.outcome == ruling2.outcome:
            score += 10
        
        # Same category (10 points)
        if ruling1.category == ruling2.category:
            score += 10
        
        # Time proximity (up to 20 points)
        # Calculate years between rulings
        if ruling1.date_of_ruling and ruling2.date_of_ruling:
            years_diff = abs((ruling1.date_of_ruling.year - ruling2.date_of_ruling.year))
            time_score = max(0, 20 - years_diff * 2)  # Subtract 2 points per year difference
            score += time_score
        
        # Same judges (up to 10 points)
        ruling1_judges = set([j.id for j in ruling1.judges])
        ruling2_judges = set([j.id for j in ruling2.judges])
        common_judges = ruling1_judges.intersection(ruling2_judges)
        if ruling1_judges and ruling2_judges:
            judge_similarity = min(10, int((len(common_judges) / max(len(ruling1_judges), len(ruling2_judges))) * 10))
            score += judge_similarity
        
        return score
"""
ClinicalTrials.gov API service for Strategic Insights GPT Backend
"""

import os
import time
import requests
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ClinicalTrialsService:
    """Service for interacting with ClinicalTrials.gov API"""
    
    def __init__(self):
        self.base_url = "https://clinicaltrials.gov/api/v2/studies"
        
        # Strategic queries for RWE clinical trials
        self.strategic_queries = [
            "real-world evidence",
            "observational study",
            "registry study",
            "post-marketing surveillance",
            "comparative effectiveness",
            "patient-reported outcomes",
            "health economics",
            "real-world data",
            "pragmatic trial",
            "effectiveness study",
            "safety surveillance",
            "outcomes research"
        ]
    
    def search_studies(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search ClinicalTrials.gov studies by query"""
        try:
            params = {
                'query.term': query,
                'pageSize': min(max_results, 1000),
                'format': 'json'
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            studies = data.get('studies', [])
            
            # Parse and format studies
            formatted_studies = []
            for study in studies[:max_results]:
                formatted_study = self._parse_study(study)
                if formatted_study:
                    formatted_studies.append(formatted_study)
            
            return formatted_studies
            
        except Exception as e:
            logger.error(f"Error searching ClinicalTrials.gov: {str(e)}")
            return []
    
    def bulk_strategic_search(self, topic: str, max_results_per_query: int = 5) -> List[Dict[str, Any]]:
        """Perform bulk strategic search using predefined queries"""
        all_results = []
        
        for query in self.strategic_queries:
            try:
                # Combine topic with strategic query
                full_query = f"{topic} AND {query}"
                results = self.search_studies(full_query, max_results_per_query)
                
                # Add query context to results
                for result in results:
                    result['search_query'] = query
                    result['topic'] = topic
                
                all_results.extend(results)
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in strategic query '{query}': {str(e)}")
                continue
        
        # Remove duplicates based on NCT ID
        seen_nct_ids = set()
        unique_results = []
        for result in all_results:
            nct_id = result.get('nct_id')
            if nct_id and nct_id not in seen_nct_ids:
                seen_nct_ids.add(nct_id)
                unique_results.append(result)
        
        return unique_results
    
    def search_by_filters(self, **filters) -> List[Dict[str, Any]]:
        """Search studies with specific filters"""
        try:
            params = {
                'format': 'json',
                'pageSize': filters.get('max_results', 100)
            }
            
            # Add filter parameters
            if filters.get('condition'):
                params['query.cond'] = filters['condition']
            if filters.get('intervention'):
                params['query.intr'] = filters['intervention']
            if filters.get('phase'):
                params['query.phase'] = filters['phase']
            if filters.get('status'):
                params['query.status'] = filters['status']
            if filters.get('sponsor'):
                params['query.spons'] = filters['sponsor']
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            studies = data.get('studies', [])
            
            # Parse and format studies
            formatted_studies = []
            for study in studies:
                formatted_study = self._parse_study(study)
                if formatted_study:
                    formatted_studies.append(formatted_study)
            
            return formatted_studies
            
        except Exception as e:
            logger.error(f"Error searching with filters: {str(e)}")
            return []
    
    def _parse_study(self, study: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and format study data"""
        try:
            protocol_section = study.get('protocolSection', {})
            identification_module = protocol_section.get('identificationModule', {})
            status_module = protocol_section.get('statusModule', {})
            description_module = protocol_section.get('descriptionModule', {})
            conditions_module = protocol_section.get('conditionsModule', {})
            design_module = protocol_section.get('designModule', {})
            arms_interventions_module = protocol_section.get('armsInterventionsModule', {})
            sponsors_collaborators_module = protocol_section.get('sponsorCollaboratorsModule', {})
            contacts_locations_module = protocol_section.get('contactsLocationsModule', {})
            
            # Extract basic information
            nct_id = identification_module.get('nctId', '')
            title = identification_module.get('briefTitle', 'No title available')
            brief_summary = description_module.get('briefSummary', 'No summary available')
            detailed_description = description_module.get('detailedDescription', '')
            
            # Extract status and phase
            overall_status = status_module.get('overallStatus', 'Unknown')
            phase = design_module.get('phases', ['Unknown'])[0] if design_module.get('phases') else 'Unknown'
            
            # Extract conditions
            conditions = conditions_module.get('conditions', [])
            
            # Extract interventions
            interventions = []
            if arms_interventions_module.get('interventions'):
                for intervention in arms_interventions_module['interventions']:
                    interventions.append({
                        'type': intervention.get('type', 'Unknown'),
                        'name': intervention.get('name', 'Unknown')
                    })
            
            # Extract sponsors
            lead_sponsor = sponsors_collaborators_module.get('leadSponsor', {})
            sponsor_name = lead_sponsor.get('name', 'Unknown sponsor')
            
            # Extract locations
            locations = []
            if contacts_locations_module.get('locations'):
                for location in contacts_locations_module['locations']:
                    facility = location.get('facility', {})
                    locations.append({
                        'facility': facility.get('name', 'Unknown facility'),
                        'city': facility.get('city', 'Unknown city'),
                        'country': facility.get('country', 'Unknown country')
                    })
            
            # Extract dates
            start_date = status_module.get('startDateStruct', {}).get('date', 'Unknown')
            completion_date = status_module.get('completionDateStruct', {}).get('date', 'Unknown')
            
            return {
                'nct_id': nct_id,
                'title': title,
                'brief_summary': brief_summary,
                'detailed_description': detailed_description,
                'overall_status': overall_status,
                'phase': phase,
                'conditions': conditions,
                'interventions': interventions,
                'sponsor': sponsor_name,
                'locations': locations,
                'start_date': start_date,
                'completion_date': completion_date,
                'source': 'clinicaltrials',
                'url': f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None
            }
            
        except Exception as e:
            logger.error(f"Error parsing study: {str(e)}")
            return None


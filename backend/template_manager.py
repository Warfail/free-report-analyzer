import re
import json
from collections import defaultdict
from datetime import datetime

class TemplateManager:
    def __init__(self):
        self.templates = {}
        self.field_patterns = {
            'date': [r'\b\d{4}-\d{2}-\d{2}\b', r'\b\d{1,2}/\d{1,2}/\d{4}\b'],
            'time': [r'\b\d{1,2}:\d{2}\s*(?:AM|PM)?\b'],
            'percentage': [r'\b\d+(?:\.\d+)?%\b'],
            'number': [r'\b\d+(?:\.\d+)?\b'],
            'email': [r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'],
            'url': [r'https?://\S+']
        }
    
    def analyze_report_structure(self, text, department):
        """Analyze report to detect template structure"""
        lines = text.split('\n')
        
        # Common section headers
        section_headers = []
        current_section = None
        sections = defaultdict(list)
        
        section_patterns = [
            (r'^(?:#+\s*)?(?:accomplishments|achievements|completed|done):?$', 'accomplishments'),
            (r'^(?:#+\s*)?(?:challenges|problems|issues|blockers):?$', 'challenges'),
            (r'^(?:#+\s*)?(?:plans?|next|tomorrow|future):?$', 'plans'),
            (r'^(?:#+\s*)?(?:metrics|kpis|stats):?$', 'metrics'),
            (r'^(?:#+\s*)?(?:risks?|concerns):?$', 'risks'),
            (r'^(?:#+\s*)?(?:resources?|needs):?$', 'resources')
        ]
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if line is a section header
            is_section = False
            for pattern, section_name in section_patterns:
                if re.search(pattern, line_stripped.lower()):
                    current_section = section_name
                    section_headers.append(line_stripped)
                    is_section = True
                    break
            
            if not is_section and current_section:
                sections[current_section].append(line_stripped)
        
        # Detect bullet style
        bullet_style = self._detect_bullet_style(lines)
        
        # Detect date format
        date_format = self._detect_date_format(text)
        
        # Build template
        template = {
            'department': department,
            'section_headers': list(set(section_headers)),
            'sections_found': list(sections.keys()),
            'bullet_style': bullet_style,
            'date_format': date_format,
            'sample_lines': lines[:10],  # First 10 lines as sample
            'last_updated': datetime.now().isoformat(),
            'usage_count': 1
        }
        
        return template
    
    def _detect_bullet_style(self, lines):
        """Detect what bullet style is used"""
        bullet_counts = defaultdict(int)
        
        bullet_patterns = {
            'dash': r'^\s*[-–—]\s+',
            'asterisk': r'^\s*\*\s+',
            'number': r'^\s*\d+[\.\)]\s+',
            'letter': r'^\s*[a-zA-Z][\.\)]\s+',
            'checkbox': r'^\s*\[[ x]\]\s+',
            'arrow': r'^\s*[→⇒›]\s+',
            'bullet': r'^\s*[•◦]\s+'
        }
        
        for line in lines:
            for style, pattern in bullet_patterns.items():
                if re.search(pattern, line):
                    bullet_counts[style] += 1
        
        if bullet_counts:
            return max(bullet_counts.items(), key=lambda x: x[1])[0]
        return None
    
    def _detect_date_format(self, text):
        """Detect date format used in report"""
        date_patterns = {
            'iso': r'\b\d{4}-\d{2}-\d{2}\b',
            'us': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'euro': r'\b\d{1,2}\.\d{1,2}\.\d{4}\b',
            'text': r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
        }
        
        for format_name, pattern in date_patterns.items():
            if re.search(pattern, text):
                return format_name
        
        return 'unknown'
    
    def save_template(self, department, template):
        """Save or update template for a department"""
        if department in self.templates:
            # Merge with existing template
            existing = self.templates[department]
            existing['section_headers'] = list(set(existing['section_headers'] + template['section_headers']))
            existing['sections_found'] = list(set(existing['sections_found'] + template['sections_found']))
            existing['usage_count'] += 1
            existing['last_updated'] = datetime.now().isoformat()
        else:
            self.templates[department] = template
    
    def get_template(self, department):
        """Get template for a department"""
        return self.templates.get(department, None)
    
    def validate_report(self, text, department):
        """Validate report against department template"""
        template = self.get_template(department)
        if not template:
            return {'valid': True, 'message': 'No template defined for this department'}
        
        # Check for required sections
        missing_sections = []
        for section in template.get('required_sections', []):
            if section not in text.lower():
                missing_sections.append(section)
        
        # Check date format
        date_warning = None
        if template.get('date_format') and template['date_format'] != 'unknown':
            expected_pattern = self._get_date_pattern(template['date_format'])
            if not re.search(expected_pattern, text):
                date_warning = f"Date format doesn't match expected {template['date_format']} format"
        
        # Check bullet style consistency
        bullet_warning = None
        if template.get('bullet_style'):
            lines = text.split('\n')
            bullet_count = sum(1 for line in lines if self._has_bullet(line, template['bullet_style']))
            total_items = sum(1 for line in lines if any(self._has_bullet(line, style) for style in 
                                                        ['dash', 'asterisk', 'number', 'checkbox', 'arrow', 'bullet']))
            
            if total_items > 0 and bullet_count / total_items < 0.5:
                bullet_warning = f"Inconsistent bullet style. Expected: {template['bullet_style']}"
        
        return {
            'valid': len(missing_sections) == 0,
            'missing_sections': missing_sections,
            'warnings': [w for w in [date_warning, bullet_warning] if w],
            'template_match_score': self._calculate_match_score(text, template)
        }
    
    def _calculate_match_score(self, text, template):
        """Calculate how well report matches template"""
        score = 100
        lines = text.lower().split('\n')
        
        # Penalize for missing sections
        for section in template.get('required_sections', []):
            if section not in text.lower():
                score -= 20
        
        # Check section headers
        template_headers = set(h.lower() for h in template.get('section_headers', []))
        found_headers = 0
        for line in lines:
            if any(header in line for header in template_headers):
                found_headers += 1
        
        if template_headers:
            header_score = (found_headers / len(template_headers)) * 30
            score = min(score, header_score)
        
        return max(0, score)
    
    def _has_bullet(self, line, style):
        """Check if line has specific bullet style"""
        patterns = {
            'dash': r'^\s*[-–—]\s+',
            'asterisk': r'^\s*\*\s+',
            'number': r'^\s*\d+[\.\)]\s+',
            'checkbox': r'^\s*\[[ x]\]\s+',
            'arrow': r'^\s*[→⇒›]\s+',
            'bullet': r'^\s*[•◦]\s+'
        }
        return bool(re.search(patterns.get(style, ''), line))
    
    def _get_date_pattern(self, date_format):
        patterns = {
            'iso': r'\b\d{4}-\d{2}-\d{2}\b',
            'us': r'\b\d{1,2}/\d{1,2}/\d{4}\b',
            'euro': r'\b\d{1,2}\.\d{1,2}\.\d{4}\b'
        }
        return patterns.get(date_format, '')
    
    def generate_template_guide(self, department):
        """Generate a guide for department's template"""
        template = self.get_template(department)
        if not template:
            return "No template defined for this department yet."
        
        guide = f"# {department} Report Template Guide\n\n"
        
        if template.get('section_headers'):
            guide += "## Required Sections:\n"
            for header in template['section_headers']:
                guide += f"- {header}\n"
            guide += "\n"
        
        if template.get('date_format') and template['date_format'] != 'unknown':
            guide += f"## Date Format: {template['date_format'].upper()}\n\n"
        
        if template.get('bullet_style'):
            bullet_symbols = {
                'dash': '-',
                'asterisk': '*',
                'number': '1.',
                'checkbox': '[ ]',
                'arrow': '→',
                'bullet': '•'
            }
            symbol = bullet_symbols.get(template['bullet_style'], '-')
            guide += f"## Bullet Style: {symbol}\n\n"
        
        if template.get('sample_lines'):
            guide += "## Example Format:\n```\n"
            guide += "\n".join(template['sample_lines'][:5])
            guide += "\n```\n"
        
        return guide
    
    def extract_structured_data(self, text, department):
        """Extract structured data based on template"""
        template = self.get_template(department)
        if not template:
            return self._extract_generic_data(text)
        
        structured = {
            'department': department,
            'sections': {},
            'metadata': {}
        }
        
        # Extract by sections
        current_section = None
        lines = text.split('\n')
        
        for line in lines:
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Check if this starts a new section
            for section in template.get('sections_found', []):
                pattern = rf'^(?:#+\s*)?{section}:?$'
                if re.search(pattern, line_stripped.lower()):
                    current_section = section
                    structured['sections'][section] = []
                    continue
            
            # Add to current section
            if current_section and line_stripped:
                structured['sections'].setdefault(current_section, []).append(line_stripped)
        
        # Extract dates
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{4}\b', text)
        if dates:
            structured['metadata']['dates_found'] = dates
        
        # Extract metrics
        metrics = re.findall(r'\b\d+(?:\.\d+)?%\b', text)
        if metrics:
            structured['metadata']['metrics'] = metrics
        
        return structured
    
    def _extract_generic_data(self, text):
        """Extract data when no template exists"""
        return {
            'department': 'unknown',
            'lines': text.split('\n'),
            'word_count': len(text.split()),
            'has_dates': bool(re.search(r'\b\d{4}-\d{2}-\d{2}\b', text))
        }
    
    def get_all_templates(self):
        """Get all learned templates"""
        return self.templates

# Global instance
template_manager = TemplateManager()
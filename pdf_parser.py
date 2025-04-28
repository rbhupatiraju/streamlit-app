import pdfplumber
import json
from typing import List, Dict, Any
import re
from datetime import datetime

class PDFParser:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.document_name = pdf_path.split('/')[-1]
        self.elements = []
        
    def _is_title(self, text: str) -> bool:
        """Check if text is likely a title based on formatting and content."""
        # Check for common title patterns
        title_patterns = [
            r'^[A-Z][A-Z\s]+$',  # All caps
            r'^\d+\.\s+[A-Z]',   # Numbered headings
            r'^[A-Z][a-z]+(\s[A-Z][a-z]+)*$'  # Title case
        ]
        return any(re.match(pattern, text.strip()) for pattern in title_patterns)
    
    def _extract_metadata(self, pdf) -> Dict[str, Any]:
        """Extract metadata from PDF."""
        metadata = {
            'author': pdf.metadata.get('Author', ''),
            'title': pdf.metadata.get('Title', ''),
            'creation_date': pdf.metadata.get('CreationDate', ''),
            'modification_date': pdf.metadata.get('ModDate', ''),
            'producer': pdf.metadata.get('Producer', ''),
            'total_pages': len(pdf.pages)
        }
        return metadata
    
    def _extract_footnotes(self, text: str, page_number: int, page) -> List[Dict[str, Any]]:
        """Extract footnotes from text with bounding boxes."""
        footnotes = []
        # Common footnote patterns
        footnote_patterns = [
            r'\[\d+\].*?(?=\n|$)',  # [1] style
            r'\(\d+\].*?(?=\n|$)',  # (1) style
            r'^\d+\.\s.*?(?=\n|$)'  # 1. style
        ]
        
        words = page.extract_words()
        all_footnote_texts = []
        all_footnote_words = []
        
        for pattern in footnote_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                footnote_text = match.group(0).strip()
                footnote_words = [w for w in words if w['text'] in footnote_text]
                if footnote_words:
                    all_footnote_texts.append(footnote_text)
                    all_footnote_words.extend(footnote_words)
        
        if all_footnote_words:
            # Calculate combined footnote bounding box
            x0 = min(w['x0'] for w in all_footnote_words)
            y0 = min(w['top'] for w in all_footnote_words)
            x1 = max(w['x1'] for w in all_footnote_words)
            y1 = max(w['bottom'] for w in all_footnote_words)
            
            footnote = {
                'document_name': self.document_name,
                'section_name': 'Footnotes',
                'element_type': 'footnote',
                'content': '\n'.join(all_footnote_texts),
                'metadata': {
                    'page_number': page_number,
                    'count': len(all_footnote_texts),
                    'bounding_box': {
                        'x0': x0,
                        'y0': y0,
                        'x1': x1,
                        'y1': y1
                    }
                },
                'page_number': page_number
            }
            footnotes.append(footnote)
        
        return footnotes
    
    def _extract_tables(self, page) -> List[Dict[str, Any]]:
        """Extract tables from page and convert to plain text format with bounding boxes."""
        tables = []
        
        # Enhanced table detection settings
        table_settings = {
            "vertical_strategy": "text",  # Use text-based strategy
            "horizontal_strategy": "text",  # Use text-based strategy
            "intersection_y_tolerance": 10,
            "intersection_x_tolerance": 10,
            "snap_y_tolerance": 5,
            "snap_x_tolerance": 5,
            "join_y_tolerance": 3,
            "join_x_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 1,
            "min_words_horizontal": 1
        }
        
        try:
            # Find tables first to get bounding boxes
            found_tables = page.find_tables(table_settings)
            
            # Extract table content with the same settings
            extracted_tables = page.extract_tables(table_settings)
            
            if extracted_tables and found_tables:
                for table_idx, (table, table_bbox) in enumerate(zip(extracted_tables, found_tables)):
                    # Clean and process table content
                    cleaned_table = []
                    for row in table:
                        # Clean each cell and handle None values
                        cleaned_row = []
                        for cell in row:
                            if cell is None:
                                cleaned_row.append("")
                            else:
                                # Clean the cell content
                                cell_text = str(cell).strip()
                                # Remove extra spaces and newlines
                                cell_text = ' '.join(cell_text.split())
                                cleaned_row.append(cell_text)
                        
                        # Only add non-empty rows
                        if any(cell.strip() for cell in cleaned_row):
                            cleaned_table.append(cleaned_row)
                    
                    if cleaned_table:
                        # Convert to plain text format
                        text_rows = []
                        for row in cleaned_table:
                            # Join cells with spaces
                            text_row = ' '.join(cell for cell in row if cell.strip())
                            if text_row.strip():
                                text_rows.append(text_row)
                        
                        # Join all rows with newlines
                        text_content = '\n'.join(text_rows)
                        
                        table_data = {
                            'document_name': self.document_name,
                            'section_name': f'Table {table_idx + 1}',
                            'element_type': 'table',
                            'content': text_content,
                            'metadata': {
                                'rows': len(cleaned_table),
                                'columns': len(cleaned_table[0]) if cleaned_table else 0,
                                'table_index': table_idx,
                                'format': 'text',
                                'bounding_box': {
                                    'x0': table_bbox.bbox[0],
                                    'y0': table_bbox.bbox[1],
                                    'x1': table_bbox.bbox[2],
                                    'y1': table_bbox.bbox[3]
                                }
                            },
                            'page_number': page.page_number
                        }
                        tables.append(table_data)
        
        except Exception as e:
            print(f"Error extracting tables: {str(e)}")
        
        return tables
    
    def _extract_paragraphs(self, text: str, page_number: int, page) -> List[Dict[str, Any]]:
        """Extract paragraphs from text with bounding boxes."""
        paragraphs = []
        current_section = "Introduction"  # Default section name
        
        # Split text into paragraphs (assuming paragraphs are separated by double newlines)
        raw_paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        for para in raw_paragraphs:
            if self._is_title(para):
                current_section = para
                continue
                
            # Get words and their bounding boxes
            words = page.extract_words()
            para_words = [w for w in words if w['text'] in para]
            
            if para_words:
                # Calculate paragraph bounding box
                x0 = min(w['x0'] for w in para_words)
                y0 = min(w['top'] for w in para_words)
                x1 = max(w['x1'] for w in para_words)
                y1 = max(w['bottom'] for w in para_words)
                
                paragraph_data = {
                    'document_name': self.document_name,
                    'section_name': current_section,
                    'element_type': 'paragraph',
                    'content': para,
                    'metadata': {
                        'length': len(para),
                        'word_count': len(para.split()),
                        'bounding_box': {
                            'x0': x0,
                            'y0': y0,
                            'x1': x1,
                            'y1': y1
                        }
                    },
                    'page_number': page_number
                }
                paragraphs.append(paragraph_data)
        
        return paragraphs
    
    def parse(self) -> List[Dict[str, Any]]:
        """Parse the PDF and return structured elements."""
        with pdfplumber.open(self.pdf_path) as pdf:
            # Extract document metadata
            metadata = self._extract_metadata(pdf)
            
            for page in pdf.pages:
                # Extract text
                text = page.extract_text() or ""
                
                # Extract elements
                paragraphs = self._extract_paragraphs(text, page.page_number, page)
                tables = self._extract_tables(page)
                footnotes = self._extract_footnotes(text, page.page_number, page)
                
                # Add all elements to the list
                self.elements.extend(paragraphs)
                self.elements.extend(tables)
                self.elements.extend(footnotes)
        
        return self.elements
    
    def save_to_json(self, output_path: str):
        """Save parsed elements to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.elements, f, indent=2, ensure_ascii=False)

def main():
    # Example usage
    pdf_path = "/Users/ragmeister/Desktop/gsco-12-31-2023.pdf"  # Replace with your PDF path
    output_path = "/Users/ragmeister/Desktop/parsed_elements.json"
    
    parser = PDFParser(pdf_path)
    elements = parser.parse()
    parser.save_to_json(output_path)
    print(f"PDF parsed successfully. Results saved to {output_path}")

if __name__ == "__main__":
    main()

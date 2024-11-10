import json
from pathlib import Path
import logging
from datetime import datetime
import os
import sqlite3
import pandas as pd
from typing import Dict, List, Optional, Union
import re
from collections import defaultdict

class DocumentProcessor:
    def __init__(self):
        self.knowledge_base = {
            "company": """
            מובנה גלובל הינה חברה לשיווק השקעות בעלת רישיון מרשות ניירות ערך.
            החברה מתמחה במוצרים פיננסיים מובנים ופועלת בשקיפות מלאה מול לקוחותיה.
            אנו מספקים פתרונות השקעה מותאמים אישית למשקיעים כשירים.
            """,
            
            "product": """
            המוצרים שלנו הם מכשירים פיננסיים מובנים המונפקים על ידי בנקים בינלאומיים מובילים.
            המוצרים מאפשרים חשיפה לשווקים הפיננסיים עם הגנות מובנות.
            כל מוצר מותאם לצרכי הלקוח ומאפשר נזילות יומית.
            """,
            
            "advantages": """
            1. נזילות יומית עם מחיר מהמנפיק
            2. העסקה ישירה מול הבנק ללא צד שלישי
            3. המוצר נמצא בחשבון הבנק של הלקוח
            4. שקיפות מלאה בתמחור ובתנאים
            5. התאמה אישית לצרכי הלקוח
            """
        }
        
        self.knowledge_categories = {
            "investment_types": [
                "מוצרים מובנים",
                "תעודות פיקדון",
                "אגרות חוב מובנות",
                "מוצרי הגנה"
            ],
            "risk_levels": [
                "סיכון נמוך",
                "סיכון בינוני",
                "סיכון גבוה"
            ],
            "investment_terms": [
                "קצר טווח",
                "בינוני טווח",
                "ארוך טווח"
            ]
        }
        
        self.knowledge_path = Path(__file__).parent / "knowledge"
        self.db_path = Path(__file__).parent / "database" / "documents.db"
        self.setup_logging()
        self.ensure_directories()
        self.setup_database()

    def setup_logging(self):
        """Set up logging configuration"""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        
        if not self.logger.handlers:
            log_dir = Path('logs')
            log_dir.mkdir(exist_ok=True)
            
            # File handler for all logs
            file_handler = logging.FileHandler(
                log_dir / 'document_processor.log',
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            
            # Error file handler
            error_handler = logging.FileHandler(
                log_dir / 'error.log',
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            
            self.logger.addHandler(file_handler)
            self.logger.addHandler(error_handler)

    def ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            self.knowledge_path,
            self.knowledge_path / "processed",
            self.knowledge_path / "raw",
            self.knowledge_path / "temp",
            self.db_path.parent,
            Path("logs")
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)

    def setup_database(self):
        """Initialize SQLite database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create documents table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        content TEXT,
                        document_type TEXT,
                        created_at TIMESTAMP,
                        updated_at TIMESTAMP,
                        metadata TEXT
                    )
                """)
                
                # Create knowledge_base table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS knowledge_base (
                        id TEXT PRIMARY KEY,
                        category TEXT,
                        content TEXT,
                        last_updated TIMESTAMP,
                        source TEXT
                    )
                """)
                
                # Create document_tags table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS document_tags (
                        document_id TEXT,
                        tag TEXT,
                        FOREIGN KEY (document_id) REFERENCES documents(id)
                    )
                """)
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Database setup error: {str(e)}")
            raise

    def get_core_knowledge(self, knowledge_type: str) -> str:
        """Retrieve core knowledge by type with enhanced error handling"""
        try:
            if knowledge_type not in self.knowledge_base:
                self.logger.warning(f"Unknown knowledge type requested: {knowledge_type}")
                return ""
            
            knowledge = self.knowledge_base[knowledge_type]
            self.logger.debug(f"Retrieved knowledge for type: {knowledge_type}")
            return knowledge
            
        except Exception as e:
            self.logger.error(f"Error retrieving core knowledge for {knowledge_type}: {str(e)}")
            return ""

    def query_knowledge(self, query: str) -> List[str]:
        """Query additional knowledge based on user input with advanced processing"""
        try:
            relevant_info = []
            query_lower = query.lower()
            
            # Create keyword mappings
            keyword_mappings = {
                'risk_protection': {
                    'keywords': ['סיכון', 'הגנה', 'בטוח', 'בטחון', 'אבטחה'],
                    'response': """
                    המוצרים שלנו מגיעים עם מנגנוני הגנה מובנים.
                    כל השקעה כרוכה בסיכונים, אך אנו מתמחים בהתאמת רמת הסיכון לצרכי הלקוח.
                    המוצרים שלנו מציעים רמות הגנה שונות בהתאם להעדפות הלקוח.
                    """
                },
                'returns': {
                    'keywords': ['תשואה', 'רווח', 'החזר', 'ריבית', 'רווחים'],
                    'response': """
                    המוצרים שלנו מציעים פוטנציאל תשואה בהתאם לתנאי השוק ורמת הסיכון.
                    אנו מתמחים בבניית מוצרים עם יחס סיכון-תשואה אטרקטיבי.
                    התשואה מותאמת לפרופיל הסיכון של הלקוח ולתנאי השוק.
                    """
                },
                'liquidity': {
                    'keywords': ['נזילות', 'משיכה', 'פדיון', 'זמינות', 'גישה'],
                    'response': """
                    המוצרים שלנו מציעים נזילות יומית עם מחיר מהמנפיק.
                    ניתן לפדות את ההשקעה בכל יום מסחר.
                    אין תקופת נעילה והכסף נשאר נזיל.
                    """
                },
                'process': {
                    'keywords': ['תהליך', 'השקעה', 'להשקיע', 'להתחיל', 'התחלה'],
                    'response': """
                    תהליך ההשקעה מתחיל בפגישת היכרות והתאמה.
                    אנו מתאימים את המוצר לצרכים הספציפיים של כל לקוח.
                    ההשקעה מתבצעת ישירות מול הבנק בחשבון הלקוח.
                    """
                },
                'company': {
                    'keywords': ['חברה', 'רישיון', 'פיקוח', 'רגולציה', 'אמינות'],
                    'response': """
                    מובנה גלובל פועלת ברישיון של רשות ניירות ערך.
                    אנו פועלים בשקיפות מלאה ובהתאם לכל הדרישות הרגולטוריות.
                    החברה מתמחה במוצרים פיננסיים מובנים מעל עשור.
                    """
                }
            }
            
            # Check for keyword matches and add relevant responses
            for category in keyword_mappings.values():
                if any(keyword in query_lower for keyword in category['keywords']):
                    relevant_info.append(category['response'])
            
            # Add custom response for complex queries
            if len(relevant_info) > 1:
                relevant_info.append("""
                אנחנו כאן לענות על כל השאלות שלך ולהתאים עבורך את הפתרון המושלם.
                נשמח לקבוע פגישת ייעוץ אישית לדיון מעמיק יותר.
                """)
            
            return relevant_info
            
        except Exception as e:
            self.logger.error(f"Error querying knowledge: {str(e)}")
            return []

    def save_processed_document(self, document_data: Dict) -> bool:
        """Save processed document with metadata"""
        try:
            doc_id = str(datetime.now().timestamp())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Save main document data
                cursor.execute("""
                    INSERT INTO documents (
                        id, title, content, document_type, 
                        created_at, updated_at, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    document_data.get('title', ''),
                    json.dumps(document_data.get('content', {}), ensure_ascii=False),
                    document_data.get('type', 'general'),
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                    json.dumps(document_data.get('metadata', {}), ensure_ascii=False)
                ))
                
                # Save document tags
                tags = document_data.get('tags', [])
                cursor.executemany("""
                    INSERT INTO document_tags (document_id, tag)
                    VALUES (?, ?)
                """, [(doc_id, tag) for tag in tags])
                
                conn.commit()
            
            self.logger.info(f"Document saved successfully with ID: {doc_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving document: {str(e)}")
            return False

    def load_processed_document(self, document_id: str) -> Optional[Dict]:
        """Load a processed document by ID with full metadata"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get document data
                cursor.execute("""
                    SELECT * FROM documents WHERE id = ?
                """, (document_id,))
                doc = cursor.fetchone()
                
                if not doc:
                    return None
                
                # Get document tags
                cursor.execute("""
                    SELECT tag FROM document_tags WHERE document_id = ?
                """, (document_id,))
                tags = [row['tag'] for row in cursor.fetchall()]
                
                # Construct full document object
                document = dict(doc)
                document['content'] = json.loads(document['content'])
                document['metadata'] = json.loads(document['metadata'])
                document['tags'] = tags
                
                return document
                
        except Exception as e:
            self.logger.error(f"Error loading document {document_id}: {str(e)}")
            return None

    def update_knowledge_base(self, knowledge_type: str, content: str) -> bool:
        """Update knowledge base with new content"""
        try:
            if knowledge_type not in self.knowledge_base:
                self.logger.warning(f"Attempted to update unknown knowledge type: {knowledge_type}")
                return False
                
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO knowledge_base (
                        id, category, content, last_updated, source
                    ) VALUES (?, ?, ?, ?, ?)
                """, (
                    f"{knowledge_type}_{datetime.now().timestamp()}",
                    knowledge_type,
                    content,
                    datetime.now().isoformat(),
                    "manual_update"
                ))
                
                conn.commit()
            
            # Update in-memory knowledge base
            self.knowledge_base[knowledge_type] = content
            self.logger.info(f"Knowledge base updated for type: {knowledge_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating knowledge base: {str(e)}")
            return False

    def get_document_stats(self) -> Dict:
        """Get statistics about processed documents"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {
                    'total_documents': 0,
                    'document_types': defaultdict(int),
                    'tags': defaultdict(int),
                    'latest_update': None
                }
                
                # Count total documents
                cursor.execute("SELECT COUNT(*) FROM documents")
                stats['total_documents'] = cursor.fetchone()[0]
                
                # Count documents by type
                cursor.execute("""
                    SELECT document_type, COUNT(*) 
                    FROM documents 
                    GROUP BY document_type
                """)
                for doc_type, count in cursor.fetchall():
                    stats['document_types'][doc_type] = count
                
                # Count tag usage
                cursor.execute("""
                    SELECT tag, COUNT(*) 
                    FROM document_tags 
                    GROUP BY
                 SELECT tag, COUNT(*) 
                    FROM document_tags 
                    GROUP BY tag
                """)
                for tag, count in cursor.fetchall():
                    stats['tags'][tag] = count
                
                # Get latest update
                cursor.execute("""
                    SELECT MAX(updated_at) 
                    FROM documents
                """)
                stats['latest_update'] = cursor.fetchone()[0]
                
                return dict(stats)
                
        except Exception as e:
            self.logger.error(f"Error getting document stats: {str(e)}")
            return {}

    def search_documents(self, query: str, document_type: Optional[str] = None) -> List[Dict]:
        """Search through processed documents"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if document_type:
                    sql = """
                        SELECT * FROM documents 
                        WHERE (title LIKE ? OR content LIKE ?) 
                        AND document_type = ?
                        ORDER BY created_at DESC
                    """
                    params = (f"%{query}%", f"%{query}%", document_type)
                else:
                    sql = """
                        SELECT * FROM documents 
                        WHERE title LIKE ? OR content LIKE ?
                        ORDER BY created_at DESC
                    """
                    params = (f"%{query}%", f"%{query}%")
                
                cursor.execute(sql, params)
                documents = [dict(row) for row in cursor.fetchall()]
                
                # Add tags to each document
                for doc in documents:
                    cursor.execute("""
                        SELECT tag FROM document_tags 
                        WHERE document_id = ?
                    """, (doc['id'],))
                    doc['tags'] = [row['tag'] for row in cursor.fetchall()]
                    doc['content'] = json.loads(doc['content'])
                    doc['metadata'] = json.loads(doc['metadata'])
                
                return documents
                
        except Exception as e:
            self.logger.error(f"Error searching documents: {str(e)}")
            return []

    def analyze_document_content(self, content: str) -> Dict:
        """Analyze document content for key information"""
        try:
            analysis = {
                'word_count': len(content.split()),
                'key_terms': [],
                'categories': [],
                'suggested_tags': []
            }
            
            # Check for key investment terms
            investment_terms = {
                'risk': ['סיכון', 'הגנה', 'בטחון'],
                'returns': ['תשואה', 'רווח', 'ריבית'],
                'liquidity': ['נזילות', 'משיכה', 'פדיון'],
                'process': ['תהליך', 'השקעה', 'התחלה']
            }
            
            for category, terms in investment_terms.items():
                if any(term in content.lower() for term in terms):
                    analysis['categories'].append(category)
            
            # Extract potential key terms
            words = re.findall(r'\b\w+\b', content.lower())
            word_freq = defaultdict(int)
            for word in words:
                word_freq[word] += 1
            
            # Get top terms
            analysis['key_terms'] = sorted(
                word_freq.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:10]
            
            # Suggest tags based on content
            for category in self.knowledge_categories:
                for term in self.knowledge_categories[category]:
                    if term.lower() in content.lower():
                        analysis['suggested_tags'].append(term)
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing document content: {str(e)}")
            return {}

    def export_knowledge_base(self, format: str = 'json') -> Union[str, Dict]:
        """Export knowledge base in specified format"""
        try:
            if format.lower() == 'json':
                return json.dumps(self.knowledge_base, ensure_ascii=False, indent=2)
            elif format.lower() == 'dict':
                return self.knowledge_base
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        except Exception as e:
            self.logger.error(f"Error exporting knowledge base: {str(e)}")
            return {} if format.lower() == 'dict' else "{}"

    def import_knowledge_base(self, data: Union[str, Dict], format: str = 'json') -> bool:
        """Import knowledge base from specified format"""
        try:
            if format.lower() == 'json':
                new_knowledge = json.loads(data)
            elif format.lower() == 'dict':
                new_knowledge = data
            else:
                raise ValueError(f"Unsupported import format: {format}")
            
            # Validate and update knowledge base
            if isinstance(new_knowledge, dict):
                self.knowledge_base.update(new_knowledge)
                self.logger.info("Knowledge base updated successfully")
                return True
            else:
                raise ValueError("Invalid knowledge base format")
                
        except Exception as e:
            self.logger.error(f"Error importing knowledge base: {str(e)}")
            return False

    def cleanup_old_documents(self, days: int = 30) -> bool:
        """Clean up old processed documents"""
        try:
            cutoff_date = datetime.now() - pd.Timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old documents
                cursor.execute("""
                    DELETE FROM documents 
                    WHERE created_at < ?
                """, (cutoff_date.isoformat(),))
                
                # Delete orphaned tags
                cursor.execute("""
                    DELETE FROM document_tags 
                    WHERE document_id NOT IN (
                        SELECT id FROM documents
                    )
                """)
                
                conn.commit()
                
            self.logger.info(f"Cleaned up documents older than {days} days")
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up old documents: {str(e)}")
            return False   
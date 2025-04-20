import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ttkthemes import ThemedTk
import PyPDF2
import json
import sqlite3
import os
from datetime import datetime
from PIL import Image, ImageTk
import re

# --- spaCy imports for advanced NLP extraction (works offline after model download) ---
import spacy
from spacy.matcher import PhraseMatcher

class ResumeExtractor:
    # Common Indian and Western name patterns
    NAME_PATTERNS = [
        # Pattern for names with titles
        r'(?:Mr\.|Mrs\.|Ms\.|Dr\.|Prof\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
        # Pattern for names without titles (2-4 words, each capitalized)
        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})$',
        # Pattern for names with initials
        r'([A-Z](?:\.[A-Z])*\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    ]

    # Regex patterns for date extraction
    DATE_PATTERNS = [
        r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*[,-]?\s*(20\d{2})',
        r'(\d{1,2})/(\d{4})',
        r'(\d{4})'
    ]

    # Position keywords to help identify job titles
    POSITION_KEYWORDS = {
        'intern', 'engineer', 'developer', 'manager', 'lead', 'analyst', 'consultant',
        'coordinator', 'administrator', 'specialist', 'director', 'head', 'architect',
        'designer', 'researcher', 'scientist', 'associate', 'executive', 'president',
        'ceo', 'cto', 'cfo', 'vp', 'vice president', 'founder', 'co-founder',
        'team lead', 'project manager', 'product manager', 'program manager',
        'software', 'web', 'mobile', 'data', 'cloud', 'devops', 'full stack',
        'frontend', 'backend', 'qa', 'test', 'testing', 'support', 'technical',
        'research', 'teaching', 'assistant', 'professor', 'lecturer'
    }
    
    # Common technical skills to look for
    COMMON_SKILLS = {
        # Programming Languages
        'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'ruby', 'php', 'swift', 'kotlin', 'go',
        'rust', 'scala', 'perl', 'r', 'matlab', 'sql', 'bash', 'shell', 'powershell', 'dart',
        'objective-c', 'assembly', 'haskell', 'lua', 'julia', 'groovy', 'fortran',
        
        # Web Technologies
        'html', 'css', 'sass', 'less', 'bootstrap', 'tailwind', 'react', 'angular', 'vue',
        'svelte', 'jquery', 'node.js', 'express', 'django', 'flask', 'spring', 'asp.net',
        'laravel', 'ruby on rails', 'gatsby', 'next.js', 'nuxt.js', 'webpack', 'babel',
        'graphql', 'rest api', 'soap', 'xml', 'json', 'ajax', 'websocket',
        
        # Databases
        'sql', 'mysql', 'postgresql', 'mongodb', 'oracle', 'sqlite', 'redis', 'cassandra',
        'dynamodb', 'mariadb', 'elasticsearch', 'neo4j', 'couchbase', 'firebase',
        'microsoft sql server', 'influxdb', 'apache hbase', 'realm',
        
        # Cloud & DevOps
        'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git', 'ci/cd',
        'terraform', 'ansible', 'puppet', 'chef', 'nginx', 'apache', 'linux', 'unix',
        'windows server', 'vmware', 'virtualbox', 'vagrant', 'heroku', 'netlify',
        'vercel', 'cloudflare', 'aws lambda', 'serverless',
        
        # Data Science & AI
        'machine learning', 'deep learning', 'artificial intelligence', 'neural networks',
        'tensorflow', 'pytorch', 'keras', 'scikit-learn', 'pandas', 'numpy', 'scipy',
        'matplotlib', 'seaborn', 'tableau', 'power bi', 'opencv', 'nltk', 'spacy',
        'hadoop', 'spark', 'kafka', 'airflow', 'mlops', 'computer vision', 'nlp',
        
        # Mobile Development
        'android', 'ios', 'swift', 'react native', 'flutter', 'xamarin', 'ionic',
        'kotlin', 'objective-c', 'mobile development', 'android studio', 'xcode',
        
        # Testing & QA
        'junit', 'selenium', 'cypress', 'jest', 'mocha', 'pytest', 'testng',
        'cucumber', 'postman', 'jmeter', 'gatling', 'katalon', 'appium',
        
        # Project Management & Tools
        'agile', 'scrum', 'kanban', 'jira', 'confluence', 'trello', 'asana',
        'git', 'github', 'gitlab', 'bitbucket', 'svn', 'mercurial',
        
        # Security
        'cybersecurity', 'penetration testing', 'ethical hacking', 'cryptography',
        'oauth', 'jwt', 'ssl/tls', 'encryption', 'firewall', 'security+',
        
        # Other Technical Skills
        'microservices', 'restful apis', 'soap', 'websockets', 'oauth',
        'design patterns', 'oop', 'functional programming', 'parallel programming',
        'blockchain', 'ethereum', 'solidity', 'web3', 'unity', 'unreal engine'
    }
    
    # List of common skills for matching
    DEFAULT_SKILLS = [
        "Python", "Java", "C++", "C#", "JavaScript", "SQL", "HTML", "CSS", "Machine Learning", "Deep Learning",
        "Data Analysis", "Project Management", "Communication", "Leadership", "Teamwork", "Git", "Django", "Flask",
        "React", "Angular", "Node.js", "Tableau", "Power BI", "Excel", "AWS", "Azure", "Docker", "Kubernetes"
    ]

    def __init__(self):
        # Initialize main window
        self.root = ThemedTk(theme="arc")  # Modern theme
        self.root.title("Resume Skill Extractor")
        self.root.geometry("800x600")

        # --- Initialize spaCy NLP model (requires en_core_web_sm, see note below) ---
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            messagebox.showerror(
                "spaCy Model Missing",
                "spaCy English model not found. Please run: python -m spacy download en_core_web_sm\nThen restart the app."
            )
            raise
        # Initialize PhraseMatcher for skills
        self.matcher = PhraseMatcher(self.nlp.vocab, attr='LOWER')
        patterns = [self.nlp(skill) for skill in self.DEFAULT_SKILLS]
        self.matcher.add("SKILLS", patterns)

        # Initialize database
        self.init_db()

        # Create GUI
        self.create_gui()

    def init_db(self):
        """Initialize SQLite database and handle migrations"""
        self.conn = sqlite3.connect('resumes.db')
        self.cursor = self.conn.cursor()

        # Create table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                email TEXT,
                phone TEXT,
                skills TEXT,
                work_experience TEXT,
                upload_date TEXT,
                filename TEXT
            )
        ''')

        # Check if status column exists
        self.cursor.execute("PRAGMA table_info(resumes)")
        columns = [column[1] for column in self.cursor.fetchall()]

        if 'status' not in columns:
            # Add status column to existing table
            self.cursor.execute('ALTER TABLE resumes ADD COLUMN status TEXT DEFAULT "To Review"')
            # Update existing rows
            self.cursor.execute('UPDATE resumes SET status = "To Review" WHERE status IS NULL')

        self.conn.commit()

    def create_gui(self):
        """Create the main GUI elements"""
        # Create main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure main frame grid weights
        main_frame.columnconfigure(0, weight=2)  # Results column gets more space
        main_frame.columnconfigure(1, weight=1)  # History column gets less space
        main_frame.rowconfigure(2, weight=1)     # Results/History row expands
        
        # Title
        title = ttk.Label(main_frame, text="Resume Skill Extractor", font=('Helvetica', 16, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Upload frame
        upload_frame = ttk.LabelFrame(main_frame, text="Upload Resume", padding="10")
        upload_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.file_label = ttk.Label(upload_frame, text="No file selected")
        self.file_label.grid(row=0, column=0, padx=5)
        
        upload_btn = ttk.Button(upload_frame, text="Select PDF", command=self.select_file)
        upload_btn.grid(row=0, column=1, padx=5)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(main_frame, text="Filter by Skills", padding="10")
        filter_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.skill_filter = ttk.Entry(filter_frame)
        self.skill_filter.grid(row=0, column=0, padx=5, sticky=(tk.W, tk.E))
        self.skill_filter.insert(0, "Enter skills (comma-separated)")
        self.skill_filter.bind('<FocusIn>', lambda e: self.skill_filter.delete(0, tk.END) if 
                               self.skill_filter.get() == "Enter skills (comma-separated)" else None)
        
        filter_btn = ttk.Button(filter_frame, text="Filter", command=self.filter_resumes)
        filter_btn.grid(row=0, column=1, padx=5)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Extracted Information", padding="10")
        results_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        # Text widget for displaying results
        self.results_text = tk.Text(results_frame, height=10, width=50)
        self.results_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for results
        scrollbar = ttk.Scrollbar(results_frame, orient=tk.VERTICAL, command=self.results_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        # History frame
        history_frame = ttk.LabelFrame(main_frame, text="Previous Uploads", padding="10")
        history_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=5)
        history_frame.columnconfigure(0, weight=1)
        history_frame.rowconfigure(0, weight=1)
        
        # Treeview for history
        self.history_tree = ttk.Treeview(history_frame, columns=('Date', 'Filename', 'Status'), show='headings', height=10)
        self.history_tree.heading('Date', text='Date')
        self.history_tree.heading('Filename', text='Filename')
        self.history_tree.heading('Status', text='Status')
        self.history_tree.column('Status', width=100)
        self.history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar for history
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        history_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        
        # Bind history selection
        self.history_tree.bind('<<TreeviewSelect>>', self.show_selected_resume)
        
        # Resume management frame
        management_frame = ttk.LabelFrame(main_frame, text="Resume Management", padding="10")
        management_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Status buttons
        ttk.Button(management_frame, text="Accept", command=lambda: self.update_resume_status('Accept'), style='Accept.TButton').grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(management_frame, text="Reject", command=lambda: self.update_resume_status('Reject'), style='Reject.TButton').grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(management_frame, text="To Review", command=lambda: self.update_resume_status('To Review')).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(management_frame, text="Delete Resume", command=self.delete_resume).grid(row=0, column=3, padx=5, pady=5)
        
        # Status filter
        filter_frame = ttk.LabelFrame(main_frame, text="Filter by Status", padding="10")
        filter_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.status_var = tk.StringVar(value='All')
        ttk.Label(filter_frame, text="Show:").grid(row=0, column=0, padx=5)
        for i, status in enumerate(['All', 'Accept', 'Reject', 'To Review']):
            ttk.Radiobutton(filter_frame, text=status, variable=self.status_var, value=status, command=self.load_history).grid(row=0, column=i+1, padx=5)
        
        # Configure button styles
        style = ttk.Style()
        style.configure('Accept.TButton', foreground='green')
        style.configure('Reject.TButton', foreground='red')
        
        # Load history
        self.load_history()
        
    def select_file(self):
        """Handle file selection"""
        filename = filedialog.askopenfilename(
            title="Select PDF Resume",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if filename:
            self.file_label.config(text=os.path.basename(filename))
            self.process_pdf(filename)
    
    def process_pdf(self, filename):
        """Process the selected PDF file"""
        try:
            # Extract text from PDF
            text = self.extract_text_from_pdf(filename)
            
            # Extract information
            info = self.extract_information(text)
            
            # Save to database
            self.save_to_db(info, filename)
            
            # Display results
            self.display_results(info)
            
            # Refresh history
            self.load_history()
            
            messagebox.showinfo("Success", "Resume processed successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error processing PDF: {str(e)}")
    
    def extract_text_from_pdf(self, file_path):
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    
    def extract_information(self, text):
        """
        Extract relevant information from resume text using spaCy for advanced NLP.
        - Name: First PERSON entity found
        - Skills: PhraseMatcher on a predefined list
        - Email/Phone: Heuristic
        - Work Experience: NER + keyword heuristics (ORG, DATE, position keyword)
        """
        doc = self.nlp(text)
        lines = text.split('\n')
        info = {
            'name': '',
            'email': '',
            'phone': '',
            'skills': [],
            'work_experience': []
        }
        # --- Skills Extraction ---
        matches = self.matcher(doc)
        found_skills = set()
        for match_id, start, end in matches:
            found_skills.add(doc[start:end].text)
        info['skills'] = sorted(found_skills)

        # --- Work Experience Extraction ---
        experience_entries = []
        for sent in doc.sents:
            sent_text = sent.text.strip()
            org = None
            date = None
            position = None
            # Extract organization and date entities
            for ent in sent.ents:
                if ent.label_ == "ORG":
                    org = ent.text
                if ent.label_ == "DATE":
                    date = ent.text
            # Extract a position by keyword
            for word in sent_text.split():
                if word.lower() in self.POSITION_KEYWORDS:
                    position = word
                    break
            # If this sentence looks like work experience, add it
            if org or date or position or any(word in sent_text.lower() for word in ['experience', 'work', 'employment', 'company', 'internship']):
                experience_entries.append({
                    'position': position if position else '',
                    'organization': org if org else '',
                    'duration': date if date else '',
                    'dates': date if date else '',
                    'raw': sent_text
                })
        # Remove duplicates based on 'raw' text
        seen = set()
        uniq_experience = []
        for entry in experience_entries:
            if entry['raw'] not in seen:
                uniq_experience.append(entry)
                seen.add(entry['raw'])
        info['work_experience'] = uniq_experience

        # --- Email and Phone Extraction ---
        for line in lines:
            # Email detection
            email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', line)
            if email_match:
                info['email'] = email_match.group()
                break
            # Phone detection
            phone_match = re.search(r'\d{10}', line)
            if phone_match:
                info['phone'] = phone_match.group()
                break
        return info

        # Detect start of a new section
        if in_experience and any(any(kw in lower_line for kw in kws) for sec, kws in section_headers.items() if sec != 'experience'):
            in_experience = False
        if in_experience:
            # Look for date patterns
            dates = []
            for pattern in self.DATE_PATTERNS:
                matches = re.finditer(pattern, line)
                for match in matches:
                    dates.append(match.group())
            # If we found dates, this might be a new position
            if dates and len(line) < 150:
                # Try to extract position and organization
                parts = re.split(r'\s*(?:at|@|-|,|\||with|for)\s*', line)
                position = parts[0].strip() if len(parts) > 0 else ''
                org = parts[1].strip() if len(parts) > 1 else ''
                exp_entry = {
                    'position': position.title(),
                    'organization': org,
                    'dates': ', '.join(dates),
                    'duration': ''
                }
                info['work_experience'].append(exp_entry)
        # If no work experience found, leave as empty list
        # Section detection
        if any(word in lower_line for word in ['skills', 'expertise', 'competencies', 'technical skills']):
            current_section = 'skills'
            skill_section_found = True
        elif any(word in lower_line for word in ['experience', 'employment', 'work history']):
            current_section = 'experience'
            
            # Skills extraction - only from skills section
            if current_section == 'skills':
                # Skip lines that look like headers
                if any(header in lower_line for header in ['skills:', 'expertise:', 'competencies:', 'technical skills:']):
                    pass  # Do nothing, skip
                # Skip lines that look like they're from other sections
                elif any(header in lower_line for header in ['experience', 'education', 'projects', 'achievements']):
                    current_section = None
                else:
                    # Split by common delimiters and process each potential skill
                    for skill in re.split('[,•\n\t|/]', line):
                        skill = skill.strip()
                        # Remove common bullet points and symbols
                        skill = re.sub(r'^[-•●\*]\s*', '', skill)
                        # Skip if too short or looks like a date/number
                        if len(skill) < 2 or skill.isdigit() or re.match(r'\d{4}', skill):
                            continue
                        # Skip if it's a common word that's not a skill
                        if skill.lower() in ['and', 'or', 'in', 'with', 'using', 'etc', 'etc.', 'including']:
                            continue
                        # Add skill with proper formatting
                        if skill.isupper() and len(skill) <= 5:  # Keep acronyms uppercase
                            info['skills'].add(skill)
                        else:
                            # Capitalize first letter of each word for normal skills
                            formatted_skill = ' '.join(word.capitalize() if not word.isupper() 
                                                      else word for word in skill.split())
                            info['skills'].add(formatted_skill)
            
            # Work experience extraction
            if current_section == 'experience':
                # Look for date patterns
                dates = []
                for pattern in self.DATE_PATTERNS:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        dates.append(match.group())
                # If we found dates, this might be a new position
                if dates and len(line) < 150:  # Allow slightly longer lines for full position details
                    # Skip if this line appears to be a bullet point or description
                    if line.strip().startswith(('•', '-', '>', '*')) or len(line.strip()) > 100:
                        pass  # Do nothing, skip
                    else:
                        # Try to extract position and organization
                        # Common patterns: "Position at Organization" or "Position - Organization"
                        parts = re.split(r'\s*(?:at|@|-|,|\||with|for)\s*', line)
                        if len(parts) >= 1:
                            # Check if any part contains position keywords
                            position_part = None
                            org_part = None
                            for part in parts:
                                part = part.strip().lower()
                                # If this part contains a position keyword, it's likely the position
                                if any(keyword in part for keyword in self.POSITION_KEYWORDS):
                                    position_part = part
                                    break
                            if position_part:
                                # The other part is likely the organization
                                org_part = next((p.strip() for p in parts if p.strip().lower() != position_part), '')
                            else:
                                # If no position keyword found, use first part as position
                                position_part = parts[0].strip()
                                org_part = parts[1].strip() if len(parts) > 1 else ''
                            position = position_part.title()  # Capitalize position title
                            org = org_part.strip()
                            # Skip if we don't have both position and organization
                            if not position or not org:
                                pass  # Do nothing, skip
                            else:
                                # Calculate duration if possible
                                duration = ''
                                if len(dates) >= 2:
                                    try:
                                        start_year = int(re.search(r'20\d{2}', dates[0]).group())
                                        end_year = int(re.search(r'20\d{2}', dates[1]).group())
                                        duration = f"{end_year - start_year} years"
                                    except:
                                        pass
                        
                        # Add to work experience list
                        exp_entry = {
                            'position': position,
                            'organization': org,
                            'dates': ' - '.join(dates[:2]) if len(dates) >= 2 else dates[0] if dates else '',
                            'duration': duration
                        }
                        info['work_experience'].append(exp_entry)
        
        # If no skills section was found, make sure we have some skills from keyword matching
        if not skill_section_found:
            # Scan the entire text again for technical terms
            text_lower = text.lower()
            for skill in self.COMMON_SKILLS:
                if skill in text_lower:
                    info['skills'].add(skill)
        
        # Extract additional skills (words starting with uppercase followed by lowercase)
        potential_skills = set()
        for line in lines:
            # Find words that start with uppercase followed by lowercase (potential technical terms)
            matches = re.finditer(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b', line)
            for match in matches:
                word = match.group()
                if len(word) > 2:  # Avoid short abbreviations
                    potential_skills.add(word.lower())
        
        # Add potential skills to the skills set
        info['skills'].update(potential_skills)
        
        # Format skills with proper capitalization
        formatted_skills = []
        for skill in sorted(info['skills']):
            # Handle special cases like 'iOS', 'macOS', etc.
            if skill.lower() in {'ios', 'macos'}:
                formatted_skills.append(skill.upper())
            # Handle multi-word skills
            elif ' ' in skill:
                formatted_skills.append(' '.join(word.capitalize() for word in skill.split()))
            # Handle skills with dots like 'node.js'
            elif '.' in skill:
                formatted_skills.append('.'.join(word.capitalize() for word in skill.split('.')))
            else:
                formatted_skills.append(skill.capitalize())
        
        info['skills'] = formatted_skills
        return info
    
    def save_to_db(self, info, filename):
        """Save extracted information to database"""
        self.cursor.execute('''
            INSERT INTO resumes (name, email, phone, skills, work_experience, upload_date, filename, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            info['name'],
            info['email'],
            info['phone'],
            json.dumps(info['skills']),
            json.dumps([{  # Convert work experience entries to a consistent format
                'position': exp.get('position', ''),
                'organization': exp.get('organization', ''),
                'dates': exp.get('dates', ''),
                'duration': exp.get('duration', '')
            } for exp in info['work_experience']]),
            datetime.now().isoformat(),
            os.path.basename(filename),
            'To Review'
        ))
        self.conn.commit()
    
    def load_history(self):
        """Load upload history from database with status filter"""
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Load history from database with status filter
        status_filter = self.status_var.get()
        if status_filter == 'All':
            self.cursor.execute('SELECT upload_date, filename, status FROM resumes ORDER BY upload_date DESC')
        else:
            self.cursor.execute('SELECT upload_date, filename, status FROM resumes WHERE status = ? ORDER BY upload_date DESC', (status_filter,))
        
        for row in self.cursor.fetchall():
            date = datetime.fromisoformat(row[0]).strftime('%Y-%m-%d %H:%M')
            item = self.history_tree.insert('', 'end', values=(date, row[1], row[2]))
            
            # Color-code based on status
            if row[2] == 'Accept':
                self.history_tree.tag_configure('accept', foreground='green')
                self.history_tree.item(item, tags=('accept',))
            elif row[2] == 'Reject':
                self.history_tree.tag_configure('reject', foreground='red')
                self.history_tree.item(item, tags=('reject',))
    
    def update_resume_status(self, status):
        """Update the status of the selected resume"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to update its status.")
            return
        
        filename = self.history_tree.item(selection[0])['values'][1]
        self.cursor.execute('UPDATE resumes SET status = ? WHERE filename = ?', (status, filename))
        self.conn.commit()
        self.load_history()
    
    def delete_resume(self):
        """Delete the selected resume from the database"""
        selection = self.history_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a resume to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this resume?"):
            filename = self.history_tree.item(selection[0])['values'][1]
            self.cursor.execute('DELETE FROM resumes WHERE filename = ?', (filename,))
            self.conn.commit()
            self.load_history()
    
    def show_selected_resume(self, event):
        """Display selected resume from history"""
        selection = self.history_tree.selection()
        if not selection:
            return
        
        # Get filename from selected item
        filename = self.history_tree.item(selection[0])['values'][1]
        
        # Fetch resume data
        self.cursor.execute('''
            SELECT email, phone, skills, work_experience
            FROM resumes WHERE filename = ?
        ''', (filename,))
        row = self.cursor.fetchone()
        
        if row:
            # Display in results text widget
            self.results_text.delete(1.0, tk.END)
            self.results_text.insert(tk.END, f"Email: {row[0]}\n\n")
            self.results_text.insert(tk.END, f"Phone: {row[1]}\n\n")
            self.results_text.insert(tk.END, "Skills:\n")
            for skill in json.loads(row[2]):
                self.results_text.insert(tk.END, f"- {skill}\n")
            
            # Display work experience in table format
            work_exp = json.loads(row[3])
            self.results_text.insert(tk.END, "\nWork Experience:\n")
            self.results_text.insert(tk.END, "-" * 60 + "\n")
            self.results_text.insert(tk.END, "{:<25} {:<20} {:<15}\n".format("Position", "Organization", "Duration"))
            self.results_text.insert(tk.END, "-" * 60 + "\n")
            
            for exp in work_exp:
                self.results_text.insert(tk.END, "{:<25} {:<20} {:<15}\n".format(
                    exp['position'][:24],
                    exp['organization'][:19],
                    exp['duration'] if exp['duration'] else exp['dates']
                ))
            self.results_text.insert(tk.END, "-" * 60)
    
    def display_results(self, info):
        """Display extracted information in the results text widget"""
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Email: {info['email']}\n\n")
        self.results_text.insert(tk.END, f"Phone: {info['phone']}\n\n")
        self.results_text.insert(tk.END, "Skills:\n")
        for skill in info['skills']:
            self.results_text.insert(tk.END, f"- {skill}\n")
        
        self.results_text.insert(tk.END, "\nWork Experience:\n")
        self.results_text.insert(tk.END, "-" * 60 + "\n")
        self.results_text.insert(tk.END, "{:<25} {:<20} {:<15}\n".format("Position", "Organization", "Duration"))
        self.results_text.insert(tk.END, "-" * 60 + "\n")
        
        for exp in info['work_experience']:
            self.results_text.insert(tk.END, "{:<25} {:<20} {:<15}\n".format(
                exp['position'][:24],
                exp['organization'][:19],
                exp['duration'] if exp['duration'] else exp['dates']
            ))
        self.results_text.insert(tk.END, "-" * 60)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()
        
    def filter_resumes(self):
        """Filter resumes based on required skills"""
        skill_text = self.skill_filter.get()
        if skill_text == "Enter skills (comma-separated)" or not skill_text.strip():
            return
            
        required_skills = [s.strip().lower() for s in skill_text.split(',')]
        
        # Clear existing items
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        
        # Query resumes with matching skills
        self.cursor.execute('SELECT upload_date, filename, skills FROM resumes ORDER BY upload_date DESC')
        for row in self.cursor.fetchall():
            resume_skills = [s.lower() for s in json.loads(row[2])]
            # Check if any of the required skills are in the resume's skills
            if any(skill in resume_skills for skill in required_skills):
                date = datetime.fromisoformat(row[0]).strftime('%Y-%m-%d %H:%M')
                self.history_tree.insert('', 'end', values=(date, row[1]))

if __name__ == "__main__":
    app = ResumeExtractor()
    app.run()

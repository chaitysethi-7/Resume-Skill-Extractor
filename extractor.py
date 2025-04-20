import spacy
from spacy.matcher import PhraseMatcher
import PyPDF2
import re

nlp = spacy.load("en_core_web_sm")
matcher = PhraseMatcher(nlp.vocab, attr='LOWER')

COMMON_SKILLS = [
    # Add your skills here, e.g.:
    'python', 'java', 'c++', 'sql', 'javascript', 'html', 'css', 'react', 'node.js', 'django', 'flask',
    'machine learning', 'deep learning', 'data science', 'nlp', 'aws', 'azure', 'git', 'docker', 'kubernetes'
]

patterns = [nlp.make_doc(skill) for skill in COMMON_SKILLS]
matcher.add("SKILLS", patterns)

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

def extract_information(text):
    doc = nlp(text)
    lines = text.split('\n')
    info = {
        'name': '',
        'email': '',
        'phone': '',
        'skills': [],
        'work_experience': [],
        'cgpa': ''
    }

    # 0. CGPA Extraction
    import re
    cgpa_pattern = re.compile(r'(CGPA|GPA)[^\d]*(\d\.\d{2,3})', re.I)
    cgpa = ''
    for line in lines:
        match = cgpa_pattern.search(line)
        if match:
            cgpa = match.group(2)
            break
    if not cgpa:
        # fallback: find first X.XX or X.XXX anywhere
        match = re.search(r'\b(\d\.\d{2,3})\b', text)
        if match:
            cgpa = match.group(1)
    info['cgpa'] = cgpa

    # 1. Name Extraction: Prefer 'Name:' or 'Name -' label in top 12 lines
    info['name'] = ''
    lines = text.splitlines()
    # Try to extract name from 'Name:' or 'Name -' label
    for line in lines[:12]:
        lstrip = line.strip()
        if lstrip.lower().startswith('name:') or lstrip.lower().startswith('name -'):
            possible_name = lstrip.split(':', 1)[-1].strip() if ':' in lstrip else lstrip.split('-', 1)[-1].strip()
            # Accept if at least 2 words, all capitalized or initialed
            words = possible_name.split()
            if len(words) >= 2 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
                info['name'] = possible_name
                break
    # Fallback: Strictly from top 6 lines, avoid titles and keywords
    if not info['name']:
        skip_keywords = [
            'curriculum vitae', 'resume', 'email', 'phone', 'contact', 'address', 'dob', 'date of birth',
            'cgpa', 'gpa', 'linkedin', 'github', 'india', 'bengaluru', 'bangalore', 'delhi', 'mumbai', 'pune',
            'summary', 'profile', 'objective', 'skills', 'education', 'career', 'professional', 'work experience',
            'title', 'course', 'specialisation', 'specialization', 'department', 'branch', 'stream'
        ]
        skip_titles = ['mr', 'ms', 'mrs', 'dr', 'prof', 'sir', 'madam', 'miss', 'shri', 'smt']
        for line in lines[:6]:
            lstrip = line.strip()
            if not lstrip:
                continue
            lwr = lstrip.lower()
            if any(k in lwr for k in skip_keywords):
                continue
            if any(lwr.startswith(t + ' ') for t in skip_titles):
                continue
            words = lstrip.split()
            # Require at least 2 words, all capitalized and alphabetic, no digits
            if len(words) >= 2 and all(w[0].isupper() and w.isalpha() for w in words) and not any(char.isdigit() for char in lstrip):
                info['name'] = lstrip.title()
                break
        # Fallback: regex for two capitalized words (first 6 lines)
        if not info['name']:
            import re
            for line in lines[:6]:
                lstrip = line.strip()
                if not lstrip:
                    continue
                lwr = lstrip.lower()
                if any(k in lwr for k in skip_keywords):
                    continue
                if any(lwr.startswith(t + ' ') for t in skip_titles):
                    continue
                match = re.match(r'^([A-Z][a-zA-Z]+) ([A-Z][a-zA-Z]+)$', lstrip)
                if match:
                    info['name'] = match.group(0)
                    break
    # If still no plausible name, leave blank

    # 2. Email Extraction (robust multi-TLD, extract all)
    import re
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.(com|in|co\.in|ac\.in|net|org|edu|gov)(\.[a-z]{2,})*', re.IGNORECASE)
    all_emails = email_pattern.findall(text)
    # findall returns tuples, so we need to use finditer to get full matches
    info['emails'] = [m.group(0) for m in email_pattern.finditer(text)]
    info['email'] = info['emails'][0] if info['emails'] else ''

    # 2.5. Work Experience Extraction: Prefer direct statement in top 20 lines
    info['total_experience'] = None
    for line in lines[:20]:
        lstrip = line.strip()
        match = re.search(r'(work experience|experience)(\s*\(years\))?\s*[:\-]?\s*(\d+(?:\.\d+)?)', lstrip, re.IGNORECASE)
        if match:
            try:
                info['total_experience'] = float(match.group(3))
            except Exception:
                pass
            break
    # Fallback: previous logic if not found (leave as None or handle below)
    # For compatibility, always set work_experience to total_experience if present
    if info['total_experience'] is not None:
        info['work_experience'] = info['total_experience']

    # 3. Technical Skills Extraction (section-aware, comma-separated)
    skills_section_idx = -1
    next_section_idx = None
    skill_section_headers = [r"technical skills"]
    for i, line in enumerate(lines):
        if any(re.match(rf"^\s*{header}\s*:?$", line.strip(), re.I) for header in skill_section_headers):
            skills_section_idx = i
            break
    extracted_skills = set()
    if skills_section_idx != -1:
        # The skills are usually on the next line after the header
        skill_line = lines[skills_section_idx+1] if skills_section_idx+1 < len(lines) else ''
        extracted_skills = set(s.strip().lower() for s in skill_line.split(',') if len(s.strip()) > 1)
    # Add matcher-based skills
    matches = matcher(doc)
    for match_id, start, end in matches:
        span = doc[start:end]
        extracted_skills.add(span.text.lower())
    info['skills'] = sorted(set(extracted_skills))

    # 3. Email and Phone Extraction (all emails, multi-part domains)
    email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[-a-zA-Z0-9]+(\.[a-zA-Z0-9-]+)+")
    all_emails = email_pattern.findall(text)
    all_emails_full = re.findall(email_pattern, text)
    # Findall returns only groups, so use finditer to get full matches
    emails = [m.group() for m in email_pattern.finditer(text)]
    # Prefer .ac.in or .edu, else first
    preferred_email = next((e for e in emails if ".ac.in" in e or ".edu" in e), emails[0] if emails else "")
    info['email'] = preferred_email
    # Phone extraction (first valid)
    phone_pattern = re.compile(r"\b(\+?\d{1,3}[- ]?)?(\d{10,12})\b")
    for line in lines:
        if not info['phone']:
            match = phone_pattern.search(line)
            if match:
                info['phone'] = match.group()
        if not info['phone']:
            match = phone_pattern.search(line)
            if match:
                info['phone'] = match.group()
        if info['email'] and info['phone']:
            break

    # 4. Work Experience Extraction (resume-specific, structured)
    import re
    exp_section_idx = -1
    next_exp_section_idx = None
    exp_headers = ["work experience", "experience", "professional experience", "employment history", "career history"]
    for i, line in enumerate(lines):
        if any(h == line.strip().lower() for h in exp_headers):
            exp_section_idx = i
            break
    # Find next section header (all-caps or known section)
    known_section_headers = ["projects", "position of responsibility", "entrepreneurship", "extra curriculars", "education", "skills", "summary", "profile", "objective"]
    if exp_section_idx != -1:
        for j in range(exp_section_idx+1, len(lines)):
            if re.match(r"^[A-Z][A-Z\s\-]{2,}$", lines[j].strip()) or any(h in lines[j].strip().lower() for h in known_section_headers):
                next_exp_section_idx = j
                break
        exp_lines = lines[exp_section_idx+1:next_exp_section_idx] if next_exp_section_idx else lines[exp_section_idx+1:]
    else:
        exp_lines = []

    experience_entries = []
    i = 0
    def is_caps_line(line):
        return line.isupper() and len(line) > 4 and not any(h in line.strip().lower() for h in known_section_headers)
    while i < len(exp_lines):
        line = exp_lines[i].strip()
        # Detect entry header: all caps (not section), or loose pattern with comma and date at end
        entry_match = re.match(r"^([A-Za-z\s\-&/]+),\s*([A-Za-z0-9\s\-&/()]+).*?(\w{3,9} \d{4}\s*[-–to]+\s*\w{3,9} \d{4}|Present|present)?$", line)
        if is_caps_line(line) or entry_match:
            if entry_match:
                position = entry_match.group(1).strip()
                organization = entry_match.group(2).strip()
                duration = entry_match.group(3).strip() if entry_match.group(3) else ''
            else:
                position = line
                organization = ''
                duration = ''
            description_lines = []
            j = i + 1
            while j < len(exp_lines):
                desc_line = exp_lines[j].strip()
                if desc_line.startswith(('-', '•', '*')):
                    description_lines.append(desc_line.lstrip('-•*').strip())
                    j += 1
                else:
                    break
            experience_entries.append({
                'position': position,
                'organization': organization,
                'duration': duration,
                'description': ' '.join(description_lines)
            })
            i = j
        else:
            # fallback: just add raw line if non-empty
            if line:
                experience_entries.append({'raw': line})
            i += 1
    # Calculate total work experience duration (oldest year method)
    import re
    from datetime import datetime
    now = datetime.now()
    current_year = now.year
    # Gather all years from the entire resume text
    years_found = []
    year_pattern = re.compile(r'(19[5-9][0-9]|20[0-4][0-9]|2050)')  # Years from 1950 to 2050
    for match in year_pattern.findall(text):
        y = int(match)
        if 1950 <= y <= current_year:
            years_found.append(y)
    if years_found:
        oldest = min(years_found)
        info['total_experience'] = current_year - oldest
    else:
        info['total_experience'] = 0
    info['work_experience'] = experience_entries

    # Improved email extraction: robust extraction for .com, .in, .co.in, etc.
    import re
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
    match = email_pattern.search(text)
    email = match.group(0) if match else None
    info['email'] = email

    # 3. Email and Phone Extraction (unchanged)
    email_pattern = re.compile(r"[\w\.-]+@[\w\.-]+", re.I)
    phone_pattern = re.compile(r"\b(\+?\d{1,3}[- ]?)?(\d{10,12})\b")
    for line in lines:
        if not info['email']:
            match = email_pattern.search(line)
            if match:
                info['email'] = match.group()
        if not info['phone']:
            match = phone_pattern.search(line)
            if match:
                info['phone'] = match.group()
        if info['email'] and info['phone']:
            break

    # 4. Work Experience Extraction (section-aware, stricter)
    job_keywords = [
        "intern", "engineer", "manager", "developer", "consultant", "analyst", "lead", "specialist", "director", "officer", "associate", "architect", "scientist", "administrator", "coordinator",
        "designer", "executive", "trainer", "supervisor", "president", "vice", "head", "founder", "cofounder", "researcher", "professor", "lecturer"
    ]
    years_found = []
    year_pattern = re.compile(r'(19[5-9][0-9]|20[0-4][0-9]|2050)')  # Years from 1950 to 2050
    for match in year_pattern.findall(text):
        y = int(match)
        if 1950 <= y <= current_year:
            years_found.append(y)
    if years_found:
        oldest = min(years_found)
        info['total_experience'] = current_year - oldest
    else:
        info['total_experience'] = 0
    info['work_experience'] = experience_entries

    # Improved email extraction: robust extraction for .com, .in, .co.in, etc.
    import re
    email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
    match = email_pattern.search(text)
    email = match.group(0) if match else None
    info['email'] = email

    # 5. CGPA Extraction
    cgpa_regex = re.compile(r'(?:CGPA|C\.G\.P\.A|GPA)[^\\d]{0,10}(\\d\\.\\d{2,3})', re.I)
    cgpa_found = None
    for line in lines:
        m = cgpa_regex.search(line)
        if m:
            cgpa_found = m.group(1)
            break
    if cgpa_found:
        info['cgpa'] = cgpa_found

    return info

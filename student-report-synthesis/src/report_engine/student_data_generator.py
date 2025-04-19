"""
Student Data Generator module.

This module provides classes for generating realistic student profiles
and school data for report generation.
"""

import random
import logging
from typing import Dict, Any, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

class StudentProfile:
    """Class representing a student's profile with realistic attributes."""
    
    # Data for generating realistic students
    FIRST_NAMES_MALE = [
        "Oliver", "Noah", "William", "Jack", "Liam", "Lucas", "Henry", "Ethan",
        "Thomas", "James", "Oscar", "Leo", "Charlie", "Mason", "Alexander", "Ryan",
        "Lachlan", "Harrison", "Cooper", "Daniel", "Aiden", "Isaac", "Hunter", "Benjamin",
        "Max", "Samuel", "Archie", "Patrick", "Felix", "Muhammad", "Xavier", "Jasper"
    ]
    
    FIRST_NAMES_FEMALE = [
        "Charlotte", "Olivia", "Amelia", "Ava", "Mia", "Isla", "Grace", "Willow",
        "Harper", "Ruby", "Ella", "Sophia", "Chloe", "Zoe", "Isabella", "Evie",
        "Sophie", "Sienna", "Ayla", "Matilda", "Ivy", "Layla", "Evelyn", "Alice",
        "Lucy", "Hannah", "Emily", "Abigail", "Maya", "Zara", "Emma", "Lily"
    ]
    
    LAST_NAMES = [
        "Smith", "Jones", "Williams", "Brown", "Wilson", "Taylor", "Johnson", "White",
        "Martin", "Anderson", "Thompson", "Nguyen", "Ryan", "Chen", "Scott", "Davis",
        "Green", "Roberts", "Campbell", "Kelly", "Baker", "Wang", "Singh", "Li",
        "Jackson", "Miller", "Harris", "Young", "Allen", "King", "Lee", "Wright",
        "Thomas", "Robinson", "Lewis", "Hill", "Clarke", "Zhang", "Patel", "Mitchell",
        "Carter", "Phillips", "Evans", "Collins", "Turner", "Parker", "Edwards", "Murphy"
    ]
    
    # Australian names with Indigenous origin
    INDIGENOUS_FIRST_NAMES = [
        "Kirra", "Jarrah", "Talia", "Koa", "Marlee", "Bindi", "Alkira", "Yarran",
        "Allira", "Jedda", "Kyah", "Tanami", "Tallara", "Jayde", "Tianna", "Lowanna"
    ]
    
    # Australian names with common Asian backgrounds
    ASIAN_FIRST_NAMES = [
        "Anh", "Chen", "Daiyu", "Eun", "Haruki", "Jin", "Kai", "Lian", "Ming",
        "Nguyen", "Phuong", "Qi", "Ryo", "Seo", "Tran", "Wei", "Xia", "Yi", "Zhen"
    ]
    
    ASIAN_LAST_NAMES = [
        "Chen", "Kim", "Lee", "Liu", "Nguyen", "Park", "Singh", "Suzuki", "Tanaka",
        "Wang", "Wong", "Wu", "Xu", "Yang", "Zhang", "Zhao", "Patel", "Khan", "Tran"
    ]
    
    # School-specific data
    TEACHER_TITLES = ["Mr.", "Mrs.", "Ms.", "Dr."]
    
    TEACHER_LAST_NAMES = [
        "Thompson", "Campbell", "Richardson", "Anderson", "Mitchell", "Williams", 
        "Smith", "Johnson", "Rodriguez", "Martinez", "Wilson", "Taylor", "Martin", 
        "Wilson", "Davis", "White", "Jones", "Lee", "Patel", "Brown", "Singh",
        "Chen", "McDonald", "Nguyen", "Harris", "Clark", "Baker", "Adams", "Miller"
    ]
    
    # More realistic principals for Australian schools
    PRINCIPAL_NAMES = [
        "Dr. Sarah Mitchell", "Mr. David Thompson", "Mrs. Jennifer Roberts",
        "Dr. Michael Chen", "Ms. Emily Wilson", "Mr. Andrew Baker",
        "Mrs. Samantha Richardson", "Dr. Robert Zhang", "Ms. Elizabeth Johnson",
        "Mr. Christopher Williams", "Dr. Amanda Singh", "Mrs. Stephanie Clark",
        "Mr. Richard Anderson", "Dr. Karen Martinez", "Ms. Megan Taylor",
        "Mr. John Davidson", "Dr. Patricia Lewis", "Mrs. Michelle Harris",
        "Dr. Robyn Strangward", "Mr. James Robertson"
    ]
    
    # Common Australian school grades/years
    GRADE_SYSTEMS = {
        "act": ["Preschool", "Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "nsw": ["Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "qld": ["Prep", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "vic": ["Foundation", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"],
        "generic": ["Kindergarten", "Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "Year 6"]
    }
    
    # Common class names used in Australian primary schools
    CLASS_NAMES = {
        # Animals
        "kindergarten": ["Koalas", "Kangaroos", "Possums", "Wombats", "Echidnas", "Kookaburras", "Emus"],
        # First letter of the teacher's surname
        "standard": ["KR", "KT", "KS", "1P", "1M", "1R", "2B", "2W", "2S", "3N", "3L", "3C"],
        # Other naming systems
        "colors": ["Red", "Blue", "Green", "Yellow", "Purple", "Orange"],
        "nature": ["Rainforest", "Ocean", "Desert", "River", "Mountain", "Coral"],
        # Specialized
        "early_learning": ["Butterflies", "Ladybugs", "Caterpillars", "Dragonflies"],
        "montessori": ["Peace", "Harmony", "Discovery", "Curiosity", "Wonder"],
        # Foreign language classes
        "language": ["Llamas", "Dragons", "Tigers", "Eagles", "Dolphins"]
    }
    
    def __init__(
        self, 
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        gender: Optional[str] = None,
        grade: Optional[str] = None,
        style: str = "generic",
        class_name: Optional[str] = None,
        diversity_factor: float = 0.3
    ):
        """
        Initialize a student profile with either provided or randomly generated attributes.
        
        Args:
            first_name: Optional student first name
            last_name: Optional student last name
            gender: Optional gender ('male', 'female', or None for random)
            grade: Optional grade/year level
            style: Report style (affects grade naming)
            class_name: Optional class name
            diversity_factor: A float between 0-1 determining likelihood of diverse names
        """
        # Set gender first as names depend on it
        self.gender = gender if gender else random.choice(["male", "female"])
        
        # Set name
        self.first_name = first_name if first_name else self._generate_first_name(diversity_factor)
        self.last_name = last_name if last_name else self._generate_last_name(diversity_factor)
        
        # Set grade based on style
        self.style = style.lower()
        grade_options = self.GRADE_SYSTEMS.get(self.style, self.GRADE_SYSTEMS["generic"])
        self.grade = grade if grade else random.choice(grade_options)
        
        # Set class
        self.class_name = class_name if class_name else self._generate_class_name()
        
        # Generate teacher information
        self.teacher = self._generate_teacher()
        
        # Parent/guardian information
        self.guardians = self._generate_guardians()
        
        # Generate attendance info
        self.attendance = self._generate_attendance()
    
    def _generate_first_name(self, diversity_factor: float) -> str:
        """Generate a realistic first name based on gender and diversity factor."""
        # Determine which name pool to use based on diversity factor
        name_pool_selector = random.random()
        
        if name_pool_selector < diversity_factor * 0.5:  # Indigenous names
            return random.choice(self.INDIGENOUS_FIRST_NAMES)
        elif name_pool_selector < diversity_factor:  # Asian names
            return random.choice(self.ASIAN_FIRST_NAMES)
        else:  # Standard Anglo names
            if self.gender == "male":
                return random.choice(self.FIRST_NAMES_MALE)
            else:
                return random.choice(self.FIRST_NAMES_FEMALE)
    
    def _generate_last_name(self, diversity_factor: float) -> str:
        """Generate a realistic last name based on diversity factor."""
        if random.random() < diversity_factor:
            return random.choice(self.ASIAN_LAST_NAMES)
        else:
            return random.choice(self.LAST_NAMES)
    
    def _generate_class_name(self) -> str:
        """Generate an appropriate class name based on the student's grade."""
        grade_lower = self.grade.lower()
        
        if "kindergarten" in grade_lower or "prep" in grade_lower or "foundation" in grade_lower:
            naming_system = random.choice(["kindergarten", "standard", "early_learning"])
        else:
            naming_system = random.choice(["standard", "colors", "nature", "language"])
            
        return random.choice(self.CLASS_NAMES[naming_system])
    
    def _generate_teacher(self) -> Dict[str, str]:
        """Generate teacher information."""
        title = random.choice(self.TEACHER_TITLES)
        last_name = random.choice(self.TEACHER_LAST_NAMES)
        
        # Sometimes include first initial or first name
        if random.random() < 0.3:
            if random.random() < 0.5:
                # First initial only
                first_initial = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                full_name = f"{title} {first_initial}. {last_name}"
            else:
                # Full first name
                if title == "Mr.":
                    first_name = random.choice(self.FIRST_NAMES_MALE)
                elif title == "Mrs." or title == "Ms.":
                    first_name = random.choice(self.FIRST_NAMES_FEMALE)
                else:  # Dr.
                    first_name = random.choice(self.FIRST_NAMES_MALE + self.FIRST_NAMES_FEMALE)
                
                full_name = f"{title} {first_name} {last_name}"
        else:
            full_name = f"{title} {last_name}"
        
        return {
            "title": title,
            "last_name": last_name,
            "full_name": full_name
        }
    
    def _generate_guardians(self) -> List[Dict[str, str]]:
        """Generate information about parents/guardians."""
        # Determine number of guardians to generate
        if random.random() < 0.7:  # 70% chance of two guardians
            num_guardians = 2
        else:
            num_guardians = 1
        
        guardians = []
        last_names_used = set([self.last_name])
        
        for i in range(num_guardians):
            # Gender distribution
            if num_guardians == 2:
                if i == 0:
                    gender = random.choice(["male", "female"])
                else:
                    # Usually opposite gender for second guardian
                    if random.random() < 0.9:
                        gender = "female" if guardians[0]["gender"] == "male" else "male"
                    else:
                        gender = guardians[0]["gender"]
            else:
                # Single guardian more often female
                gender = "female" if random.random() < 0.7 else "male"
            
            # Name generation
            if gender == "male":
                first_name = random.choice(self.FIRST_NAMES_MALE)
            else:
                first_name = random.choice(self.FIRST_NAMES_FEMALE)
            
            # Last name logic
            if i == 0 or random.random() < 0.7:  # 70% chance same last name for second guardian
                last_name = self.last_name
            else:
                # Generate a different last name
                while True:
                    new_last_name = random.choice(self.LAST_NAMES)
                    if new_last_name not in last_names_used:
                        last_name = new_last_name
                        last_names_used.add(last_name)
                        break
            
            # Relationship
            if gender == "male":
                relationship = "Father"
            else:
                relationship = "Mother"
            
            # Add to guardians
            guardians.append({
                "first_name": first_name,
                "last_name": last_name,
                "full_name": f"{first_name} {last_name}",
                "gender": gender,
                "relationship": relationship
            })
        
        return guardians
    
    def _generate_attendance(self) -> Dict[str, int]:
        """Generate realistic attendance data."""
        # Base on typical school term of around 10 weeks (50 days)
        total_days = random.randint(45, 55)
        
        # Most students have good attendance
        if random.random() < 0.7:  # 70% have good attendance
            absent_days = random.randint(0, 5)
            late_days = random.randint(0, 3)
        elif random.random() < 0.9:  # 20% have moderate attendance issues
            absent_days = random.randint(5, 10)
            late_days = random.randint(2, 6)
        else:  # 10% have significant attendance issues
            absent_days = random.randint(10, 20)
            late_days = random.randint(4, 10)
        
        present_days = total_days - absent_days
        
        return {
            "total_days": total_days,
            "present_days": present_days,
            "absent_days": absent_days,
            "late_days": late_days,
            "attendance_rate": round(present_days / total_days * 100, 1)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert student profile to dictionary."""
        return {
            "name": {
                "first_name": self.first_name,
                "last_name": self.last_name,
                "full_name": f"{self.first_name} {self.last_name}"
            },
            "gender": self.gender,
            "grade": self.grade,
            "class": self.class_name,
            "teacher": self.teacher,
            "guardians": self.guardians,
            "attendance": self.attendance
        }


class SchoolProfile:
    """Class representing an Australian school profile."""
    
    # Australian school types
    SCHOOL_TYPES = [
        "Primary School",
        "Public School",
        "Primary College",
        "Grammar School",
        "Catholic Primary School",
        "Elementary School",
        "Christian College",
        "State School",
        "Public Primary School",
        "Early Learning Centre",
        "Community School",
        "Primary Academy"
    ]
    
    # Australian suburbs by state
    SUBURBS = {
        "act": ["Lyons", "Belconnen", "Gungahlin", "Woden", "Tuggeranong", "Dickson", "Braddon", "Barton", "Kingston", "Ainslie"],
        "nsw": ["Parramatta", "Newcastle", "Cronulla", "Bondi", "Manly", "Blacktown", "Penrith", "Liverpool", "Campbelltown", "Wollongong"],
        "qld": ["Brisbane", "Gold Coast", "Sunshine Coast", "Toowoomba", "Townsville", "Cairns", "Rockhampton", "Mackay", "Bundaberg", "Ipswich"],
        "vic": ["Melbourne", "Geelong", "Ballarat", "Bendigo", "Wodonga", "Shepparton", "Mildura", "Warrnambool", "Bairnsdale", "Sale"],
        "sa": ["Adelaide", "Mount Gambier", "Whyalla", "Port Lincoln", "Port Augusta", "Victor Harbor", "Murray Bridge", "Port Pirie", "Renmark", "Gawler"],
        "wa": ["Perth", "Fremantle", "Mandurah", "Bunbury", "Geraldton", "Albany", "Kalgoorlie", "Broome", "Port Hedland", "Esperance"],
        "tas": ["Hobart", "Launceston", "Devonport", "Burnie", "Kingston", "Ulverstone", "Wynyard", "New Norfolk", "Sorell", "George Town"],
        "nt": ["Darwin", "Alice Springs", "Katherine", "Nhulunbuy", "Tennant Creek", "Palmerston", "Jabiru", "Yulara", "Alyangula", "Wadeye"]
    }
    
    def __init__(
        self,
        name: Optional[str] = None,
        type_name: Optional[str] = None,
        state: Optional[str] = None,
        suburb: Optional[str] = None,
        principal: Optional[str] = None
    ):
        """
        Initialize a school profile with either provided or randomly generated attributes.
        
        Args:
            name: Optional school name
            type_name: Optional school type
            state: Optional state code (act, nsw, qld, vic, sa, wa, tas, nt)
            suburb: Optional suburb name
            principal: Optional principal name
        """
        # Set state first as other values may depend on it
        self.state = state.lower() if state else random.choice(list(self.SUBURBS.keys()))
        
        # Set suburb
        self.suburb = suburb
        if not self.suburb:
            self.suburb = random.choice(self.SUBURBS.get(self.state, self.SUBURBS["act"]))
        
        # Set school type
        self.type_name = type_name if type_name else random.choice(self.SCHOOL_TYPES)
        
        # Set school name
        if name:
            self.name = name
        else:
            self.name = f"{self.suburb} {self.type_name}"
        
        # Set principal
        self.principal = principal if principal else random.choice(StudentProfile.PRINCIPAL_NAMES)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert school profile to dictionary."""
        return {
            "name": self.name,
            "type": self.type_name,
            "state": self.state,
            "suburb": self.suburb,
            "principal": self.principal
        }


class StudentDataGenerator:
    """Generate realistic student data and reports."""
    
    def __init__(self, style: str = "generic"):
        """
        Initialize the Student Data Generator.
        
        Args:
            style: The report style to use (act, nsw, etc.)
        """
        self.style = style.lower()
    
    def generate_student_profile(self, **kwargs) -> StudentProfile:
        """Generate a student profile with optional specific attributes."""
        return StudentProfile(style=self.style, **kwargs)
    
    def generate_school_profile(self, **kwargs) -> SchoolProfile:
        """Generate a school profile with optional specific attributes."""
        return SchoolProfile(**kwargs)
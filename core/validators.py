from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
import re


class InputValidator:
    # Grade label validator (e.g., V0, V1, V16)
    grade_validator = RegexValidator(
        regex=r'^V\d{1,2}$',
        message='Grade label must be in format V0-V99',
        code='invalid_grade'
    )
    
    # Alphanumeric with spaces, hyphens, underscores
    safe_name_validator = RegexValidator(
        regex=r'^[\w\s\-\'\".,()]+$',
        message='Name contains invalid characters',
        code='invalid_name'
    )
    
    @staticmethod
    def validate_integer_range(value, min_val=None, max_val=None, field_name="Value"):
        try:
            int_value = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} must be a valid integer")
        
        if min_val is not None and int_value < min_val:
            raise ValidationError(f"{field_name} must be at least {min_val}")
        
        if max_val is not None and int_value > max_val:
            raise ValidationError(f"{field_name} must be at most {max_val}")
        
        return int_value
    
    @staticmethod
    def sanitize_string(value, max_length=None, strip=True):
        if not isinstance(value, str):
            raise ValidationError("Value must be a string")
        
        # Strip whitespace if requested
        if strip:
            value = value.strip()
        
        # Normalize multiple spaces to single space
        value = re.sub(r'\s+', ' ', value)
        
        # Enforce max length
        if max_length and len(value) > max_length:
            raise ValidationError(f"Value must not exceed {max_length} characters")
        
        return value
    
    @staticmethod
    def validate_grade_index(grade_index):
        return InputValidator.validate_integer_range(
            grade_index, 
            min_val=0, 
            max_val=17, 
            field_name="Grade index"
        )
    
    @staticmethod
    def validate_attempts(attempts):
        return InputValidator.validate_integer_range(
            attempts,
            min_val=1,
            max_val=999,
            field_name="Attempts"
        )
    
    @staticmethod
    def validate_query_params(params_dict):
        sanitized = {}
        
        if 'min_grade' in params_dict:
            sanitized['min_grade'] = InputValidator.validate_grade_index(
                params_dict['min_grade']
            )
        
        if 'max_grade' in params_dict:
            sanitized['max_grade'] = InputValidator.validate_grade_index(
                params_dict['max_grade']
            )
        
        if 'sort' in params_dict:
            # Whitelist allowed sort values
            if params_dict['sort'] not in ['asc', 'desc']:
                raise ValidationError("Sort must be 'asc' or 'desc'")
            sanitized['sort'] = params_dict['sort']
        
        if 'start_date' in params_dict:
            # Validate date format YYYY-MM-DD
            import re
            date_str = str(params_dict['start_date'])
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                raise ValidationError("start_date must be in YYYY-MM-DD format")
            sanitized['start_date'] = date_str
        
        if 'end_date' in params_dict:
            # Validate date format YYYY-MM-DD
            import re
            date_str = str(params_dict['end_date'])
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                raise ValidationError("end_date must be in YYYY-MM-DD format")
            sanitized['end_date'] = date_str
        
        return sanitized


def validate_no_sql_keywords(value):
    sql_keywords = [
        'SELECT', 'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 
        'ALTER', 'EXEC', 'UNION', 'SCRIPT', '--', ';--', '/*', '*/',
        'xp_', 'sp_', 'INFORMATION_SCHEMA'
    ]
    
    value_upper = str(value).upper()
    for keyword in sql_keywords:
        if keyword in value_upper:
            raise ValidationError(
                f"Input contains potentially dangerous SQL keyword: {keyword}",
                code='sql_injection_attempt'
            )

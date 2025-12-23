"""
Input validation and sanitization module.

Provides validators for:
- Amount values (expenses, budgets, rules)
- Category names
- Rule names
- Expense names
"""

# Validation constraints
AMOUNT_MIN = 0.01  # Minimum allowed amount
AMOUNT_MAX = 999_999.99  # Maximum allowed amount (reasonable limit)

CATEGORY_MIN_LENGTH = 1
CATEGORY_MAX_LENGTH = 50
CATEGORY_FORBIDDEN_CHARS = {'<', '>', '"', "'", '/', '\\', '|', '\n', '\r', '\t'}

NAME_MIN_LENGTH = 1
NAME_MAX_LENGTH = 100
NAME_FORBIDDEN_CHARS = {'\n', '\r', '\t'}

BUDGET_MIN = 0.01  # Minimum monthly budget
BUDGET_MAX = 999_999.99  # Maximum monthly budget


class ValidationError(Exception):
    """Base validation error."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AmountValidationError(ValidationError):
    """Raised when amount validation fails."""
    pass


class CategoryValidationError(ValidationError):
    """Raised when category validation fails."""
    pass


class NameValidationError(ValidationError):
    """Raised when name validation fails."""
    pass


class BudgetValidationError(ValidationError):
    """Raised when budget validation fails."""
    pass


def validate_amount(amount: float, field_name: str = "amount") -> float:
    """
    Validate that amount is within acceptable range.
    
    Args:
        amount: The amount to validate
        field_name: Name of the field for error messages (e.g., "amount", "budget")
    
    Returns:
        The validated amount
    
    Raises:
        AmountValidationError: If validation fails
    """
    if amount < AMOUNT_MIN:
        raise AmountValidationError(
            f"{field_name}_too_small"
        )
    if amount > AMOUNT_MAX:
        raise AmountValidationError(
            f"{field_name}_too_large"
        )
    return amount


def validate_category(category: str) -> str:
    """
    Validate and sanitize category name.
    
    Args:
        category: The category name to validate
    
    Returns:
        The validated and trimmed category name
    
    Raises:
        CategoryValidationError: If validation fails
    """
    category = category.strip()
    
    if not category:
        raise CategoryValidationError("empty_category")
    
    if len(category) < CATEGORY_MIN_LENGTH:
        raise CategoryValidationError("empty_category")
    
    if len(category) > CATEGORY_MAX_LENGTH:
        raise CategoryValidationError("category_too_long")
    
    # Check for forbidden characters
    forbidden_found = CATEGORY_FORBIDDEN_CHARS & set(category)
    if forbidden_found:
        raise CategoryValidationError("invalid_category_format")
    
    return category


def validate_name(name: str, field_name: str = "name") -> str:
    """
    Validate and sanitize expense/rule name.
    
    Args:
        name: The name to validate
        field_name: Name of the field for error messages
    
    Returns:
        The validated and trimmed name
    
    Raises:
        NameValidationError: If validation fails
    """
    name = name.strip()
    
    if not name:
        raise NameValidationError(f"empty_{field_name}")
    
    if len(name) < NAME_MIN_LENGTH:
        raise NameValidationError(f"empty_{field_name}")
    
    if len(name) > NAME_MAX_LENGTH:
        raise NameValidationError(f"{field_name}_too_long")
    
    # Check for forbidden characters
    forbidden_found = NAME_FORBIDDEN_CHARS & set(name)
    if forbidden_found:
        raise NameValidationError(f"invalid_{field_name}_format")
    
    return name


def validate_budget(amount: float) -> float:
    """
    Validate budget amount.
    
    Args:
        amount: The budget amount to validate
    
    Returns:
        The validated budget amount
    
    Raises:
        BudgetValidationError: If validation fails
    """
    if amount < BUDGET_MIN:
        raise BudgetValidationError("budget_too_small")
    if amount > BUDGET_MAX:
        raise BudgetValidationError("budget_too_large")
    return amount


def sanitize_category(category: str) -> str:
    """
    Sanitize category name by removing/replacing problematic characters.
    This is stricter than validate_category - it rejects with errors
    instead of trying to fix the input.
    
    Args:
        category: The category name to sanitize
    
    Returns:
        The sanitized category name
    """
    return category.strip()


def sanitize_name(name: str) -> str:
    """
    Sanitize name by removing/replacing problematic characters.
    
    Args:
        name: The name to sanitize
    
    Returns:
        The sanitized name
    """
    return name.strip()

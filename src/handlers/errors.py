"""
Custom exceptions and error handling for the budget bot.
Centralizes all error types for consistent error management across the application.
"""
from pathlib import Path
import yaml

# Load error messages from YAML
_current_dir = Path(__file__).parent
_errors_messages_path = _current_dir / "messages" / "errors.yaml"
with open(_errors_messages_path, "r") as file:
    ERROR_MESSAGES = yaml.safe_load(file)


class BudgetBotError(Exception):
    """Base exception for all budget bot errors."""
    pass


# ---- User Input Errors ----

class InvalidInputError(BudgetBotError):
    """Raised when user provides invalid input (format, value, etc.)."""
    pass


class ValidationError(InvalidInputError):
    """Raised when input validation fails (constraints, ranges, etc.)."""
    pass


class ParseError(InvalidInputError):
    """Raised when parsing user input fails."""
    pass


# ---- Business Logic Errors ----

class BudgetError(BudgetBotError):
    """Raised when budget-related operation fails."""
    pass


class RuleError(BudgetBotError):
    """Raised when rule-related operation fails."""
    pass


class ExpenseError(BudgetBotError):
    """Raised when expense-related operation fails."""
    pass


# ---- External Service Errors ----

class ExternalServiceError(BudgetBotError):
    """Raised when external service (API, database) fails."""
    pass


class DatabaseError(ExternalServiceError):
    """Raised when database operation fails."""
    pass


class APIError(ExternalServiceError):
    """Raised when API call fails."""
    pass


class NetworkError(APIError):
    """Raised when network connection fails."""
    pass


class APITimeoutError(APIError):
    """Raised when API request times out."""
    pass


# ---- Authorization Errors ----

class AuthorizationError(BudgetBotError):
    """Raised when user doesn't have permission for operation."""
    pass


class NotFoundError(BudgetBotError):
    """Raised when requested resource is not found."""
    pass


def get_error_message(error: Exception, default_key: str = "unexpected_error") -> str:
    """
    Get a user-friendly error message for an exception.
    
    Args:
        error: The exception that occurred
        default_key: The default message key if no specific handler exists
        
    Returns:
        User-friendly error message
    """
    error_map = {
        InvalidInputError: "invalid_input",
        ValidationError: "validation_error",
        ParseError: "parse_error",
        BudgetError: "budget_error",
        RuleError: "rule_error",
        ExpenseError: "expense_error",
        DatabaseError: "database_error",
        NetworkError: "network_error",
        APITimeoutError: "timeout_error",
        APIError: "api_error",
        AuthorizationError: "permission_denied",
        NotFoundError: "not_found",
    }
    
    # Find the appropriate message key
    for error_class, key in error_map.items():
        if isinstance(error, error_class):
            message_template = ERROR_MESSAGES.get(key, ERROR_MESSAGES.get(default_key))
            # If error has detail message, include it
            if hasattr(error, "detail"):
                return message_template.format(detail=str(error.detail))
            return message_template
    
    # Fallback to default message
    return ERROR_MESSAGES.get(default_key, ERROR_MESSAGES.get("unexpected_error"))

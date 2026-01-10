"""
Custom exceptions for the Attribution MVP application.

This module defines specific exception types for different error scenarios,
enabling better error handling and recovery throughout the codebase.
"""


class AttributionError(Exception):
    """Base exception for attribution-related errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AttributionError):
    """Raised when input validation fails."""

    def __init__(self, message: str, field: str = None, value=None):
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, details)
        self.field = field
        self.value = value


class DatabaseError(AttributionError):
    """Raised when database operations fail."""

    def __init__(self, message: str, operation: str = None, query: str = None):
        details = {}
        if operation:
            details["operation"] = operation
        if query:
            details["query"] = query[:200]  # Truncate long queries
        super().__init__(message, details)
        self.operation = operation
        self.query = query


class ConfigurationError(AttributionError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, setting_key: str = None):
        details = {}
        if setting_key:
            details["setting_key"] = setting_key
        super().__init__(message, details)
        self.setting_key = setting_key


class RuleEvaluationError(AttributionError):
    """Raised when rule evaluation fails."""

    def __init__(self, message: str, rule_name: str = None, context: dict = None):
        details = {"rule_name": rule_name} if rule_name else {}
        if context:
            details["context"] = context
        super().__init__(message, details)
        self.rule_name = rule_name
        self.context = context


class SplitCapExceededError(AttributionError):
    """Raised when attribution would exceed the split cap."""

    def __init__(
        self,
        message: str,
        account_id: str = None,
        current_total: float = None,
        requested_amount: float = None
    ):
        details = {}
        if account_id:
            details["account_id"] = account_id
        if current_total is not None:
            details["current_total"] = current_total
        if requested_amount is not None:
            details["requested_amount"] = requested_amount
        super().__init__(message, details)
        self.account_id = account_id
        self.current_total = current_total
        self.requested_amount = requested_amount


class PartnerNotFoundError(AttributionError):
    """Raised when a partner cannot be found."""

    def __init__(self, partner_id: str):
        super().__init__(f"Partner not found: {partner_id}", {"partner_id": partner_id})
        self.partner_id = partner_id


class AccountNotFoundError(AttributionError):
    """Raised when an account cannot be found."""

    def __init__(self, account_id: str):
        super().__init__(f"Account not found: {account_id}", {"account_id": account_id})
        self.account_id = account_id


class UseCaseNotFoundError(AttributionError):
    """Raised when a use case cannot be found."""

    def __init__(self, use_case_id: str):
        super().__init__(f"Use case not found: {use_case_id}", {"use_case_id": use_case_id})
        self.use_case_id = use_case_id


class AuthenticationError(AttributionError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message)


class AuthorizationError(AttributionError):
    """Raised when user lacks permission for an operation."""

    def __init__(self, message: str = "Insufficient permissions", required_role: str = None):
        details = {}
        if required_role:
            details["required_role"] = required_role
        super().__init__(message, details)
        self.required_role = required_role


class PeriodLockedError(AttributionError):
    """Raised when trying to modify a locked attribution period."""

    def __init__(self, period_id: int, period_name: str = None):
        message = f"Attribution period is locked: {period_name or period_id}"
        super().__init__(message, {"period_id": period_id, "period_name": period_name})
        self.period_id = period_id
        self.period_name = period_name


class ExternalServiceError(AttributionError):
    """Raised when an external service (OpenAI, Salesforce, etc.) fails."""

    def __init__(self, message: str, service: str = None, status_code: int = None):
        details = {}
        if service:
            details["service"] = service
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, details)
        self.service = service
        self.status_code = status_code


class DataIngestionError(AttributionError):
    """Raised when data ingestion fails."""

    def __init__(self, message: str, row_number: int = None, column: str = None):
        details = {}
        if row_number is not None:
            details["row_number"] = row_number
        if column:
            details["column"] = column
        super().__init__(message, details)
        self.row_number = row_number
        self.column = column

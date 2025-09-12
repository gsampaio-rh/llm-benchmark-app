"""
Comprehensive error handling framework.

This module provides a structured error handling system with proper error
classification, recovery strategies, and user-friendly error messages.
"""

import traceback
import logging
from typing import Optional, Dict, Any, List, Callable, Union
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error category classification"""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    SERVICE = "service"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RESOURCE = "resource"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"


@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    component: str
    user_action: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_data is None:
            self.additional_data = {}


@dataclass
class ErrorDetails:
    """Comprehensive error details"""
    error_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    user_message: str
    technical_details: str
    suggested_actions: List[str]
    context: ErrorContext
    original_exception: Optional[Exception] = None
    stack_trace: Optional[str] = None
    recovery_possible: bool = True


class ErrorHandler(ABC):
    """Abstract error handler interface"""
    
    @abstractmethod
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Check if this handler can process the error"""
        pass
    
    @abstractmethod
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle the error and return error details"""
        pass


class BaseErrorHandler(ErrorHandler):
    """Base implementation for error handlers"""
    
    def __init__(self, category: ErrorCategory, severity: ErrorSeverity = ErrorSeverity.MEDIUM):
        """Initialize base error handler
        
        Args:
            category: Error category this handler manages
            severity: Default severity level
        """
        self.category = category
        self.default_severity = severity
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Default implementation checks exception type"""
        return True  # Override in subclasses for specific handling
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Default error handling implementation"""
        error_id = self._generate_error_id(error, context)
        
        return ErrorDetails(
            error_id=error_id,
            category=self.category,
            severity=self.default_severity,
            message=str(error),
            user_message=self._create_user_message(error, context),
            technical_details=self._extract_technical_details(error),
            suggested_actions=self._get_suggested_actions(error, context),
            context=context,
            original_exception=error,
            stack_trace=traceback.format_exc(),
            recovery_possible=self._is_recovery_possible(error)
        )
    
    def _generate_error_id(self, error: Exception, context: ErrorContext) -> str:
        """Generate unique error ID"""
        import hashlib
        import time
        
        error_string = f"{type(error).__name__}_{context.operation}_{context.component}_{time.time()}"
        return hashlib.md5(error_string.encode()).hexdigest()[:12]
    
    def _create_user_message(self, error: Exception, context: ErrorContext) -> str:
        """Create user-friendly error message"""
        return f"An error occurred during {context.operation}. Please try again or contact support."
    
    def _extract_technical_details(self, error: Exception) -> str:
        """Extract technical details from exception"""
        return f"{type(error).__name__}: {str(error)}"
    
    def _get_suggested_actions(self, error: Exception, context: ErrorContext) -> List[str]:
        """Get suggested recovery actions"""
        return [
            "Try the operation again",
            "Check your network connection",
            "Contact support if the problem persists"
        ]
    
    def _is_recovery_possible(self, error: Exception) -> bool:
        """Determine if recovery is possible"""
        return True  # Override for specific error types


class ServiceErrorHandler(BaseErrorHandler):
    """Handler for service-related errors"""
    
    def __init__(self):
        super().__init__(ErrorCategory.SERVICE, ErrorSeverity.HIGH)
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle service-related exceptions"""
        return isinstance(error, (ConnectionError, TimeoutError)) or "service" in str(error).lower()
    
    def _create_user_message(self, error: Exception, context: ErrorContext) -> str:
        """Create service-specific user message"""
        if isinstance(error, ConnectionError):
            return f"Unable to connect to {context.component}. The service may be temporarily unavailable."
        elif isinstance(error, TimeoutError):
            return f"The {context.component} service is taking longer than expected to respond."
        else:
            return f"The {context.component} service encountered an error. Please try again."
    
    def _get_suggested_actions(self, error: Exception, context: ErrorContext) -> List[str]:
        """Get service-specific suggested actions"""
        actions = ["Wait a moment and try again"]
        
        if isinstance(error, ConnectionError):
            actions.extend([
                "Check if the service is running",
                "Verify network connectivity",
                "Check service configuration"
            ])
        elif isinstance(error, TimeoutError):
            actions.extend([
                "Try with a simpler request",
                "Check service load and performance",
                "Increase timeout settings if possible"
            ])
        
        actions.append("Contact your system administrator if the problem persists")
        return actions


class ConfigurationErrorHandler(BaseErrorHandler):
    """Handler for configuration-related errors"""
    
    def __init__(self):
        super().__init__(ErrorCategory.CONFIGURATION, ErrorSeverity.MEDIUM)
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle configuration-related exceptions"""
        error_indicators = ["config", "configuration", "setting", "parameter", "yaml", "json"]
        error_str = str(error).lower()
        return any(indicator in error_str for indicator in error_indicators)
    
    def _create_user_message(self, error: Exception, context: ErrorContext) -> str:
        """Create configuration-specific user message"""
        return f"There's an issue with the configuration for {context.operation}. Please check your settings."
    
    def _get_suggested_actions(self, error: Exception, context: ErrorContext) -> List[str]:
        """Get configuration-specific suggested actions"""
        return [
            "Check your configuration file for syntax errors",
            "Verify all required configuration parameters are set",
            "Use the example configuration as a reference",
            "Run configuration validation if available",
            "Check file permissions for configuration files"
        ]


class NetworkErrorHandler(BaseErrorHandler):
    """Handler for network-related errors"""
    
    def __init__(self):
        super().__init__(ErrorCategory.NETWORK, ErrorSeverity.HIGH)
    
    def can_handle(self, error: Exception, context: ErrorContext) -> bool:
        """Handle network-related exceptions"""
        network_errors = [
            "ConnectionError", "HTTPError", "URLError", "DNSError", 
            "SSLError", "ProxyError", "ConnectTimeout"
        ]
        return type(error).__name__ in network_errors or "network" in str(error).lower()
    
    def _create_user_message(self, error: Exception, context: ErrorContext) -> str:
        """Create network-specific user message"""
        if "timeout" in str(error).lower():
            return "The network request timed out. Please check your connection and try again."
        elif "ssl" in str(error).lower():
            return "There's an SSL/TLS security issue with the connection."
        else:
            return "A network error occurred. Please check your internet connection."
    
    def _get_suggested_actions(self, error: Exception, context: ErrorContext) -> List[str]:
        """Get network-specific suggested actions"""
        actions = ["Check your internet connection"]
        
        if "timeout" in str(error).lower():
            actions.extend([
                "Try again with a stable network connection",
                "Check if the target server is responding"
            ])
        elif "ssl" in str(error).lower():
            actions.extend([
                "Verify SSL certificates are valid",
                "Check system date and time settings",
                "Update your SSL/TLS configuration"
            ])
        
        actions.extend([
            "Try again in a few moments",
            "Contact your network administrator if issues persist"
        ])
        return actions


class ErrorManager:
    """Central error management system"""
    
    def __init__(self):
        """Initialize error manager with default handlers"""
        self.handlers: List[ErrorHandler] = []
        self.error_log: List[ErrorDetails] = []
        self.logger = logging.getLogger(__name__)
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default error handlers"""
        self.handlers.extend([
            ServiceErrorHandler(),
            ConfigurationErrorHandler(),
            NetworkErrorHandler(),
            BaseErrorHandler(ErrorCategory.SYSTEM)  # Catch-all handler
        ])
    
    def register_handler(self, handler: ErrorHandler):
        """Register a custom error handler
        
        Args:
            handler: Error handler to register
        """
        # Insert at beginning so custom handlers take precedence
        self.handlers.insert(0, handler)
    
    def handle_error(self, error: Exception, context: ErrorContext) -> ErrorDetails:
        """Handle an error using registered handlers
        
        Args:
            error: Exception to handle
            context: Error context information
            
        Returns:
            Error details with suggested actions
        """
        # Find appropriate handler
        handler = None
        for h in self.handlers:
            if h.can_handle(error, context):
                handler = h
                break
        
        if not handler:
            # Use fallback handler
            handler = BaseErrorHandler(ErrorCategory.SYSTEM, ErrorSeverity.HIGH)
        
        # Handle the error
        error_details = handler.handle_error(error, context)
        
        # Log the error
        self._log_error(error_details)
        
        # Store in error log
        self.error_log.append(error_details)
        
        return error_details
    
    def _log_error(self, error_details: ErrorDetails):
        """Log error details"""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_details.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"Error {error_details.error_id}: {error_details.message}",
            extra={
                "error_id": error_details.error_id,
                "category": error_details.category.value,
                "severity": error_details.severity.value,
                "operation": error_details.context.operation,
                "component": error_details.context.component
            }
        )
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of recent errors
        
        Returns:
            Summary statistics of errors
        """
        if not self.error_log:
            return {"total_errors": 0}
        
        categories = {}
        severities = {}
        
        for error in self.error_log:
            categories[error.category.value] = categories.get(error.category.value, 0) + 1
            severities[error.severity.value] = severities.get(error.severity.value, 0) + 1
        
        return {
            "total_errors": len(self.error_log),
            "by_category": categories,
            "by_severity": severities,
            "recent_errors": [
                {
                    "error_id": e.error_id,
                    "category": e.category.value,
                    "severity": e.severity.value,
                    "message": e.user_message
                }
                for e in self.error_log[-5:]  # Last 5 errors
            ]
        }
    
    def clear_error_log(self):
        """Clear the error log"""
        self.error_log.clear()


# Global error manager instance
error_manager = ErrorManager()


def handle_error(error: Exception, operation: str, component: str, 
                user_action: Optional[str] = None, **additional_data) -> ErrorDetails:
    """Convenient function to handle errors
    
    Args:
        error: Exception to handle
        operation: Operation being performed
        component: Component where error occurred
        user_action: User action that triggered the error
        **additional_data: Additional context data
        
    Returns:
        Error details with suggested actions
    """
    context = ErrorContext(
        operation=operation,
        component=component,
        user_action=user_action,
        additional_data=additional_data
    )
    
    return error_manager.handle_error(error, context)


def create_error_context(operation: str, component: str, 
                        user_action: Optional[str] = None, **kwargs) -> ErrorContext:
    """Create an error context for consistent error handling
    
    Args:
        operation: Operation being performed
        component: Component where operation is happening
        user_action: User action that triggered the operation
        **kwargs: Additional context data
        
    Returns:
        Error context object
    """
    return ErrorContext(
        operation=operation,
        component=component,
        user_action=user_action,
        additional_data=kwargs
    )

"""
Hexagonal Architecture Package - TranscriberApp.

Clean Architecture Layers:
- Domain: Core business logic, entities, domain services, domain ports
- Application: Use cases orchestrating domain services
- Infrastructure: Concrete implementations of ports (persistence, AI, etc.)
- Adapters: Primary (HTTP/API) and Secondary (DB, external services) adapters
"""

# Package initialization - avoids circular imports by importing only what's safe

__all__ = []

# HTTP application

## Purpose

Describe the implemented HTTP composition and generated API description. Database lifecycle is documented in the PY-002 change; the current business route is specified separately in stone-registration/spec.md. These capabilities coexist.

## Requirements

### Requirement: Application factory
The application SHALL expose a factory that constructs a FastAPI application and an ASGI entry point usable by Uvicorn.

#### Scenario: Construct an application
- **WHEN** the application factory is called
- **THEN** it returns a FastAPI application without requiring a database connection

### Requirement: Generated API description
The application SHALL serve its generated OpenAPI document at `/openapi.json` with the title `Stone Shelter API` and interactive documentation at `/docs`.

#### Scenario: Read the API description
- **WHEN** a client requests `/openapi.json`
- **THEN** the application returns HTTP 200 with an OpenAPI document whose `info.title` is `Stone Shelter API`

#### Scenario: Open interactive documentation
- **WHEN** a client requests `/docs`
- **THEN** the application serves the interactive API documentation page

## Evidence

Implemented in PY-001 and merged into `master` at `99bac3c`. The OpenAPI integration test and manual documentation check were reported successful. This evidence records the original bootstrap verification. Later database wiring and single-stone registration are documented separately; complete CRUD is not a current goal.

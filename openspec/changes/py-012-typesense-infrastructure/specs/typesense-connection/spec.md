## ADDED Requirements

### Requirement: Explicit validated connection settings
The Typesense factory SHALL accept validated host, port, protocol, secret API key and positive timeout settings. Tests SHALL supply explicit disposable-container settings without local dotenv fallback.

#### Scenario: Construct a test client
- **WHEN** the factory receives settings from the Typesense Testcontainers fixture
- **THEN** subsequent SDK requests target that container's assigned host port and use its test-only key

### Requirement: Application-owned client lifecycle
FastAPI lifespan SHALL create one asynchronous Typesense client per app instance and close its HTTP pool at shutdown. Constructing the app or client SHALL NOT issue Typesense requests or create a collection. Database resource cleanup SHALL remain registered when the Typesense resource is added.

#### Scenario: Enter and exit lifespan
- **WHEN** the application starts and later shuts down
- **THEN** app.state.typesense_client exposes the shared client during operation and both the client pool and database engine are released during shutdown

### Requirement: Disposable test infrastructure
Typesense integration checks SHALL use a temporary container with the pinned server image, a random host port and no development volume. Asynchronous clients SHALL be closed within their test's event loop.

#### Scenario: Authenticate with the SDK
- **WHEN** the client requests /debug from the ready disposable server
- **THEN** the test key is accepted and the response identifies the pinned Typesense version

# Technical Interview Notes - Maya Patel
Interviewer: David Vance (Principal Engineer) | Date: 2026-09-15 | Candidate: Maya Patel
Role: Senior Distributed Systems & Cloud Engineer

## Section: Distributed Systems & Backend Architecture
- Candidate walked through her FastAPI microservice architecture at Nexus Retail Tech.
- "We decoupled the checkout endpoint by publishing order events asynchronously, reducing checkout API response time down to 85ms."
- Explained database connection pooling using SQLAlchemy and PostgreSQL index optimizations.
- Rating: Strong depth on API design and relational data schemas. Demonstrated good understanding of concurrency.

## Section: Cloud & Container Orchestration
- Maya explained how she containerized the Python applications using multi-stage Dockerfiles to minimize image size.
- Discussed deploying to Kubernetes via Helm charts and configuring Horizontal Pod Autoscalers (HPA).
- Rating: Acceptable. Has good operational familiarity with Kubernetes pods and services, though did not design cluster networking from scratch.

## Section: Kafka & Event-Driven Data Streaming
- Did not evaluate. Ran out of time during the architecture deep dive.
- Rating: Not evaluated.

## Final Interviewer Comments
- Maya gave strong, grounded answers on Python service scaling and AWS deployments.
- We need to validate her Kafka and event-driven streaming capabilities in the next round.

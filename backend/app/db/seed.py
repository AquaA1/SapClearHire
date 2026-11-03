"""
Seed script for populating demo accounts and initial job requisitions.
Enables instant one-click login and manual end-to-end testing of all ClearHire features.
"""

import asyncio
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.password import hash_password
from app.core.security import UserRole
from app.db.models.enums import CriterionCategory, JobStatus
from app.db.models.job import Job, JobCriterion
from app.db.models.user import User
from app.db.session import close_db_engine, get_session_factory

DEMO_USERS = [
    {
        "email": "alex.morgan@test.com",
        "full_name": "Alex Morgan",
        "role": UserRole.CANDIDATE,
        "password": "ValidPassword123!",
    },
    {
        "email": "employer.admin@clearhire.dev",
        "full_name": "Sarah Chen (Talent Lead)",
        "role": UserRole.EMPLOYER_ADMIN,
        "password": "AdminPassword123!",
    },
    {
        "email": "senior.reviewer@clearhire.dev",
        "full_name": "Marcus Vance (Staff Reviewer)",
        "role": UserRole.REVIEWER,
        "password": "ReviewerPass123!",
    },
    {
        "email": "auditor@clearhire.dev",
        "full_name": "Dr. Elena Rostova (Lead Compliance Auditor)",
        "role": UserRole.SYSTEM_AUDITOR,
        "password": "AuditorPass123!",
    },
]

DEMO_JOB_CRITERIA = [
    {
        "name": "Experience in FastAPI or Python Web Frameworks",
        "category": CriterionCategory.REQUIRED,
        "description": "Demonstrated hands-on experience designing and building RESTful APIs using Python frameworks such as FastAPI, Flask, or Django.",
        "order": 1,
    },
    {
        "name": "PostgreSQL Scaling & Index Optimization",
        "category": CriterionCategory.REQUIRED,
        "description": "Practical understanding of relational schema design, query optimization, indexing strategies (B-Tree, GIN), and connection pooling.",
        "order": 2,
    },
    {
        "name": "Cloud Architecture on SAP BTP / Kubernetes / AWS",
        "category": CriterionCategory.REQUIRED,
        "description": "Experience deploying microservices to cloud environments (SAP BTP, Kyma/Kubernetes, or hyperscalers).",
        "order": 3,
    },
    {
        "name": "Asynchronous Task Queues (Redis / Celery)",
        "category": CriterionCategory.PREFERRED,
        "description": "Familiarity with distributed background queues, event streams, or caching using Redis.",
        "order": 4,
    },
]


async def seed_database() -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        print("🌱 Seeding ClearHire demo users...")
        employer_user = None

        for user_data in DEMO_USERS:
            stmt = select(User).where(User.email == user_data["email"])
            res = await session.execute(stmt)
            existing = res.scalar_one_or_none()

            if not existing:
                new_user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    password_hash=hash_password(user_data["password"]),
                    is_active=True,
                    email_verified=True,
                )
                session.add(new_user)
                if user_data["role"] == UserRole.EMPLOYER_ADMIN:
                    employer_user = new_user
                print(f"  ✓ Created {user_data['role'].value}: {user_data['email']}")
            else:
                if user_data["role"] == UserRole.EMPLOYER_ADMIN:
                    employer_user = existing
                print(f"  • Existing {user_data['role'].value}: {user_data['email']}")

        await session.flush()

        # Seed initial sample job
        stmt_job = select(Job).where(Job.title.ilike("%Cloud Backend Engineer%"))
        res_job = await session.execute(stmt_job)
        existing_job = res_job.scalar_one_or_none()

        if not existing_job and employer_user:
            print("\n🌱 Seeding initial Job Requisition: Senior Cloud Backend Engineer (SAP BTP)...")
            job_id = uuid.uuid4()
            sample_job = Job(
                id=job_id,
                employer_id=employer_user.id,
                title="Senior Cloud Backend Engineer (SAP BTP)",
                department="SAP Business Technology Platform",
                description=(
                    "Join the ClearHire team to build transparent, evidence-backed hiring transparency pipelines "
                    "integrated with SAP BTP and modern enterprise stacks."
                ),
                status=JobStatus.ACTIVE,
            )
            session.add(sample_job)
            await session.flush()

            for crit in DEMO_JOB_CRITERIA:
                category_str = "requirement" if crit["category"] == CriterionCategory.REQUIRED else "preferred"
                c = JobCriterion(
                    id=uuid.uuid4(),
                    job_id=job_id,
                    name=crit["name"],
                    category=category_str,
                    description=crit["description"],
                    version=1,
                    weight=1.0,
                    is_active=True,
                )
                session.add(c)
                print(f"  ✓ Created Criterion [{category_str.upper()}]: {crit['name']}")

        await session.commit()
        print("\n✨ Database seeding complete! Ready for end-to-end testing.\n")

    await close_db_engine()


if __name__ == "__main__":
    asyncio.run(seed_database())

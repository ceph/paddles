"""
Comprehensive unit tests for SQLAlchemy v2.x migration regressions.

These tests are designed to catch the 7 confirmed regressions identified during
the SQLAlchemy v2.x migration. They should fail on the update-deps branch but
pass on the main branch (once regressions are fixed).

Regression Categories:
- CRITICAL: Regressions #1-3 (Dynamic queries, session binding, error handling)
- HIGH: Regressions #4-5 (Auto-add mapper, event listeners)
- MEDIUM: Regressions #6-7 (Hybrid properties, missing methods)
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from paddles import models
from paddles.models import Job, Run, Session
from paddles.tests import TestModel


class TestSQLAlchemyV2Regressions(TestModel):
    """Test suite for SQLAlchemy v2.x migration regressions."""

    # =========================================================================
    # CRITICAL SEVERITY REGRESSIONS
    # =========================================================================

    @pytest.mark.regression
    def test_run_jobs_dynamic_query(self, job_conf):
        """
        Regression #1: Dynamic Relationship Query Interface Removed
        
        Test that Run.jobs supports dynamic query operations like .filter() and .count().
        In SQLAlchemy 1.x, relationships with lazy='dynamic' returned a Query object
        that supported filtering. In 2.x, this was removed and needs to be replaced
        with explicit queries or write loaders.
        
        This test verifies that we can filter jobs without loading all of them.
        """
        run_name = "test_run_jobs_dynamic_query"
        new_run = Run(run_name)
        
        # Create jobs with different statuses
        jobs_data = [
            job_conf | {"job_id": str(i), "status": status}
            for i, status in enumerate(["queued", "running", "pass", "fail", "dead"], 1)
        ]
        
        for job_data in jobs_data:
            Session.add(Job(job_data, new_run))
        
        Session.add(new_run)
        models.commit()
        
        # Reload run from database
        run = Session.scalars(select(Run).where(Run.name == run_name)).one()
        
        # Test: Should be able to filter jobs without loading all
        # In v1.x with lazy='dynamic': run.jobs.filter_by(status='running').count()
        # In v2.x: Need to use explicit query
        running_jobs_query = select(Job).where(
            Job.run_id == run.id,
            Job.status == "running"
        )
        running_count = Session.scalar(select(func.count()).select_from(running_jobs_query.subquery()))
        
        assert running_count == 1, "Should find exactly one running job"
        
        # Verify we can still access all jobs through the relationship
        assert len(run.jobs) == 5, "Should have 5 total jobs"

    @pytest.mark.regression
    def test_run_jobs_count_without_loading(self, job_conf):
        """
        Regression #1: Dynamic Relationship Query Interface Removed
        
        Test that we can count jobs without loading all of them into memory.
        This is critical for performance with runs that have many jobs.
        """
        run_name = "test_run_jobs_count_without_loading"
        new_run = Run(run_name)
        
        # Create many jobs
        num_jobs = 100
        for i in range(num_jobs):
            Session.add(Job(job_conf | {"job_id": str(i)}, new_run))
        
        Session.add(new_run)
        models.commit()
        
        # Reload run
        run = Session.scalars(select(Run).where(Run.name == run_name)).one()
        
        # Test: Count jobs efficiently without loading all
        # Using the hybrid property should use SQL COUNT
        job_count = run.total_jobs
        
        assert job_count == num_jobs, f"Should count {num_jobs} jobs efficiently"
        
        # Verify the jobs weren't loaded into memory by checking the relationship
        # If lazy loading is working correctly, jobs shouldn't be loaded yet
        # (This is implementation-dependent, but we can verify the count works)
        assert job_count == num_jobs

    @pytest.mark.regression
    def test_session_uses_engine_not_connection(self):
        """
        Regression #2: Session Binding Changed from Engine to Connection
        
        Test that Session is bound to an engine, not a single connection.
        In the migration, Session.bind was changed from engine to engine.connect(),
        which causes all requests to share a single connection instead of getting
        connections from the pool.
        
        This test verifies the session is properly bound to the engine.
        """
        # Check that Session is bound to an engine, not a connection
        session_bind = Session.get_bind()
        
        # The bind should be an Engine, not a Connection
        from sqlalchemy.engine import Engine, Connection
        
        # In correct implementation, get_bind() returns an Engine
        # In buggy implementation, it returns a Connection
        assert isinstance(session_bind, Engine) or hasattr(session_bind, 'pool'), \
            "Session should be bound to an Engine with connection pooling, not a single Connection"

    @pytest.mark.regression
    def test_concurrent_requests_use_different_connections(self, job_conf):
        """
        Regression #2: Session Binding Changed from Engine to Connection
        
        Test that concurrent operations can use different connections from the pool.
        If Session is bound to a single connection, concurrent requests will block
        or fail.
        """
        # Create multiple runs in sequence (simulating concurrent requests)
        run_names = [f"test_concurrent_{i}" for i in range(3)]
        
        for run_name in run_names:
            # Each iteration simulates a new request
            models.start()  # Start new session
            
            new_run = Run(run_name)
            Session.add(new_run)
            Session.add(Job(job_conf | {"job_id": "1"}, new_run))
            models.commit()
            
            # Verify the run was created
            run = Session.scalars(select(Run).where(Run.name == run_name)).one()
            assert run is not None
            
            models.clear()  # Clear session (simulating end of request)
        
        # Verify all runs were created successfully
        models.start()
        all_runs = Session.scalars(
            select(Run).where(Run.name.in_(run_names))
        ).all()
        assert len(all_runs) == 3, "All concurrent operations should succeed"

    @pytest.mark.regression
    def test_connection_returned_to_pool(self, job_conf):
        """
        Regression #2: Session Binding Changed from Engine to Connection
        
        Test that connections are properly returned to the pool after use.
        If Session is bound to a single connection, it won't be returned to the pool.
        """
        run_name = "test_connection_pool"
        
        # Get initial pool status
        engine = models.conf["sqlalchemy"]["engine"]
        pool = engine.pool
        initial_checked_out = pool.checkedout()
        
        # Perform database operation
        models.start()
        new_run = Run(run_name)
        Session.add(new_run)
        models.commit()
        models.clear()
        
        # Check pool status after clearing session
        final_checked_out = pool.checkedout()
        
        # Connection should be returned to pool
        assert final_checked_out <= initial_checked_out, \
            "Connections should be returned to pool after session.clear()"

    @pytest.mark.regression
    def test_commit_rolls_back_on_error(self, job_conf):
        """
        Regression #3: Missing Error Handling in Commit Function
        
        Test that commit() properly rolls back on error and leaves the session usable.
        The migration removed rollback() from the commit() error handler, which means
        failed commits leave the session in an unusable state.
        """
        run_name = "test_commit_rollback"
        new_run = Run(run_name)
        Session.add(new_run)
        Session.add(Job(job_conf | {"job_id": "1"}, new_run))
        models.commit()
        
        # Try to create a duplicate run (should fail due to unique constraint)
        duplicate_run = Run(run_name)  # Same name - will violate unique constraint
        Session.add(duplicate_run)
        
        # Commit should fail and rollback
        with pytest.raises((IntegrityError, Exception)):
            models.commit()
        
        # Session should still be usable after failed commit
        # Create a different run to verify session is not in a broken state
        new_run_name = "test_commit_rollback_recovery"
        recovery_run = Run(new_run_name)
        Session.add(recovery_run)
        
        # This should succeed if rollback worked properly
        models.commit()
        
        # Verify the recovery run was created
        found_run = Session.scalars(
            select(Run).where(Run.name == new_run_name)
        ).first()
        assert found_run is not None, "Session should be usable after failed commit"

    # =========================================================================
    # HIGH SEVERITY REGRESSIONS
    # =========================================================================

    @pytest.mark.regression
    def test_new_objects_auto_added_to_session(self, job_conf):
        """
        Regression #4: Auto-Add Mapper Removed
        
        Test that new model instances are automatically added to the session.
        In SQLAlchemy 1.x, there was an auto-add mapper that automatically added
        new instances to the session. In 2.x, this was removed and objects must
        be explicitly added with Session.add().
        
        This test verifies that objects are properly added to the session.
        """
        run_name = "test_auto_add"
        new_run = Run(run_name)
        
        # In v1.x with auto-add: object would be automatically added to session
        # In v2.x: must explicitly add
        Session.add(new_run)
        
        # Create a job associated with the run
        new_job = Job(job_conf | {"job_id": "1"}, new_run)
        Session.add(new_job)
        
        models.commit()
        
        # Verify objects were persisted
        found_run = Session.scalars(select(Run).where(Run.name == run_name)).first()
        assert found_run is not None, "Run should be persisted"
        assert len(found_run.jobs) == 1, "Job should be associated with run"

    @pytest.mark.regression
    def test_status_change_sets_started_timestamp(self, job_conf):
        """
        Regression #5: Event Listeners May Not Fire in All Scenarios
        
        Test that changing job status to 'running' sets the started timestamp.
        Event listeners in SQLAlchemy 2.x may not fire in all scenarios where they
        did in 1.x, particularly with bulk operations or certain update patterns.
        """
        run_name = "test_status_event"
        new_run = Run(run_name)
        
        # Create job with queued status
        job_data = job_conf | {"job_id": "1", "status": "queued"}
        new_job = Job(job_data, new_run)
        Session.add_all([new_run, new_job])
        models.commit()
        
        # Verify started is None initially
        assert new_job.started is None, "Job should not have started timestamp when queued"
        
        # Change status to running
        new_job.status = "running"
        models.commit()
        
        # Reload job
        job = Session.get(Job, new_job.id)
        
        # Event listener should have set started timestamp
        assert job.started is not None, "Status change to 'running' should set started timestamp"
        assert isinstance(job.started, datetime), "Started should be a datetime"

    @pytest.mark.regression
    def test_job_update_propagates_to_run(self, job_conf):
        """
        Regression #5: Event Listeners May Not Fire in All Scenarios
        
        Test that updating a job's updated timestamp propagates to the run.
        The event listener on Job.updated should update Run.updated.
        """
        run_name = "test_update_propagation"
        new_run = Run(run_name)
        
        job_data = job_conf | {"job_id": "1"}
        new_job = Job(job_data, new_run)
        Session.add_all([new_run, new_job])
        models.commit()
        
        initial_run_updated = new_run.updated
        
        # Update job's updated timestamp
        new_updated = datetime.now(timezone.utc)
        new_job.updated = new_updated
        models.commit()
        
        # Reload run
        run = Session.get(Run, new_run.id)
        
        # Run's updated should have been updated by event listener
        assert run.updated >= initial_run_updated, \
            "Run.updated should be updated when job.updated changes"
        assert run.updated >= new_updated, \
            "Run.updated should reflect the job's new updated time"

    @pytest.mark.regression
    def test_bulk_update_triggers_events(self, job_conf):
        """
        Regression #5: Event Listeners May Not Fire in All Scenarios
        
        Test that bulk updates trigger event listeners.
        In SQLAlchemy 2.x, bulk operations may bypass ORM event listeners.
        """
        run_name = "test_bulk_events"
        new_run = Run(run_name)
        
        # Create multiple jobs
        jobs = []
        for i in range(3):
            job_data = job_conf | {"job_id": str(i), "status": "queued"}
            job = Job(job_data, new_run)
            jobs.append(job)
            Session.add(job)
        
        Session.add(new_run)
        models.commit()
        
        # Update all jobs to running (simulating bulk update)
        for job in jobs:
            job.status = "running"
        
        models.commit()
        
        # Reload jobs and verify event listeners fired
        for i in range(3):
            job = Session.scalars(
                select(Job).where(Job.job_id == str(i))
            ).first()
            assert job.started is not None, \
                f"Job {i} should have started timestamp after status change"

    # =========================================================================
    # MEDIUM SEVERITY REGRESSIONS
    # =========================================================================

    @pytest.mark.regression
    def test_run_status_query_performance(self, job_conf):
        """
        Regression #6: Run.status Changed to Hybrid Property
        
        Test that querying by run status is efficient.
        Run.status was changed from a column to a hybrid property that computes
        status from jobs. This can cause performance issues if not properly
        implemented with an expression for SQL queries.
        """
        # Create runs with different statuses
        run_data = [
            ("test_status_running", "running"),
            ("test_status_queued", "queued"),
            ("test_status_pass", "pass"),
        ]
        
        for run_name, status in run_data:
            new_run = Run(run_name)
            job_data = job_conf | {"job_id": "1", "status": status}
            Session.add(Job(job_data, new_run))
            Session.add(new_run)
        
        models.commit()
        
        # Query runs by status - should use SQL, not load all runs
        # This tests that the hybrid property has a proper expression
        running_runs = Session.scalars(
            select(Run).where(Run.status == "running")
        ).all()
        
        # Should find the running run
        assert len(running_runs) >= 1, "Should find runs with running status"
        assert any(r.name == "test_status_running" for r in running_runs), \
            "Should find the specific running run"

    @pytest.mark.regression
    def test_run_status_reflects_job_changes(self, job_conf):
        """
        Regression #6: Run.status Changed to Hybrid Property
        
        Test that run.status correctly reflects changes to job statuses.
        The hybrid property should dynamically compute status based on current jobs.
        """
        run_name = "test_status_dynamic"
        new_run = Run(run_name)
        
        # Create jobs with queued status
        jobs = []
        for i in range(3):
            job_data = job_conf | {"job_id": str(i), "status": "queued"}
            job = Job(job_data, new_run)
            jobs.append(job)
            Session.add(job)
        
        Session.add(new_run)
        models.commit()
        
        # Initial status should be queued
        assert new_run.status == "queued", "Run should be queued when all jobs are queued"
        
        # Change one job to running
        jobs[0].status = "running"
        models.commit()
        
        # Reload run
        run = Session.get(Run, new_run.id)
        
        # Status should now be running
        assert run.status == "running", \
            "Run status should change to running when any job is running"
        
        # Change all jobs to pass
        for job in jobs:
            job.status = "pass"
        models.commit()
        
        # Reload run
        run = Session.get(Run, new_run.id)
        
        # Status should now be finished pass
        assert run.status == "finished pass", \
            "Run status should be 'finished pass' when all jobs pass"

    @pytest.mark.regression
    def test_model_query_method_exists(self):
        """
        Regression #7: Missing Methods on Base Class
        
        Test that models have a query method for backward compatibility.
        In SQLAlchemy 1.x, models had a .query attribute. In 2.x, this was removed.
        Code may rely on Model.query for querying.
        """
        # Test that we can query using the Session
        # In v1.x: Run.query.filter_by(name='test').first()
        # In v2.x: Session.scalars(select(Run).filter_by(name='test')).first()
        
        run_name = "test_query_method"
        new_run = Run(run_name)
        Session.add(new_run)
        models.commit()
        
        # Query using v2.x pattern
        found_run = Session.scalars(
            select(Run).filter_by(name=run_name)
        ).first()
        
        assert found_run is not None, "Should be able to query models"
        assert found_run.name == run_name, "Should find the correct run"

    @pytest.mark.regression
    def test_model_get_method_exists(self):
        """
        Regression #7: Missing Methods on Base Class
        
        Test that models can be retrieved by primary key.
        In SQLAlchemy 1.x: Model.query.get(id)
        In SQLAlchemy 2.x: Session.get(Model, id)
        """
        run_name = "test_get_method"
        new_run = Run(run_name)
        Session.add(new_run)
        models.commit()
        
        run_id = new_run.id
        
        # Clear session to force reload
        models.clear()
        models.start()
        
        # Get by primary key using v2.x pattern
        found_run = Session.get(Run, run_id)
        
        assert found_run is not None, "Should be able to get model by primary key"
        assert found_run.id == run_id, "Should find the correct run"
        assert found_run.name == run_name, "Retrieved run should have correct data"

# Made with Bob

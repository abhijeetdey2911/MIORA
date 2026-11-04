"""Central Workflow Orchestrator powered by LangGraph (Parts 1, 2, 8, 9).

Coordinates the 5 specialized agents independently for every active JobPreference:
- Agent 1: Job Discovery (`agent_1_discovery`)
- Agent 2: Job Matching (`agent_2_matching`)
- Agent 3: Application Route Discovery (`agent_3_routes`)
- Agent 4: Application Execution (`agent_4_execution`)
- Agent 5: Application Tracking (`agent_5_tracking`)

Features:
- True LangGraph `StateGraph` execution with conditional safe-boundary routing.
- Independent per-preference execution (`PreferenceExecution`) where a failure or pause in P1
  never stops P2 or P3.
- PostgreSQL checkpoint persistence (`PreferenceExecution.checkpoint_state`) enabling pause/resume
  and recovery after server restart from the exact next agent node.
- Genuine kill switch (`stop`), pause, runtime limit, and API spend limit enforcement at every node boundary.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict
import uuid

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.multi_agent import (
    AgentExecution,
    Application,
    ApplicationRoute,
    AutomationSettings,
    DiscoveredJob,
    JobMatch,
)
from app.models.orchestration import JobHuntRun, PreferenceExecution
from app.models.job_preference import JobPreference
from app.models.resume import Resume
from app.models.resume_intelligence import ResumeVersion
from app.services.agents import (
    BaseJobSourceAdapter,
    agent1_discovery,
    agent2_matching,
    agent3_routes,
    agent4_execution,
    agent5_tracking,
)
from app.services.telegram_service import telegram_service

AGENT_SEQUENCE = (
    "agent_1_discovery",
    "agent_2_matching",
    "agent_3_routes",
    "agent_4_execution",
    "agent_5_tracking",
)


class PreferenceWorkflowState(TypedDict, total=False):
    """Typed state passed through the LangGraph StateGraph for a single preference workflow."""

    workflow_run_id: str
    preference_run_id: str
    preference_id: str
    preference_name: str
    resume_from_agent: Optional[str]
    current_agent: str
    completed_agents: List[str]
    discovered_job_ids: List[str]
    matched_job_ids: List[str]
    shortlisted_match_ids: List[str]
    route_ids: List[str]
    application_ids: List[str]
    jobs_discovered_count: int
    jobs_matched_count: int
    jobs_shortlisted_count: int
    applications_submitted_count: int
    interviews_scheduled_count: int
    offers_received_count: int
    api_spend_usd: float
    halted_status: Optional[str]
    halt_reason: Optional[str]
    error_message: Optional[str]


class CentralOrchestrator:
    """LangGraph-powered Central Orchestrator for Project JobHunter."""

    def __init__(
        self,
        custom_discovery_adapters: Optional[List[BaseJobSourceAdapter]] = None,
    ) -> None:
        self.custom_discovery_adapters = custom_discovery_adapters

    @staticmethod
    def get_or_create_settings(db: Session) -> AutomationSettings:
        """Retrieve or initialize the singleton AutomationSettings record."""
        settings = db.scalars(select(AutomationSettings).limit(1)).first()
        if settings is None:
            settings = AutomationSettings(
                is_kill_switch_engaged=False,
                automation_state="ready",
                approval_mode="manual",
                max_jobs_per_run=50,
                max_applications_per_run=10,
                max_applications_per_day=25,
                max_runtime_seconds=1800,
                max_api_spend_usd=5.0,
                current_api_spend_usd=0.0,
                minimum_match_score=70,
                retry_limit=2,
            )
            db.add(settings)
            db.commit()
            db.refresh(settings)
        return settings

    @staticmethod
    def _check_safe_boundary(
        db: Session,
        workflow_run_id: uuid.UUID,
        preference_run_id: uuid.UUID,
        preference_id: uuid.UUID,
    ) -> TupleStatusAndReason:
        """Inspect kill switch, run status, preference status, runtime limit, and API spend limit
        at safe node boundaries before executing an agent.
        """
        db.expire_all()
        settings = CentralOrchestrator.get_or_create_settings(db)
        wf_run = db.get(JobHuntRun, workflow_run_id)
        pref_run = db.get(PreferenceExecution, preference_run_id)
        pref = db.get(JobPreference, preference_id)

        if settings.is_kill_switch_engaged or settings.automation_state == "stopped":
            return "stopped", "Kill switch engaged by user."

        if wf_run and wf_run.status == "stopped":
            return "stopped", "Workflow run stopped."

        if pref_run and pref_run.status == "stopped":
            return "stopped", "Preference workflow stopped."

        if (
            settings.automation_state == "paused"
            or (wf_run and wf_run.status == "paused")
            or (pref_run and pref_run.status == "paused")
        ):
            return "paused", "Workflow paused at safe agent boundary."

        if not pref or not pref.is_active:
            return "paused", "Preference was paused or deactivated by user."

        # Check runtime limit
        if pref_run and pref_run.started_at and settings.max_runtime_seconds > 0:
            started_utc = (
                pref_run.started_at
                if pref_run.started_at.tzinfo
                else pref_run.started_at.replace(tzinfo=timezone.utc)
            )
            elapsed = (datetime.now(timezone.utc) - started_utc).total_seconds()
            if elapsed > settings.max_runtime_seconds:
                return (
                    "stopped",
                    f"Maximum runtime limit ({settings.max_runtime_seconds}s) exceeded.",
                )

        # Check API spend limit
        if (
            settings.max_api_spend_usd > 0
            and settings.current_api_spend_usd >= settings.max_api_spend_usd
        ):
            return (
                "stopped",
                f"Maximum API spend limit (${settings.max_api_spend_usd:.2f}) reached.",
            )

        return None, None

    @staticmethod
    def _persist_checkpoint(
        db: Session,
        preference_run_id: uuid.UUID,
        state: PreferenceWorkflowState,
    ) -> None:
        """Persist current LangGraph workflow state into `PreferenceExecution.checkpoint_state`."""
        pref_run = db.get(PreferenceExecution, preference_run_id)
        if not pref_run:
            return
        pref_run.current_agent = state.get("current_agent") or "pending"
        pref_run.jobs_discovered = int(state.get("jobs_discovered_count", 0))
        pref_run.matching_jobs = int(state.get("jobs_matched_count", 0))
        pref_run.shortlisted_jobs = int(state.get("jobs_shortlisted_count", 0))
        pref_run.applications_submitted = int(state.get("applications_submitted_count", 0))
        pref_run.interviews_scheduled = int(state.get("interviews_scheduled_count", 0))
        pref_run.offers_received = int(state.get("offers_received_count", 0))
        pref_run.checkpoint_state = dict(state)
        db.commit()

    def _build_preference_graph(self, db: Session):
        """Construct and compile the 5-agent LangGraph StateGraph bound to `db`."""

        def should_continue(state: PreferenceWorkflowState) -> str:
            if state.get("halted_status") or state.get("error_message"):
                return "halt"
            return "continue"

        def make_node(agent_name: str, execute_fn):
            def node_fn(state: PreferenceWorkflowState) -> PreferenceWorkflowState:
                completed = list(state.get("completed_agents") or [])
                # If recovering/resuming and this agent already finished in checkpoint, skip cleanly
                if agent_name in completed:
                    return state

                wf_id = uuid.UUID(state["workflow_run_id"])
                pr_id = uuid.UUID(state["preference_run_id"])
                p_id = uuid.UUID(state["preference_id"])

                halted_status, halt_reason = self._check_safe_boundary(
                    db, wf_id, pr_id, p_id
                )
                if halted_status:
                    state["halted_status"] = halted_status
                    state["halt_reason"] = halt_reason
                    self._persist_checkpoint(db, pr_id, state)
                    return state

                state["current_agent"] = agent_name
                self._persist_checkpoint(db, pr_id, state)

                agent_exec = AgentExecution(
                    workflow_run_id=wf_id,
                    preference_run_id=pr_id,
                    preference_id=p_id,
                    agent_name=agent_name,
                    status="running",
                    started_at=datetime.now(timezone.utc),
                )
                db.add(agent_exec)
                db.commit()
                db.refresh(agent_exec)

                try:
                    updated_state, items_processed, cost_usd, details = execute_fn(
                        state, wf_id, pr_id, p_id
                    )
                    completed.append(agent_name)
                    updated_state["completed_agents"] = completed
                    updated_state["api_spend_usd"] = round(
                        float(updated_state.get("api_spend_usd", 0.0)) + cost_usd, 6
                    )

                    agent_exec.status = "completed"
                    agent_exec.items_processed = items_processed
                    agent_exec.api_cost_usd = cost_usd
                    agent_exec.details = details
                    agent_exec.completed_at = datetime.now(timezone.utc)

                    settings = self.get_or_create_settings(db)
                    settings.current_api_spend_usd = round(
                        float(settings.current_api_spend_usd or 0.0) + cost_usd, 6
                    )
                    db.commit()
                    self._persist_checkpoint(db, pr_id, updated_state)
                    return updated_state
                except Exception as exc:
                    agent_exec.status = "failed"
                    agent_exec.error_message = str(exc)
                    agent_exec.completed_at = datetime.now(timezone.utc)
                    db.commit()

                    state["halted_status"] = "failed"
                    state["error_message"] = f"{agent_name} failed: {exc}"
                    self._persist_checkpoint(db, pr_id, state)
                    return state

            return node_fn

        def run_agent_1(
            state: PreferenceWorkflowState,
            wf_id: uuid.UUID,
            pr_id: uuid.UUID,
            p_id: uuid.UUID,
        ):
            pref = db.get(JobPreference, p_id)
            settings = self.get_or_create_settings(db)
            discovery_agent = (
                agent1_discovery
                if self.custom_discovery_adapters is None
                else type(agent1_discovery)(adapters=self.custom_discovery_adapters)
            )
            discovered_jobs = discovery_agent.discover_for_preference(
                db=db,
                preference=pref,
                max_jobs=max(1, int(settings.max_jobs_per_run or 50)),
            )
            state["discovered_job_ids"] = [str(j.id) for j in discovered_jobs]
            state["jobs_discovered_count"] = len(discovered_jobs)
            return (
                state,
                len(discovered_jobs),
                0.0,
                {"discovered_count": len(discovered_jobs)},
            )

        def run_agent_2(
            state: PreferenceWorkflowState,
            wf_id: uuid.UUID,
            pr_id: uuid.UUID,
            p_id: uuid.UUID,
        ):
            pref = db.get(JobPreference, p_id)
            settings = self.get_or_create_settings(db)
            job_ids = [uuid.UUID(jid) for jid in (state.get("discovered_job_ids") or [])]
            discovered_jobs = (
                list(
                    db.scalars(
                        select(DiscoveredJob).where(DiscoveredJob.id.in_(job_ids))
                    ).all()
                )
                if job_ids
                else []
            )
            matches, est_cost = agent2_matching.evaluate_jobs_for_preference(
                db=db,
                preference=pref,
                discovered_jobs=discovered_jobs,
                preference_run_id=pr_id,
                override_threshold=int(settings.minimum_match_score or 70),
            )
            matching_rows = [m for m in matches if m.is_matching]
            shortlisted_rows = [m for m in matches if m.shortlisted]
            state["matched_job_ids"] = [str(m.id) for m in matching_rows]
            state["shortlisted_match_ids"] = [str(m.id) for m in shortlisted_rows]
            state["jobs_matched_count"] = len(matching_rows)
            state["jobs_shortlisted_count"] = len(shortlisted_rows)
            return (
                state,
                len(matches),
                est_cost,
                {
                    "evaluated_count": len(matches),
                    "matching_count": len(matching_rows),
                    "shortlisted_count": len(shortlisted_rows),
                },
            )

        def run_agent_3(
            state: PreferenceWorkflowState,
            wf_id: uuid.UUID,
            pr_id: uuid.UUID,
            p_id: uuid.UUID,
        ):
            shortlisted_ids = [
                uuid.UUID(mid) for mid in (state.get("shortlisted_match_ids") or [])
            ]
            shortlisted_matches = (
                list(
                    db.scalars(
                        select(JobMatch).where(JobMatch.id.in_(shortlisted_ids))
                    ).all()
                )
                if shortlisted_ids
                else []
            )
            routes = agent3_routes.discover_routes_for_shortlisted_matches(
                db=db,
                shortlisted_matches=shortlisted_matches,
            )
            state["route_ids"] = [str(r.id) for r in routes]
            return (
                state,
                len(routes),
                0.0,
                {
                    "routes_discovered": len(routes),
                    "verified_routes": sum(
                        1 for r in routes if r.verification_status == "verified"
                    ),
                },
            )

        def run_agent_4(
            state: PreferenceWorkflowState,
            wf_id: uuid.UUID,
            pr_id: uuid.UUID,
            p_id: uuid.UUID,
        ):
            pref = db.get(JobPreference, p_id)
            pref_run = db.get(PreferenceExecution, pr_id)
            settings = self.get_or_create_settings(db)
            shortlisted_ids = [
                uuid.UUID(mid) for mid in (state.get("shortlisted_match_ids") or [])
            ]
            route_ids = [uuid.UUID(rid) for rid in (state.get("route_ids") or [])]
            shortlisted_matches = (
                list(
                    db.scalars(
                        select(JobMatch).where(JobMatch.id.in_(shortlisted_ids))
                    ).all()
                )
                if shortlisted_ids
                else []
            )
            routes = (
                list(
                    db.scalars(
                        select(ApplicationRoute).where(ApplicationRoute.id.in_(route_ids))
                    ).all()
                )
                if route_ids
                else []
            )
            apps = agent4_execution.process_shortlisted_jobs(
                db=db,
                preference=pref,
                shortlisted_matches=shortlisted_matches,
                routes=routes,
                automation_settings=settings,
                preference_run_id=pr_id,
                preferred_resume_version_id=(
                    pref_run.approved_resume_version_id if pref_run else None
                ),
            )
            state["application_ids"] = [str(a.id) for a in apps]
            return (
                state,
                len(apps),
                0.0,
                {
                    "applications_processed": len(apps),
                    "submitted": sum(1 for a in apps if a.status == "Submitted"),
                    "awaiting_approval": sum(
                        1 for a in apps if a.status == "Awaiting Approval"
                    ),
                    "submission_unconfirmed": sum(
                        1 for a in apps if a.status == "Submission Unconfirmed"
                    ),
                },
            )

        def run_agent_5(
            state: PreferenceWorkflowState,
            wf_id: uuid.UUID,
            pr_id: uuid.UUID,
            p_id: uuid.UUID,
        ):
            metrics = agent5_tracking.sync_preference_applications(
                db=db,
                preference_id=p_id,
                preference_run_id=pr_id,
            )
            state["applications_submitted_count"] = metrics["applications_submitted"]
            state["interviews_scheduled_count"] = metrics["interviews_scheduled"]
            state["offers_received_count"] = metrics["offers_received"]
            return (
                state,
                metrics["total_applications"],
                0.0,
                metrics,
            )

        builder = StateGraph(PreferenceWorkflowState)
        builder.add_node("agent_1_discovery", make_node("agent_1_discovery", run_agent_1))
        builder.add_node("agent_2_matching", make_node("agent_2_matching", run_agent_2))
        builder.add_node("agent_3_routes", make_node("agent_3_routes", run_agent_3))
        builder.add_node("agent_4_execution", make_node("agent_4_execution", run_agent_4))
        builder.add_node("agent_5_tracking", make_node("agent_5_tracking", run_agent_5))

        builder.add_edge(START, "agent_1_discovery")
        builder.add_conditional_edges(
            "agent_1_discovery",
            should_continue,
            {"continue": "agent_2_matching", "halt": END},
        )
        builder.add_conditional_edges(
            "agent_2_matching",
            should_continue,
            {"continue": "agent_3_routes", "halt": END},
        )
        builder.add_conditional_edges(
            "agent_3_routes",
            should_continue,
            {"continue": "agent_4_execution", "halt": END},
        )
        builder.add_conditional_edges(
            "agent_4_execution",
            should_continue,
            {"continue": "agent_5_tracking", "halt": END},
        )
        builder.add_edge("agent_5_tracking", END)
        return builder.compile()

    def execute_preference_workflow(
        self,
        db: Session,
        preference_run_id: uuid.UUID,
    ) -> PreferenceExecution:
        """Execute (or resume from checkpoint) the 5-agent LangGraph workflow for a single preference."""
        pref_run = db.get(PreferenceExecution, preference_run_id)
        if not pref_run:
            raise ValueError(f"PreferenceExecution {preference_run_id} not found.")

        pref = db.get(JobPreference, pref_run.preference_id)
        if not pref or not pref.is_active:
            pref_run.status = "skipped"
            pref_run.completed_at = datetime.now(timezone.utc)
            db.commit()
            return pref_run

        pref_run.status = "running"
        if not pref_run.started_at:
            pref_run.started_at = datetime.now(timezone.utc)
        db.commit()

        existing_ckpt = dict(pref_run.checkpoint_state or {})
        initial_state: PreferenceWorkflowState = {
            "workflow_run_id": str(pref_run.run_id),
            "preference_run_id": str(pref_run.id),
            "preference_id": str(pref.id),
            "preference_name": pref.preference_name,
            "current_agent": existing_ckpt.get("current_agent", "agent_1_discovery"),
            "completed_agents": list(existing_ckpt.get("completed_agents", [])),
            "discovered_job_ids": list(existing_ckpt.get("discovered_job_ids", [])),
            "matched_job_ids": list(existing_ckpt.get("matched_job_ids", [])),
            "shortlisted_match_ids": list(existing_ckpt.get("shortlisted_match_ids", [])),
            "route_ids": list(existing_ckpt.get("route_ids", [])),
            "application_ids": list(existing_ckpt.get("application_ids", [])),
            "jobs_discovered_count": int(existing_ckpt.get("jobs_discovered_count", 0)),
            "jobs_matched_count": int(existing_ckpt.get("jobs_matched_count", 0)),
            "jobs_shortlisted_count": int(existing_ckpt.get("jobs_shortlisted_count", 0)),
            "applications_submitted_count": int(
                existing_ckpt.get("applications_submitted_count", 0)
            ),
            "interviews_scheduled_count": int(
                existing_ckpt.get("interviews_scheduled_count", 0)
            ),
            "offers_received_count": int(existing_ckpt.get("offers_received_count", 0)),
            "api_spend_usd": float(existing_ckpt.get("api_spend_usd", 0.0)),
            "halted_status": None,
            "halt_reason": None,
            "error_message": None,
        }

        graph = self._build_preference_graph(db)
        final_state = graph.invoke(initial_state)

        db.refresh(pref_run)
        now = datetime.now(timezone.utc)
        halted = final_state.get("halted_status")

        if halted == "paused":
            pref_run.status = "paused"
            pref_run.error_message = final_state.get("halt_reason")
        elif halted == "stopped":
            pref_run.status = "stopped"
            pref_run.error_message = final_state.get("halt_reason")
            pref_run.completed_at = now
        elif halted == "failed" or final_state.get("error_message"):
            pref_run.status = "failed"
            pref_run.error_message = final_state.get("error_message")
            pref_run.completed_at = now
            telegram_service.record_and_dispatch(
                db,
                event_type="workflow_error",
                title=f"Preference Workflow Error: {pref.preference_name}",
                message=pref_run.error_message or "Workflow encountered an unexpected error.",
                preference_id=pref.id,
                workflow_run_id=pref_run.run_id,
                status_badge="Failed",
            )
        else:
            pref_run.status = "completed"
            pref_run.current_agent = "completed"
            pref_run.error_message = None
            pref_run.completed_at = now

        db.commit()
        self.recompute_workflow_run_totals(db, pref_run.run_id)
        return pref_run

    @staticmethod
    def recompute_workflow_run_totals(
        db: Session,
        workflow_run_id: uuid.UUID,
    ) -> Optional[JobHuntRun]:
        """Aggregate metrics from all `PreferenceExecution` records into `JobHuntRun`."""
        wf_run = db.get(JobHuntRun, workflow_run_id)
        if not wf_run:
            return None

        pref_runs = list(
            db.scalars(
                select(PreferenceExecution).where(
                    PreferenceExecution.run_id == workflow_run_id
                )
            ).all()
        )
        total_spend = sum(
            float((pr.checkpoint_state or {}).get("api_spend_usd", 0.0))
            for pr in pref_runs
        )
        wf_run.api_spend_usd = round(total_spend, 6)

        statuses = {pr.status for pr in pref_runs}
        now = datetime.now(timezone.utc)
        if not statuses or statuses <= {"completed", "skipped"}:
            wf_run.status = "completed"
            wf_run.current_stage = "completed"
            wf_run.completed_at = now
        elif "stopped" in statuses and not ("running" in statuses or "queued" in statuses):
            wf_run.status = "stopped"
            wf_run.current_stage = "stopped"
            wf_run.stopped_at = now
            wf_run.completed_at = now
        elif "paused" in statuses and not ("running" in statuses or "queued" in statuses):
            wf_run.status = "paused"
            wf_run.current_stage = "paused"
            wf_run.paused_at = now
        elif statuses <= {"failed", "completed", "skipped"} and "failed" in statuses:
            wf_run.status = (
                "completed" if "completed" in statuses else "failed"
            )
            wf_run.current_stage = wf_run.status
            wf_run.completed_at = now

        db.commit()
        db.refresh(wf_run)
        return wf_run

    def start_jobhunter_workflow(
        self,
        db: Session,
        trigger_source: str = "manual",
        preference_ids: Optional[List[uuid.UUID]] = None,
        idempotency_key: Optional[str] = None,
        execute_synchronously: bool = True,
    ) -> JobHuntRun:
        """Start JobHunter for all active preferences (or filtered `preference_ids`).

        Enforces:
        1. At least one active job preference exists.
        2. At least one approved resume exists.
        3. Paused preferences are never included.
        4. Every active preference gets its own independent `PreferenceExecution` instance.
        """
        if idempotency_key:
            existing_run = db.scalars(
                select(JobHuntRun).where(JobHuntRun.idempotency_key == idempotency_key)
            ).first()
            if existing_run:
                return existing_run

        stmt_prefs = select(JobPreference).where(JobPreference.is_active.is_(True))
        if preference_ids:
            stmt_prefs = stmt_prefs.where(JobPreference.id.in_(preference_ids))
        active_preferences = list(
            db.scalars(stmt_prefs.order_by(JobPreference.created_at.asc())).all()
        )
        if not active_preferences:
            raise ValueError(
                "No active job preferences found. Activate or create at least one job preference to start JobHunter."
            )

        approved_versions = list(
            db.scalars(
                select(ResumeVersion)
                .where(ResumeVersion.approval_status == "Approved")
                .order_by(ResumeVersion.updated_at.desc())
            ).all()
        )
        if not approved_versions:
            raise ValueError(
                "No approved resume found. Upload, process, and approve a resume version before starting JobHunter."
            )

        settings = self.get_or_create_settings(db)
        settings.is_kill_switch_engaged = False
        settings.automation_state = "running"
        db.flush()

        total_prefs_count = len(list(db.scalars(select(JobPreference.id)).all()))
        now = datetime.now(timezone.utc)
        wf_run = JobHuntRun(
            status="running",
            trigger_source=trigger_source,
            total_preferences=total_prefs_count,
            active_preferences=len(active_preferences),
            current_stage="agent_1_discovery",
            approval_mode=settings.approval_mode,
            max_jobs_per_run=settings.max_jobs_per_run,
            max_applications_per_run=settings.max_applications_per_run,
            idempotency_key=idempotency_key or f"run-{uuid.uuid4()}",
            started_at=now,
        )
        db.add(wf_run)
        db.flush()

        pref_runs: List[PreferenceExecution] = []
        for pref in active_preferences:
            ver_id = pref.approved_resume_version_id or approved_versions[0].id

            pref_run = PreferenceExecution(
                run_id=wf_run.id,
                preference_id=pref.id,
                approved_resume_version_id=ver_id,
                status="queued",
                current_agent="agent_1_discovery",
                checkpoint_state={
                    "workflow_run_id": str(wf_run.id),
                    "preference_id": str(pref.id),
                    "preference_name": pref.preference_name,
                    "completed_agents": [],
                },
            )
            db.add(pref_run)
            pref_runs.append(pref_run)

        db.commit()
        db.refresh(wf_run)

        telegram_service.record_and_dispatch(
            db,
            event_type="workflow_start",
            title="JobHunter Multi-Agent Workflow Started",
            message=(
                f"Started independent multi-agent workflows for {len(active_preferences)} active preference(s): "
                + ", ".join(p.preference_name for p in active_preferences)
            ),
            workflow_run_id=wf_run.id,
            status_badge="Running",
        )

        if execute_synchronously:
            for pr in pref_runs:
                # Independent execution: failure in one preference never stops others
                try:
                    self.execute_preference_workflow(db, pr.id)
                except Exception as exc:
                    pr.status = "failed"
                    pr.error_message = str(exc)
                    pr.completed_at = datetime.now(timezone.utc)
                    db.commit()

            wf_run = self.recompute_workflow_run_totals(db, wf_run.id)
            settings = self.get_or_create_settings(db)
            if wf_run and wf_run.status in ("completed", "failed"):
                settings.automation_state = "ready"
                db.commit()

            if wf_run and wf_run.status == "completed":
                total_disc = sum(pr.jobs_discovered for pr in wf_run.preference_executions)
                total_match = sum(pr.matching_jobs for pr in wf_run.preference_executions)
                total_short = sum(pr.shortlisted_jobs for pr in wf_run.preference_executions)
                telegram_service.record_and_dispatch(
                    db,
                    event_type="workflow_complete",
                    title="JobHunter Workflow Completed",
                    message=(
                        f"Discovered {total_disc} jobs, matched {total_match}, "
                        f"shortlisted {total_short}, and processed applications across "
                        f"{wf_run.active_preferences} active preference(s)."
                    ),
                    workflow_run_id=wf_run.id,
                    status_badge="Completed",
                )
        else:
            from app.services.celery_app import (
                execute_preference_workflow_task,
                is_redis_broker_available,
            )
            if is_redis_broker_available():
                for pr in pref_runs:
                    task = execute_preference_workflow_task.delay(str(pr.id))
                    pr.celery_task_id = str(task.id)
                db.commit()

        db.refresh(wf_run)
        return wf_run

    def pause_workflows(
        self,
        db: Session,
        workflow_run_id: Optional[uuid.UUID] = None,
        preference_id: Optional[uuid.UUID] = None,
    ) -> AutomationSettings:
        """Pause running or queued workflows at safe agent boundaries."""
        settings = self.get_or_create_settings(db)
        if preference_id is None:
            settings.automation_state = "paused"

        stmt = select(PreferenceExecution).where(
            PreferenceExecution.status.in_(("running", "queued"))
        )
        if workflow_run_id:
            stmt = stmt.where(PreferenceExecution.run_id == workflow_run_id)
        if preference_id:
            stmt = stmt.where(PreferenceExecution.preference_id == preference_id)

        affected_run_ids: set[uuid.UUID] = set()
        for pr in db.scalars(stmt).all():
            pr.status = "paused"
            pr.error_message = "Paused by user."
            affected_run_ids.add(pr.run_id)

        if workflow_run_id and preference_id is None:
            wf_run = db.get(JobHuntRun, workflow_run_id)
            if wf_run and wf_run.status == "running":
                wf_run.status = "paused"

        db.commit()
        for rid in affected_run_ids:
            self.recompute_workflow_run_totals(db, rid)
        db.refresh(settings)
        return settings

    def resume_workflows(
        self,
        db: Session,
        workflow_run_id: Optional[uuid.UUID] = None,
        preference_id: Optional[uuid.UUID] = None,
        execute_synchronously: bool = True,
    ) -> List[PreferenceExecution]:
        """Resume paused preference workflows from their saved PostgreSQL checkpoint_state."""
        settings = self.get_or_create_settings(db)
        settings.is_kill_switch_engaged = False
        settings.automation_state = "running"

        stmt = select(PreferenceExecution).where(PreferenceExecution.status == "paused")
        if workflow_run_id:
            stmt = stmt.where(PreferenceExecution.run_id == workflow_run_id)
        if preference_id:
            stmt = stmt.where(PreferenceExecution.preference_id == preference_id)

        paused_runs = list(db.scalars(stmt).all())
        for pr in paused_runs:
            wf_run = db.get(JobHuntRun, pr.run_id)
            if wf_run and wf_run.status == "paused":
                wf_run.status = "running"
            pr.status = "queued"
            pr.error_message = None
        db.commit()

        resumed: List[PreferenceExecution] = []
        if execute_synchronously:
            for pr in paused_runs:
                resumed.append(self.execute_preference_workflow(db, pr.id))
            settings = self.get_or_create_settings(db)
            settings.automation_state = "ready"
            db.commit()
        else:
            from app.services.celery_app import (
                execute_preference_workflow_task,
                is_redis_broker_available,
            )
            if is_redis_broker_available():
                for pr in paused_runs:
                    task = execute_preference_workflow_task.delay(str(pr.id))
                    pr.celery_task_id = str(task.id)
                db.commit()
            resumed = paused_runs
        return resumed

    def stop_all_workflows(
        self,
        db: Session,
        reason: str = "Emergency kill switch engaged by user.",
    ) -> AutomationSettings:
        """Engage the genuine kill switch: immediately stop all active/paused runs and prevent new tasks."""
        settings = self.get_or_create_settings(db)
        settings.is_kill_switch_engaged = True
        settings.automation_state = "stopped"

        now = datetime.now(timezone.utc)
        active_pref_runs = list(
            db.scalars(
                select(PreferenceExecution).where(
                    PreferenceExecution.status.in_(("running", "queued", "paused"))
                )
            ).all()
        )
        for pr in active_pref_runs:
            pr.status = "stopped"
            pr.error_message = reason
            pr.completed_at = now

        active_wf_runs = list(
            db.scalars(
                select(JobHuntRun).where(
                    JobHuntRun.status.in_(("running", "queued", "paused"))
                )
            ).all()
        )
        for wf in active_wf_runs:
            wf.status = "stopped"
            wf.error_message = reason
            wf.completed_at = now

        db.commit()
        db.refresh(settings)
        return settings

    def recover_interrupted_runs(
        self,
        db: Session,
        execute_synchronously: bool = True,
    ) -> List[PreferenceExecution]:
        """Recover any preference workflows left in `running` or `queued` state after a server/worker restart."""
        settings = self.get_or_create_settings(db)
        if settings.is_kill_switch_engaged:
            return []

        interrupted = list(
            db.scalars(
                select(PreferenceExecution).where(
                    PreferenceExecution.status.in_(("running", "queued"))
                )
            ).all()
        )
        recovered: List[PreferenceExecution] = []
        if execute_synchronously:
            for pr in interrupted:
                recovered.append(self.execute_preference_workflow(db, pr.id))
        else:
            from app.services.celery_app import (
                execute_preference_workflow_task,
                is_redis_broker_available,
            )
            if is_redis_broker_available():
                for pr in interrupted:
                    task = execute_preference_workflow_task.delay(str(pr.id))
                    pr.celery_task_id = str(task.id)
                db.commit()
            recovered = interrupted
        return recovered


TupleStatusAndReason = tuple[Optional[str], Optional[str]]
central_orchestrator = CentralOrchestrator()

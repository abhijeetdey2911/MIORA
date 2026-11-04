"""Central Orchestration, Automation Control Centre, and Dashboard API endpoints."""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.multi_agent import (
    AgentExecutionResponse,
    AutomationSettingsResponse,
    AutomationSettingsUpdate,
    DashboardOverviewResponse,
    PreferenceRunSummaryResponse,
    ScheduledJobResponse,
    ScheduledJobUpdate,
    WorkflowRunSummaryResponse,
)
from app.schemas.orchestration import OrchestrationReadinessResponse
from app.services.orchestration import OrchestrationService
from app.services.orchestrator import central_orchestrator

router = APIRouter(prefix="/orchestration")


class StartWorkflowRequest(BaseModel):
    trigger_source: str = Field(default="manual", max_length=32)
    preference_ids: Optional[List[UUID]] = None
    idempotency_key: Optional[str] = Field(default=None, max_length=128)


class PauseResumeRequest(BaseModel):
    workflow_run_id: Optional[UUID] = None
    preference_id: Optional[UUID] = None


class StopWorkflowRequest(BaseModel):
    reason: str = Field(
        default="Emergency kill switch engaged by user.",
        max_length=500,
    )


@router.get(
    "/readiness",
    response_model=OrchestrationReadinessResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Central Orchestration Readiness",
)
def get_orchestration_readiness(
    db: Session = Depends(get_db),
) -> OrchestrationReadinessResponse:
    """Retrieve orchestration readiness and preference eligibility."""
    return OrchestrationService.get_readiness(db)


@router.get(
    "/dashboard",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get PostgreSQL Dashboard Overview (Part 10)",
)
def get_dashboard_overview(
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    """Return live overall statistics, per-preference performance cards, automation status,
    last run summary, and recent updates directly from PostgreSQL.
    """
    return OrchestrationService.get_dashboard_overview(db)


@router.post(
    "/start",
    response_model=WorkflowRunSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Start JobHunter Multi-Agent Workflow (Parts 1 & 9)",
)
def start_jobhunter(
    payload: Optional[StartWorkflowRequest] = None,
    db: Session = Depends(get_db),
) -> WorkflowRunSummaryResponse:
    """Trigger the LangGraph Central Orchestrator across all active job preferences."""
    req = payload or StartWorkflowRequest()
    try:
        wf_run = central_orchestrator.start_jobhunter_workflow(
            db=db,
            trigger_source=req.trigger_source,
            preference_ids=req.preference_ids,
            idempotency_key=req.idempotency_key,
            execute_synchronously=True,
        )
        return OrchestrationService.serialize_workflow_run(db, wf_run)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/pause",
    response_model=AutomationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Pause Active Workflows at Safe Boundaries",
)
def pause_jobhunter(
    payload: Optional[PauseResumeRequest] = None,
    db: Session = Depends(get_db),
) -> AutomationSettingsResponse:
    req = payload or PauseResumeRequest()
    central_orchestrator.pause_workflows(
        db=db,
        workflow_run_id=req.workflow_run_id,
        preference_id=req.preference_id,
    )
    return OrchestrationService.get_settings(db)


@router.post(
    "/resume",
    response_model=List[PreferenceRunSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="Resume Paused Workflows from Checkpoint",
)
def resume_jobhunter(
    payload: Optional[PauseResumeRequest] = None,
    db: Session = Depends(get_db),
) -> List[PreferenceRunSummaryResponse]:
    req = payload or PauseResumeRequest()
    resumed = central_orchestrator.resume_workflows(
        db=db,
        workflow_run_id=req.workflow_run_id,
        preference_id=req.preference_id,
        execute_synchronously=True,
    )
    return [
        PreferenceRunSummaryResponse.model_validate(pr) for pr in resumed
    ]


@router.post(
    "/stop",
    response_model=AutomationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Emergency Stop / Genuine Kill Switch",
)
def stop_jobhunter(
    payload: Optional[StopWorkflowRequest] = None,
    db: Session = Depends(get_db),
) -> AutomationSettingsResponse:
    req = payload or StopWorkflowRequest()
    central_orchestrator.stop_all_workflows(db=db, reason=req.reason)
    return OrchestrationService.get_settings(db)


@router.post(
    "/recover",
    response_model=List[PreferenceRunSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="Recover Interrupted Preference Workflows After Restart",
)
def recover_interrupted_workflows(
    db: Session = Depends(get_db),
) -> List[PreferenceRunSummaryResponse]:
    recovered = central_orchestrator.recover_interrupted_runs(
        db=db,
        execute_synchronously=True,
    )
    return [
        PreferenceRunSummaryResponse.model_validate(pr) for pr in recovered
    ]


@router.get(
    "/settings",
    response_model=AutomationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Automation Control Centre Settings & Limits",
)
def get_automation_settings(
    db: Session = Depends(get_db),
) -> AutomationSettingsResponse:
    return OrchestrationService.get_settings(db)


@router.put(
    "/settings",
    response_model=AutomationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Automation Control Centre Settings & Limits",
)
def update_automation_settings(
    payload: AutomationSettingsUpdate,
    db: Session = Depends(get_db),
) -> AutomationSettingsResponse:
    return OrchestrationService.update_settings(db, payload)


@router.get(
    "/schedule",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Scheduled JobHunter Configuration",
)
def get_schedule(
    db: Session = Depends(get_db),
) -> ScheduledJobResponse:
    return OrchestrationService.get_schedule(db)


@router.put(
    "/schedule",
    response_model=ScheduledJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Scheduled JobHunter Configuration",
)
def update_schedule(
    payload: ScheduledJobUpdate,
    db: Session = Depends(get_db),
) -> ScheduledJobResponse:
    return OrchestrationService.update_schedule(db, payload)


@router.get(
    "/runs",
    response_model=List[WorkflowRunSummaryResponse],
    status_code=status.HTTP_200_OK,
    summary="List Recent Workflow Runs",
)
def list_workflow_runs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> List[WorkflowRunSummaryResponse]:
    return OrchestrationService.list_workflow_runs(db, limit=limit)


@router.get(
    "/agent-executions",
    response_model=List[AgentExecutionResponse],
    status_code=status.HTTP_200_OK,
    summary="List Step-Level Agent Executions",
)
def list_agent_executions(
    workflow_run_id: Optional[UUID] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> List[AgentExecutionResponse]:
    return OrchestrationService.list_agent_executions(
        db, workflow_run_id=workflow_run_id, limit=limit
    )

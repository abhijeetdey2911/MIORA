"""Configurable LLM Provider Integration Layer for Phase 3B AI Resume Intelligence.

Security & Reliability Guarantees:
- Reads API keys exclusively from backend environment variables via `settings`.
- Never exposes API keys in logs or HTTP responses.
- Never logs raw resume contents or sensitive personal information (PII).
- Never substitutes fake or mock data when an API key is missing; raises a clear 503 setup error.
- Implements exponential backoff with jitter (max 3 attempts) for HTTP 429, 500, 502, 503, 504.
- Automatically switches to configurable fallback model on transient primary-model failures.
- Non-retryable authentication (401/403) and invalid model errors fail fast without retry or fallback.
- Validates all LLM JSON responses using Pydantic schemas.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, TypeVar

import httpx
from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.schemas.resume_intelligence import (
    AIProviderStatusResponse,
    LLMRegenerateSuggestionPayload,
    LLMResumeAnalysisPayload,
    LLMResumeEnhancementPayload,
)

logger = logging.getLogger("jobhunter.ai_provider")

T = TypeVar("T", bound=BaseModel)

SETUP_INSTRUCTIONS_MESSAGE = (
    "AI Resume Intelligence is not configured yet. To enable real AI analysis and resume "
    "enhancement, set AI_API_KEY (and optionally AI_PROVIDER and AI_MODEL) in your backend "
    ".env file and restart the backend server."
)

PROVIDER_DEFAULT_BASE_URLS: Dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "anthropic": "https://api.anthropic.com/v1",
}


class AIProviderTransientError(Exception):
    """Raised for transient upstream errors eligible for retry (HTTP 429, 500, 502, 503, 504, timeout)."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.model = model


class AIProviderPermanentError(Exception):
    """Raised for non-retryable upstream errors (HTTP 401, 403, 400, 404)."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        model: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.model = model


def _extract_json_object(raw_text: str) -> Dict[str, Any]:
    """Extract and parse a JSON object from an LLM text response."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback: locate outermost JSON object braces
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = cleaned[start : end + 1]
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed

    raise ValueError("LLM response did not contain a valid JSON object.")


class AIProviderClient:
    """Configurable LLM client with retry backoff, jitter, and fallback model support."""

    def __init__(
        self,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
        initial_backoff_seconds: Optional[float] = None,
        sleep_fn: Optional[Callable[[float], None]] = None,
    ) -> None:
        self.provider = (provider or settings.AI_PROVIDER or "openai").strip().lower()
        self.api_key = (
            api_key.strip()
            if api_key is not None
            else settings.get_effective_ai_api_key()
        )
        self.model = (model or settings.AI_MODEL or "gpt-4o-mini").strip()
        self.fallback_model = (
            fallback_model.strip()
            if fallback_model and fallback_model.strip()
            else settings.get_effective_fallback_model()
        )
        self.base_url = (
            base_url.strip()
            if base_url and base_url.strip()
            else (
                settings.AI_BASE_URL.strip()
                if settings.AI_BASE_URL and settings.AI_BASE_URL.strip()
                else PROVIDER_DEFAULT_BASE_URLS.get(
                    self.provider, PROVIDER_DEFAULT_BASE_URLS.get("openai", "")
                )
            )
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.AI_TIMEOUT_SECONDS
        self.max_retries = max_retries or getattr(settings, "AI_MAX_RETRIES", 3)
        self.initial_backoff_seconds = (
            initial_backoff_seconds
            if initial_backoff_seconds is not None
            else getattr(settings, "AI_INITIAL_BACKOFF_SECONDS", 1.0)
        )
        self.sleep_fn = sleep_fn or time.sleep

    @property
    def is_configured(self) -> bool:
        """Return True if a non-placeholder API key is present."""
        return bool(self.api_key)

    def get_status(self) -> AIProviderStatusResponse:
        """Return safe configuration status without exposing any secret keys."""
        return AIProviderStatusResponse(
            configured=self.is_configured,
            provider=self.provider,
            model=self.model,
            fallback_model=self.fallback_model,
            setup_message=None if self.is_configured else SETUP_INSTRUCTIONS_MESSAGE,
        )

    def require_configured(self) -> None:
        """Raise HTTP 503 with clear setup instructions when no API key is configured."""
        if not self.is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=SETUP_INSTRUCTIONS_MESSAGE,
            )

    def generate_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_cls: Type[T],
        operation_label: str = "ai_operation",
    ) -> T:
        """Execute an LLM call with retry/fallback and validate structured JSON output with Pydantic."""
        self.require_configured()

        # Log only safe metadata (never log resume text, prompts or API keys)
        logger.info(
            "Starting %s via provider=%s primary_model=%s fallback_model=%s (prompt_chars=%d)",
            operation_label,
            self.provider,
            self.model,
            self.fallback_model or "none",
            len(user_prompt),
        )

        try:
            res = self._call_provider(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                operation_label=operation_label,
            )
        except TypeError:
            res = self._call_provider(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

        if isinstance(res, tuple):
            raw_text, model_used = res
        else:
            raw_text = str(res)
            model_used = self.model

        try:
            json_data = _extract_json_object(raw_text)
            validated = schema_cls.model_validate(json_data)
            logger.info(
                "Completed %s via provider=%s model=%s successfully",
                operation_label,
                self.provider,
                model_used,
            )
            try:
                object.__setattr__(validated, "_model_used", model_used)
            except Exception:
                pass
            return validated
        except (ValueError, ValidationError, json.JSONDecodeError) as exc:
            logger.warning(
                "Structured validation failed for %s (provider=%s model=%s): %s",
                operation_label,
                self.provider,
                model_used,
                type(exc).__name__,
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(
                    f"AI provider returned an invalid structured response during "
                    f"{operation_label}. Please try again."
                ),
            ) from exc

    def _call_provider(
        self,
        system_prompt: str,
        user_prompt: str,
        operation_label: str = "ai_operation",
    ) -> Tuple[str, str]:
        """Dispatch HTTP request with exponential backoff + jitter and fallback model support.

        Returns:
            Tuple[str, str]: (raw_text_response, model_used)
        """
        models_to_try: List[str] = [self.model]
        if self.fallback_model and self.fallback_model != self.model:
            models_to_try.append(self.fallback_model)

        last_transient_error: Optional[AIProviderTransientError] = None

        for model_idx, current_model in enumerate(models_to_try):
            is_fallback = model_idx > 0
            if is_fallback:
                logger.warning(
                    "Switching to fallback model=%s for %s after primary model=%s experienced transient failure",
                    current_model,
                    operation_label,
                    self.model,
                )

            for attempt in range(1, self.max_retries + 1):
                try:
                    raw_text = self._call_provider_model(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        model=current_model,
                    )
                    return raw_text, current_model

                except AIProviderPermanentError as perm_err:
                    # Non-retryable authentication or invalid model error: fail fast immediately
                    logger.error(
                        "Non-retryable AI error from provider=%s model=%s status_code=%s",
                        self.provider,
                        current_model,
                        perm_err.status_code,
                    )
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=str(perm_err),
                    ) from perm_err

                except AIProviderTransientError as trans_err:
                    last_transient_error = trans_err
                    status_code_val = trans_err.status_code or 503

                    # If more attempts remain on this model tier, back off and retry
                    if attempt < self.max_retries:
                        # Exponential backoff with jitter: initial_backoff * 2^(attempt-1) + jitter
                        backoff = self.initial_backoff_seconds * (2 ** (attempt - 1))
                        jitter = random.uniform(0.1, 0.5)
                        delay = min(backoff + jitter, 10.0)

                        logger.warning(
                            "AI provider retry attempt=%d/%d provider=%s model=%s status_code=%s delay=%.2fs",
                            attempt + 1,
                            self.max_retries,
                            self.provider,
                            current_model,
                            status_code_val,
                            delay,
                        )
                        self.sleep_fn(delay)
                    else:
                        logger.warning(
                            "Exhausted all %d attempts on provider=%s model=%s status_code=%s",
                            self.max_retries,
                            self.provider,
                            current_model,
                            status_code_val,
                        )

            # End of attempts for current_model; loop moves to fallback_model if available

        # All attempts and fallbacks exhausted
        final_code = (
            last_transient_error.status_code
            if last_transient_error
            and last_transient_error.status_code in (429, 500, 502, 503, 504)
            else 503
        )

        detail_msg = (
            f"The AI service ({self.model}) is temporarily unavailable due to high demand or rate limits "
            f"(HTTP {final_code}). Automatic retries were exhausted. Please wait a moment and try again."
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail_msg,
        ) from last_transient_error

    def _call_provider_model(
        self, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        """Execute a single attempt against a specific model with structured exception translation."""
        start_time = time.perf_counter()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                if self.provider == "gemini":
                    res = self._call_gemini(client, system_prompt, user_prompt, model=model)
                elif self.provider == "anthropic":
                    res = self._call_anthropic(client, system_prompt, user_prompt, model=model)
                else:
                    res = self._call_openai_compatible(client, system_prompt, user_prompt, model=model)

                duration = time.perf_counter() - start_time
                logger.info(
                    "AI provider call succeeded: provider=%s model=%s status=200 duration=%.2fs",
                    self.provider,
                    model,
                    duration,
                )
                return res
        except (AIProviderTransientError, AIProviderPermanentError) as exc:
            duration = time.perf_counter() - start_time
            logger.warning(
                "AI provider call error: provider=%s model=%s status=%s duration=%.2fs",
                self.provider,
                model,
                exc.status_code,
                duration,
            )
            raise
        except HTTPException:
            raise
        except httpx.TimeoutException as exc:
            duration = time.perf_counter() - start_time
            logger.warning(
                "AI provider timeout: provider=%s model=%s duration=%.2fs",
                self.provider,
                model,
                duration,
            )
            raise AIProviderTransientError(
                f"AI provider request timed out after {self.timeout_seconds}s.",
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                model=model,
            ) from exc
        except (httpx.RequestError, httpx.NetworkError) as exc:
            duration = time.perf_counter() - start_time
            logger.warning(
                "AI provider network error: provider=%s model=%s error=%s duration=%.2fs",
                self.provider,
                model,
                type(exc).__name__,
                duration,
            )
            raise AIProviderTransientError(
                f"Network error communicating with AI provider: {type(exc).__name__}",
                status_code=status.HTTP_502_BAD_GATEWAY,
                model=model,
            ) from exc

    def _call_openai_compatible(
        self, client: httpx.Client, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        response = client.post(url, headers=headers, json=payload)
        self._check_http_status(response, model=model)
        body = response.json()
        choices = body.get("choices") or []
        if not choices or not choices[0].get("message", {}).get("content"):
            raise AIProviderTransientError(
                "AI provider returned an empty completion response.",
                status_code=502,
                model=model,
            )
        return str(choices[0]["message"]["content"])

    def _call_gemini(
        self, client: httpx.Client, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        url = f"{self.base_url}/models/{model}:generateContent"
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": str(self.api_key),
        }
        payload: Dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        response = client.post(url, headers=headers, json=payload)
        self._check_http_status(response, model=model)
        body = response.json()
        candidates = body.get("candidates") or []
        if not candidates:
            raise AIProviderTransientError(
                "Gemini API returned no candidates.",
                status_code=502,
                model=model,
            )
        parts = candidates[0].get("content", {}).get("parts") or []
        if not parts or "text" not in parts[0]:
            raise AIProviderTransientError(
                "Gemini API returned an empty text part.",
                status_code=502,
                model=model,
            )
        return str(parts[0]["text"])

    def _call_anthropic(
        self, client: httpx.Client, system_prompt: str, user_prompt: str, model: str
    ) -> str:
        url = f"{self.base_url}/messages"
        headers = {
            "x-api-key": str(self.api_key),
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        response = client.post(url, headers=headers, json=payload)
        self._check_http_status(response, model=model)
        body = response.json()
        content_blocks = body.get("content") or []
        if not content_blocks or "text" not in content_blocks[0]:
            raise AIProviderTransientError(
                "Anthropic API returned an empty message content.",
                status_code=502,
                model=model,
            )
        return str(content_blocks[0]["text"])

    def _check_http_status(self, response: httpx.Response, model: str) -> None:
        """Validate response status code and translate into Transient vs Permanent errors."""
        if 200 <= response.status_code < 300:
            return

        status_code = response.status_code
        err_msg = ""
        try:
            body = response.json()
            if isinstance(body, dict):
                err = body.get("error")
                if isinstance(err, dict):
                    err_msg = err.get("message") or ""
                elif isinstance(err, str):
                    err_msg = err
        except Exception:
            pass

        if not err_msg:
            err_msg = response.text[:200]

        # 1. Authentication errors (401, 403) -> Non-retryable
        if status_code in (401, 403):
            raise AIProviderPermanentError(
                f"AI provider authentication failed (HTTP {status_code}). Please verify your AI_API_KEY in backend/.env.",
                status_code=status_code,
                model=model,
            )

        # 2. Invalid model or bad request (400, 404) -> Non-retryable
        if status_code in (400, 404):
            raise AIProviderPermanentError(
                f"AI provider rejected request for model '{model}' (HTTP {status_code}): {err_msg}",
                status_code=status_code,
                model=model,
            )

        # 3. Rate limits (429) -> Transient / Retryable
        if status_code == 429:
            raise AIProviderTransientError(
                f"AI provider rate limit reached (HTTP 429): {err_msg}",
                status_code=429,
                model=model,
            )

        # 4. Server errors & High Demand (500, 502, 503, 504) -> Transient / Retryable
        if status_code in (500, 502, 503, 504):
            raise AIProviderTransientError(
                f"AI provider temporary error (HTTP {status_code}): {err_msg}",
                status_code=status_code,
                model=model,
            )

        # 5. Other 4xx client errors -> Non-retryable
        if 400 <= status_code < 500:
            raise AIProviderPermanentError(
                f"AI provider client error (HTTP {status_code}): {err_msg}",
                status_code=status_code,
                model=model,
            )

        # 6. Fallback -> Transient
        raise AIProviderTransientError(
            f"AI provider returned HTTP {status_code}: {err_msg}",
            status_code=status_code,
            model=model,
        )

    # ==========================================================================
    # High-level Structured Operations
    # ==========================================================================

    def analyse_resume(
        self,
        resume_text: str,
        preferences_context: List[Dict[str, Any]],
    ) -> LLMResumeAnalysisPayload:
        """Analyse extracted resume text and evaluate against associated job preferences."""
        system_prompt = (
            "You are an expert technical recruiter and career coach for Project JobHunter.\n"
            "STRICT RULES:\n"
            "1. Analyse ONLY the provided resume text. Do NOT assume or invent facts, degrees, "
            "employers, metrics, tools, or achievements not present in the resume.\n"
            "2. For each associated Job Preference, generate a separate evaluation in `preference_analyses`.\n"
            "3. Never treat missing keywords as proof that the candidate lacks a skill; frame them as "
            "keywords not explicitly mentioned in the resume text.\n"
            "4. Assign integer scores from 0 to 100 as realistic estimates (not guarantees) and explain "
            "briefly why each score was assigned in `score_explanations`.\n"
            "5. Provide actionable suggestions across sections: Professional Summary, Skills Section, "
            "Project Descriptions, Experience Descriptions, Education Section, Keywords, and Formatting and Readability.\n"
            "6. If more factual information is needed (such as team size, metrics, or specific tools used), "
            "include a `clarifying_question` and list it in `missing_information_questions` instead of guessing.\n"
            "7. Respond ONLY with a valid JSON object matching the required schema."
        )

        user_prompt = json.dumps(
            {
                "task": "Perform comprehensive resume analysis and preference-specific evaluation.",
                "associated_job_preferences": preferences_context,
                "resume_text": resume_text,
                "required_json_keys": {
                    "candidate_profile": {
                        "full_name": "string or null",
                        "headline": "string or null",
                        "location": "string or null",
                        "years_of_experience": "string or null",
                        "contact_channels_present": ["string"],
                        "summary_evaluation": "string",
                    },
                    "education": [
                        {
                            "degree": "string",
                            "institution": "string or null",
                            "graduation_year": "string or null",
                            "details": "string or null",
                        }
                    ],
                    "technical_skills": ["string"],
                    "soft_skills": ["string"],
                    "work_experience": [
                        {
                            "role": "string",
                            "company": "string or null",
                            "duration": "string or null",
                            "key_contributions": ["string"],
                        }
                    ],
                    "internships": [
                        {
                            "role": "string",
                            "company": "string or null",
                            "duration": "string or null",
                            "key_contributions": ["string"],
                        }
                    ],
                    "projects": [
                        {
                            "title": "string",
                            "technologies": ["string"],
                            "summary": "string",
                            "impact": "string or null",
                        }
                    ],
                    "certifications": ["string"],
                    "achievements": ["string"],
                    "tools_and_technologies": ["string"],
                    "preference_analyses": [
                        {
                            "preference_id": "string",
                            "preference_name": "string",
                            "target_roles": ["string"],
                            "preference_relevance_score": "0-100 integer",
                            "score_explanation": "string",
                            "relevant_skills": ["string"],
                            "relevant_projects": ["string"],
                            "experience_alignment": "string",
                            "missing_relevant_keywords": ["string"],
                            "strengths": ["string"],
                            "weaknesses": ["string"],
                            "improvement_opportunities": ["string"],
                        }
                    ],
                    "overall_quality_score": "0-100 integer",
                    "preference_relevance_score": "0-100 integer",
                    "skills_alignment_score": "0-100 integer",
                    "experience_alignment_score": "0-100 integer",
                    "project_relevance_score": "0-100 integer",
                    "ats_readability_score": "0-100 integer",
                    "score_explanations": {
                        "overall_quality": "string",
                        "preference_relevance": "string",
                        "skills_alignment": "string",
                        "experience_alignment": "string",
                        "project_relevance": "string",
                        "ats_readability": "string",
                    },
                    "overall_strengths": ["string"],
                    "overall_weaknesses": ["string"],
                    "missing_information_questions": ["string"],
                    "suggestions": [
                        {
                            "section_name": "Professional Summary | Skills Section | Project Descriptions | Experience Descriptions | Education Section | Keywords | Formatting and Readability",
                            "current_content": "string or null",
                            "suggested_improvement": "string",
                            "reason": "string",
                            "priority": "High | Medium | Low",
                            "clarifying_question": "string or null",
                        }
                    ],
                },
            },
            ensure_ascii=False,
        )

        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_cls=LLMResumeAnalysisPayload,
            operation_label="resume_analysis",
        )

    def enhance_resume(
        self,
        resume_text: str,
        sections: Optional[List[str]],
        preferences_context: List[Dict[str, Any]],
        accepted_suggestions: List[Dict[str, Any]],
    ) -> LLMResumeEnhancementPayload:
        """Generate an improved resume draft with side-by-side section comparisons."""
        system_prompt = (
            "You are an expert resume writer for Project JobHunter ('Improve My Resume').\n"
            "STRICT RULES:\n"
            "1. Preserve 100% of the candidate's actual facts, dates, employers, degrees, and tools.\n"
            "2. NEVER fabricate numbers, metrics, achievements, tools, or responsibilities.\n"
            "3. Improve grammar, clarity, professional language, and action verbs.\n"
            "4. Make project and experience descriptions clearer and easier to scan.\n"
            "5. Suggest relevant keywords ONLY when supported by actual experience in the resume.\n"
            "6. Return both the full improved resume text (`improved_full_content`) and a list of "
            "side-by-side section comparisons (`section_changes`) with `section_name`, "
            "`original_content`, `suggested_content`, and `reason`.\n"
            "7. Respond ONLY with a valid JSON object."
        )

        user_prompt = json.dumps(
            {
                "task": "Generate fact-preserving AI resume enhancement draft and side-by-side section comparisons.",
                "requested_sections": sections or [
                    "Professional Summary",
                    "Skills Section",
                    "Experience Descriptions",
                    "Project Descriptions",
                    "Education Section",
                ],
                "target_job_preferences": preferences_context,
                "accepted_suggestions_to_incorporate": accepted_suggestions,
                "original_resume_text": resume_text,
                "required_json_keys": {
                    "title": "string",
                    "improved_full_content": "string",
                    "section_changes": [
                        {
                            "section_name": "string",
                            "original_content": "string",
                            "suggested_content": "string",
                            "reason": "string",
                        }
                    ],
                },
            },
            ensure_ascii=False,
        )

        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_cls=LLMResumeEnhancementPayload,
            operation_label="resume_enhancement",
        )

    def regenerate_suggestion(
        self,
        resume_text: str,
        section_name: str,
        current_content: Optional[str],
        previous_suggestion: str,
        user_instruction: Optional[str],
        preferences_context: List[Dict[str, Any]],
    ) -> LLMRegenerateSuggestionPayload:
        """Regenerate a single section suggestion while preserving candidate facts."""
        system_prompt = (
            "You are an expert resume advisor for Project JobHunter.\n"
            "Regenerate an alternative improvement suggestion for the specified resume section.\n"
            "Preserve the candidate's actual facts and never fabricate metrics, tools, or responsibilities.\n"
            "Respond ONLY with a valid JSON object matching the required schema."
        )

        user_prompt = json.dumps(
            {
                "task": "Regenerate section improvement suggestion.",
                "section_name": section_name,
                "current_content": current_content,
                "previous_suggestion": previous_suggestion,
                "user_instruction": user_instruction,
                "target_job_preferences": preferences_context,
                "resume_text": resume_text,
                "required_json_keys": {
                    "section_name": section_name,
                    "current_content": "string or null",
                    "suggested_improvement": "string",
                    "reason": "string",
                    "priority": "High | Medium | Low",
                    "clarifying_question": "string or null",
                },
            },
            ensure_ascii=False,
        )

        return self.generate_structured(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_cls=LLMRegenerateSuggestionPayload,
            operation_label="regenerate_suggestion",
        )


def get_ai_provider_client() -> AIProviderClient:
    """Dependency / factory function returning a configured AIProviderClient instance."""
    return AIProviderClient()


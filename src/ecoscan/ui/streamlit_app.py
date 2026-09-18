from __future__ import annotations

import base64
import hashlib
import html
import json
import logging
import os
from datetime import datetime
import tempfile
from pathlib import Path
from typing import Any

from ecoscan.app.pipeline import ProcessingPipelineOptions
from ecoscan.config import load_config
from ecoscan.ui.identity import render_identity
from ecoscan.ui.learning import render_contribution, render_review, render_scope, render_citizen_protocols
from ecoscan.disposal.collection_points import (
    CollectionPoint,
    build_collection_point_directions_url,
    build_collection_point_map_url,
    filter_collection_points,
    load_collection_points,
    rank_collection_points,
)
from ecoscan.disposal.guidance import DisposalGuidance, load_guidance
from ecoscan.disposal.impact import (
    EnvironmentalImpact,
    get_environmental_impact,
    load_environmental_impacts,
)
from ecoscan.disposal.targets import (
    DisposalTarget,
    build_map_search_url,
    get_disposal_target,
    load_disposal_targets,
)
from ecoscan.errors import describe_exception, error_catalog
from ecoscan.services.academic_report import write_academic_report
from ecoscan.services.acceptance_checks import run_acceptance_checks
from ecoscan.services.analysis_service import analyze_waste_image
from ecoscan.services.aps_audit import build_aps_audit, summarize_audit
from ecoscan.services.accounts import (
    UserProfile,
    append_point_transaction,
    build_point_transaction,
    fallback_profiles,
    has_awarded_evidence,
    load_user_profiles,
    points_ledger_path_from_config,
    profiles_path_from_config,
    read_point_transactions,
    summarize_points_by_user,
    total_points_for_user,
)
from ecoscan.services.access_plan import (
    access_link_rows,
    build_access_plan,
    probe_access_services,
    shareable_access_text,
)
from ecoscan.services.campaigns import (
    Campaign,
    Mission,
    campaign_path_from_config,
    evaluate_mission_submission,
    load_campaign,
)
from ecoscan.services.civic_reports import (
    append_civic_report,
    append_civic_report_review,
    build_civic_report_review,
    build_civic_report_record,
    civic_report_reviews_path_from_config,
    civic_reports_path_from_config,
    latest_reviews_by_report,
    read_civic_reports,
    read_civic_report_reviews,
    save_civic_report_evidence,
)
from ecoscan.services.completion import build_completion_plan
from ecoscan.services.dataset_governance import build_dataset_readiness
from ecoscan.services.dataset_ingestion import (
    IncomingImage,
    ingestion_manifest_path_from_config,
    ingest_uploaded_images,
)
from ecoscan.services.delivery_pack import build_delivery_pack, write_delivery_pack
from ecoscan.services.deployment_readiness import build_free_hosting_plan, deployment_check_rows
from ecoscan.services.diagnostics import dataset_status, dependency_status, model_status
from ecoscan.services.history import (
    append_history_entry,
    build_history_entry,
    history_path_from_config,
    read_history,
)
from ecoscan.services.final_readiness import build_final_readiness_items, summarize_final_readiness
from ecoscan.services.field_testing import (
    append_field_test_record,
    build_field_test_record,
    field_test_class_rows,
    field_test_manifest_path_from_config,
    field_test_rows,
    read_field_test_records,
    summarize_field_tests,
)
from ecoscan.services.model_governance import (
    build_model_governance_plan,
    hard_case_table_rows,
    metric_snapshot_rows,
    model_gate_table_rows,
)
from ecoscan.services.operations import (
    build_campaign_operations_summary,
    format_class_labels,
    mission_activity_rows,
    published_mission_rows,
)
from ecoscan.services.photo_requirements import PhotoRequirement, load_photo_requirements
from ecoscan.services.public_flow import PublicNextAction, build_public_next_action
from ecoscan.services.recognition_feedback import (
    append_recognition_feedback,
    feedback_manifest_path_from_config,
    read_recognition_feedback,
)
from ecoscan.services.recognition_improvement import (
    RecognitionImprovementPlan,
    build_recognition_improvement_plan,
    confusion_table_rows,
    priority_table_rows,
)
from ecoscan.services.recognition_safety import (
    RecognitionSafetyDecision,
    build_recognition_safety_decision,
    capture_photo_tips,
)
from ecoscan.services.usage_quality import (
    build_recognition_quality_summary,
    class_quality_rows,
    correction_rows,
)
from ecoscan.services.visual_report import save_pipeline_artifacts
from ecoscan.utils.logging_config import configure_logging


LOGGER = logging.getLogger(__name__)


def _format_percent(value: float | None) -> str:
    if value is None:
        return "indisponível"
    return f"{value * 100:.1f}%"


def _format_count(value: int, singular: str, plural: str | None = None) -> str:
    label = singular if value == 1 else (plural or f"{singular}s")
    return f"{value} {label}"


def _render_theme(st: Any) -> None:
    st.markdown(
        """
        <style>
        #MainMenu,
        footer,
        header,
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="stDeployButton"] {
            display: none !important;
            visibility: hidden !important;
        }
        :root {
            --eco-ink: #17342a;
            --eco-ink-strong: #0a2f27;
            --eco-muted: #5b6f65;
            --eco-surface: #ffffff;
            --eco-surface-soft: #f3faf6;
            --eco-line: #d4e7de;
            --eco-primary: #0e7a57;
            --eco-primary-soft: #e3f7ee;
            --eco-leaf: #49a464;
            --eco-water: #1f7897;
            --eco-blue: #2468b2;
            --eco-blue-soft: #e8f3ff;
            --eco-accent: #f0bd3f;
            --eco-earth: #8b6b38;
            --eco-danger: #b94a3a;
            --eco-shadow: 0 14px 34px rgba(14, 84, 61, 0.095);
            --eco-shadow-strong: 0 24px 60px rgba(7, 57, 43, 0.20);
            --eco-font: "Segoe UI Variable", "Segoe UI", Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }
        html,
        body,
        .stApp,
        button,
        input,
        textarea,
        select {
            font-family: var(--eco-font) !important;
            letter-spacing: 0;
        }
        p,
        span,
        label,
        small,
        div {
            line-height: 1.42;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: 1180px;
            padding-top: 0.75rem;
            padding-bottom: 2rem;
        }
        .stApp {
            background:
                linear-gradient(135deg, rgba(14, 122, 87, 0.08) 0 13%, transparent 13% 100%),
                repeating-linear-gradient(135deg, rgba(31, 120, 151, 0.045) 0 1px, transparent 1px 24px),
                linear-gradient(180deg, #f8fcf8 0%, #edf7f1 52%, #f6f9fb 100%);
            color: var(--eco-ink);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, var(--eco-surface-soft) 100%);
            border-right: 1px solid var(--eco-line);
        }
        [data-testid="stMetric"] {
            border: 1px solid var(--eco-line);
            border-radius: 8px;
            background: var(--eco-surface);
            padding: 0.72rem 0.82rem;
            box-shadow: var(--eco-shadow);
        }
        [data-testid="stButton"] button,
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stDownloadButton"] button {
            border-radius: 8px;
            border: 1px solid #b8d4c7;
            min-height: 2.72rem;
            font-weight: 780;
            background: var(--eco-surface);
            box-shadow: 0 8px 18px rgba(12, 47, 36, 0.055);
            transition: border-color 160ms ease, box-shadow 160ms ease, transform 160ms ease, color 160ms ease;
        }
        [data-testid="stButton"] button:hover,
        [data-testid="stFormSubmitButton"] button:hover,
        [data-testid="stDownloadButton"] button:hover {
            border-color: var(--eco-primary);
            color: var(--eco-primary);
            box-shadow: 0 12px 24px rgba(15, 111, 80, 0.13);
            transform: translateY(-1px);
        }
        [data-testid="stButton"] button:disabled,
        [data-testid="stFormSubmitButton"] button:disabled,
        [data-testid="stDownloadButton"] button:disabled {
            border-color: #d5ded8;
            background: #eef5f1;
            color: #7a8c83;
            box-shadow: none;
            transform: none;
        }
        div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
            gap: 0.4rem;
            background: rgba(255, 255, 255, 0.94);
            border: 1px solid var(--eco-line);
            border-radius: 8px;
            padding: 0.42rem;
            margin-bottom: 1rem;
            box-shadow: var(--eco-shadow);
            overflow-x: auto;
            position: sticky;
            top: 0.45rem;
            z-index: 30;
            backdrop-filter: blur(14px);
        }
        div[data-testid="stTabs"] button {
            border-radius: 8px;
            font-weight: 780;
            min-height: 2.72rem;
            padding: 0.25rem 0.92rem;
            border: 1px solid transparent;
            white-space: nowrap;
        }
        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: linear-gradient(135deg, var(--eco-primary) 0%, var(--eco-leaf) 54%, var(--eco-water) 100%);
            color: #ffffff;
            box-shadow: 0 10px 22px rgba(15, 111, 80, 0.22);
        }
        .ecoscan-hero {
            border: 1px solid rgba(219, 235, 226, 0.72);
            border-top: 0;
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(7, 66, 50, 0.98) 0%, rgba(17, 119, 85, 0.97) 48%, rgba(31, 120, 151, 0.96) 100%);
            padding: 0;
            margin-bottom: 0.85rem;
            box-shadow: var(--eco-shadow-strong);
            overflow: hidden;
            position: relative;
        }
        .ecoscan-hero-admin {
            background:
                linear-gradient(135deg, rgba(7, 70, 54, 0.98) 0%, rgba(14, 122, 87, 0.97) 50%, rgba(36, 104, 178, 0.95) 100%);
        }
        .ecoscan-hero-user {
            background:
                linear-gradient(135deg, rgba(6, 77, 58, 0.98) 0%, rgba(24, 146, 88, 0.97) 52%, rgba(31, 120, 151, 0.95) 100%);
        }
        .ecoscan-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(90deg, rgba(255, 255, 255, 0.08) 0 1px, transparent 1px 100%),
                linear-gradient(0deg, rgba(255, 255, 255, 0.07) 0 1px, transparent 1px 100%),
                repeating-linear-gradient(135deg, rgba(231, 255, 240, 0.12) 0 1px, transparent 1px 18px);
            background-size: 42px 42px, 42px 42px, auto;
            pointer-events: none;
        }
        .ecoscan-hero::after {
            content: "";
            position: absolute;
            inset: auto 0 0;
            height: 5px;
            background: linear-gradient(90deg, #2474c9 0 24%, #d9342b 24% 46%, #f2bc28 46% 68%, #1b8f5a 68% 100%);
            pointer-events: none;
        }
        .ecoscan-gov-ribbon {
            align-items: center;
            background: rgba(6, 69, 51, 0.82);
            color: #ffffff;
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            padding: 0.46rem 0.95rem;
            font-size: 0.76rem;
            font-weight: 720;
            position: relative;
            z-index: 1;
        }
        .ecoscan-gov-ribbon span {
            color: #d9f5e8;
            font-weight: 620;
        }
        .ecoscan-appbar {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            margin: 0;
            padding: 0.9rem 1rem 0.25rem;
            position: relative;
            z-index: 1;
        }
        .ecoscan-brand {
            align-items: center;
            display: flex;
            gap: 0.65rem;
            min-width: 0;
        }
        .ecoscan-logo-mark {
            align-items: center;
            background: linear-gradient(135deg, #e8fff4 0%, #bdf0d3 100%);
            border-radius: 8px;
            color: #0c4b38;
            display: inline-flex;
            flex: 0 0 auto;
            font-size: 0.78rem;
            font-weight: 820;
            height: 2.35rem;
            justify-content: center;
            width: 2.35rem;
            box-shadow: inset 0 -4px 0 #2f80ed, 0 10px 24px rgba(0, 0, 0, 0.16);
        }
        .ecoscan-brand strong {
            color: #ffffff;
            display: block;
            font-size: 1rem;
            font-weight: 760;
            line-height: 1.1;
        }
        .ecoscan-brand span {
            color: rgba(237, 253, 246, 0.82);
            display: block;
            font-size: 0.78rem;
            font-weight: 580;
            line-height: 1.25;
        }
        .ecoscan-mode-pill {
            border: 1px solid rgba(220, 250, 234, 0.42);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            color: #e6fff2;
            flex: 0 0 auto;
            font-size: 0.78rem;
            font-weight: 760;
            padding: 0.36rem 0.68rem;
            white-space: nowrap;
        }
        .ecoscan-hero-body {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(290px, 0.9fr);
            gap: 1rem;
            align-items: stretch;
            padding: 0.8rem 1rem 1.05rem;
            position: relative;
            z-index: 1;
        }
        .ecoscan-hero-copy {
            align-self: center;
        }
        .ecoscan-hero-side {
            display: grid;
            gap: 0.72rem;
        }
        .ecoscan-hero-panel {
            border: 1px solid rgba(229, 246, 238, 0.34);
            border-radius: 8px;
            background: rgba(255,255,255,0.13);
            backdrop-filter: blur(12px);
            padding: 0.85rem;
            display: grid;
            gap: 0.55rem;
        }
        .ecoscan-hero-panel-row {
            align-items: center;
            display: flex;
            justify-content: space-between;
            gap: 0.65rem;
            border-bottom: 1px solid rgba(230, 255, 242, 0.22);
            padding-bottom: 0.5rem;
        }
        .ecoscan-hero-panel-row:last-child {
            border-bottom: 0;
            padding-bottom: 0;
        }
        .ecoscan-hero-panel-row span {
            color: rgba(234, 255, 245, 0.72);
            font-size: 0.78rem;
            font-weight: 750;
        }
        .ecoscan-hero-panel-row strong {
            color: #ffffff;
            font-size: 0.9rem;
            text-align: right;
        }
        .ecoscan-recycle-visual {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.62rem;
            min-height: 100%;
        }
        .ecoscan-recycle-center {
            align-items: center;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(237, 253, 246, 0.96) 100%);
            border: 1px solid rgba(255, 255, 255, 0.72);
            border-radius: 8px;
            box-shadow: 0 18px 36px rgba(0, 0, 0, 0.13);
            color: #103d2f;
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 132px;
            padding: 0.88rem;
            position: relative;
            overflow: hidden;
        }
        .ecoscan-recycle-center::before {
            content: "";
            position: absolute;
            inset: 0;
            background: repeating-linear-gradient(135deg, rgba(36, 116, 93, 0.08) 0 1px, transparent 1px 12px);
            pointer-events: none;
        }
        .ecoscan-recycle-symbol {
            color: #24745d;
            font-size: 2.1rem;
            font-weight: 900;
            line-height: 1;
            position: relative;
        }
        .ecoscan-recycle-center strong,
        .ecoscan-recycle-center small {
            position: relative;
        }
        .ecoscan-recycle-center strong {
            font-size: 1rem;
            line-height: 1.1;
            margin-top: 0.2rem;
        }
        .ecoscan-recycle-center small {
            color: #52685e;
            font-size: 0.76rem;
            font-weight: 760;
            margin-top: 0.25rem;
            text-align: center;
        }
        .ecoscan-recycle-tile {
            align-items: center;
            background: rgba(255, 255, 255, 0.13);
            border: 1px solid rgba(229, 246, 238, 0.30);
            border-radius: 8px;
            display: flex;
            gap: 0.55rem;
            min-height: 88px;
            padding: 0.55rem;
        }
        .ecoscan-recycle-tile img {
            background: rgba(255, 255, 255, 0.88);
            border-radius: 8px;
            display: block;
            height: 60px;
            object-fit: contain;
            padding: 0.28rem;
            width: 60px;
        }
        .ecoscan-recycle-tile span {
            color: #ffffff;
            display: block;
            font-size: 0.82rem;
            font-weight: 860;
            line-height: 1.18;
        }
        .ecoscan-recycle-tile small {
            color: rgba(237, 253, 246, 0.74);
            display: block;
            font-size: 0.72rem;
            font-weight: 720;
            margin-top: 0.16rem;
        }
        .ecoscan-service-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 0.85rem;
        }
        .ecoscan-service-chip {
            border: 1px solid rgba(224, 255, 238, 0.36);
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.14);
            color: #effff7;
            display: inline-flex;
            font-size: 0.82rem;
            font-weight: 800;
            min-height: 2rem;
            align-items: center;
            padding: 0 0.7rem;
            white-space: nowrap;
        }
        .ecoscan-user-flow {
            border: 0;
            border-radius: 0;
            background: transparent;
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.62rem;
            overflow: hidden;
            margin: 0.25rem 0 1rem;
            box-shadow: none;
        }
        .ecoscan-user-flow div {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(244, 251, 247, 0.98) 100%);
            border: 1px solid var(--eco-line);
            border-radius: 8px;
            box-shadow: var(--eco-shadow);
            padding: 0.82rem 0.85rem;
            position: relative;
            min-height: 92px;
            cursor: default;
        }
        .ecoscan-user-flow div:hover {
            border-color: var(--eco-line);
            box-shadow: var(--eco-shadow);
            transform: none;
        }
        .ecoscan-user-flow div::before {
            content: "";
            background: linear-gradient(180deg, var(--eco-primary), var(--eco-water));
            border-radius: 999px;
            height: 32px;
            left: 0;
            position: absolute;
            top: 0.82rem;
            width: 4px;
        }
        .ecoscan-user-flow div::after {
            align-items: center;
            background: linear-gradient(135deg, var(--eco-primary) 0%, var(--eco-accent) 100%);
            border-radius: 999px;
            content: attr(data-step);
            display: inline-flex;
            color: #0c3d2f;
            font-size: 0.66rem;
            font-weight: 900;
            height: 1.35rem;
            justify-content: center;
            position: absolute;
            right: 0.65rem;
            top: 0.62rem;
            width: 1.35rem;
        }
        .ecoscan-user-flow div:last-child {
            border-right: 1px solid var(--eco-line);
        }
        .ecoscan-user-flow span {
            color: var(--eco-primary);
            display: block;
            font-size: 0.74rem;
            font-weight: 760;
            text-transform: uppercase;
        }
        .ecoscan-user-flow strong {
            color: var(--eco-ink-strong);
            display: block;
            font-size: 0.96rem;
            font-weight: 730;
            margin-top: 0.18rem;
        }
        .ecoscan-kicker {
            color: #bdf0d3;
            font-size: 0.78rem;
            font-weight: 720;
            letter-spacing: 0;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }
        .ecoscan-title {
            color: #f8fff9 !important;
            font-size: 2.22rem;
            line-height: 1.08;
            font-weight: 780;
            margin: 0;
            max-width: 720px;
            text-shadow: 0 2px 16px rgba(3, 34, 25, 0.22);
        }
        .ecoscan-subtitle {
            color: rgba(241, 253, 247, 0.86);
            font-size: 0.98rem;
            font-weight: 460;
            line-height: 1.45;
            margin-top: 0.45rem;
            max-width: 720px;
        }
        .ecoscan-badges,
        .ecoscan-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.75rem;
        }
        .ecoscan-badge,
        .ecoscan-chip {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            border: 1px solid #d3ddd4;
            background: #ffffff;
            color: #22362d;
            padding: 0.28rem 0.58rem;
            font-size: 0.82rem;
            font-weight: 650;
            white-space: nowrap;
        }
        .ecoscan-badge-ok {
            border-color: #acd7c5;
            background: #e6f4ee;
            color: #155f49;
        }
        .ecoscan-badge-warn {
            border-color: #f0cf85;
            background: #fff7e3;
            color: #76520c;
        }
        .ecoscan-badge-danger {
            border-color: #e2b0a6;
            background: #fff0ed;
            color: #8c3024;
        }
        .ecoscan-chip small {
            color: #6b7d73;
            font-weight: 600;
        }
        .ecoscan-status-strip {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.65rem;
            margin: 0 0 0.95rem;
        }
        .ecoscan-status-item {
            border: 1px solid var(--eco-line);
            border-radius: 8px;
            background: linear-gradient(180deg, var(--eco-surface) 0%, var(--eco-surface-soft) 100%);
            padding: 0.75rem 0.85rem;
            min-height: 84px;
            box-shadow: var(--eco-shadow);
        }
        .ecoscan-status-item span {
            display: block;
            color: var(--eco-muted);
            font-size: 0.78rem;
            font-weight: 680;
            margin-bottom: 0.35rem;
        }
        .ecoscan-status-item strong {
            display: block;
            color: var(--eco-ink);
            font-size: 1rem;
            line-height: 1.2;
            overflow-wrap: anywhere;
        }
        .ecoscan-status-item small {
            color: var(--eco-muted);
            display: block;
            line-height: 1.3;
            margin-top: 0.28rem;
        }
        .ecoscan-status-ok {
            border-top: 4px solid var(--eco-primary);
        }
        .ecoscan-status-warn {
            border-top: 4px solid var(--eco-accent);
        }
        .ecoscan-status-danger {
            border-top: 4px solid #b94a3a;
        }
        .ecoscan-section-title {
            color: #10233f;
            font-size: 1.06rem;
            font-weight: 850;
            margin: 0.2rem 0 0.55rem;
            display: flex;
            align-items: center;
            gap: 0.45rem;
        }
        .ecoscan-section-title::before {
            content: "";
            background: linear-gradient(180deg, #24745d 0%, #2f80ed 100%);
            border-radius: 999px;
            display: inline-block;
            height: 1.1rem;
            width: 0.26rem;
        }
        .ecoscan-note {
            border: 1px solid #eadab1;
            background: #fffbef;
            border-radius: 8px;
            color: #51432a;
            padding: 0.75rem 0.9rem;
            margin: 0.65rem 0 1rem;
        }
        .ecoscan-result {
            border: 1px solid #d5e6dc;
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbf9 100%);
            padding: 1rem;
            box-shadow: 0 16px 32px rgba(18, 31, 25, 0.07);
        }
        .ecoscan-result h3 {
            margin-top: 0;
        }
        .ecoscan-disposal-panel {
            border: 1px solid #d5e6dc;
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f7fbf8 100%);
            padding: 1rem;
            margin: 0.9rem 0;
            box-shadow: 0 16px 32px rgba(25, 41, 32, 0.065);
        }
        .ecoscan-disposal-panel.featured {
            border-color: #b9d8ca;
            background: linear-gradient(135deg, #ffffff 0%, #f2faf6 100%);
        }
        .ecoscan-action-eyebrow {
            color: #5d7368;
            font-size: 0.76rem;
            font-weight: 850;
            text-transform: uppercase;
            margin-bottom: 0.3rem;
        }
        .ecoscan-disposal-title {
            display: flex;
            align-items: center;
            gap: 0.55rem;
            color: #17211b;
            font-size: 1.05rem;
            font-weight: 800;
            margin-bottom: 0.25rem;
        }
        .ecoscan-public-action {
            border: 1px solid #c9dfd4;
            border-radius: 8px;
            background: linear-gradient(135deg, #ffffff 0%, #f2fbf6 100%);
            box-shadow: var(--eco-shadow);
            margin: 0.55rem 0 0.9rem;
            overflow: hidden;
        }
        .ecoscan-public-action.warn {
            border-color: #ead8a5;
            background: linear-gradient(135deg, #ffffff 0%, #fffaf0 100%);
        }
        .ecoscan-public-action.danger {
            border-color: #e4b4aa;
            background: linear-gradient(135deg, #ffffff 0%, #fff4f1 100%);
        }
        .ecoscan-public-action-head {
            align-items: center;
            border-bottom: 1px solid rgba(23, 52, 42, 0.08);
            display: flex;
            gap: 0.72rem;
            padding: 0.92rem 1rem;
        }
        .ecoscan-public-action-icon {
            align-items: center;
            border: 1px solid rgba(23, 52, 42, 0.14);
            border-radius: 999px;
            display: inline-flex;
            flex: 0 0 auto;
            height: 2.25rem;
            justify-content: center;
            width: 2.25rem;
        }
        .ecoscan-public-action-head strong {
            color: #10233f;
            display: block;
            font-size: 1rem;
            line-height: 1.18;
        }
        .ecoscan-public-action-head span {
            color: #5f7268;
            display: block;
            font-size: 0.82rem;
            line-height: 1.3;
            margin-top: 0.14rem;
        }
        .ecoscan-public-action-body {
            padding: 0.9rem 1rem 1rem;
        }
        .ecoscan-public-action-grid {
            display: grid;
            gap: 0.62rem;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            margin-bottom: 0.75rem;
        }
        .ecoscan-public-action-tile {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.78);
            min-height: 78px;
            padding: 0.65rem;
        }
        .ecoscan-public-action-tile span {
            color: #66796e;
            display: block;
            font-size: 0.72rem;
            font-weight: 850;
            text-transform: uppercase;
        }
        .ecoscan-public-action-tile strong {
            color: #17211b;
            display: block;
            font-size: 0.92rem;
            line-height: 1.24;
            margin-top: 0.18rem;
            overflow-wrap: anywhere;
        }
        .ecoscan-public-action-steps {
            color: #31483d;
            margin: 0.45rem 0 0;
            padding-left: 1.1rem;
        }
        .ecoscan-public-action-steps li {
            margin: 0.22rem 0;
        }
        .ecoscan-public-action-note {
            color: #536a60;
            font-size: 0.84rem;
            line-height: 1.36;
            margin: 0.65rem 0 0;
        }
        .ecoscan-destination-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.65rem;
            margin-top: 0.75rem;
        }
        .ecoscan-destination-tile {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #f8fbf9;
            padding: 0.72rem;
            min-height: 84px;
        }
        .ecoscan-destination-tile span {
            color: #64766c;
            display: block;
            font-size: 0.75rem;
            font-weight: 850;
            margin-bottom: 0.26rem;
            text-transform: uppercase;
        }
        .ecoscan-destination-tile strong {
            color: #18261e;
            display: block;
            font-size: 0.92rem;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .ecoscan-color-dot {
            width: 1rem;
            height: 1rem;
            border-radius: 999px;
            border: 1px solid rgba(18, 30, 24, 0.22);
            flex: 0 0 auto;
        }
        .ecoscan-step-list {
            margin: 0.55rem 0 0;
            padding-left: 1.15rem;
            color: #31483d;
        }
        .ecoscan-step-list li {
            margin: 0.25rem 0;
        }
        .ecoscan-map-box {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #f7faf7;
            padding: 0.85rem;
            margin-top: 0.75rem;
        }
        .ecoscan-point-list {
            display: grid;
            gap: 0.65rem;
            margin-top: 0.75rem;
        }
        .ecoscan-point-card {
            border: 1px solid #d5e6dc;
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f9fcfa 100%);
            padding: 0.82rem 0.9rem;
            box-shadow: 0 12px 26px rgba(25, 41, 32, 0.055);
        }
        .ecoscan-point-card strong {
            color: #17211b;
            display: block;
            font-size: 0.98rem;
            line-height: 1.25;
            margin-bottom: 0.18rem;
        }
        .ecoscan-point-card span {
            color: #5f7268;
            display: block;
            font-size: 0.84rem;
            line-height: 1.38;
        }
        .ecoscan-point-materials {
            color: #31483d !important;
            font-size: 0.82rem !important;
            font-weight: 700;
            margin-top: 0.38rem;
        }
        .ecoscan-point-actions {
            display: flex;
            gap: 0.45rem;
            margin-top: 0.58rem;
            flex-wrap: wrap;
        }
        .ecoscan-point-actions a {
            align-items: center;
            border: 1px solid #bfd2c8;
            border-radius: 8px;
            color: #165845 !important;
            display: inline-flex;
            font-size: 0.82rem;
            font-weight: 850;
            justify-content: center;
            min-height: 2rem;
            padding: 0 0.62rem;
            text-decoration: none !important;
        }
        .ecoscan-point-actions a.primary {
            background: #24745d;
            border-color: #24745d;
            color: #ffffff !important;
        }
        .ecoscan-impact-panel {
            border: 1px solid #d7e0d8;
            border-left: 4px solid #24745d;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.95rem 1rem;
            margin: 0.85rem 0 0;
            box-shadow: 0 8px 20px rgba(25, 41, 32, 0.055);
        }
        .ecoscan-impact-panel.alto {
            border-left-color: #b94a3a;
            background: #fff8f6;
        }
        .ecoscan-impact-panel.moderado {
            border-left-color: #d79f35;
            background: #fffaf0;
        }
        .ecoscan-impact-panel.baixo {
            border-left-color: #2f80ed;
            background: #f4f8ff;
        }
        .ecoscan-impact-head {
            display: flex;
            justify-content: space-between;
            gap: 0.65rem;
            align-items: flex-start;
            margin-bottom: 0.45rem;
        }
        .ecoscan-impact-head strong {
            color: #17211b;
            display: block;
            font-size: 1rem;
            line-height: 1.25;
        }
        .ecoscan-risk-tag {
            border: 1px solid rgba(35, 54, 45, 0.16);
            border-radius: 999px;
            color: #23362d;
            background: rgba(255, 255, 255, 0.72);
            flex: 0 0 auto;
            font-size: 0.75rem;
            font-weight: 850;
            padding: 0.22rem 0.5rem;
            white-space: nowrap;
        }
        .ecoscan-impact-panel ul {
            color: #34483e;
            margin: 0.35rem 0 0.55rem;
            padding-left: 1.05rem;
            font-size: 0.9rem;
        }
        .ecoscan-impact-panel li {
            margin: 0.22rem 0;
        }
        .ecoscan-positive-action {
            color: #1f4f40;
            font-weight: 750;
            margin: 0.55rem 0 0;
        }
        .ecoscan-source-link {
            color: #275f83 !important;
            font-size: 0.8rem;
            font-weight: 700;
            text-decoration: none !important;
        }
        .ecoscan-live-component a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 2.8rem;
            border: 1px solid #24745d;
            border-radius: 8px;
            color: #ffffff !important;
            background: #24745d;
            text-decoration: none !important;
            font-weight: 850;
        }
        .ecoscan-live-component small {
            color: #63766c;
            display: block;
            font-size: 0.78rem;
            margin-top: 0.35rem;
            text-align: center;
        }
        .ecoscan-soft-divider {
            border-top: 1px solid #dbe3dc;
            margin: 0.9rem 0;
        }
        .ecoscan-muted {
            color: #63766c;
            font-size: 0.9rem;
        }
        .ecoscan-camera-panel {
            border: 1px solid #bfe4d0;
            border-left: 5px solid #24745d;
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(239, 252, 246, 0.98) 100%);
            box-shadow: 0 16px 34px rgba(36, 116, 93, 0.10);
            padding: 0.95rem;
            margin-bottom: 0.8rem;
        }
        .ecoscan-live-link {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 2.6rem;
            border: 1px solid #24745d;
            border-radius: 8px;
            color: #ffffff !important;
            background: #24745d;
            text-decoration: none !important;
            font-weight: 800;
            padding: 0 0.95rem;
            margin-top: 0.55rem;
        }
        .ecoscan-confidence-panel {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.85rem;
            margin-top: 0.8rem;
        }
        .ecoscan-confidence-title {
            color: #1b2921;
            font-size: 0.92rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }
        .ecoscan-prob-row {
            display: grid;
            grid-template-columns: minmax(120px, 0.88fr) minmax(120px, 1.4fr) 52px;
            align-items: center;
            gap: 0.62rem;
            min-height: 30px;
        }
        .ecoscan-prob-label {
            color: #23362d;
            font-size: 0.86rem;
            font-weight: 700;
            overflow-wrap: anywhere;
        }
        .ecoscan-prob-track {
            height: 9px;
            border-radius: 999px;
            background: #edf2ef;
            overflow: hidden;
        }
        .ecoscan-prob-fill {
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #24745d 0%, #2f80ed 100%);
        }
        .ecoscan-prob-fill-warn {
            background: linear-gradient(90deg, #d79f35 0%, #2f80ed 100%);
        }
        .ecoscan-prob-value {
            color: #52685e;
            font-size: 0.82rem;
            font-weight: 800;
            text-align: right;
        }
        .ecoscan-quality-strip {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin-top: 0.65rem;
        }
        .ecoscan-mini-pill {
            border: 1px solid #d3ddd4;
            border-radius: 999px;
            background: #f8faf8;
            color: #263a30;
            display: inline-flex;
            gap: 0.35rem;
            padding: 0.25rem 0.55rem;
            font-size: 0.8rem;
            font-weight: 700;
        }
        .ecoscan-mini-pill small {
            color: #66796f;
            font-weight: 800;
        }
        .ecoscan-capture-advice {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #f8fbf9;
            padding: 0.82rem 0.9rem;
            margin-top: 0.75rem;
        }
        .ecoscan-capture-advice.attention {
            border-color: #ead6a2;
            background: #fffaf0;
        }
        .ecoscan-capture-advice.retake {
            border-color: #ecc5c0;
            background: #fff7f5;
        }
        .ecoscan-capture-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.6rem;
            color: #18261e;
            font-weight: 850;
            margin-bottom: 0.3rem;
        }
        .ecoscan-capture-score {
            color: #53685e;
            font-size: 0.82rem;
            font-weight: 850;
            white-space: nowrap;
        }
        .ecoscan-capture-advice p {
            margin: 0.2rem 0;
            color: #34483e;
            font-size: 0.92rem;
        }
        .ecoscan-capture-advice ul {
            margin: 0.45rem 0 0;
            padding-left: 1.1rem;
            color: #42584d;
            font-size: 0.9rem;
        }
        .ecoscan-tech-summary {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #ffffff;
            margin-top: 0.78rem;
            overflow: hidden;
        }
        .ecoscan-tech-summary-title {
            color: #16241d;
            font-size: 0.9rem;
            font-weight: 850;
            padding: 0.62rem 0.75rem;
            background: #f4f8f5;
            border-bottom: 1px solid #d7e0d8;
        }
        .ecoscan-tech-row {
            display: grid;
            grid-template-columns: minmax(92px, 0.34fr) minmax(0, 1fr);
            gap: 0.7rem;
            padding: 0.62rem 0.75rem;
            border-bottom: 1px solid #edf2ef;
        }
        .ecoscan-tech-row:last-child {
            border-bottom: 0;
        }
        .ecoscan-tech-label {
            color: #5c7065;
            font-size: 0.78rem;
            font-weight: 850;
            text-transform: uppercase;
        }
        .ecoscan-tech-value {
            color: #1f3328;
            font-size: 0.88rem;
            font-weight: 800;
            overflow-wrap: anywhere;
        }
        .ecoscan-tech-reason {
            color: #63766c;
            display: block;
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 0.18rem;
        }
        .ecoscan-evidence-panel {
            border: 1px solid #d5e6dc;
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f6fbf8 100%);
            box-shadow: 0 16px 32px rgba(18, 31, 25, 0.07);
            margin: 0.95rem 0;
            padding: 0.95rem;
        }
        .ecoscan-evidence-head {
            align-items: flex-start;
            display: flex;
            justify-content: space-between;
            gap: 0.75rem;
            margin-bottom: 0.75rem;
        }
        .ecoscan-evidence-head strong {
            color: #13251d;
            display: block;
            font-size: 1rem;
            font-weight: 860;
        }
        .ecoscan-evidence-head span {
            color: #61766b;
            display: block;
            font-size: 0.84rem;
            font-weight: 600;
            margin-top: 0.12rem;
        }
        .ecoscan-evidence-badge {
            border: 1px solid #b9d8ca;
            border-radius: 999px;
            background: #e9f8f0;
            color: #166146;
            flex: 0 0 auto;
            font-size: 0.76rem;
            font-weight: 860;
            padding: 0.32rem 0.58rem;
            white-space: nowrap;
        }
        .ecoscan-method-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.55rem;
            margin: 0.75rem 0 0.25rem;
        }
        .ecoscan-method-chip {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #fbfdfb;
            min-height: 72px;
            padding: 0.58rem;
        }
        .ecoscan-method-chip span {
            color: #64776c;
            display: block;
            font-size: 0.7rem;
            font-weight: 880;
            text-transform: uppercase;
        }
        .ecoscan-method-chip strong {
            color: #163126;
            display: block;
            font-size: 0.88rem;
            line-height: 1.2;
            margin-top: 0.18rem;
            overflow-wrap: anywhere;
        }
        .ecoscan-photo-plan {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.95rem;
            margin-top: 0.7rem;
        }
        .ecoscan-photo-plan h4 {
            color: #17211b;
            font-size: 1rem;
            margin: 0 0 0.4rem;
        }
        .ecoscan-photo-plan-meta {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 0.55rem;
            margin: 0.55rem 0;
        }
        .ecoscan-photo-plan-meta div {
            border: 1px solid #d7e0d8;
            border-radius: 8px;
            background: #f8fbf9;
            padding: 0.55rem;
        }
        .ecoscan-photo-plan-meta span {
            color: #64766c;
            display: block;
            font-size: 0.72rem;
            font-weight: 850;
            text-transform: uppercase;
        }
        .ecoscan-photo-plan-meta strong {
            color: #17211b;
            display: block;
            font-size: 1.05rem;
            margin-top: 0.1rem;
        }
        .ecoscan-photo-plan-list {
            color: #34483e;
            font-size: 0.88rem;
            margin: 0.3rem 0 0.65rem;
            padding-left: 1.08rem;
        }
        .ecoscan-photo-plan-list li {
            margin: 0.18rem 0;
        }
        .ecoscan-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 0.78rem;
            margin: 0.75rem 0 1rem;
        }
        .ecoscan-info-card,
        .ecoscan-mission-card,
        .ecoscan-reward-card {
            border: 1px solid #d5e6dc;
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f7fbf9 100%);
            padding: 0.9rem;
            box-shadow: 0 14px 30px rgba(25, 41, 32, 0.065);
            min-height: 132px;
            position: relative;
            overflow: hidden;
        }
        .ecoscan-info-card::before,
        .ecoscan-mission-card::before,
        .ecoscan-reward-card::before {
            content: "";
            background: linear-gradient(90deg, #24745d 0%, #2f80ed 55%, #f2bc28 100%);
            height: 4px;
            left: 0;
            position: absolute;
            right: 0;
            top: 0;
        }
        .ecoscan-info-card strong,
        .ecoscan-mission-card strong,
        .ecoscan-reward-card strong {
            color: #17211b;
            display: block;
            font-size: 0.98rem;
            line-height: 1.25;
            margin-bottom: 0.32rem;
        }
        .ecoscan-info-card span,
        .ecoscan-mission-card span,
        .ecoscan-reward-card span {
            color: #5f7268;
            display: block;
            font-size: 0.84rem;
            line-height: 1.38;
        }
        .ecoscan-card-meta {
            color: #155f49 !important;
            font-size: 0.82rem !important;
            font-weight: 850;
            margin-top: 0.55rem;
        }
        .ecoscan-admin-panel {
            border: 1px solid #cfdcd4;
            border-radius: 8px;
            background: #f8fbf9;
            padding: 0.95rem;
        }
        .ecoscan-admin-panel strong {
            color: #10233f;
            display: block;
            font-size: 0.98rem;
            line-height: 1.25;
            margin-bottom: 0.3rem;
        }
        .ecoscan-admin-panel p {
            margin: 0.2rem 0 0.45rem;
        }
        .ecoscan-admin-panel ul {
            color: #34483e;
            font-size: 0.9rem;
            margin: 0.45rem 0 0;
            padding-left: 1.1rem;
        }
        .ecoscan-admin-panel li {
            margin: 0.22rem 0;
        }
        .ecoscan-ops-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 0.8rem;
            margin: 0.75rem 0 1rem;
        }
        .ecoscan-priority-card {
            border: 1px solid #cfddd5;
            border-left: 4px solid #24745d;
            border-radius: 8px;
            background: #ffffff;
            box-shadow: var(--eco-shadow);
            min-height: 170px;
            padding: 0.92rem;
        }
        .ecoscan-priority-card.high {
            border-left-color: #b8452d;
        }
        .ecoscan-priority-card.medium {
            border-left-color: #d79f35;
        }
        .ecoscan-priority-card.low {
            border-left-color: #24745d;
        }
        .ecoscan-priority-card span {
            color: #607269;
            display: block;
            font-size: 0.74rem;
            font-weight: 850;
            text-transform: uppercase;
        }
        .ecoscan-priority-card strong {
            color: #10233f;
            display: block;
            font-size: 1.02rem;
            line-height: 1.24;
            margin-top: 0.18rem;
        }
        .ecoscan-priority-card p {
            color: #34483e;
            font-size: 0.86rem;
            line-height: 1.38;
            margin: 0.48rem 0 0;
        }
        .ecoscan-priority-card small {
            color: #6c7d73;
            display: block;
            font-size: 0.76rem;
            line-height: 1.32;
            margin-top: 0.48rem;
        }
        .ecoscan-territory-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.55rem 0 0;
        }
        .ecoscan-territory-chip {
            border: 1px solid #bfdccd;
            border-radius: 999px;
            background: #ffffff;
            color: #145742;
            display: inline-flex;
            font-size: 0.78rem;
            font-weight: 800;
            line-height: 1;
            padding: 0.42rem 0.64rem;
        }
        .ecoscan-profile-card {
            border: 1px solid #d7e0d8;
            border-left: 4px solid #24745d;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.82rem;
            margin: 0.45rem 0 0.75rem;
        }
        .ecoscan-profile-card strong {
            color: #17211b;
            display: block;
            font-size: 0.95rem;
            line-height: 1.25;
        }
        .ecoscan-profile-card span {
            color: #607269;
            display: block;
            font-size: 0.78rem;
            line-height: 1.35;
            margin-top: 0.18rem;
        }
        .ecoscan-admin-table-note {
            color: #607269;
            font-size: 0.84rem;
            margin: 0.3rem 0 0.8rem;
        }
        .ecoscan-completion-banner {
            border: 1px solid #bfe1d1;
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(239, 252, 246, 0.98) 100%);
            box-shadow: var(--eco-shadow);
            margin: 0.65rem 0 0.9rem;
            padding: 0.95rem 1rem;
        }
        .ecoscan-completion-banner strong {
            color: var(--eco-ink-strong);
            display: block;
            font-size: 1rem;
            line-height: 1.28;
            margin-bottom: 0.25rem;
        }
        .ecoscan-completion-banner span {
            color: #4f665b;
            display: block;
            font-size: 0.9rem;
            line-height: 1.42;
        }
        .ecoscan-completion-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
            gap: 0.72rem;
            margin: 0.8rem 0 1rem;
        }
        .ecoscan-completion-card {
            border: 1px solid #d5e6dc;
            border-top: 4px solid var(--eco-primary);
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f7fbf9 100%);
            box-shadow: 0 14px 30px rgba(25, 41, 32, 0.065);
            min-height: 188px;
            padding: 0.85rem;
        }
        .ecoscan-completion-card.attention {
            border-top-color: var(--eco-accent);
        }
        .ecoscan-completion-card.pending {
            border-top-color: #8ba2ad;
        }
        .ecoscan-completion-card.failed {
            border-top-color: var(--eco-danger);
        }
        .ecoscan-completion-card span {
            color: var(--eco-muted);
            display: block;
            font-size: 0.74rem;
            font-weight: 850;
            letter-spacing: 0;
            margin-bottom: 0.28rem;
            text-transform: uppercase;
        }
        .ecoscan-completion-card strong {
            color: var(--eco-ink-strong);
            display: block;
            font-size: 0.98rem;
            line-height: 1.25;
            margin-bottom: 0.4rem;
        }
        .ecoscan-completion-card p {
            color: #4f665b;
            font-size: 0.86rem;
            line-height: 1.38;
            margin: 0.25rem 0;
        }
        .ecoscan-completion-card small {
            color: #155f49;
            display: block;
            font-size: 0.78rem;
            font-weight: 780;
            line-height: 1.35;
            margin-top: 0.48rem;
        }
        .ecoscan-report-status {
            border: 1px solid #d7e0d8;
            border-left: 4px solid #24745d;
            border-radius: 8px;
            background: #ffffff;
            padding: 0.9rem;
            margin-top: 0.8rem;
        }
        .ecoscan-report-status.inconclusivo,
        .ecoscan-report-status.insuficiente {
            border-left-color: #d79f35;
            background: #fffaf0;
        }
        .ecoscan-report-status strong {
            color: #17211b;
            display: block;
            margin-bottom: 0.25rem;
        }
        @media (max-width: 980px) {
            .ecoscan-hero-body {
                grid-template-columns: 1fr;
            }
            .ecoscan-user-flow {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .ecoscan-status-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
        }
        @media (max-width: 760px) {
            [data-testid="stAppViewContainer"] .main .block-container {
                padding-left: 0.68rem;
                padding-right: 0.68rem;
                padding-top: 0.55rem;
                padding-bottom: 5rem;
            }
            div[data-testid="stTabs"] div[data-baseweb="tab-list"] {
                border-radius: 8px;
                bottom: 0.55rem;
                left: 0.68rem;
                margin: 0;
                position: sticky;
                z-index: 40;
                box-shadow: 0 18px 38px rgba(7, 29, 65, 0.16);
                top: auto;
            }
            div[data-testid="stTabs"] button {
                min-height: 2.9rem;
                min-width: 6.2rem;
                padding: 0.2rem 0.75rem;
            }
            .ecoscan-gov-ribbon {
                display: none;
            }
            .ecoscan-appbar {
                align-items: flex-start;
                flex-direction: column;
                gap: 0.55rem;
                padding: 0.72rem 0.82rem 0.1rem;
            }
            .ecoscan-brand strong {
                font-size: 0.96rem;
            }
            .ecoscan-brand span {
                font-size: 0.73rem;
            }
            .ecoscan-logo-mark {
                height: 2.1rem;
                width: 2.1rem;
            }
            .ecoscan-hero-body,
            .ecoscan-user-flow {
                grid-template-columns: 1fr;
            }
            .ecoscan-hero-body {
                gap: 0.74rem;
                padding: 0.58rem 0.82rem 0.92rem;
            }
            .ecoscan-hero-panel {
                margin-top: 0.2rem;
            }
            .ecoscan-recycle-visual {
                grid-template-columns: 1fr 1fr;
            }
            .ecoscan-recycle-center {
                grid-column: 1 / -1;
                min-height: 108px;
            }
            .ecoscan-recycle-tile {
                min-height: 78px;
            }
            .ecoscan-recycle-tile img {
                height: 52px;
                width: 52px;
            }
            .ecoscan-user-flow div {
                border-right: 0;
                border-bottom: 0;
                min-height: 76px;
            }
            .ecoscan-user-flow div:last-child {
                border-bottom: 0;
            }
            .ecoscan-hero {
                padding: 0;
            }
            .ecoscan-title {
                font-size: 1.78rem;
                line-height: 1.05;
            }
            .ecoscan-subtitle {
                font-size: 0.9rem;
                line-height: 1.35;
            }
            .ecoscan-service-chip-row {
                gap: 0.38rem;
                margin-top: 0.6rem;
            }
            .ecoscan-service-chip {
                font-size: 0.76rem;
                min-height: 1.78rem;
                padding: 0 0.56rem;
            }
            .ecoscan-status-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .ecoscan-status-item {
                min-height: 78px;
                padding: 0.65rem;
            }
            .ecoscan-prob-row {
                grid-template-columns: minmax(92px, 0.92fr) minmax(86px, 1.1fr) 48px;
                gap: 0.45rem;
            }
            .ecoscan-chip-row {
                max-height: 5.2rem;
                overflow: auto;
                padding-bottom: 0.15rem;
            }
            .ecoscan-destination-grid {
                grid-template-columns: 1fr;
            }
            .ecoscan-impact-head {
                display: block;
            }
            .ecoscan-risk-tag {
                display: inline-flex;
                margin-top: 0.38rem;
            }
            .ecoscan-photo-plan-meta {
                grid-template-columns: 1fr;
            }
            .ecoscan-point-actions a {
                width: 100%;
            }
            .ecoscan-card-grid {
                grid-template-columns: 1fr;
            }
            [data-testid="stButton"] button {
                width: 100%;
            }
        }
        @media (max-width: 430px) {
            .ecoscan-status-strip {
                grid-template-columns: 1fr;
            }
            .ecoscan-prob-row {
                grid-template-columns: minmax(82px, 0.95fr) minmax(74px, 1fr) 44px;
            }
            .ecoscan-title {
                font-size: 1.58rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_public_app_chrome(st: Any) -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                linear-gradient(145deg, rgba(73, 164, 100, 0.10) 0 18%, transparent 18% 100%),
                repeating-linear-gradient(135deg, rgba(14, 122, 87, 0.055) 0 1px, transparent 1px 22px),
                linear-gradient(180deg, #f7fcf8 0%, #edf8f1 50%, #f6fafb 100%) !important;
        }
        [data-testid="stSidebar"],
        [data-testid="collapsedControl"],
        [data-testid="stSidebarCollapsedControl"] {
            display: none !important;
            visibility: hidden !important;
        }
        [data-testid="stAppViewContainer"] .main .block-container {
            max-width: 1040px;
            padding-bottom: 5.5rem;
        }
        [data-testid="stTabs"] div[data-baseweb="tab-list"] {
            background: rgba(255, 255, 255, 0.97);
            border-color: var(--eco-line);
        }
        [data-testid="stTabs"] button {
            min-width: 5.8rem;
        }
        .ecoscan-hero,
        .ecoscan-camera-panel,
        .ecoscan-result,
        .ecoscan-disposal-panel,
        .ecoscan-point-card,
        .ecoscan-info-card,
        .ecoscan-mission-card,
        .ecoscan-reward-card {
            box-shadow: 0 18px 42px rgba(3, 16, 36, 0.16);
        }
        @media (min-width: 860px) {
            [data-testid="stAppViewContainer"] .main .block-container {
                background:
                    linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(246, 251, 248, 0.96) 100%);
                border: 1px solid rgba(220, 234, 228, 0.95);
                border-radius: 8px;
                box-shadow: 0 28px 80px rgba(7, 29, 65, 0.14);
                margin-bottom: 1.2rem;
                margin-top: 1rem;
                padding: 0.9rem 0.95rem 5.5rem;
            }
        }
        @media (max-width: 760px) {
            [data-testid="stAppViewContainer"] .main .block-container {
                max-width: 100%;
                padding-left: 0.64rem;
                padding-right: 0.64rem;
                padding-top: 0.52rem;
            }
            .ecoscan-user-flow {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .ecoscan-evidence-head {
                display: block;
            }
            .ecoscan-evidence-badge {
                display: inline-flex;
                margin-top: 0.45rem;
            }
            .ecoscan-method-strip {
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }
            .ecoscan-hero,
            .ecoscan-status-item,
            .ecoscan-camera-panel,
            .ecoscan-result,
            .ecoscan-disposal-panel,
            .ecoscan-point-card,
            .ecoscan-info-card,
            .ecoscan-mission-card,
            .ecoscan-reward-card {
                box-shadow: 0 12px 30px rgba(14, 84, 61, 0.12);
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _badge(label: str, tone: str = "ok") -> str:
    return f'<span class="ecoscan-badge ecoscan-badge-{tone}">{html.escape(label)}</span>'


def _load_guidance_map(config: Any) -> dict[str, DisposalGuidance]:
    try:
        return load_guidance(config.project_root / "config" / "disposal_guidance.json")
    except Exception as exc:
        LOGGER.warning("guidance_map_load_failed detail=%s", exc)
        return {}


def _load_disposal_target_map(config: Any) -> dict[str, DisposalTarget]:
    try:
        return load_disposal_targets(config.project_root / "config" / "disposal_targets.json")
    except Exception as exc:
        LOGGER.warning("disposal_target_map_load_failed detail=%s", exc)
        return {}


def _load_environmental_impact_map(config: Any) -> dict[str, EnvironmentalImpact]:
    try:
        return load_environmental_impacts(config.project_root / "config" / "environmental_impacts.json")
    except Exception as exc:
        LOGGER.warning("environmental_impact_map_load_failed detail=%s", exc)
        return {}


def _load_photo_requirement_map(config: Any) -> dict[str, PhotoRequirement]:
    try:
        return load_photo_requirements(config.project_root / "config" / "photo_requirements.json")
    except Exception as exc:
        LOGGER.warning("photo_requirement_map_load_failed detail=%s", exc)
        return {}


def _load_collection_point_list(config: Any) -> list[CollectionPoint]:
    try:
        return load_collection_points(config.project_root / "config" / "collection_points.json")
    except Exception as exc:
        LOGGER.warning("collection_points_load_failed detail=%s", exc)
        return []


def _load_user_profile_list(config: Any) -> tuple[UserProfile, ...]:
    try:
        return load_user_profiles(profiles_path_from_config(config))
    except Exception as exc:
        LOGGER.warning("user_profiles_load_failed detail=%s", exc)
        return fallback_profiles()


def _load_campaign_config(config: Any) -> Campaign | None:
    try:
        return load_campaign(campaign_path_from_config(config))
    except Exception as exc:
        LOGGER.warning("campaign_load_failed detail=%s", exc)
        return None


def _target_for_guidance(
    guidance: DisposalGuidance | None,
    targets_by_class: dict[str, DisposalTarget],
) -> DisposalTarget | None:
    if guidance is None:
        return None
    try:
        return get_disposal_target(guidance.class_id, targets_by_class)
    except Exception as exc:
        LOGGER.warning("disposal_target_missing class_id=%s detail=%s", guidance.class_id, exc)
        return None


def _impact_for_guidance(
    guidance: DisposalGuidance | None,
    impacts_by_class: dict[str, EnvironmentalImpact],
) -> EnvironmentalImpact | None:
    if guidance is None:
        return None
    try:
        return get_environmental_impact(guidance.class_id, impacts_by_class)
    except Exception as exc:
        LOGGER.warning("environmental_impact_missing class_id=%s detail=%s", guidance.class_id, exc)
        return None


def _render_user_error(st: Any, exc: BaseException, *, context: str) -> None:
    error = describe_exception(exc)
    log_message = (
        "ui_handled_error context=%s code=%s category=%s detail=%s"
        % (context, error.code, error.category, error.technical_detail)
    )
    if error.code == "APP-001":
        LOGGER.exception(log_message)
    else:
        LOGGER.warning(log_message)

    st.error(f"{error.code} - {error.title}: {error.message}")
    st.info(f"Ação recomendada: {error.action}")
    if error.technical_detail:
        with st.expander("Detalhe técnico"):
            st.code(error.technical_detail)


def _class_label(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> str:
    guidance = guidance_by_class.get(class_id)
    if not guidance:
        return class_id
    return f"{guidance.display_name} ({class_id})"


def _class_chip(class_id: str, guidance_by_class: dict[str, DisposalGuidance]) -> str:
    guidance = guidance_by_class.get(class_id)
    label = guidance.display_name if guidance else class_id
    category = guidance.environmental_category if guidance else "classe ativa"
    return (
        '<span class="ecoscan-chip">'
        f"{html.escape(label)} <small>{html.escape(category)}</small>"
        "</span>"
    )


def _status_item(label: str, value: str, detail: str, tone: str = "ok") -> str:
    tone = tone if tone in {"ok", "warn", "danger"} else "ok"
    return (
        f'<div class="ecoscan-status-item ecoscan-status-{tone}">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        f"<small>{html.escape(detail)}</small>"
        "</div>"
    )


def _service_chip(label: str) -> str:
    return f'<span class="ecoscan-service-chip">{html.escape(label)}</span>'


def _asset_data_uri(project_root: Path, relative_path: str) -> str:
    path = project_root / relative_path
    try:
        suffix = path.suffix.lower()
        mime = "image/png" if suffix == ".png" else "image/jpeg"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
    except OSError:
        return ""
    return f"data:{mime};base64,{payload}"


def _hero_recycle_visual(project_root: Path, active_profile: UserProfile) -> str:
    if active_profile.is_admin:
        items = [
            ("assets/disposal_targets/electronic_orange_dropoff.png", "Eletrônicos", "logística reversa"),
            ("assets/disposal_targets/glass_green_bin.png", "Vidro", "coleta seletiva"),
            ("assets/disposal_targets/lamp_orange_dropoff.png", "Lâmpadas", "coleta especial"),
        ]
        center_title = "Gestão"
        center_subtitle = "dados para melhorar a coleta"
    else:
        items = [
            ("assets/disposal_targets/plastic_red_bin.png", "Plástico", "lixeira vermelha"),
            ("assets/disposal_targets/paper_blue_bin.png", "Papel", "lixeira azul"),
            ("assets/disposal_targets/battery_orange_dropoff.png", "Pilhas", "ponto especial"),
        ]
        center_title = "Reciclar"
        center_subtitle = "começa pela foto"

    tiles = [
        """
        <div class="ecoscan-recycle-center">
            <div class="ecoscan-recycle-symbol">&#9851;</div>
            <strong>{title}</strong>
            <small>{subtitle}</small>
        </div>
        """.format(title=html.escape(center_title), subtitle=html.escape(center_subtitle))
    ]
    for relative_path, label, detail in items:
        source = _asset_data_uri(project_root, relative_path)
        image_html = f'<img src="{source}" alt="">' if source else ""
        tiles.append(
            '<div class="ecoscan-recycle-tile">'
            f"{image_html}"
            "<div>"
            f"<span>{html.escape(label)}</span>"
            f"<small>{html.escape(detail)}</small>"
            "</div>"
            "</div>"
        )
    return '<div class="ecoscan-recycle-visual">' + "".join(tiles) + "</div>"


def _render_institutional_hero(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    campaign: Campaign | None,
) -> None:
    if active_profile.is_admin:
        hero_role = "admin"
        mode = "Portal de gestão"
        title = "Gestão Ambiental Municipal"
        subtitle = (
            "Painel institucional para acompanhar campanhas, participação cidadã, denúncias "
            "e evidências técnicas do EcoScan."
        )
        panel_rows = [
            ("Unidade", "Secretaria do Meio Ambiente"),
            ("Serviço", "Campanhas e missões"),
            ("Controle", "Denúncias e revisão"),
            ("Evidência", "Visão computacional"),
        ]
        chips = ["Gestão ambiental", "Participação cidadã", "Triagem", "Relatórios"]
    else:
        hero_role = "user"
        mode = "Modo cidadão"
        title = "Escaneie. Recicle. Pontue."
        subtitle = (
            "Aponte a câmera para o resíduo e receba, em poucos segundos, onde descartar, como preparar "
            "e qual ponto de coleta procurar."
        )
        panel_rows = [
            ("Foto", "do resíduo"),
            ("Resposta", "destino correto"),
            ("Coleta", "pontos próximos"),
            ("Impacto", "educação ambiental"),
        ]
        chips = ["Escanear", "Reciclar", "Encontrar coleta", "Ganhar pontos"]

    campaign_label = campaign.title if campaign else "Campanha ambiental"
    panel_rows.append(("Campanha", campaign_label))
    rows_html = "".join(
        '<div class="ecoscan-hero-panel-row">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        "</div>"
        for label, value in panel_rows
    )
    chips_html = "".join(_service_chip(item) for item in chips)
    recycle_visual = _hero_recycle_visual(config.project_root, active_profile)
    st.markdown(
        f"""
        <section class="ecoscan-hero ecoscan-hero-{hero_role}">
            <div class="ecoscan-gov-ribbon">
                <strong>Portal Municipal de Serviços Ambientais</strong>
                <span>Atendimento digital integrado</span>
            </div>
            <div class="ecoscan-appbar">
                <div class="ecoscan-brand">
                    <div class="ecoscan-logo-mark">SMA</div>
                    <div>
                        <strong>Secretaria do Meio Ambiente</strong>
                        <span>EcoScan · orientação, coleta e educação ambiental</span>
                    </div>
                </div>
                <div class="ecoscan-mode-pill">{html.escape(mode)}</div>
            </div>
            <div class="ecoscan-hero-body">
                <div class="ecoscan-hero-copy">
                    <div class="ecoscan-kicker">Reciclagem guiada por câmera</div>
                    <h1 class="ecoscan-title">{html.escape(title)}</h1>
                    <div class="ecoscan-subtitle">{html.escape(subtitle)}</div>
                    <div class="ecoscan-service-chip-row">{chips_html}</div>
                </div>
                <div class="ecoscan-hero-side">
                    {recycle_visual}
                    <div class="ecoscan-hero-panel">{rows_html}</div>
                </div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_user_flow_strip(st: Any) -> None:
    st.markdown(
        """
        <div class="ecoscan-user-flow">
            <div data-step="1"><span>Primeiro passo</span><strong>Abra a câmera e enquadre o resíduo</strong></div>
            <div data-step="2"><span>Resposta</span><strong>Veja lixeira, preparo e risco ambiental</strong></div>
            <div data-step="3"><span>Destino</span><strong>Procure ponto de coleta próximo</strong></div>
            <div data-step="4"><span>Participação</span><strong>Registre missão ou denúncia quando fizer sentido</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_public_overview_strip(st: Any) -> None:
    strip = "".join(
        [
            _status_item("Foto", "do resíduo", "captura ou galeria", "ok"),
            _status_item("Resposta", "descarte certo", "lixeira, preparo e impacto", "ok"),
            _status_item("Mapa", "coleta próxima", "busca rápida por material", "ok"),
            _status_item("Participação", "missões e pontos", "campanha ambiental ativa", "ok"),
        ]
    )
    st.markdown(f'<section class="ecoscan-status-strip">{strip}</section>', unsafe_allow_html=True)


def _public_code(code: str) -> str:
    return code.replace("APS-", "ECO-")


def _public_ui_text(value: str) -> str:
    replacements = {
        "APS": "EcoScan",
        "A baseline": "O modelo inicial",
        "a baseline": "o modelo inicial",
        "Baseline": "Modelo inicial",
        "baseline": "modelo inicial",
        "no dataset bruto": "na base bruta de imagens",
        "No dataset bruto": "Na base bruta de imagens",
        "o dataset curado": "a base curada de imagens",
        "O dataset curado": "A base curada de imagens",
        "o dataset bruto": "a base bruta de imagens",
        "O dataset bruto": "A base bruta de imagens",
        "do dataset": "da base de imagens",
        "Do dataset": "Da base de imagens",
        "no dataset": "na base de imagens",
        "No dataset": "Na base de imagens",
        "Dataset bruto": "Base bruta de imagens",
        "dataset bruto": "base bruta de imagens",
        "Dataset curado": "Base curada de imagens",
        "dataset curado": "base curada de imagens",
        "Dataset": "Base de imagens",
        "dataset": "base de imagens",
        "acadêmica": "técnica",
        "acadêmico": "técnico",
        "acadêmicas": "técnicas",
        "acadêmicos": "técnicos",
        "Professor": "Usuário",
        "professor": "usuário",
        "Score": "Confiança",
        "score": "confiança",
    }
    text = value
    for old, new in replacements.items():
        text = text.replace(old, new)
    fixups = {
        "Modelo inicial avaliada": "Modelo inicial avaliado",
        "modelo inicial avaliada": "modelo inicial avaliado",
        "Tratar a modelo inicial": "Tratar o modelo inicial",
        "a modelo inicial": "o modelo inicial",
        "o base curada de imagens": "a base curada de imagens",
        "o base bruta de imagens": "a base bruta de imagens",
        "a base curada de imagens ainda está vazio": "a base curada de imagens ainda está vazia",
        "a base bruta de imagens ainda está vazio": "a base bruta de imagens ainda está vazia",
        "no base bruta de imagens": "na base bruta de imagens",
        "salvo no base bruta de imagens": "salvo na base bruta de imagens",
        "supero modelo inicial": "supera o modelo inicial",
        "histórico e status": "histórico e sistema",
    }
    for old, new in fixups.items():
        text = text.replace(old, new)
    return text


def _render_overview_strip(st: Any, config: Any) -> None:
    selected_model = model_status(config)
    dataset = dataset_status(config)
    audit_summary = summarize_audit(build_aps_audit(config))
    readiness = build_dataset_readiness(config, target_per_class=50)[0]

    raw_total = sum(dataset.raw_counts.values())
    curated_total = sum(dataset.curated_counts.values())
    model_tone = "ok" if selected_model.selected_kind in {"transfer_learning", "visual_svm", "visual_knn"} else "warn"
    model_labels = {
        "transfer_learning": "modelo final",
        "visual_svm": "modelo visual supervisionado",
        "visual_knn": "modelo visual",
        "baseline": "modelo inicial",
    }
    model_label = model_labels.get(selected_model.selected_kind, "sem modelo")
    dataset_tone = "ok" if readiness.ready_for_final_training else "warn"
    strip = "".join(
        [
            _status_item(
                "Modelo ativo",
                model_label,
                "transfer learning carregado" if selected_model.selected_kind == "transfer_learning" else "classificador visual supervisionado carregado" if selected_model.selected_kind == "visual_svm" else "classificador visual carregado" if selected_model.selected_kind == "visual_knn" else "modelo final quando disponível",
                model_tone,
            ),
            _status_item(
                "Prontidão técnica",
                f"{audit_summary['readiness_score']}%",
                "qualidade do sistema",
                "ok" if float(audit_summary["readiness_score"]) >= 70 else "warn",
            ),
            _status_item(
                "Base de imagens",
                f"{raw_total} brutas / {curated_total} curadas",
                f"faltam {readiness.missing_raw_total} fotos brutas",
                dataset_tone,
            ),
            _status_item(
                "Validação",
                "executável",
                "validação automatizada disponível",
                "ok",
            ),
        ]
    )
    st.markdown(f'<section class="ecoscan-status-strip">{strip}</section>', unsafe_allow_html=True)


def _confidence_tone(class_id: str, predicted_class: str | None, accepted: bool) -> str:
    if accepted and class_id == predicted_class:
        return "ok"
    return "warn"


def _probability_bar(
    class_id: str,
    probability: float,
    *,
    guidance_by_class: dict[str, DisposalGuidance],
    predicted_class: str | None,
    accepted: bool,
) -> str:
    guidance = guidance_by_class.get(class_id)
    label = guidance.display_name if guidance else class_id
    width = max(0.0, min(100.0, probability * 100.0))
    tone = _confidence_tone(class_id, predicted_class, accepted)
    fill_class = "ecoscan-prob-fill" if tone == "ok" else "ecoscan-prob-fill ecoscan-prob-fill-warn"
    return (
        '<div class="ecoscan-prob-row">'
        f'<div class="ecoscan-prob-label">{html.escape(label)}</div>'
        '<div class="ecoscan-prob-track">'
        f'<div class="{fill_class}" style="width: {width:.1f}%"></div>'
        "</div>"
        f'<div class="ecoscan-prob-value">{width:.0f}%</div>'
        "</div>"
    )


def _render_probability_bars(st: Any, result: Any, guidance_by_class: dict[str, DisposalGuidance]) -> None:
    probabilities = sorted(
        result.probabilities.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:5]
    if not probabilities:
        return
    rows = "".join(
        _probability_bar(
            class_id,
            float(probability),
            guidance_by_class=guidance_by_class,
            predicted_class=result.predicted_class,
            accepted=result.accepted,
        )
        for class_id, probability in probabilities
    )
    st.markdown(
        '<section class="ecoscan-confidence-panel">'
        '<div class="ecoscan-confidence-title">Leitura de confiança por classe</div>'
        f"{rows}"
        "</section>",
        unsafe_allow_html=True,
    )


def _render_browser_location_search(st: Any, target: DisposalTarget) -> None:
    import streamlit.components.v1 as components

    component_id = f"ecoscan_geo_{target.class_id}"
    query_json = json.dumps(target.search_query, ensure_ascii=False)
    components.html(
        f"""
        <div style="font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif;">
          <button id="{component_id}_button" style="
            width:100%; min-height:42px; border:1px solid #24745d; border-radius:8px;
            background:#24745d; color:#fff; font-weight:800; cursor:pointer;">
            Usar minha localização atual
          </button>
          <div id="{component_id}_status" style="margin-top:8px; color:#5f7268; font-size:13px;"></div>
        </div>
        <script>
        (() => {{
          const button = document.getElementById("{component_id}_button");
          const status = document.getElementById("{component_id}_status");
          const query = {query_json};
          button.addEventListener("click", () => {{
            if (!navigator.geolocation) {{
              status.textContent = "Este navegador não oferece geolocalização. Digite cidade, bairro ou CEP no campo acima.";
              return;
            }}
            status.textContent = "Solicitando permissão de localização...";
            navigator.geolocation.getCurrentPosition(
              (position) => {{
                const lat = position.coords.latitude.toFixed(6);
                const lon = position.coords.longitude.toFixed(6);
                const mapsQuery = encodeURIComponent(`${{query}} perto de ${{lat}},${{lon}}`);
                window.open(`https://www.google.com/maps/search/?api=1&query=${{mapsQuery}}`, "_blank", "noopener,noreferrer");
                status.textContent = "Busca aberta no mapa.";
              }},
              () => {{
                status.textContent = "Não foi possível obter a localização. Digite cidade, bairro ou CEP no campo acima.";
              }},
              {{ enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }}
            );
          }});
        }})();
        </script>
        """,
        height=84,
    )


def _render_live_camera_link(st: Any) -> None:
    import streamlit.components.v1 as components

    configured_live_url = os.environ.get("ECOSCAN_LIVE_URL", "").strip()
    html_code = (
        """
        <div style="
          font-family: Inter, system-ui, -apple-system, Segoe UI, sans-serif;
          border:1px solid #c7ead8; border-radius:8px; padding:10px;
          background:linear-gradient(180deg,#ffffff 0%,#f1fbf6 100%);
          box-shadow:0 16px 32px rgba(36,116,93,.12);">
          <a id="ecoscan_live_url" href="http://localhost:8765/" target="_blank" rel="noopener noreferrer" style="
            display:flex; align-items:center; justify-content:center; width:100%;
            min-height:58px; border:1px solid #1b8f5a; border-radius:8px;
            background:linear-gradient(135deg,#24745d 0%,#1b8f5a 52%,#2f80ed 100%);
            color:#fff; text-decoration:none; font-weight:820; letter-spacing:0;
            box-shadow:0 14px 28px rgba(36,116,93,.24);">
            <span style="
              display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px;
              border-radius:999px; background:rgba(255,255,255,.20); margin-right:10px;">&#128247;</span>
            <span style="display:flex; flex-direction:column; line-height:1.1;">
              <strong style="font-size:15px;">Escanear com câmera traseira</strong>
              <small style="font-size:11px; font-weight:750; color:rgba(255,255,255,.82); margin-top:3px;">ao vivo, com rastreamento do resíduo</small>
            </span>
          </a>
          <small id="ecoscan_live_hint" style="
            color:#4f6d5e; display:block; font-size:12.2px; margin-top:8px; text-align:center; font-weight:700;">
            Recomendado no celular: prioriza a câmera de trás e rastreia o resíduo em tempo real.
          </small>
        </div>
        <script>
        (() => {
          const link = document.getElementById("ecoscan_live_url");
          const hint = document.getElementById("ecoscan_live_hint");
          const configuredLiveUrl = __ECOSCAN_LIVE_URL__;
          let hostname = "localhost";
          let protocol = "http:";
          try {
            hostname = window.parent?.location?.hostname || window.location.hostname || hostname;
            protocol = window.parent?.location?.protocol || window.location.protocol || protocol;
          } catch (error) {
            hostname = window.location.hostname || hostname;
            protocol = window.location.protocol || protocol;
          }
          const liveProtocol = protocol === "https:" ? "https:" : "http:";
          const liveUrl = configuredLiveUrl || `${liveProtocol}//${hostname}:8765/`;
          const secureHost = ["localhost", "127.0.0.1"].includes(hostname);
          const externalHttpsWithoutLive = protocol === "https:" && !secureHost && !configuredLiveUrl;
          if (externalHttpsWithoutLive) {
            link.href = "#";
            link.addEventListener("click", (event) => event.preventDefault());
            hint.textContent = "No app hospedado grátis, use a câmera/foto abaixo. O modo ao vivo exige backend HTTPS dedicado.";
            return;
          }
          link.href = liveUrl;
          if (configuredLiveUrl) {
            hint.textContent = `Câmera traseira ao vivo: ${liveUrl}`;
            return;
          }
          if (protocol !== "https:" && !secureHost) {
            hint.textContent = `Ao vivo no celular exige HTTPS. Em rede local, use a foto rápida abaixo ou um túnel HTTPS seguro.`;
          } else {
            hint.textContent = `Câmera traseira ao vivo: ${liveUrl}`;
          }
        })();
        </script>
        """
    ).replace("__ECOSCAN_LIVE_URL__", json.dumps(configured_live_url))
    components.html(
        html_code,
        height=104,
    )


def _render_environmental_impact(st: Any, impact: EnvironmentalImpact | None) -> None:
    if impact is None:
        return

    risk_level = impact.risk_level.lower().strip()
    if risk_level not in {"baixo", "moderado", "alto"}:
        risk_level = "moderado"
    risks = "".join(f"<li>{html.escape(risk)}</li>" for risk in impact.bad_disposal_risks[:3])
    st.markdown(
        f"""
        <div class="ecoscan-impact-panel {html.escape(risk_level)}">
            <div class="ecoscan-impact-head">
                <strong>{html.escape(impact.impact_title)}</strong>
                <span class="ecoscan-risk-tag">{html.escape(impact.risk_label)}</span>
            </div>
            <ul>{risks}</ul>
            <p class="ecoscan-positive-action">{html.escape(impact.positive_action)}</p>
            <a class="ecoscan-source-link" href="{html.escape(impact.source_url)}" target="_blank" rel="noopener noreferrer">
                Fonte de referência: {html.escape(impact.source_label)}
            </a>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _format_point_materials(point: CollectionPoint, *, limit: int = 5) -> str:
    materials = list(point.accepted_materials[:limit])
    suffix = "" if len(point.accepted_materials) <= limit else "..."
    return ", ".join(materials) + suffix


def _render_collection_point_cards(
    st: Any,
    points: list[CollectionPoint],
    *,
    origin: str | None = None,
    limit: int = 3,
) -> None:
    if not points:
        st.info("Nenhum ponto cadastrado para esse material na base local. Use a busca no mapa ou cadastre pontos oficiais em config/collection_points.json.")
        return

    ranked = rank_collection_points(points, limit=limit)
    cards: list[str] = []
    for item in ranked:
        point = item.point
        distance = f"{item.distance_km:.2f} km" if item.distance_km is not None else "distância via Maps"
        map_url = build_collection_point_map_url(point)
        directions_url = build_collection_point_directions_url(point, origin=origin)
        materials = _format_point_materials(point)
        cards.append(
            '<div class="ecoscan-point-card">'
            f"<strong>{html.escape(point.name)}</strong>"
            f"<span>{html.escape(point.full_address)}</span>"
            f"<span>{html.escape(point.hours)} · {html.escape(distance)}</span>"
            f'<span class="ecoscan-point-materials">{html.escape(materials)}</span>'
            '<div class="ecoscan-point-actions">'
            f'<a class="primary" href="{html.escape(directions_url)}" target="_blank" rel="noopener noreferrer">Traçar rota</a>'
            f'<a href="{html.escape(map_url)}" target="_blank" rel="noopener noreferrer">Ver no mapa</a>'
            "</div>"
            "</div>"
        )
    st.markdown(
        '<div class="ecoscan-point-list">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )


def _render_photo_requirement_plan(st: Any, requirement: PhotoRequirement | None) -> None:
    if requirement is None:
        st.info("Plano de fotos ainda não configurado para esta classe.")
        return

    examples = "".join(f"<li>{html.escape(item)}</li>" for item in requirement.examples[:7])
    contexts = "".join(f"<li>{html.escape(item)}</li>" for item in requirement.contexts[:5])
    avoid = "".join(f"<li>{html.escape(item)}</li>" for item in requirement.avoid[:5])
    st.markdown(
        f"""
        <div class="ecoscan-photo-plan">
            <h4>{html.escape(requirement.title)}</h4>
            <div class="ecoscan-photo-plan-meta">
                <div>
                    <span>Mínimo por classe</span>
                    <strong>{requirement.minimum_images}</strong>
                </div>
                <div>
                    <span>Ideal para treino</span>
                    <strong>{requirement.ideal_images}</strong>
                </div>
            </div>
            <strong>Fotos para procurar</strong>
            <ul class="ecoscan-photo-plan-list">{examples}</ul>
            <strong>Variações importantes</strong>
            <ul class="ecoscan-photo-plan-list">{contexts}</ul>
            <strong>Evitar no lote</strong>
            <ul class="ecoscan-photo-plan-list">{avoid}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_disposal_action_panel(
    st: Any,
    config: Any,
    guidance: DisposalGuidance,
    target: DisposalTarget | None,
    impact: EnvironmentalImpact | None,
    collection_points: list[CollectionPoint],
) -> None:
    if target is None:
        st.info("Orientação visual de descarte ainda não configurada para esta classe.")
        return

    st.markdown('<div class="ecoscan-section-title">Próximo passo de descarte</div>', unsafe_allow_html=True)
    visual_col, action_col = st.columns([0.95, 1.05])
    with visual_col:
        asset_path = target.asset_absolute_path(config.project_root)
        if asset_path.exists():
            st.image(str(asset_path), caption=target.destination_title, width="stretch")
        else:
            st.markdown(
                f"""
                <div class="ecoscan-disposal-panel">
                    <div class="ecoscan-disposal-title">
                        <span class="ecoscan-color-dot" style="background:{html.escape(target.bin_color_hex)}"></span>
                        {html.escape(target.destination_title)}
                    </div>
                    <p class="ecoscan-muted">{html.escape(target.destination_type)}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with action_col:
        steps = "".join(f"<li>{html.escape(step)}</li>" for step in target.preparation_steps)
        st.markdown(
            f"""
            <div class="ecoscan-disposal-panel featured">
                <div class="ecoscan-action-eyebrow">Destino recomendado</div>
                <div class="ecoscan-disposal-title">
                    <span class="ecoscan-color-dot" style="background:{html.escape(target.bin_color_hex)}"></span>
                    {html.escape(target.destination_title)}
                </div>
                <p>{html.escape(target.destination_type)}</p>
                <div class="ecoscan-destination-grid">
                    <div class="ecoscan-destination-tile">
                        <span>Material</span>
                        <strong>{html.escape(guidance.display_name)}</strong>
                    </div>
                    <div class="ecoscan-destination-tile">
                        <span>Categoria</span>
                        <strong>{html.escape(guidance.environmental_category)}</strong>
                    </div>
                </div>
                <p class="ecoscan-muted">{html.escape(guidance.guidance)}</p>
                <ol class="ecoscan-step-list">{steps}</ol>
                <p class="ecoscan-muted"><strong>Atenção:</strong> {html.escape(target.attention_note)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        location_text = st.text_input(
            "Digite cidade, bairro ou CEP para buscar um ponto próximo",
            key=f"disposal_location_{target.class_id}",
            placeholder="ex.: Ribeirão Preto, SP ou 14000-000",
        )
        map_url = build_map_search_url(
            target.search_query,
            location_text if location_text else "perto de mim",
        )
        generic_map_url = build_map_search_url(
            "ecoponto coleta seletiva logística reversa resíduos",
            location_text if location_text else "perto de mim",
        )
        maps_col, ecopoint_col = st.columns(2)
        maps_col.link_button("Ponto específico", map_url, width="stretch")
        ecopoint_col.link_button("Ecopontos próximos", generic_map_url, width="stretch")
        _render_browser_location_search(st, target)
        st.caption("Confirme horário, regras e materiais aceitos pelo ponto de coleta antes de levar o resíduo.")
    _render_environmental_impact(st, impact)
    matching_points = filter_collection_points(collection_points, class_id=target.class_id)
    if matching_points:
        st.markdown('<div class="ecoscan-section-title">Pontos cadastrados compatíveis</div>', unsafe_allow_html=True)
        _render_collection_point_cards(
            st,
            matching_points,
            origin=location_text or None,
            limit=3,
        )


def _render_quality_snapshot(st: Any, pipeline: Any) -> None:
    quality = pipeline.quality_original
    items = [
        ("exposição", quality.exposure_status),
        ("contraste", quality.contrast_status),
        ("foco", quality.focus_status),
        ("filtro", pipeline.filter_result.name),
        ("segmentação", pipeline.segmentation_result.name),
    ]
    pills = "".join(
        '<span class="ecoscan-mini-pill">'
        f"{html.escape(label)} <small>{html.escape(value)}</small>"
        "</span>"
        for label, value in items
    )
    st.markdown(f'<div class="ecoscan-quality-strip">{pills}</div>', unsafe_allow_html=True)


def _render_capture_tips(st: Any) -> None:
    tips = "".join(f"<li>{html.escape(tip)}</li>" for tip in capture_photo_tips())
    st.markdown(
        f"""
        <div class="ecoscan-admin-panel">
            <strong>Para reconhecer melhor</strong>
            <ul>{tips}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_recognition_decision(st: Any, decision: RecognitionSafetyDecision) -> None:
    renderer = {
        "ok": st.success,
        "warn": st.warning,
        "danger": st.error,
    }.get(decision.tone, st.info)
    renderer(f"{decision.title}. {decision.message} {decision.primary_action}")


def _render_public_next_action(st: Any, action: PublicNextAction) -> None:
    steps = "".join(f"<li>{html.escape(step)}</li>" for step in action.preparation_steps)
    st.markdown(
        f"""
        <section class="ecoscan-public-action {html.escape(action.tone)}">
            <div class="ecoscan-public-action-head">
                <div class="ecoscan-public-action-icon" style="background:{html.escape(action.bin_color_hex)}"></div>
                <div>
                    <strong>{html.escape(action.title)}</strong>
                    <span>{html.escape(action.message)}</span>
                </div>
            </div>
            <div class="ecoscan-public-action-body">
                <div class="ecoscan-public-action-grid">
                    <div class="ecoscan-public-action-tile">
                        <span>Material</span>
                        <strong>{html.escape(action.material_label)}</strong>
                    </div>
                    <div class="ecoscan-public-action-tile">
                        <span>Confiança</span>
                        <strong>{html.escape(action.confidence_label)}</strong>
                    </div>
                    <div class="ecoscan-public-action-tile">
                        <span>Destino</span>
                        <strong>{html.escape(action.destination_title)}</strong>
                    </div>
                    <div class="ecoscan-public-action-tile">
                        <span>Orientação</span>
                        <strong>{html.escape(action.destination_type)}</strong>
                    </div>
                </div>
                <ol class="ecoscan-public-action-steps">{steps}</ol>
                <p class="ecoscan-public-action-note">{html.escape(action.attention_note)}</p>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if action.can_search_collection and action.search_query:
        location_text = st.text_input(
            "Buscar ponto próximo",
            key="public_next_action_location",
            placeholder="Digite cidade, bairro ou CEP",
        )
        st.link_button(
            "Encontrar ponto de coleta",
            build_map_search_url(action.search_query, location_text if location_text else "perto de mim"),
            width="stretch",
        )


def _render_capture_quality_advice(st: Any, pipeline: Any) -> None:
    assessment = pipeline.metadata.get("capture_quality", {})
    if not assessment:
        return
    status = str(assessment.get("status", "good"))
    actions = assessment.get("actions") or []
    action_items = "".join(f"<li>{html.escape(str(action))}</li>" for action in actions[:3])
    st.markdown(
        f"""
        <div class="ecoscan-capture-advice {html.escape(status)}">
            <div class="ecoscan-capture-title">
                <span>{html.escape(str(assessment.get("title", "Qualidade da captura")))}</span>
                <span class="ecoscan-capture-score">{html.escape(str(assessment.get("score", "-")))} / 100</span>
            </div>
            <p>{html.escape(str(assessment.get("message", "")))}</p>
            <ul>{action_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_photo_processing_summary(st: Any, pipeline: Any) -> None:
    filter_meta = pipeline.metadata.get("filter", {})
    filter_decision = filter_meta.get("decision") or {}
    segmentation_meta = pipeline.metadata.get("segmentation", {})
    segmentation_decision = segmentation_meta.get("decision") or {}
    capture_quality = pipeline.metadata.get("capture_quality", {})
    element_analysis = pipeline.element_analysis
    capture_label = str(capture_quality.get("title") or "Qualidade da captura")
    capture_score = capture_quality.get("score")
    if capture_score is not None:
        capture_label = f"{capture_label} ({capture_score}/100)"

    rows = [
        (
            "Filtragem",
            str(filter_decision.get("selected") or filter_meta.get("name") or pipeline.filter_result.name),
            str(filter_decision.get("reason") or filter_meta.get("explanation") or ""),
        ),
        (
            "Segmentação",
            str(segmentation_decision.get("selected") or segmentation_meta.get("name") or pipeline.segmentation_result.name),
            str(segmentation_decision.get("reason") or segmentation_meta.get("explanation") or ""),
        ),
        (
            "Elementos",
            f"{element_analysis.significant_count} elemento(s) relevante(s)",
            str(element_analysis.warning),
        ),
        (
            "Captura",
            capture_label,
            str(capture_quality.get("message") or ""),
        ),
    ]
    rendered_rows = "".join(
        "<div class=\"ecoscan-tech-row\">"
        f"<div class=\"ecoscan-tech-label\">{html.escape(label)}</div>"
        f"<div class=\"ecoscan-tech-value\">{html.escape(value)}"
        f"<span class=\"ecoscan-tech-reason\">{html.escape(reason)}</span></div>"
        "</div>"
        for label, value, reason in rows
    )
    st.markdown(
        '<div class="ecoscan-tech-summary">'
        '<div class="ecoscan-tech-summary-title">Processamento usado nesta foto</div>'
        f"{rendered_rows}"
        "</div>",
        unsafe_allow_html=True,
    )


def _method_chip(label: str, value: str) -> str:
    return (
        '<div class="ecoscan-method-chip">'
        f"<span>{html.escape(label)}</span>"
        f"<strong>{html.escape(value)}</strong>"
        "</div>"
    )


def _render_processing_evidence(
    st: Any,
    result: Any,
    active_profile: UserProfile,
    *,
    render_details_expander: bool = True,
) -> None:
    pipeline = result.pipeline
    filter_name = pipeline.filter_result.name
    segmentation_name = pipeline.segmentation_result.name
    element_count = pipeline.element_analysis.significant_count
    model_name = result.model_type
    accepted_label = "classificação sugerida" if result.accepted else "reconhecimento incerto"
    if result.material_rule is not None:
        accepted_label = "modelo + regra visual"

    method_chips = "".join(
        [
            _method_chip("Filtro", filter_name),
            _method_chip("Segmentação", segmentation_name),
            _method_chip("Elementos", f"{element_count} detectado(s)"),
            _method_chip("Modelo", model_name),
        ]
    )
    st.markdown(
        f"""
        <section class="ecoscan-evidence-panel">
            <div class="ecoscan-evidence-head">
                <div>
                    <strong>Evidência visual da análise</strong>
                    <span>Antes, depois e mapa de detecção gerados para esta imagem específica.</span>
                </div>
                <div class="ecoscan-evidence-badge">{html.escape(accepted_label)}</div>
            </div>
            <div class="ecoscan-method-strip">{method_chips}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    primary_cols = st.columns(2)
    primary_cols[0].image(pipeline.loaded.array, caption="Antes: imagem original enviada", width="stretch")
    primary_cols[1].image(
        pipeline.detection_heatmap,
        caption="Máscara em cores: região selecionada pela segmentação, não confiança do modelo",
        width="stretch",
    )

    detail_cols = st.columns(3)
    detail_cols[0].image(
        pipeline.filter_result.image,
        caption=f"Depois do filtro adaptativo: {filter_name}",
        width="stretch",
    )
    detail_cols[1].image(
        pipeline.segmentation_result.image,
        caption=f"Objeto segmentado: {segmentation_name}",
        width="stretch",
    )
    detail_cols[2].image(
        pipeline.element_overlay,
        caption="Componentes da máscara; não equivalem a objetos reconhecidos",
        width="stretch",
    )

    def render_details() -> None:
        stage_cols = st.columns(3)
        stage_cols[0].image(pipeline.preprocessing.resized, caption="1. Redimensionamento", width="stretch")
        stage_cols[1].image(pipeline.filter_result.image, caption=f"2. Filtragem: {filter_name}", width="stretch")
        stage_cols[2].image(
            pipeline.segmentation_result.mask,
            caption=f"3. Máscara: {segmentation_name}",
            width="stretch",
        )
        stage_cols = st.columns(3)
        stage_cols[0].image(pipeline.segmentation_result.image, caption="4. Imagem segmentada", width="stretch")
        stage_cols[1].image(pipeline.model_input_preview, caption="5. Entrada enviada ao modelo", width="stretch")
        stage_cols[2].image(pipeline.element_overlay, caption="6. Componentes visuais", width="stretch")

        _render_photo_processing_summary(st, pipeline)
        _render_filter_decision(st, pipeline)
        _render_segmentation_decision(st, pipeline)
        _render_element_diagnostics(st, pipeline)
        if result.material_rule is not None:
            st.info(f"Validação visual aplicada: {result.material_rule.reason}")

    if render_details_expander:
        with st.expander("Ver etapas completas e decisão técnica", expanded=active_profile.is_admin):
            render_details()
    else:
        render_details()


def _render_recognition_feedback_form(
    st: Any,
    config: Any,
    result: Any,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    render_contribution(st, config, result, active_profile)


def _select_filter_parameters(st: Any, filter_name: str) -> dict[str, Any]:
    if filter_name == "auto":
        st.caption("Pipeline adaptativo por brilho, contraste, nitidez, densidade de bordas e preservação de cor.")
        return {}
    if filter_name == "gaussian":
        return {
            "kernel_size": st.select_slider("Kernel Gaussiano", options=[3, 5, 7, 9], value=5),
            "sigma": st.slider("Sigma", 0.1, 5.0, 1.0, 0.1),
        }
    if filter_name == "median":
        return {"kernel_size": st.select_slider("Kernel mediana", options=[3, 5, 7, 9], value=5)}
    if filter_name == "bilateral":
        return {
            "diameter": st.select_slider("Diâmetro bilateral", options=[5, 7, 9, 11], value=9),
            "sigma_color": st.slider("Sigma cor", 10, 150, 75, 5),
            "sigma_space": st.slider("Sigma espaço", 10, 150, 75, 5),
        }
    if filter_name == "clahe":
        return {
            "clip_limit": st.slider("Clip limit", 0.5, 6.0, 2.0, 0.1),
            "tile_grid_size": [
                st.select_slider("Grade CLAHE horizontal", options=[4, 8, 12, 16], value=8),
                st.select_slider("Grade CLAHE vertical", options=[4, 8, 12, 16], value=8),
            ],
        }
    if filter_name == "canny":
        low = st.slider("Canny baixo", 10, 240, 80, 5)
        high = st.slider("Canny alto", low + 5, 255, max(160, low + 5), 5)
        return {"threshold1": low, "threshold2": high}
    return {}


def _select_segmentation_parameters(st: Any, segmentation_name: str) -> dict[str, Any]:
    if segmentation_name == "auto":
        st.caption("Escolha adaptativa entre Otsu, HSV e GrabCut conforme contraste, cor, bordas e máscara gerada.")
        return {}
    if segmentation_name == "otsu":
        mode = st.radio("Máscara Otsu", ["automática", "objeto claro", "objeto escuro"], horizontal=True)
        if mode == "objeto claro":
            return {"invert": False}
        if mode == "objeto escuro":
            return {"invert": True}
        return {"invert": None}
    if segmentation_name == "hsv_color":
        return {
            "saturation_min": st.slider("Saturação mínima", 0, 255, 45, 5),
            "value_min": st.slider("Brilho mínimo", 0, 255, 35, 5),
        }
    if segmentation_name == "grabcut":
        return {
            "iterations": st.slider("Iterações GrabCut", 1, 10, 5, 1),
            "margin_percent": st.slider("Margem central", 0.02, 0.25, 0.08, 0.01),
        }
    return {}


def _render_model_status(st: Any, config: Any) -> None:
    status = model_status(config)
    if status.selected_kind == "transfer_learning":
        st.markdown(_badge("Modelo final ativo", "ok"), unsafe_allow_html=True)
    elif status.selected_kind == "visual_svm":
        st.markdown(_badge("Modelo visual supervisionado ativo", "ok"), unsafe_allow_html=True)
    elif status.selected_kind == "visual_knn":
        st.markdown(_badge("Modelo visual ativo", "ok"), unsafe_allow_html=True)
    elif status.selected_kind == "baseline":
        st.markdown(_badge("Modelo inicial ativo", "warn"), unsafe_allow_html=True)
    else:
        st.markdown(_badge("Nenhum modelo disponível", "danger"), unsafe_allow_html=True)
    if status.selected_path:
        st.caption(status.selected_path)


def _dataset_rows(st: Any, config: Any, guidance_by_class: dict[str, DisposalGuidance]) -> tuple[list[dict], Any]:
    status = dataset_status(config)
    rows = []
    for class_id in config.classes:
        guidance = guidance_by_class.get(class_id)
        rows.append(
            {
                "classe": class_id,
                "nome": guidance.display_name if guidance else class_id,
                "categoria": guidance.environmental_category if guidance else "",
                "brutas": status.raw_counts[class_id],
                "curadas": status.curated_counts[class_id],
                "treino": status.train_counts[class_id],
                "validação": status.validation_counts[class_id],
                "teste": status.test_counts[class_id],
            }
        )
    return rows, status


def _render_dataset_status(st: Any, config: Any, guidance_by_class: dict[str, DisposalGuidance]) -> None:
    rows, status = _dataset_rows(st, config, guidance_by_class)
    raw_total = sum(status.raw_counts.values())
    curated_total = sum(status.curated_counts.values())
    split_total = sum(status.train_counts.values()) + sum(status.validation_counts.values()) + sum(status.test_counts.values())
    special_total = 0
    for class_id in config.classes:
        guidance = guidance_by_class.get(class_id)
        category = guidance.environmental_category.lower() if guidance else ""
        if "especial" in category or "eletro" in category or "perigoso" in category:
            special_total += status.raw_counts[class_id]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Imagens brutas", raw_total)
    metric_cols[1].metric("Curadas", curated_total)
    metric_cols[2].metric("Em treino/val/teste", split_total)
    metric_cols[3].metric("Resíduos especiais", special_total)
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_dataset_readiness(st: Any, config: Any) -> None:
    summary, rows = build_dataset_readiness(config, target_per_class=50)
    ready_label = "sim" if summary.ready_for_final_training else "não"
    metric_cols = st.columns(4)
    metric_cols[0].metric("Alvo por classe", summary.target_per_class)
    metric_cols[1].metric("Classes no alvo bruto", f"{summary.classes_at_raw_target}/{summary.class_count}")
    metric_cols[2].metric("Faltam fotos brutas", summary.missing_raw_total)
    metric_cols[3].metric("Pronto p/ treino final", ready_label)

    planning_rows = [
        {
            "classe": row.class_id,
            "nome": row.display_name,
            "categoria": row.environmental_category,
            "fotos brutas": row.raw_count,
            "fotos curadas": row.curated_count,
            "faltam brutas": row.missing_raw,
            "faltam curadas": row.missing_curated,
            "gate": row.gate,
            "próxima ação": row.next_action,
        }
        for row in rows
    ]
    st.dataframe(planning_rows, width="stretch", hide_index=True)


def _render_pipeline_diagnostics(st: Any, pipeline: Any) -> None:
    quality_rows = [
        {
            "etapa": "antes do filtro",
            "brilho médio": pipeline.quality_original.brightness_mean,
            "contraste": pipeline.quality_original.contrast,
            "nitidez": pipeline.quality_original.sharpness,
            "densidade de bordas": pipeline.quality_original.edge_density,
            "exposição": pipeline.quality_original.exposure_status,
            "foco": pipeline.quality_original.focus_status,
            "recomendação": pipeline.quality_original.recommendation,
        },
        {
            "etapa": "após filtro",
            "brilho médio": pipeline.quality_filtered.brightness_mean,
            "contraste": pipeline.quality_filtered.contrast,
            "nitidez": pipeline.quality_filtered.sharpness,
            "densidade de bordas": pipeline.quality_filtered.edge_density,
            "exposição": pipeline.quality_filtered.exposure_status,
            "foco": pipeline.quality_filtered.focus_status,
            "recomendação": pipeline.quality_filtered.recommendation,
        },
    ]
    st.dataframe(quality_rows, width="stretch", hide_index=True)


def _render_filter_decision(st: Any, pipeline: Any) -> None:
    decision = pipeline.metadata.get("filter", {}).get("decision", {})
    if not decision:
        return
    selected = decision.get("selected", pipeline.filter_result.name)
    issues = decision.get("quality_issues") or []
    issue_text = ", ".join(str(issue) for issue in issues)
    st.markdown(
        f"""
        <div class="ecoscan-note">
            <strong>Filtragem escolhida:</strong> {html.escape(str(selected))}<br>
            {html.escape(str(decision.get("reason", "")))}<br>
            <span class="ecoscan-muted">Diagnóstico: {html.escape(issue_text)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    candidates = decision.get("candidates") or []
    if candidates:
        st.dataframe(candidates, width="stretch", hide_index=True)
    skipped = decision.get("skipped") or []
    if skipped:
        st.caption("Sequências ignoradas por indisponibilidade técnica:")
        st.dataframe(skipped, width="stretch", hide_index=True)


def _render_segmentation_decision(st: Any, pipeline: Any) -> None:
    decision = pipeline.metadata.get("segmentation", {}).get("decision", {})
    if not decision:
        return
    st.markdown(
        f"""
        <div class="ecoscan-note">
            <strong>Segmentação escolhida:</strong> {html.escape(str(decision.get("selected", pipeline.segmentation_result.name)))}<br>
            {html.escape(str(decision.get("reason", "")))}
        </div>
        """,
        unsafe_allow_html=True,
    )
    candidates = decision.get("candidates") or []
    if candidates:
        st.dataframe(candidates, width="stretch", hide_index=True)
    skipped = decision.get("skipped") or []
    if skipped:
        st.caption("Métodos ignorados por indisponibilidade técnica:")
        st.dataframe(skipped, width="stretch", hide_index=True)


def _render_element_diagnostics(st: Any, pipeline: Any) -> None:
    analysis = pipeline.element_analysis
    metric_cols = st.columns(4)
    metric_cols[0].metric("Elementos", analysis.significant_count)
    metric_cols[1].metric("Área segmentada", _format_percent(analysis.foreground_ratio))
    metric_cols[2].metric("Maior elemento", _format_percent(analysis.largest_area_ratio))
    metric_cols[3].metric("Múltiplos objetos", "sim" if analysis.likely_multi_object else "não")

    st.caption(analysis.warning)
    rows = [
        {
            "id": element.label,
            "bbox": element.bbox_xyxy,
            "centro": element.centroid_xy,
            "área": element.area_pixels,
            "área relativa": element.area_ratio,
            "toca borda": element.touches_border,
        }
        for element in analysis.elements
    ]
    if rows:
        st.dataframe(rows, width="stretch", hide_index=True)


def _render_ingestion_results(st: Any, results: list[dict[str, Any]]) -> None:
    if not results:
        return
    summary = {
        "saved": sum(1 for result in results if result["status"] == "saved"),
        "duplicate": sum(1 for result in results if result["status"] == "duplicate"),
        "rejected": sum(1 for result in results if result["status"] == "rejected"),
    }
    st.markdown(
        "".join(
            [
                _badge(f"{summary['saved']} salvas", "ok"),
                _badge(f"{summary['duplicate']} duplicadas", "warn"),
                _badge(f"{summary['rejected']} rejeitadas", "danger" if summary["rejected"] else "ok"),
            ]
        ),
        unsafe_allow_html=True,
    )
    rows = [
        {
            "status": result["status"],
            "arquivo": result["original_name"],
            "classe": result["class_id"],
            "destino": result["saved_path"] or result["duplicate_of"],
            "mensagem": result["message"],
            "tamanho": f"{result['width']}x{result['height']}" if result["width"] and result["height"] else "",
        }
        for result in results
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_dependencies(st: Any) -> None:
    rows = [
        {
            "dependência": item.name,
            "status": "ok" if item.installed else "ausente",
            "uso": item.purpose,
        }
        for item in dependency_status()
    ]
    st.dataframe(rows, width="stretch")


def _render_access_testing_panel(st: Any) -> None:
    plan = build_access_plan()
    services = probe_access_services(timeout_seconds=1.2)
    status_html = "".join(
        _status_item(
            service.label,
            "OK" if service.ok else "não respondeu",
            service.note,
            "ok" if service.ok else "warn",
        )
        for service in services
    )
    st.markdown(f'<section class="ecoscan-status-strip">{status_html}</section>', unsafe_allow_html=True)

    st.markdown(
        '<div class="ecoscan-note">Use estes links para uma rodada controlada com colegas. '
        "Em celular, todos precisam estar na mesma rede Wi-Fi; fora da rede local, publique em HTTPS.</div>",
        unsafe_allow_html=True,
    )

    local_cols = st.columns(3)
    for column, link in zip(local_cols, plan.local_links):
        column.link_button(link.label, link.url, width="stretch")

    network_cols = st.columns(3)
    for column, link in zip(network_cols, plan.network_links):
        column.link_button(link.label, link.url, width="stretch")

    st.markdown('<div class="ecoscan-section-title">Mensagem para enviar ao grupo</div>', unsafe_allow_html=True)
    st.code(shareable_access_text(plan), language="text")

    st.markdown(
        '<div class="ecoscan-ops-grid">'
        '<div class="ecoscan-admin-panel"><strong>Regras de acesso</strong>'
        + _html_list(plan.notes)
        + '</div>'
        '<div class="ecoscan-admin-panel"><strong>Roteiro de teste</strong>'
        + _html_list(plan.test_steps)
        + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.dataframe(access_link_rows(plan), width="stretch", hide_index=True)


def _render_error_catalog(st: Any) -> None:
    rows = [
        {
            "código": item.code,
            "categoria": _public_ui_text(item.category),
            "título": _public_ui_text(item.title),
            "mensagem": _public_ui_text(item.message),
            "ação recomendada": _public_ui_text(item.action),
        }
        for item in error_catalog()
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_free_hosting_panel(st: Any, config: Any) -> None:
    plan = build_free_hosting_plan(config)
    st.markdown(
        f"""
        <div class="ecoscan-admin-panel">
            <strong>{html.escape(plan.recommended_platform)}</strong>
            <p>{html.escape(plan.summary)}</p>
            <p><strong>Entrada:</strong> {html.escape(plan.entrypoint)} · <strong>URL esperada:</strong> {html.escape(plan.expected_url)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    cols = st.columns(3)
    cols[0].metric("Foto/câmera no app", "sim" if plan.can_use_camera_photo else "não")
    cols[1].metric("EcoScan Live grátis", "sim" if plan.live_mode_available else "não")
    cols[2].metric("Checklist", sum(1 for item in plan.checks if item.status == "ok"), f"{len(plan.checks)} itens")

    step_items = "".join(f"<li>{html.escape(step)}</li>" for step in plan.steps)
    limitation_items = "".join(f"<li>{html.escape(item)}</li>" for item in plan.limitations)
    st.markdown(
        '<div class="ecoscan-ops-grid">'
        '<div class="ecoscan-admin-panel"><strong>Passo a passo para publicar</strong>'
        f"<ol>{step_items}</ol>"
        "</div>"
        '<div class="ecoscan-admin-panel"><strong>Limitações do gratuito</strong>'
        f"<ul>{limitation_items}</ul>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.dataframe(deployment_check_rows(plan.checks), width="stretch", hide_index=True)


def _completion_label(status: str) -> str:
    labels = {
        "ok": "pronto",
        "attention": "atenção",
        "pending": "pendente",
        "failed": "falha",
    }
    return labels.get(status, status)


def _render_completion_panel(st: Any, config: Any) -> None:
    plan = build_completion_plan(config)
    status_title = (
        "Pronto para demonstração controlada"
        if plan.ready_for_demo
        else "Ainda exige ajuste antes da apresentação"
    )
    status_detail = (
        "O fluxo principal, a experiência de usuário, a gestão, a câmera e as evidências técnicas estão em condição de apresentação."
        if plan.ready_for_demo
        else "Revise os itens em atenção e pendentes antes de tratar o sistema como entrega final."
    )
    st.markdown(
        f"""
        <div class="ecoscan-completion-banner">
            <strong>{html.escape(status_title)}</strong>
            <span>{html.escape(status_detail)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Score técnico", f"{plan.readiness_score}%")
    metric_cols[1].metric("Aceite", f"{plan.acceptance_ok} OK", f"{plan.acceptance_failed} falha")
    metric_cols[2].metric("Base bruta", plan.raw_total, f"faltam {plan.missing_raw_total}")
    metric_cols[3].metric("Base curada", plan.curated_total, f"faltam {plan.missing_curated_total}")

    cards = []
    for action in plan.actions:
        cards.append(
            '<div class="ecoscan-completion-card {status}">'
            "<span>{area} · {label}</span>"
            "<strong>{title}</strong>"
            "<p>{detail}</p>"
            "<small>Próximo passo: {next_step}</small>"
            "</div>".format(
                status=html.escape(action.status),
                area=html.escape(action.area),
                label=html.escape(_completion_label(action.status)),
                title=html.escape(action.title),
                detail=html.escape(action.detail),
                next_step=html.escape(action.next_step),
            )
        )
    st.markdown('<div class="ecoscan-completion-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    if plan.final_model_exists:
        st.success("Modelo final encontrado. A próxima etapa é comparar métricas e validar em imagens reais.")
    else:
        st.warning(
            "Conclusão honesta: o produto está pronto para demonstração e uso orientativo, "
            "mas o reconhecimento definitivo ainda depende de base curada e treino do modelo final."
        )

    st.markdown('<div class="ecoscan-section-title">Comandos finais recomendados</div>', unsafe_allow_html=True)
    st.code(
        "\n".join(
            [
                "python scripts\\run_acceptance_checks.py",
                "python scripts\\generate_final_readiness.py",
                "python scripts\\generate_academic_report.py",
                "python scripts\\prepare_delivery_pack.py",
            ]
        ),
        language="powershell",
    )
    _render_final_readiness(st, config)


def _render_final_readiness(st: Any, config: Any) -> None:
    items = build_final_readiness_items(config)
    summary = summarize_final_readiness(items)
    st.markdown('<div class="ecoscan-section-title">Estrutura preparada para a fase final</div>', unsafe_allow_html=True)
    cols = st.columns(4)
    cols[0].metric("Pronto", summary.get("ready", 0))
    cols[1].metric("Preparado", summary.get("prepared", 0))
    cols[2].metric("Depende de dados/treino", summary.get("needs_data", 0) + summary.get("needs_training", 0))
    cols[3].metric("Evolução futura", summary.get("future", 0))
    st.dataframe(
        [
            {
                "área": item.area,
                "item": item.title,
                "status": item.status,
                "preparado_para_depois": "sim" if item.prepared_for_later else "parcial",
                "evidência": item.evidence,
                "próximo_passo": item.next_step,
            }
            for item in items
        ],
        width="stretch",
        hide_index=True,
    )


def _model_governance_status_label(status: str) -> str:
    labels = {
        "ready": "apto",
        "prepared": "preparado",
        "attention": "atenção",
        "blocked": "bloqueado",
    }
    return labels.get(status, status)


def _render_model_governance(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    labels = _guidance_class_labels(guidance_by_class)
    feedback_entries = read_recognition_feedback(feedback_manifest_path_from_config(config), limit=500)
    field_test_entries = read_field_test_records(field_test_manifest_path_from_config(config), limit=500)
    plan = build_model_governance_plan(
        config,
        feedback_entries=feedback_entries,
        field_test_entries=field_test_entries,
        class_labels=labels,
    )
    status_label = _model_governance_status_label(plan.promotion_status)

    st.markdown('<div class="ecoscan-section-title">Governança do modelo final</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="ecoscan-completion-banner">
            <strong>Promoção do reconhecimento: {html.escape(status_label)}</strong>
            <span>{html.escape(plan.promotion_label)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cols = st.columns(4)
    cols[0].metric("Modelo ativo", _public_ui_text(plan.active_model_kind))
    cols[1].metric("Relatórios", plan.evaluation_count)
    cols[2].metric("Casos difíceis", len(plan.hard_cases))
    cols[3].metric("Status", status_label)

    recommendation_items = "".join(f"<li>{html.escape(item)}</li>" for item in plan.recommendations)
    st.markdown(
        '<div class="ecoscan-admin-panel">'
        "<strong>Regra de engenharia</strong>"
        f"<ul>{recommendation_items}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.dataframe(model_gate_table_rows(plan.gates), width="stretch", hide_index=True)

    metric_rows = metric_snapshot_rows(plan)
    if metric_rows:
        st.markdown('<div class="ecoscan-section-title">Métricas comparativas</div>', unsafe_allow_html=True)
        st.dataframe(metric_rows, width="stretch", hide_index=True)
    else:
        st.info("Ainda não há relatório de avaliação suficiente para comparar modelos.")

    case_rows = hard_case_table_rows(plan.hard_cases, labels)
    if case_rows:
        st.markdown('<div class="ecoscan-section-title">Casos difíceis para regressão</div>', unsafe_allow_html=True)
        st.dataframe(case_rows, width="stretch", hide_index=True)
    else:
        st.info("Quando o grupo registrar erros reais, eles aparecerão aqui como validação obrigatória do próximo modelo.")


def _render_delivery_pack(st: Any, config: Any) -> None:
    pack = build_delivery_pack(config)
    selected_model = _public_ui_text(pack.selected_model)
    metric_cols = st.columns(4)
    metric_cols[0].metric("Prontidão", f"{pack.readiness_score}%")
    metric_cols[1].metric("Imagens brutas", pack.raw_total)
    metric_cols[2].metric("Imagens curadas", pack.curated_total)
    metric_cols[3].metric("Modelo ativo", selected_model)

    if st.button("Gerar pacote técnico"):
        try:
            paths = write_delivery_pack(config)
            st.success(f"Pacote gerado em {paths['index'].parent}")
        except Exception as exc:
            _render_user_error(st, exc, context="delivery_pack")

    rows = [
        {
            "código": criterion.code,
            "cenário": _public_ui_text(criterion.scenario),
            "status": criterion.status,
            "evidência": criterion.evidence,
            "nota": _public_ui_text(criterion.note),
        }
        for criterion in pack.acceptance
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_acceptance_checks(st: Any, config: Any) -> None:
    if st.button("Rodar validação do sistema"):
        try:
            report = run_acceptance_checks(config)
            st.session_state["acceptance_checks_report"] = report
            summary = report.summary
            st.success(
                "Validação concluída: "
                f"{summary.get('ok', 0)} ok, "
                f"{summary.get('attention', 0)} atenção, "
                f"{summary.get('pending', 0)} pendente, "
                f"{summary.get('failed', 0)} falha."
            )
        except Exception as exc:
            _render_user_error(st, exc, context="acceptance_checks")

    report = st.session_state.get("acceptance_checks_report")
    if report is None:
        return
    rows = [
        {
            "código": check.code,
            "área": _public_ui_text(check.area),
            "status": check.status,
            "evidência": check.evidence,
            "detalhes": _public_ui_text(check.details),
        }
        for check in report.checks
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_aps_audit(st: Any, config: Any) -> None:
    items = build_aps_audit(config)
    summary = summarize_audit(items)
    counts = summary["counts"]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Prontidão técnica", f"{summary['readiness_score']}%")
    metric_cols[1].metric("OK", counts.get("ok", 0))
    metric_cols[2].metric("Atenção", counts.get("attention", 0))
    metric_cols[3].metric("Pendente", counts.get("pending", 0))

    rows = [
        {
            "código": _public_code(item.code),
            "área": _public_ui_text(item.area),
            "prioridade": item.priority,
            "status": item.status,
            "critério": _public_ui_text(item.requirement),
            "próxima ação": _public_ui_text(item.next_action),
        }
        for item in items
    ]
    st.dataframe(rows, width="stretch", hide_index=True)

    attention = [
        {
            "código": _public_code(item.code),
            "ponto": _public_ui_text(item.rationale),
            "próxima ação": _public_ui_text(item.next_action),
        }
        for item in items
        if item.priority == "alta" and item.status in {"attention", "pending"}
    ]
    if attention:
        st.markdown(
            '<div class="ecoscan-note">Os itens abaixo são os que mais influenciam a qualidade final: '
            "base de imagens real, curadoria e modelo final.</div>",
            unsafe_allow_html=True,
        )
        st.dataframe(attention, width="stretch", hide_index=True)


def _render_history(st: Any, config: Any) -> None:
    entries = read_history(history_path_from_config(config), limit=30)
    if not entries:
        st.write("Nenhum registro salvo.")
        return
    rows = [
        {
            "data_utc": entry.timestamp_utc,
            "classe": entry.predicted_class or "__uncertain__",
            "confiança": entry.probability,
            "modelo": entry.model_type,
            "filtro": entry.filter_name,
            "sequência de filtro": entry.filter_decision or entry.filter_name,
            "segmentação": entry.segmentation_decision or entry.segmentation_name,
            "qualidade": (
                f"{entry.capture_quality_status} ({entry.capture_quality_score}/100)"
                if entry.capture_quality_status and entry.capture_quality_score is not None
                else entry.capture_quality_status
            ),
            "elementos": entry.elements_count,
            "categoria": entry.environmental_category,
        }
        for entry in reversed(entries)
    ]
    st.dataframe(rows, width="stretch")


def _render_collection_points_tab(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
    collection_points: list[CollectionPoint],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Encontrar ponto de coleta</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ecoscan-note">Use a base cadastrada para consultar pontos compatíveis por material. '
        'A base inclui Ecopontos cadastrados para Ribeirão Preto e São Paulo; quando não houver ponto para a classe, '
        'a busca externa no mapa continua disponível.</div>',
        unsafe_allow_html=True,
    )
    control_col, source_col = st.columns([1.05, 0.95])
    with control_col:
        selected_class = st.selectbox(
            "Material",
            config.classes,
            format_func=lambda class_id: _class_label(class_id, guidance_by_class),
            key="collection_point_class",
        )
        city_options = ["São Paulo", "Ribeirão Preto", "Todas"]
        city_scope = st.selectbox(
            "Cidade",
            city_options,
            key="collection_point_city_scope",
        )
        origin = st.text_input(
            "Local de origem para rota",
            placeholder="ex.: Centro, São Paulo, Ribeirão Preto ou seu CEP",
            key="collection_point_origin",
        )
        city_query = st.text_input(
            "Filtrar por bairro, rua ou cidade",
            placeholder="ex.: São Paulo, Pinheiros, Sé, Jardim ou Ribeirão Preto",
            key="collection_point_city_query",
        )
    with source_col:
        covered_cities = sorted({f"{point.city}/{point.state}" for point in collection_points if point.city})
        st.metric("Pontos cadastrados", len(collection_points))
        st.metric("Cidades cobertas", len(covered_cities))
        source_labels = sorted({point.source_label for point in collection_points if point.source_label})
        if source_labels:
            st.caption("Fonte: " + "; ".join(source_labels))
        if covered_cities:
            city_chips = "".join(
                f'<span class="ecoscan-territory-chip">{html.escape(city)}</span>'
                for city in covered_cities
            )
            st.markdown(
                f'<div class="ecoscan-territory-chip-row">{city_chips}</div>',
                unsafe_allow_html=True,
            )
        st.link_button(
            "Buscar no mapa",
            build_map_search_url(
                "ecoponto coleta seletiva logística reversa resíduos São Paulo Ribeirão Preto",
                origin if origin else "perto de mim",
            ),
            width="stretch",
        )

    scoped_points = (
        collection_points
        if city_scope == "Todas"
        else [point for point in collection_points if point.city == city_scope]
    )
    filtered_points = filter_collection_points(
        scoped_points,
        class_id=selected_class,
        city_query=city_query or None,
    )
    if not filtered_points:
        guidance = guidance_by_class.get(selected_class)
        label = guidance.display_name if guidance else selected_class
        st.info(
            f"A base local ainda não tem ponto cadastrado para {label}. "
            "Use a busca no mapa ou cadastre pontos oficiais em config/collection_points.json."
        )
        fallback = build_map_search_url(
            f"ponto de coleta {label} descarte reciclagem",
            origin if origin else "perto de mim",
        )
        st.link_button("Procurar ponto externo", fallback, width="stretch")
        return

    st.markdown('<div class="ecoscan-section-title">Pontos compatíveis</div>', unsafe_allow_html=True)
    _render_collection_point_cards(st, filtered_points, origin=origin or None, limit=8)
    rows = [
        {
            "nome": point.name,
            "bairro": point.neighborhood,
            "endereço": point.full_address,
            "horário": point.hours,
            "materiais": _format_point_materials(point, limit=8),
            "rota": build_collection_point_directions_url(point, origin=origin or None),
        }
        for point in filtered_points
    ]
    st.dataframe(rows, width="stretch", hide_index=True)


def _render_campaign_cards(st: Any, campaign: Campaign, guidance_by_class: dict[str, DisposalGuidance]) -> None:
    cards = []
    for mission in campaign.missions:
        classes = _campaign_class_labels(mission.target_classes, guidance_by_class, limit=4)
        cards.append(
            '<div class="ecoscan-mission-card">'
            f"<strong>{html.escape(mission.title)}</strong>"
            f"<span>{html.escape(mission.description)}</span>"
            f'<span class="ecoscan-card-meta">{mission.points} pontos'
            f"{' · ' + html.escape(classes) if classes else ''}</span>"
            "</div>"
        )
    st.markdown('<div class="ecoscan-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def _render_reward_cards(st: Any, campaign: Campaign) -> None:
    if not campaign.rewards:
        return
    cards = [
        '<div class="ecoscan-reward-card">'
        f"<strong>{html.escape(reward.title)}</strong>"
        f"<span>{html.escape(reward.description)}</span>"
        f'<span class="ecoscan-card-meta">a partir de {reward.points_required} pontos</span>'
        "</div>"
        for reward in campaign.rewards
    ]
    st.markdown('<div class="ecoscan-card-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)


def _campaign_class_labels(
    class_ids: tuple[str, ...],
    guidance_by_class: dict[str, DisposalGuidance],
    *,
    limit: int = 5,
) -> str:
    return format_class_labels(class_ids, _guidance_class_labels(guidance_by_class), limit=limit)


def _guidance_class_labels(guidance_by_class: dict[str, DisposalGuidance]) -> dict[str, str]:
    return {class_id: guidance.display_name for class_id, guidance in guidance_by_class.items()}


def _html_list(items: tuple[str, ...] | list[str], *, empty_text: str = "Não configurado.") -> str:
    clean_items = [str(item).strip() for item in items if str(item).strip()]
    if not clean_items:
        return f'<p class="ecoscan-muted">{html.escape(empty_text)}</p>'
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in clean_items) + "</ul>"


def _mission_label(mission: Mission) -> str:
    return f"{mission.title} · {mission.points} pontos"


def _role_label(role: str) -> str:
    labels = {"user": "cidadão", "admin": "gestão"}
    return labels.get(role, role)


def _profile_label(profile: UserProfile) -> str:
    organization = f" · {profile.organization}" if profile.organization else ""
    role = _role_label(profile.role)
    if profile.display_name.strip().lower() == role:
        return f"{profile.display_name}{organization}"
    return f"{profile.display_name} · {role}{organization}"


def _render_active_profile_card(st: Any, profile: UserProfile) -> None:
    mode = "Gestão" if profile.is_admin else "Cidadão"
    note = profile.notes or "Perfil local do protótipo."
    st.markdown(
        f"""
        <div class="ecoscan-profile-card">
            <strong>{html.escape(profile.display_name)}</strong>
            <span>{html.escape(mode)} · {html.escape(profile.organization or "EcoScan")}</span>
            <span>{html.escape(note)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _next_reward_text(campaign: Campaign, points: int) -> str:
    next_reward = next((reward for reward in campaign.rewards if reward.points_required > points), None)
    if next_reward:
        return f"Próxima recompensa: {next_reward.title} ({next_reward.points_required} pontos)."
    return "Todas as recompensas configuradas já estão ao seu alcance."


def _render_campaign_tab(
    st: Any,
    config: Any,
    campaign: Campaign | None,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
    impacts_by_class: dict[str, EnvironmentalImpact],
    targets_by_class: dict[str, DisposalTarget],
    pipeline_options: ProcessingPipelineOptions,
) -> None:
    st.markdown('<div class="ecoscan-section-title">Campanha ambiental</div>', unsafe_allow_html=True)
    if campaign is None:
        st.info("Campanha ainda não configurada.")
        return

    ledger_path = points_ledger_path_from_config(config)
    points = total_points_for_user(ledger_path, active_profile.id)
    info_cols = st.columns([1.2, 0.8])
    with info_cols[0]:
        st.markdown(
            f"""
            <div class="ecoscan-admin-panel">
                <strong>{html.escape(campaign.title)}</strong>
                <p class="ecoscan-muted">{html.escape(campaign.public_message)}</p>
                <span class="ecoscan-card-meta">{html.escape(campaign.owner)} · {html.escape(campaign.weekly_rotation_note)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with info_cols[1]:
        st.metric("Seus pontos", points)
        st.caption(_next_reward_text(campaign, points))

    st.markdown('<div class="ecoscan-section-title">Missões rotativas</div>', unsafe_allow_html=True)
    _render_campaign_cards(st, campaign, guidance_by_class)

    mission_col, proof_col = st.columns([0.95, 1.05])
    with mission_col:
        selected_mission = st.selectbox(
            "Missão para validar",
            campaign.missions,
            format_func=_mission_label,
            key="campaign_selected_mission",
        )
        st.info(selected_mission.proof_hint)
        admin_items = "".join(f"<li>{html.escape(item)}</li>" for item in campaign.admin_responsibilities)
        st.markdown(
            f"""
            <div class="ecoscan-admin-panel">
                <strong>Visão da gestão ambiental</strong>
                <ul>{admin_items}</ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with proof_col:
        proof_source = st.radio("Comprovação", ["Câmera", "Imagem"], horizontal=True, key="campaign_proof_source")
        if proof_source == "Câmera":
            proof_file = st.camera_input("Fotografar missão", key="campaign_camera")
            source_kind = "mission_camera"
        else:
            proof_file = st.file_uploader(
                "Enviar foto da missão",
                type=["jpg", "jpeg", "png"],
                key="campaign_upload",
            )
            source_kind = "mission_upload"

        if proof_file is None:
            st.caption("Fotografe ou envie uma evidência da missão para liberar a validação.")
        if st.button("Validar missão", disabled=proof_file is None):
            temp_path = _temporary_upload(proof_file, prefix="mission")
            evidence_sha256 = hashlib.sha256(proof_file.getvalue()).hexdigest()
            try:
                with st.spinner("Validando missão com processamento de imagem..."):
                    mission_result = analyze_waste_image(temp_path, config, options=pipeline_options)
                evaluation = evaluate_mission_submission(selected_mission, mission_result)
                st.session_state["last_mission_result"] = mission_result
                st.session_state["last_mission_evaluation"] = evaluation
                if evaluation.accepted:
                    if has_awarded_evidence(
                        ledger_path,
                        user_id=active_profile.id,
                        mission_id=selected_mission.id,
                        evidence_sha256=evidence_sha256,
                    ):
                        st.info("Essa mesma comprovação já foi pontuada para este perfil.")
                    else:
                        append_point_transaction(
                            ledger_path,
                            build_point_transaction(
                                user_id=active_profile.id,
                                mission_id=selected_mission.id,
                                points=evaluation.points_awarded,
                                evidence_sha256=evidence_sha256,
                                detected_class=evaluation.detected_class,
                                probability=evaluation.probability,
                                note=evaluation.reason,
                            ),
                        )
                        append_history_entry(
                            history_path_from_config(config),
                            build_history_entry(mission_result, source_path=source_kind),
                        )
                        updated_points = total_points_for_user(ledger_path, active_profile.id)
                        st.success(
                            f"Missão validada. +{evaluation.points_awarded} pontos. Total: {updated_points}."
                        )
                else:
                    st.warning(evaluation.reason)
            except Exception as exc:
                _render_user_error(st, exc, context="campaign_mission")

    evaluation = st.session_state.get("last_mission_evaluation")
    mission_result = st.session_state.get("last_mission_result")
    if evaluation is not None and mission_result is not None:
        status_label = "validada" if evaluation.accepted else "pendente"
        st.markdown(
            f"""
            <div class="ecoscan-report-status {'inconclusivo' if not evaluation.accepted else ''}">
                <strong>Resultado da missão: {html.escape(status_label)}</strong>
                <span>{html.escape(evaluation.reason)}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        _render_photo_processing_summary(st, mission_result.pipeline)

    st.markdown('<div class="ecoscan-section-title">Recompensas e incentivo</div>', unsafe_allow_html=True)
    _render_reward_cards(st, campaign)

    st.markdown('<div class="ecoscan-section-title">Guia educativo rápido</div>', unsafe_allow_html=True)
    guide_class = st.selectbox(
        "Material para orientar",
        list(guidance_by_class.keys()),
        format_func=lambda class_id: guidance_by_class[class_id].display_name,
        key="campaign_guide_class",
    )
    guidance = guidance_by_class.get(guide_class)
    impact = impacts_by_class.get(guide_class)
    target = targets_by_class.get(guide_class)
    if guidance:
        guide_cols = st.columns(3)
        guide_cols[0].write(f"**Como descartar:** {guidance.guidance}")
        guide_cols[1].write(f"**Por que importa:** {guidance.educational_note}")
        if target:
            guide_cols[2].write(f"**Destino:** {target.destination_title}")
        if impact:
            _render_environmental_impact(st, impact)


def _render_civic_report_status(st: Any, record: Any) -> None:
    tone = ""
    if record.verification_status == "triagem_inconclusiva":
        tone = "inconclusivo"
    elif record.verification_status == "imagem_insuficiente":
        tone = "insuficiente"
    st.markdown(
        f"""
        <div class="ecoscan-report-status {tone}">
            <strong>{html.escape(record.verification_status.replace("_", " ").title())}</strong>
            <span>{html.escape(record.verifier_note)}</span>
            <span class="ecoscan-card-meta">Classe provável: {html.escape(str(record.detected_class or record.top_class or "não identificada"))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_civic_reports_tab(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    pipeline_options: ProcessingPipelineOptions,
) -> None:
    st.markdown('<div class="ecoscan-section-title">Denunciar mau descarte</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ecoscan-note">A denúncia usa o mesmo tratamento de imagem, segmentação e reconhecimento '
        "para fazer triagem técnica da evidência. O resultado indica consistência visual, não substitui vistoria oficial.</div>",
        unsafe_allow_html=True,
    )

    form_col, info_col = st.columns([1.05, 0.95])
    with form_col:
        report_source = st.radio("Evidência", ["Câmera", "Imagem"], horizontal=True, key="civic_report_source")
        if report_source == "Câmera":
            report_file = st.camera_input("Fotografar descarte irregular", key="civic_report_camera")
            source_kind = "camera"
        else:
            report_file = st.file_uploader(
                "Enviar foto da denúncia",
                type=["jpg", "jpeg", "png"],
                key="civic_report_upload",
            )
            source_kind = "upload"
        location_note = st.text_input("Local aproximado", placeholder="ex.: rua, bairro, ponto de referência")
        description = st.text_area("Descrição breve", placeholder="ex.: resíduos descartados perto de área verde")
        contact = st.text_input("Contato opcional", placeholder="telefone ou e-mail, se quiser retorno")

        if report_file is None:
            st.caption("Adicione uma foto da situação para liberar o registro da denúncia.")
        if st.button("Analisar e registrar denúncia", disabled=report_file is None):
            temp_path = _temporary_upload(report_file, prefix="report")
            try:
                with st.spinner("Processando evidência da denúncia..."):
                    report_result = analyze_waste_image(temp_path, config, options=pipeline_options)
                evidence_path = save_civic_report_evidence(
                    config,
                    original_name=report_file.name,
                    data=report_file.getvalue(),
                )
                record = build_civic_report_record(
                    report_result,
                    evidence_path=evidence_path,
                    location_note=location_note,
                    description=description,
                    contact=contact,
                    source_kind=source_kind,
                    submitted_by=active_profile.id,
                )
                append_civic_report(civic_reports_path_from_config(config), record)
                st.session_state["last_civic_report_record"] = record
                st.session_state["last_civic_report_result"] = report_result
                st.success("Denúncia registrada para triagem.")
            except Exception as exc:
                _render_user_error(st, exc, context="civic_report")
    with info_col:
        st.markdown(
            """
            <div class="ecoscan-admin-panel">
                <strong>Como a triagem funciona</strong>
                <ul>
                    <li>valida se a imagem é legível;</li>
                    <li>aplica filtragem e segmentação adaptativas;</li>
                    <li>estima o resíduo mais provável;</li>
                    <li>registra qualidade, confiança e elementos detectados;</li>
                    <li>mantém a evidência para revisão da gestão ambiental.</li>
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        report_path = civic_reports_path_from_config(config)
        st.caption(f"Manifesto local: {report_path}")

    record = st.session_state.get("last_civic_report_record")
    report_result = st.session_state.get("last_civic_report_result")
    if record is not None:
        _render_civic_report_status(st, record)
    if report_result is not None:
        _render_photo_processing_summary(st, report_result.pipeline)

    recent = read_civic_reports(civic_reports_path_from_config(config))
    if not active_profile.is_admin:
        recent = [item for item in recent if item.submitted_by == active_profile.id]
    recent = recent[-8:]
    if recent:
        st.markdown('<div class="ecoscan-section-title">Últimas denúncias registradas</div>', unsafe_allow_html=True)
        rows = [
            {
                "data_utc": item.timestamp_utc,
                "status": item.verification_status,
                "classe": item.detected_class or item.top_class or "",
                "confiança": item.probability,
                "local": item.location_note,
                "qualidade": item.capture_quality_status,
                "elementos": item.elements_count,
                "usuário": item.submitted_by,
            }
            for item in reversed(recent)
        ]
        st.dataframe(rows, width="stretch", hide_index=True)


def _render_field_test_form(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Registrar teste da rodada</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ecoscan-note">Use esta área quando estiver testando com o grupo. '
        "Ela registra se o reconhecimento acertou, errou ou ficou inconclusivo, sem depender de print ou anotação solta.</div>",
        unsafe_allow_html=True,
    )
    class_options = list(config.classes)
    model_options = ["__none__", *class_options]
    with st.form(f"field_test_form_{active_profile.id}"):
        cols = st.columns(2)
        with cols[0]:
            expected_class = st.selectbox(
                "Material testado",
                class_options,
                format_func=lambda class_id: _class_label(class_id, guidance_by_class),
            )
            model_class = st.selectbox(
                "O app indicou",
                model_options,
                format_func=lambda class_id: "Não reconheceu / não anotei"
                if class_id == "__none__"
                else _class_label(class_id, guidance_by_class),
            )
            result_status = st.radio(
                "Resultado",
                ["acertou", "errou", "inconclusivo"],
                horizontal=True,
            )
        with cols[1]:
            device_kind = st.selectbox("Dispositivo", ["celular", "computador", "tablet", "outro"])
            capture_mode = st.selectbox("Entrada usada", ["foto enviada", "câmera ao vivo", "upload no PC"])
            has_confidence = st.checkbox("Informar confiança exibida")
            confidence_percent = st.slider("Confiança (%)", 0, 100, 0, disabled=not has_confidence)
        note = st.text_area(
            "Observação do teste",
            placeholder="ex.: lata Monster virou vidro; garrafa PET com fundo branco acertou",
        )
        submitted = st.form_submit_button("Salvar teste da rodada")

    if submitted:
        try:
            record = build_field_test_record(
                tester_id=active_profile.id,
                tester_name=active_profile.display_name,
                expected_class=expected_class,
                model_class=None if model_class == "__none__" else model_class,
                result_status=result_status,
                device_kind=device_kind,
                capture_mode=capture_mode,
                confidence=(confidence_percent / 100) if has_confidence else None,
                note=note,
            )
            append_field_test_record(field_test_manifest_path_from_config(config), record)
            st.success("Teste registrado. A gestão já consegue usar esse dado na aba Gestão.")
        except Exception as exc:
            _render_user_error(st, exc, context="field_test")

    recent_tests = read_field_test_records(
        field_test_manifest_path_from_config(config),
        tester_id=active_profile.id,
        limit=8,
    )
    if recent_tests:
        st.dataframe(
            field_test_rows(recent_tests, _guidance_class_labels(guidance_by_class), limit=8),
            width="stretch",
            hide_index=True,
        )


def _render_account_tab(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    campaign: Campaign | None,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Minha participação</div>', unsafe_allow_html=True)
    _render_active_profile_card(st, active_profile)
    render_citizen_protocols(st, config, active_profile)
    ledger_path = points_ledger_path_from_config(config)
    points = total_points_for_user(ledger_path, active_profile.id)
    transactions = read_point_transactions(ledger_path, user_id=active_profile.id, limit=20)

    cols = st.columns(3)
    cols[0].metric("Pontos acumulados", points)
    cols[1].metric("Missões validadas", len(transactions))
    cols[2].metric("Missões disponíveis", len(campaign.missions) if campaign else 0)
    if campaign:
        st.caption(_next_reward_text(campaign, points))

    if transactions:
        rows = [
            {
                "data_utc": transaction.timestamp_utc,
                "missão": transaction.mission_id,
                "pontos": transaction.points,
                "classe": transaction.detected_class,
                "confiança": transaction.probability,
                "status": transaction.status,
            }
            for transaction in reversed(transactions)
        ]
        st.dataframe(rows, width="stretch", hide_index=True)
    else:
        st.info("Este perfil ainda não possui missões pontuadas.")

    _render_field_test_form(st, config, active_profile, guidance_by_class)

    st.markdown('<div class="ecoscan-section-title">Minhas denúncias</div>', unsafe_allow_html=True)
    report_rows = [
        report
        for report in read_civic_reports(civic_reports_path_from_config(config), limit=100)
        if report.submitted_by == active_profile.id
    ]
    if not report_rows:
        st.write("Nenhuma denúncia registrada por este perfil.")
        return

    reviews = latest_reviews_by_report(read_civic_report_reviews(civic_report_reviews_path_from_config(config)))
    st.dataframe(
        [
            {
                "data_utc": report.timestamp_utc,
                "triagem": report.verification_status,
                "classe": report.detected_class or report.top_class or "",
                "local": report.location_note,
                "revisão_admin": reviews.get(report.id).decision if report.id in reviews else "aguardando",
            }
            for report in reversed(report_rows[-12:])
        ],
        width="stretch",
        hide_index=True,
    )


def _render_admin_campaign_operations(
    st: Any,
    campaign: Campaign | None,
    collection_points: list[CollectionPoint],
    point_transactions: list[Any],
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Operação da campanha</div>', unsafe_allow_html=True)
    if campaign is None:
        st.info("Campanha ainda não configurada.")
        return

    summary = build_campaign_operations_summary(
        campaign,
        collection_points,
        point_transactions,
        _guidance_class_labels(guidance_by_class),
    )

    metric_cols = st.columns(4)
    metric_cols[0].metric("Missões publicadas", summary.mission_count)
    metric_cols[1].metric("Pontos possíveis", summary.possible_points)
    metric_cols[2].metric("Participantes pontuados", summary.participant_count)
    metric_cols[3].metric("Pontos recicláveis", summary.recyclable_point_count)

    st.markdown(
        f"""
        <div class="ecoscan-admin-panel">
            <strong>{html.escape(campaign.title)}</strong>
            <p class="ecoscan-muted">{html.escape(campaign.public_message)}</p>
            <span class="ecoscan-card-meta">{html.escape(campaign.owner)} · {html.escape(campaign.weekly_rotation_note)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    city_chips = "".join(
        f'<span class="ecoscan-territory-chip">{html.escape(city)} · {count}</span>'
        for city, count in summary.city_counts
    )
    st.markdown(
        '<div class="ecoscan-ops-grid">'
        '<div class="ecoscan-admin-panel"><strong>Objetivos estratégicos</strong>'
        + _html_list(campaign.strategic_goals)
        + '</div>'
        '<div class="ecoscan-admin-panel"><strong>Rotina da secretaria</strong>'
        + _html_list(campaign.operational_routines)
        + '</div>'
        '<div class="ecoscan-admin-panel"><strong>Públicos atendidos</strong>'
        + _html_list(campaign.audience_segments)
        + f'<div class="ecoscan-territory-chip-row">{city_chips}</div>'
        + '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ecoscan-section-title">Desempenho das missões</div>', unsafe_allow_html=True)
    st.dataframe(
        mission_activity_rows(summary),
        width="stretch",
        hide_index=True,
    )

    st.markdown('<div class="ecoscan-section-title">Missões publicadas ao cidadão</div>', unsafe_allow_html=True)
    st.dataframe(published_mission_rows(summary), width="stretch", hide_index=True)


def _render_admin_recognition_improvement_plan(
    st: Any,
    plan: RecognitionImprovementPlan,
) -> None:
    st.markdown('<div class="ecoscan-section-title">Plano de reforço do reconhecimento</div>', unsafe_allow_html=True)
    recommendation_items = "".join(f"<li>{html.escape(item)}</li>" for item in plan.recommendations)
    st.markdown(
        '<div class="ecoscan-admin-panel">'
        "<strong>Próximas ações recomendadas</strong>"
        f"<ul>{recommendation_items}</ul>"
        "</div>",
        unsafe_allow_html=True,
    )

    priority_cards = []
    class_by_priority = {"alta": "high", "média": "medium", "baixa": "low"}
    actionable_priorities = [item for item in plan.priorities if item.score > 0]
    for item in actionable_priorities[:3]:
        reasons = "; ".join(item.reasons[:3])
        priority_cards.append(
            '<div class="ecoscan-priority-card '
            + html.escape(class_by_priority.get(item.priority, "low"))
            + '">'
            f"<span>Prioridade {html.escape(item.priority)} · score {item.score:.1f}</span>"
            f"<strong>{html.escape(item.label)}</strong>"
            f"<p>{html.escape(item.action)}</p>"
            f"<small>{html.escape(reasons)}</small>"
            "</div>"
        )
    if priority_cards:
        st.markdown(
            '<div class="ecoscan-ops-grid">' + "".join(priority_cards) + "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.info("Aguardando histórico e correções para formar prioridade operacional. Faça uma rodada de testes com fotos reais e corrija os erros encontrados.")

    priority_rows = priority_table_rows(plan.priorities)
    if priority_rows:
        st.dataframe(priority_rows, width="stretch", hide_index=True)

    confusion_rows = confusion_table_rows(plan.confusions)
    if confusion_rows:
        st.markdown('<div class="ecoscan-section-title">Confusões críticas para corrigir</div>', unsafe_allow_html=True)
        st.dataframe(confusion_rows, width="stretch", hide_index=True)
    else:
        st.info("Ainda não há confusões registradas por correção. Quando alguém corrigir um erro, ele aparecerá aqui.")


def _render_admin_field_tests(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Rodada de testes do grupo</div>', unsafe_allow_html=True)
    records = read_field_test_records(field_test_manifest_path_from_config(config), limit=500)
    labels = _guidance_class_labels(guidance_by_class)
    summary = summarize_field_tests(records)
    cols = st.columns(5)
    cols[0].metric("Testes registrados", summary.total)
    cols[1].metric("Acertos", summary.correct_count)
    cols[2].metric("Erros", summary.wrong_count)
    cols[3].metric("Inconclusivos", summary.inconclusive_count)
    cols[4].metric("No celular", summary.mobile_count)

    if not records:
        st.info("Ainda não há testes da rodada. Peça ao grupo para registrar cada teste na aba Perfil.")
        return

    st.markdown(
        '<div class="ecoscan-admin-table-note">'
        "Use esta leitura junto com as correções do reconhecimento. Classes com muitos erros ou inconclusivos devem virar prioridade de novas fotos."
        "</div>",
        unsafe_allow_html=True,
    )
    by_class = field_test_class_rows(records, labels)
    latest = field_test_rows(records, labels, limit=20)
    cols = st.columns([0.95, 1.05])
    with cols[0]:
        st.markdown('<div class="ecoscan-section-title">Resumo por classe testada</div>', unsafe_allow_html=True)
        st.dataframe(by_class, width="stretch", hide_index=True)
    with cols[1]:
        st.markdown('<div class="ecoscan-section-title">Últimos testes registrados</div>', unsafe_allow_html=True)
        st.dataframe(latest, width="stretch", hide_index=True)


def _render_admin_recognition_quality(
    st: Any,
    config: Any,
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Qualidade do reconhecimento</div>', unsafe_allow_html=True)
    history_entries = read_history(history_path_from_config(config), limit=500)
    feedback_entries = read_recognition_feedback(feedback_manifest_path_from_config(config), limit=500)
    field_test_entries = read_field_test_records(field_test_manifest_path_from_config(config), limit=500)
    class_labels = _guidance_class_labels(guidance_by_class)
    summary = build_recognition_quality_summary(history_entries, feedback_entries)
    improvement_plan = build_recognition_improvement_plan(
        history_entries,
        feedback_entries,
        dataset_status(config),
        class_labels,
        field_test_entries=field_test_entries,
        classes=config.classes,
    )

    metric_cols = st.columns(5)
    metric_cols[0].metric("Análises salvas", summary.analysis_count)
    metric_cols[1].metric("Aceitas", summary.accepted_count)
    metric_cols[2].metric("Inconclusivas", summary.uncertain_count)
    metric_cols[3].metric("Baixa confiança", summary.low_confidence_count)
    metric_cols[4].metric("Correções", summary.feedback_count)
    if summary.average_confidence is not None:
        st.caption(f"Confiança média registrada: {summary.average_confidence:.1%}.")

    st.markdown(
        '<div class="ecoscan-admin-table-note">'
        "Use estes dados para decidir quais fotos coletar primeiro. Classes com baixa confiança ou correções frequentes "
        "devem receber mais imagens reais, em vários ângulos e ambientes."
        "</div>",
        unsafe_allow_html=True,
    )
    _render_admin_recognition_improvement_plan(st, improvement_plan)

    correction_table = correction_rows(feedback_entries, class_labels)
    class_table = class_quality_rows(history_entries, class_labels)
    cols = st.columns([1, 1])
    with cols[0]:
        st.markdown('<div class="ecoscan-section-title">Correções enviadas</div>', unsafe_allow_html=True)
        if correction_table:
            st.dataframe(correction_table, width="stretch", hide_index=True)
        else:
            st.info("Ainda não há correções registradas. Peça ao grupo para corrigir cada erro de reconhecimento.")
    with cols[1]:
        st.markdown('<div class="ecoscan-section-title">Classes para reforçar</div>', unsafe_allow_html=True)
        if class_table:
            st.dataframe(class_table, width="stretch", hide_index=True)
        else:
            st.info("Ative salvar histórico ou valide imagens para formar indicadores por classe.")


def _render_admin_tab(
    st: Any,
    config: Any,
    active_profile: UserProfile,
    profiles: tuple[UserProfile, ...],
    campaign: Campaign | None,
    collection_points: list[CollectionPoint],
    guidance_by_class: dict[str, DisposalGuidance],
) -> None:
    st.markdown('<div class="ecoscan-section-title">Gestão ambiental</div>', unsafe_allow_html=True)
    if not active_profile.is_admin:
        st.warning("Este painel é restrito ao perfil administrativo.")
        return

    render_review(st, config, active_profile)

    ledger_path = points_ledger_path_from_config(config)
    reports_path = civic_reports_path_from_config(config)
    reviews_path = civic_report_reviews_path_from_config(config)
    reports = read_civic_reports(reports_path, limit=200)
    reviews = read_civic_report_reviews(reviews_path)
    latest_reviews = latest_reviews_by_report(reviews)
    point_transactions = read_point_transactions(ledger_path, limit=500)

    cols = st.columns(4)
    cols[0].metric("Perfis ativos", len(profiles))
    cols[1].metric("Missões", len(campaign.missions) if campaign else 0)
    cols[2].metric("Denúncias", len(reports))
    cols[3].metric("Pontos de coleta", len(collection_points))

    _render_admin_campaign_operations(
        st,
        campaign,
        collection_points,
        point_transactions,
        guidance_by_class,
    )

    _render_admin_recognition_quality(st, config, guidance_by_class)
    _render_admin_field_tests(st, config, guidance_by_class)

    st.markdown('<div class="ecoscan-section-title">Ranking e participação</div>', unsafe_allow_html=True)
    point_rows = summarize_points_by_user(ledger_path, profiles)
    if point_rows:
        st.dataframe(point_rows, width="stretch", hide_index=True)
    else:
        st.info("Ainda não há pontuação registrada.")

    st.markdown('<div class="ecoscan-section-title">Triagem de denúncias</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="ecoscan-admin-table-note">A triagem automática orienta a gestão, mas a decisão administrativa fica registrada separadamente.</div>',
        unsafe_allow_html=True,
    )
    if not reports:
        st.write("Nenhuma denúncia registrada.")
    else:
        report_rows = [
            {
                "id": report.id,
                "data_utc": report.timestamp_utc,
                "triagem": report.verification_status,
                "revisão_admin": latest_reviews.get(report.id).decision if report.id in latest_reviews else "aguardando",
                "classe": report.detected_class or report.top_class or "",
                "confiança": report.probability,
                "local": report.location_note,
                "usuário": report.submitted_by,
                "qualidade": report.capture_quality_status,
            }
            for report in reversed(reports[-30:])
        ]
        st.dataframe(report_rows, width="stretch", hide_index=True)

        selected_report = st.selectbox(
            "Denúncia para revisar",
            list(reversed(reports[-30:])),
            format_func=lambda report: f"{report.timestamp_utc} · {report.location_note or report.id}",
            key="admin_selected_report",
        )
        decision_label_map = {
            "Encaminhar para fiscalização": "encaminhar",
            "Arquivar como insuficiente": "arquivar",
            "Solicitar nova foto": "solicitar_nova_foto",
        }
        decision_label = st.selectbox(
            "Decisão administrativa",
            list(decision_label_map.keys()),
            key="admin_report_decision",
        )
        review_note = st.text_area(
            "Observação da gestão",
            placeholder="ex.: endereço incompleto, evidência boa ou encaminhamento necessário",
            key="admin_review_note",
        )
        if st.button("Registrar decisão administrativa"):
            try:
                review = build_civic_report_review(
                    report_id=selected_report.id,
                    admin_user_id=active_profile.id,
                    decision=decision_label_map[decision_label],
                    note=review_note,
                )
                append_civic_report_review(reviews_path, review)
                st.success("Decisão administrativa registrada.")
            except Exception as exc:
                _render_user_error(st, exc, context="admin_report_review")

    st.markdown('<div class="ecoscan-section-title">Arquivos de gestão</div>', unsafe_allow_html=True)
    st.write(f"Perfis: `{profiles_path_from_config(config)}`")
    st.write(f"Campanha: `{campaign_path_from_config(config)}`")
    st.write(f"Pontuação: `{ledger_path}`")
    st.write(f"Denúncias: `{reports_path}`")
    st.write(f"Revisões: `{reviews_path}`")


def _input_signature(uploaded_file: Any, source_kind: str, options: ProcessingPipelineOptions) -> str:
    data = uploaded_file.getvalue()
    payload = {
        "source_kind": source_kind,
        "name": uploaded_file.name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "options": {
            "filter_name": options.filter_name,
            "filter_parameters": options.filter_parameters or {},
            "segmentation_name": options.segmentation_name,
            "segmentation_parameters": options.segmentation_parameters or {},
        },
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def _temporary_upload(uploaded_file: Any, prefix: str = "upload") -> Path:
    suffix = Path(uploaded_file.name or "upload.png").suffix or ".png"
    with tempfile.NamedTemporaryFile(delete=False, prefix=f"ecoscan_{prefix}_", suffix=suffix) as temp_file:
        temp_file.write(uploaded_file.getbuffer())
        return Path(temp_file.name)


def main() -> None:
    import streamlit as st

    config = load_config()
    configure_logging(config.directories["logs"])
    guidance_by_class = _load_guidance_map(config)
    targets_by_class = _load_disposal_target_map(config)
    impacts_by_class = _load_environmental_impact_map(config)
    requirements_by_class = _load_photo_requirement_map(config)
    collection_points = _load_collection_point_list(config)
    campaign = _load_campaign_config(config)
    profiles = _load_user_profile_list(config)
    st.set_page_config(page_title="EcoScan", layout="wide", initial_sidebar_state="collapsed")
    _render_theme(st)

    filter_name = "auto"
    filter_parameters: dict[str, Any] = {}
    segmentation_name = "auto"
    segmentation_parameters: dict[str, Any] = {}
    save_history = False

    active_profile = render_identity(st)
    with st.sidebar:
        st.header("Identificação")
        _render_active_profile_card(st, active_profile)

        if active_profile.is_admin:
            st.header("Operação da Secretaria")
            _render_model_status(st, config)

            st.header("Parâmetros técnicos")
            filter_name = st.selectbox(
                "Filtro",
                ["auto", "none", "gaussian", "median", "clahe", "sobel", "canny", "bilateral"],
                index=0,
            )
            filter_parameters = _select_filter_parameters(st, filter_name)

            segmentation_name = st.selectbox(
                "Segmentação",
                ["auto", "none", "otsu", "hsv_color", "grabcut"],
                index=0,
            )
            segmentation_parameters = _select_segmentation_parameters(st, segmentation_name)
            save_history = st.checkbox("Salvar no histórico local", value=False)
        else:
            st.header("Atendimento")
            st.caption("O modo público usa processamento automático para manter a experiência simples.")
            with st.expander("Opções avançadas"):
                filter_name = st.selectbox(
                    "Filtro",
                    ["auto", "none", "gaussian", "median", "clahe", "sobel", "canny", "bilateral"],
                    index=0,
                    key="public_filter",
                )
                filter_parameters = _select_filter_parameters(st, filter_name)
                segmentation_name = st.selectbox(
                    "Segmentação",
                    ["auto", "none", "otsu", "hsv_color", "grabcut"],
                    index=0,
                    key="public_segmentation",
                )
                segmentation_parameters = _select_segmentation_parameters(st, segmentation_name)
                save_history = st.checkbox("Salvar no histórico local", value=False, key="public_history")

    if not active_profile.is_admin:
        _render_public_app_chrome(st)

    if active_profile.is_admin:
        _render_institutional_hero(st, config, active_profile, campaign)
    else:
        from ecoscan.ui.citizen_design import render_citizen_design
        render_citizen_design(st, _asset_data_uri(config.project_root, "assets/disposal_targets/plastic_red_bin.png"))
    st.caption("EcoScan · piloto independente de educação ambiental. Não é um canal oficial de atendimento municipal.")
    if active_profile.is_admin:
        render_scope(st)
        _render_overview_strip(st, config)

    class_chips = "".join(_class_chip(class_id, guidance_by_class) for class_id in config.classes)

    pipeline_options = ProcessingPipelineOptions(
        filter_name=filter_name,
        filter_parameters=filter_parameters,
        segmentation_name=segmentation_name,
        segmentation_parameters=segmentation_parameters,
    )

    if active_profile.is_admin:
        analysis_tab = "Análise"
        campaign_tab = "Campanha"
        report_tab = "Denúncia"
        collection_tab = "Pontos de coleta"
        account_tab = "Conta"
        tab_names = [
            analysis_tab,
            "Gestão",
            "Conclusão",
            campaign_tab,
            report_tab,
            collection_tab,
            account_tab,
            "Processamento",
            "Base de imagens",
            "Histórico",
            "Sistema",
        ]
    else:
        analysis_tab = "Escanear"
        campaign_tab = "Missões"
        report_tab = "Denunciar"
        collection_tab = "Mapa"
        account_tab = "Perfil"
        tab_names = [
            analysis_tab,
            collection_tab,
            "Descarte",
            campaign_tab,
            report_tab,
            account_tab,
        ]
    tabs = dict(zip(tab_names, st.tabs(tab_names)))
    result = st.session_state.get("last_analysis_result")

    if "Descarte" in tabs:
        with tabs["Descarte"]:
            st.subheader("Descarte responsável")
            render_scope(st)

    with tabs[analysis_tab]:
        section_title = "Escanear resíduo" if not active_profile.is_admin else "Analisar resíduo"
        st.markdown(f'<div class="ecoscan-section-title">{section_title}</div>', unsafe_allow_html=True)
        if not active_profile.is_admin:
            with st.expander("Preparar uma boa foto"):
                _render_capture_tips(st)
        source_options = ["Câmera", "Imagem"] if active_profile.is_admin else ["Tirar foto", "Enviar foto"]
        source = st.radio("Entrada", source_options, horizontal=True)
        source_kind = "camera" if source in {"Câmera", "Tirar foto"} else "upload"
        if source in {"Imagem", "Enviar foto"}:
            upload_label = "Selecionar imagem do resíduo" if active_profile.is_admin else "Enviar foto do resíduo"
            uploaded_file = st.file_uploader(upload_label, type=["jpg", "jpeg", "png"])
            waiting_message = "Aguardando imagem."
        else:
            if active_profile.is_admin:
                _render_live_camera_link(st)
                uploaded_file = st.camera_input("Ligar câmera e capturar resíduo", key="camera_capture")
                waiting_message = "Aguardando captura da câmera."
            else:
                st.caption(
                    "No celular, escolha Câmera ou Galeria no seletor do aparelho. "
                    "A disponibilidade da câmera depende do navegador."
                )
                uploaded_file = st.file_uploader(
                    "Tirar ou enviar foto do resíduo",
                    type=["jpg", "jpeg", "png"],
                    key="mobile_camera_upload",
                )
                waiting_message = "Tire ou envie uma foto do resíduo para analisar."

        if uploaded_file is None:
            st.info(waiting_message)
        else:
            signature = _input_signature(uploaded_file, source_kind, pipeline_options)
            if st.session_state.get("last_analysis_signature") != signature:
                for stale_key in ("last_analysis_result", "last_analysis_signature", "last_analysis_source"):
                    st.session_state.pop(stale_key, None)
                temp_path = None
                try:
                    temp_path = _temporary_upload(uploaded_file, prefix=source_kind)
                    with st.spinner("Detectando resíduo na captura..." if source_kind == "camera" else "Detectando resíduo na imagem..."):
                        result = analyze_waste_image(
                            temp_path,
                            config,
                            options=pipeline_options,
                        )
                    st.session_state["last_analysis_result"] = result
                    st.session_state["last_analysis_signature"] = signature
                    st.session_state["last_analysis_source"] = source_kind
                except Exception as exc:
                    result = None
                    _render_user_error(st, exc, context="image_analysis")
                finally:
                    if temp_path is not None:
                        temp_path.unlink(missing_ok=True)
            else:
                result = st.session_state.get("last_analysis_result")

            if result is not None:
                should_save_history = bool(config.history.get("enabled", True)) or save_history
                if should_save_history and st.session_state.get("last_history_saved_signature") != signature:
                    append_history_entry(
                        history_path_from_config(config),
                        build_history_entry(result, source_path=st.session_state.get("last_analysis_source")),
                    )
                    st.session_state["last_history_saved_signature"] = signature

                safety_decision = build_recognition_safety_decision(
                    result,
                    action_confidence_threshold=max(0.72, float(config.confidence_threshold)),
                )
                target = _target_for_guidance(result.guidance, targets_by_class)
                impact = _impact_for_guidance(result.guidance, impacts_by_class)
                if not active_profile.is_admin:
                    public_action = build_public_next_action(result, target, safety_decision)
                    _render_public_next_action(st, public_action)

                left, right = st.columns([1.05, 1])
                with left:
                    st.image(result.pipeline.loaded.array, caption="Imagem analisada", width="stretch")
                with right:
                    st.markdown('<div class="ecoscan-result">', unsafe_allow_html=True)
                    _render_recognition_decision(st, safety_decision)
                    if result.accepted and result.guidance and safety_decision.allow_disposal_guidance:
                        st.subheader("Sugestão: " + result.guidance.display_name)
                        st.metric("Pontuação do modelo", _format_percent(result.probability))
                        st.caption("A pontuação não é uma garantia de acerto. Confirme o material e o conteúdo antes de descartar.")
                        st.write(f"**Categoria ambiental:** {result.guidance.environmental_category}")
                        st.write(result.guidance.guidance)
                        if getattr(result, "reliability", None) and not result.reliability.is_sufficient:
                            st.warning(result.reliability.message)
                        st.caption(result.guidance.educational_note)
                    else:
                        st.subheader("Não identificado com segurança")
                        st.metric("Maior pontuação", _format_percent(result.probability))
                        st.write("Tente outra foto com melhor iluminação, fundo simples e objeto centralizado.")
                        st.caption(f"Classe mais próxima: {result.top_class}")
                    st.markdown('<div class="ecoscan-soft-divider"></div>', unsafe_allow_html=True)
                    if active_profile.is_admin:
                        st.caption(f"Filtro aplicado: {result.pipeline.filter_result.name}")
                        st.caption(result.pipeline.element_analysis.warning)
                        _render_quality_snapshot(st, result.pipeline)
                    _render_capture_quality_advice(st, result.pipeline)
                    if active_profile.is_admin:
                        _render_photo_processing_summary(st, result.pipeline)
                    else:
                        with st.expander("Como a imagem foi tratada"):
                            _render_photo_processing_summary(st, result.pipeline)
                    st.markdown("</div>", unsafe_allow_html=True)
                    if active_profile.is_admin:
                        _render_probability_bars(st, result, guidance_by_class)
                    else:
                        with st.expander("Ver confiança por classe"):
                            _render_probability_bars(st, result, guidance_by_class)

                    if active_profile.is_admin and st.button("Exportar evidência técnica"):
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        output_dir = config.directories["reports"] / "ui_exports" / timestamp
                        try:
                            save_pipeline_artifacts(result.pipeline, output_dir)
                            st.success(f"Evidência salva em {output_dir}")
                        except Exception as exc:
                            _render_user_error(st, exc, context="ui_export")

                if active_profile.is_admin:
                    _render_processing_evidence(st, result, active_profile)
                else:
                    with st.expander("Ver evidência técnica da imagem"):
                        _render_processing_evidence(
                            st,
                            result,
                            active_profile,
                            render_details_expander=False,
                        )
                _render_recognition_feedback_form(st, config, result, active_profile, guidance_by_class)

                if safety_decision.allow_disposal_guidance and result.guidance:
                    if active_profile.is_admin:
                        _render_disposal_action_panel(
                            st,
                            config,
                            result.guidance,
                            target,
                            impact,
                            collection_points,
                        )
                    else:
                        with st.expander("Ver preparo, impacto e pontos de coleta"):
                            _render_disposal_action_panel(
                                st,
                                config,
                                result.guidance,
                                target,
                                impact,
                                collection_points,
                            )

    with tabs[campaign_tab]:
        _render_campaign_tab(
            st,
            config,
            campaign,
            active_profile,
            guidance_by_class,
            impacts_by_class,
            targets_by_class,
            pipeline_options,
        )

    with tabs[report_tab]:
        _render_civic_reports_tab(st, config, active_profile, pipeline_options)

    with tabs[collection_tab]:
        _render_collection_points_tab(st, config, guidance_by_class, collection_points)

    if "Processamento" in tabs:
        with tabs["Processamento"]:
            if result is None:
                st.info("Aguardando análise.")
            else:
                cols = st.columns(3)
                cols[0].image(result.pipeline.preprocessing.resized, caption="Redimensionada", width="stretch")
                cols[1].image(result.pipeline.filter_result.image, caption=f"Filtro: {result.pipeline.filter_result.name}", width="stretch")
                cols[2].image(result.pipeline.segmentation_result.mask, caption=f"Máscara: {result.pipeline.segmentation_result.name}", width="stretch")
                cols = st.columns(3)
                cols[0].image(result.pipeline.segmentation_result.image, caption="Segmentada", width="stretch")
                cols[1].image(result.pipeline.detection_heatmap, caption="Mapa de detecção", width="stretch")
                cols[2].image(result.pipeline.model_input_preview, caption="Entrada do modelo", width="stretch")
                st.markdown('<div class="ecoscan-section-title">Qualidade da captura</div>', unsafe_allow_html=True)
                _render_capture_quality_advice(st, result.pipeline)
                st.markdown('<div class="ecoscan-section-title">Decisão de filtragem</div>', unsafe_allow_html=True)
                _render_filter_decision(st, result.pipeline)
                st.markdown('<div class="ecoscan-section-title">Decisão de segmentação</div>', unsafe_allow_html=True)
                _render_segmentation_decision(st, result.pipeline)
                st.markdown('<div class="ecoscan-section-title">Elementos visuais segmentados</div>', unsafe_allow_html=True)
                cols = st.columns([0.95, 1.05])
                cols[0].image(result.pipeline.element_overlay, caption="Componentes detectados na máscara", width="stretch")
                with cols[1]:
                    _render_element_diagnostics(st, result.pipeline)
                st.markdown('<div class="ecoscan-section-title">Métricas de qualidade da imagem</div>', unsafe_allow_html=True)
                _render_pipeline_diagnostics(st, result.pipeline)
                st.markdown('<div class="ecoscan-section-title">Metadados técnicos</div>', unsafe_allow_html=True)
                st.json(result.pipeline.metadata)

    if "Base de imagens" in tabs:
        with tabs["Base de imagens"]:
            st.markdown('<div class="ecoscan-section-title">Adicionar fotos à base</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="ecoscan-note">As fotos entram primeiro na base bruta por classe. '
                "Antes do treino final, elas devem passar por revisão, curadoria e divisão de treino/validação/teste.</div>",
                unsafe_allow_html=True,
            )
            upload_col, context_col = st.columns([1.1, 0.9])
            with upload_col:
                target_class = st.selectbox(
                    "Classe de destino",
                    config.classes,
                    format_func=lambda class_id: _class_label(class_id, guidance_by_class),
                )
                dataset_uploads = st.file_uploader(
                    "Selecionar fotos",
                    type=[extension.lstrip(".") for extension in sorted(config.allowed_extensions)],
                    accept_multiple_files=True,
                    key="dataset_uploads",
                )
                source_note = st.text_input("Origem do lote", placeholder="ex.: fotos do grupo - setembro")
                save_disabled = not dataset_uploads
                if save_disabled:
                    st.caption("Selecione uma ou mais fotos para liberar o envio para a base bruta.")
                if st.button("Salvar na base bruta", disabled=save_disabled):
                    incoming = [
                        IncomingImage(
                            name=uploaded.name,
                            data=uploaded.getvalue(),
                            source_note=source_note or "streamlit-upload",
                        )
                        for uploaded in dataset_uploads
                    ]
                    try:
                        results = ingest_uploaded_images(config, target_class, incoming)
                        st.session_state["dataset_ingestion_results"] = [result.__dict__ for result in results]
                        saved_count = sum(1 for result in results if result.status == "saved")
                        st.success(f"{saved_count} imagem(ns) adicionada(s) à base bruta.")
                    except Exception as exc:
                        _render_user_error(st, exc, context="dataset_ingestion")
            with context_col:
                st.markdown('<div class="ecoscan-section-title">Classes ativas</div>', unsafe_allow_html=True)
                st.markdown(
                    f'<div class="ecoscan-chip-row">{class_chips}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(f"Registro de uploads: {ingestion_manifest_path_from_config(config)}")
                st.markdown('<div class="ecoscan-section-title">Plano de coleta</div>', unsafe_allow_html=True)
                _render_photo_requirement_plan(st, requirements_by_class.get(target_class))

            _render_ingestion_results(st, st.session_state.get("dataset_ingestion_results", []))
            st.markdown('<div class="ecoscan-section-title">Prontidão para treino</div>', unsafe_allow_html=True)
            _render_dataset_readiness(st, config)
            st.markdown('<div class="ecoscan-section-title">Resumo da base de imagens</div>', unsafe_allow_html=True)
            _render_dataset_status(st, config, guidance_by_class)

    if "Histórico" in tabs:
        with tabs["Histórico"]:
            _render_history(st, config)

    with tabs[account_tab]:
        _render_account_tab(st, config, active_profile, campaign, guidance_by_class)

    if active_profile.is_admin:
        with tabs["Gestão"]:
            _render_admin_tab(
                st,
                config,
                active_profile,
                profiles,
                campaign,
                collection_points,
                guidance_by_class,
            )

    if "Conclusão" in tabs:
        with tabs["Conclusão"]:
            st.markdown('<div class="ecoscan-section-title">Conclusão e prontidão final</div>', unsafe_allow_html=True)
            _render_completion_panel(st, config)
            _render_model_governance(st, config, guidance_by_class)

    if "Sistema" in tabs:
        with tabs["Sistema"]:
            st.markdown('<div class="ecoscan-section-title">Acesso e rodada de testes</div>', unsafe_allow_html=True)
            _render_access_testing_panel(st)
            st.markdown('<div class="ecoscan-section-title">Hospedagem gratuita HTTPS</div>', unsafe_allow_html=True)
            _render_free_hosting_panel(st, config)
            st.markdown('<div class="ecoscan-section-title">Auditoria técnica</div>', unsafe_allow_html=True)
            _render_aps_audit(st, config)
            st.markdown('<div class="ecoscan-section-title">Relatório técnico</div>', unsafe_allow_html=True)
            if st.button("Gerar relatório consolidado"):
                try:
                    report_path = write_academic_report(config)
                    st.success(f"Relatório gerado em {report_path}")
                except Exception as exc:
                    _render_user_error(st, exc, context="academic_report")
            st.markdown('<div class="ecoscan-section-title">Validação do sistema</div>', unsafe_allow_html=True)
            _render_acceptance_checks(st, config)
            st.markdown('<div class="ecoscan-section-title">Mensagens de erro do sistema</div>', unsafe_allow_html=True)
            _render_error_catalog(st)
            st.markdown('<div class="ecoscan-section-title">Pacote técnico</div>', unsafe_allow_html=True)
            _render_delivery_pack(st, config)
            st.markdown('<div class="ecoscan-section-title">Ambiente local</div>', unsafe_allow_html=True)
            _render_dependencies(st)
            if result is not None:
                st.markdown('<div class="ecoscan-section-title">Última análise</div>', unsafe_allow_html=True)
                st.json(result.probabilities)


if __name__ == "__main__":
    main()

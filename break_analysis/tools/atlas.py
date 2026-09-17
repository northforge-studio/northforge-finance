from uuid import UUID
from pydantic import BaseModel

from registry.models import GLSegmentType

from break_analysis.services.atlas import AtlasResolutionEvidence, AtlasEvidenceService
from break_analysis.services.recon import ReconBreakRecordResolver


class InvestigateAtlasResolutionInput(BaseModel):
    workflow_run_id: UUID
    recon_result_id: UUID
    segment_type: GLSegmentType


class AtlasTools:
    def __init__(
        self,
        recon_resolver: ReconBreakRecordResolver,
        atlas_evidence_service: AtlasEvidenceService,
    ):
        self._recon = recon_resolver
        self._atlas = atlas_evidence_service


    def investigate_resolution(
        self,
        workflow_run_id: UUID,
        recon_result_id: UUID,
        segment_type: GLSegmentType,
    ) -> AtlasResolutionEvidence:
        break_record = self._recon.get_break_record(
            workflow_run_id=workflow_run_id,
            recon_result_id=recon_result_id,
        )

        return self._atlas.investigate_resolution(
            break_record=break_record,
            segment_type=segment_type,
        )
